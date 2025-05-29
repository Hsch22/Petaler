import sys
import time
import math
import random
import inspect
import types
from datetime import datetime, timedelta

# 新增导入
import asyncio
import geocoder
import python_weather

from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import interval, date, cron

from PyQt5.QtCore import Qt, QTimer, QObject, QPoint
from PyQt5.QtGui import QImage, QPixmap, QIcon, QCursor
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from typing import List, Optional

from Petal.utils import *
from Petal.conf import *

from Petal.settings import Settings


class Animation_worker(QObject):
    """
    动画处理工作线程类。
    负责根据宠物配置随机播放动画，并在独立的线程中运行。
    通过信号与主线程（通常是UI线程）通信以更新图像和位置。
    """

    # --- 信号定义 ---
    sig_setimg_anim = pyqtSignal(name='sig_setimg_anim')  # 请求设置新图像的信号
    sig_move_anim = pyqtSignal(
        float, float, name='sig_move_anim'
    )  # 请求移动宠物的信号 (dx, dy)
    sig_repaint_anim = pyqtSignal(name='sig_repaint_anim')  # 请求重绘的信号

    def __init__(self, pet_conf: PetConfig, parent: Optional[QObject] = None, settings : Settings = None) -> None:
        """
        初始化动画工作线程。
        """
        super(Animation_worker, self).__init__(parent)
        self.pet_conf: PetConfig = pet_conf
        self.is_killed: bool = False  # 线程是否被标记为终止
        self.is_paused: bool = False  # 线程是否被标记为暂停
        self.settings: Settings = settings

    def run(self) -> None:
        """
        线程主循环。
        持续运行，直到 is_killed 被设置为 True。
        循环执行随机动作，处理暂停状态，并按配置的刷新率休眠。
        """
        print(f'开始运行宠物 {self.pet_conf.petname} 的动画线程')
        while not self.is_killed:
            # 执行一个随机选择的动作序列
            self.random_act()

            # 检查是否需要暂停或已终止
            if self._check_pause_kill():
                break  # 如果在暂停期间被终止，则退出循环

            # 如果没有被终止，则按配置的间隔休眠
            if not self.is_killed:
                time.sleep(self.pet_conf.refresh)

        print(f'宠物 {self.pet_conf.petname} 的动画线程已停止')

    def kill(self) -> None:
        """标记线程为终止状态，并确保其不处于暂停状态。"""
        self.is_paused = False  # 确保解除暂停状态，以便线程能检查 is_killed
        self.is_killed = True

    def pause(self) -> None:
        """标记线程为暂停状态。"""
        self.is_paused = True

    def resume(self) -> None:
        """解除线程的暂停状态。"""
        self.is_paused = False

    def _check_pause_kill(self) -> bool:
        """
        私有辅助方法：检查并处理暂停状态。
        如果线程被暂停，则循环等待直到恢复或被终止。
        """
        while self.is_paused:
            if self.is_killed:  # 在暂停期间也检查终止标记
                return True
            time.sleep(0.2)  # 暂停时短暂休眠，避免CPU空转
        return self.is_killed  # 返回当前的终止状态

    def random_act(self) -> None:
        """
        随机选择并执行一个动作序列。
        根据 pet_conf 中定义的动作概率分布来选择动作。
        """

        # 根据概率分布选择动作索引
        prob_num = random.uniform(0, 1)
        # 计算累积概率，找到第一个大于 prob_num 的区间的索引
        act_index = sum(
            int(prob_num > self.pet_conf.act_prob[i])
            for i in range(len(self.pet_conf.act_prob))
        )

        # 获取选中的动作序列 (可能包含一个或多个动作 Act)
        acts: List[Act] = self.pet_conf.random_act[act_index]

        # 执行选中的动作序列
        self._run_acts(acts)

    def _run_acts(self, acts: List[Act]) -> None:
        """
        按顺序执行一个动作序列中的所有单个动作 (Act)。
        """
        for act in acts:
            if self.is_killed:  # 在每个动作开始前检查终止状态
                break
            self._run_act(act)

    def _run_act(self, act: Act) -> None:
        """
        执行单个动作 (Act) 的动画。
        循环播放该动作的所有帧图像，并在每帧之间处理移动、暂停和休眠。
        """
        # 一个动作可能重复执行多次 (act.act_num)
        for _ in range(act.act_num):
            if self._check_pause_kill():
                return  # 检查暂停/终止，如果终止则直接返回

            # 遍历动作中的每一帧图像
            for img in act.images:
                if self._check_pause_kill():
                    return  # 检查暂停/终止，如果终止则直接返回

                # --- 更新图像 ---
                # 注意：直接修改全局 settings 模块中的图像变量
                self.settings.previous_img = self.settings.current_img
                self.settings.current_img = img
                self.sig_setimg_anim.emit()  # 发送信号，请求UI更新图像

                # --- 帧间延迟 ---
                time.sleep(act.frame_refresh)

                self._move(act)  # 总是尝试根据动作信息移动

                # --- 请求重绘 ---
                self.sig_repaint_anim.emit()  # 发送信号，请求UI重绘

    def _static_act(self, pos: QPoint) -> None:
        """
        静态动作的位置判断。 - 目前舍弃不用
        用于确保宠物停留在屏幕边界内。
        """
        # 获取主屏幕的几何信息
        screen = QApplication.primaryScreen()
        if not screen:
            print("错误：无法获取主屏幕信息。")
            return
        screen_geo = screen.geometry()
        screen_width = screen_geo.width()
        screen_height = screen_geo.height()

        # 使用配置中的尺寸作为边界判断依据
        border_x = self.pet_conf.size[0]
        border_y = self.pet_conf.size[1]

        new_x = pos.x()
        new_y = pos.y()

        # 简单的边界碰撞检查
        if pos.x() < border_x:
            new_x = screen_width - border_x
        elif pos.x() > screen_width - border_x:
            new_x = border_x

        if pos.y() < border_y:
            new_y = screen_height - border_y
        elif pos.y() > screen_height - border_y:
            new_y = border_y

        # 如果位置需要调整，则发送移动信号
        if new_x != pos.x() or new_y != pos.y():
            # 计算相对移动量
            dx = new_x - pos.x()
            dy = new_y - pos.y()
            self.sig_move_anim.emit(float(dx), float(dy))

    def _move(self, act: Act) -> None:
        """
        根据动作信息计算位移量，并发出移动信号。
        """
        plus_x: float = 0.0
        plus_y: float = 0.0
        direction = act.direction  # 获取动作定义的方向

        if direction:  # 仅当方向有效时才计算位移
            move_amount = float(act.frame_move)  # 每帧的移动量
            if direction == 'right':
                plus_x = move_amount
            elif direction == 'left':
                plus_x = -move_amount
            elif direction == 'up':
                plus_y = -move_amount
            elif direction == 'down':
                plus_y = move_amount
        # 仅当有实际位移时才发出信号（可选优化）
        if plus_x != 0.0 or plus_y != 0.0:
            self.sig_move_anim.emit(plus_x, plus_y)  # 发送移动信号 (dx, dy)


import math

# 导入 PyQt5 相关模块
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap

# 导入自定义的设置和动作类 (假定存在)
# from Pet import settings, QAction # QAction 可能与 PyQt5.QtWidgets.QAction 冲突，需确认其来源
# 假设 settings 是一个可全局访问的配置/状态对象
# 假设 QAction 是一个描述宠物动作的自定义类

# --- 全局变量/状态 (假设存在于 settings 模块) ---
# settings.current_act: 当前动作对象
# settings.previous_act: 上一个动作对象
# settings.playid: 当前动作帧的播放索引
# settings.current_img: 当前显示的图像 (QPixmap)
# settings.previous_img: 上一个显示的图像 (QPixmap)
# settings.act_id: 在一个动画序列中，当前执行到第几个动作 (Action) 的索引
# settings.draging: 标志位，表示是否正在被鼠标拖拽 (1 表示是, 0 表示否)
# settings.onfloor: 标志位，表示宠物是否在地面上 (1 表示是, 0 表示否)
# settings.set_fall: 标志位，表示是否启用了掉落行为 (1 表示启用, 0 表示禁用)
# settings.fall_right: 标志位，表示掉落时图像是否需要水平镜像
# settings.dragspeedx: x 轴拖拽/掉落速度
# settings.dragspeedy: y 轴拖拽/掉落速度


class Interaction_worker(QObject):
    """
    处理宠物交互逻辑的工作类。
    通常在单独的线程中运行，通过信号与主界面通信。
    """

    # --- 信号定义 ---
    sig_setimg_inter = pyqtSignal(name='sig_setimg_inter')
    sig_move_inter = pyqtSignal(float, float, name='sig_move_inter')
    sig_act_finished = pyqtSignal()

    def __init__(self, pet_conf, parent=None, settings : Settings = None):
        """
        初始化 Interaction_worker。
        """
        super(Interaction_worker, self).__init__(parent)

        self.pet_conf = pet_conf
        self.is_killed = False
        self.is_paused = False
        self.interact = None
        # 注意: 每次将 act_name 设为 None 时，应重置 settings.playid 为 0
        self.act_name = None

        # 创建定时器，用于周期性地执行 run 方法
        self.timer = QTimer()
        # 连接定时器的 timeout 信号到 run 方法
        self.timer.timeout.connect(self.run)
        # 启动定时器，间隔时间由宠物配置中的 interact_speed 决定 (毫秒)
        self.timer.start(int(self.pet_conf.interact_speed))
        self.settings = settings

    def run(self):
        """
        定时器触发时执行的核心方法。
        根据 self.interact 的值调用相应的处理函数。
        """
        # 如果当前没有指定交互方法，则直接返回
        if self.interact is None:
            return
        # 如果指定的交互方法名不是当前对象的有效方法名，则清空交互方法名并返回
        elif self.interact not in dir(self):
            self.interact = None
        # 否则，获取并执行对应的交互方法
        else:
            # 使用 getattr 获取名称为 self.interact 的方法，并传入 self.act_name 作为参数执行
            getattr(self, self.interact)(self.act_name)

    def start_interact(self, interact, act_name=None):
        """
        设置当前要执行的交互及其关联的动作名称。
        """
        # 设置当前交互方法名
        self.interact = interact
        # 设置当前动作名
        self.act_name = act_name

    def kill(self):
        """
        停止工作线程的活动并准备退出。
        """
        # 清除暂停状态
        self.is_paused = False
        # 设置终止标志
        self.is_killed = True
        # 停止定时器
        self.timer.stop()

    def pause(self):
        """
        暂停工作线程的活动。
        """
        # 设置暂停标志
        self.is_paused = True
        # 停止定时器，阻止 run 方法被调用
        self.timer.stop()

    def resume(self):
        """
        恢复工作线程的活动 (如果之前被暂停)。
        注意：此方法仅清除暂停标志，需要外部逻辑或修改来重新启动定时器。
        当前代码下，调用 resume 后，需要再次调用 self.timer.start() 才能恢复 run 的执行。
        """
        # 清除暂停标志
        self.is_paused = False

    def img_from_act(self, act):
        """
        根据给定的动作(act)对象，计算并设置当前应该显示的图像帧。
        处理动画帧的重复播放逻辑，并更新全局状态 (settings)。
        """

        # 如果当前动作发生变化
        if self.settings.current_act != act:
            # 将之前的当前动作存为上一个动作
            self.settings.previous_act = self.settings.current_act
            # 更新当前动作
            self.settings.current_act = act
            # 重置当前动作的播放帧索引
            self.settings.playid = 0

        # 计算每张图片需要重复显示的次数 (基于动作帧刷新率和 InteractionWorker 的更新速度)
        # math.ceil 确保至少重复一次
        n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
        # 创建一个扩展的图像列表，其中每个图像根据 n_repeat 重复，整个序列根据 act.act_num 重复
        img_list_expand = [
            item for item in act.images for i in range(n_repeat)
        ] * act.act_num
        # 从扩展列表中获取当前 playid 对应的图像
        img = img_list_expand[self.settings.playid]

        # 播放索引加 1
        self.settings.playid += 1
        # 如果播放索引超出了扩展列表的长度，则重置为 0，实现循环播放
        if self.settings.playid >= len(img_list_expand):
            self.settings.playid = 0

        # 更新上一帧图像
        self.settings.previous_img = self.settings.current_img
        # 更新当前帧图像
        self.settings.current_img = img

    def animat(self, act_name):
        """
        执行一个指定的动画序列。
        动画序列由 pet_conf.random_act 中的多个动作(act)对象组成。
        """
        # 在宠物配置的随机动作名称列表中找到 act_name 的索引
        acts_index = self.pet_conf.random_act_name.index(act_name)
        # 获取对应的动画序列 (一个包含多个动作对象的列表)
        acts = self.pet_conf.random_act[acts_index]

        # 检查当前动作序列的索引 (settings.act_id) 是否已超出序列长度
        if self.settings.act_id >= len(acts):
            # 如果动画序列播放完毕，重置动作序列索引
            self.settings.act_id = 0
            # 清除当前交互方法名，停止 animat 的后续调用
            self.interact = None
            # 发出动作完成信号
            self.sig_act_finished.emit()
        else:
            # 获取当前要执行的动作对象
            act = acts[self.settings.act_id]
            # 计算当前动作需要执行的总帧数 (考虑图像重复和动作次数)
            n_repeat = math.ceil(
                act.frame_refresh / (self.pet_conf.interact_speed / 1000)
            )
            n_repeat *= len(act.images) * act.act_num

            # 计算并设置当前帧图像
            self.img_from_act(act)

            if self.settings.playid >= n_repeat - 1:
                # 增加动作序列索引，准备执行下一个动作
                self.settings.act_id += 1

            # 如果计算出的当前图像与上一帧不同，则需要更新显示和移动
            if self.settings.previous_img != self.settings.current_img:
                # 发出设置图像信号
                self.sig_setimg_inter.emit()
                # 根据当前动作的定义进行移动
                self._move(act)

    def mousedrag(self, act_name):
        """
        处理鼠标拖拽交互逻辑。
        根据是否启用掉落、是否在地面上、是否正在拖拽，执行不同的行为。
        """
        # 情况 1: 掉落行为被禁用 (settings.set_fall == 0)
        if not self.settings.set_fall:
            # 如果正在拖拽 (settings.draging == 1)
            if self.settings.draging == 1:
                # 获取拖拽动画对应的动作对象
                acts = self.pet_conf.drag
                # 计算并设置拖拽动画的当前帧图像
                self.img_from_act(acts)
                # 如果图像有变化，发出更新图像信号
                if self.settings.previous_img != self.settings.current_img:
                    self.sig_setimg_inter.emit()
            # 如果停止拖拽
            else:
                # 清除动作名
                self.act_name = None
                # 重置播放帧索引
                self.settings.playid = 0

        # 情况 2: 掉落行为已启用 (settings.set_fall == 1) 且宠物不在地面上 (settings.onfloor == 0)
        elif self.settings.set_fall == 1 and self.settings.onfloor == 0:
            # 如果正在拖拽 (settings.draging == 1)
            if self.settings.draging == 1:
                # 获取拖拽动画对应的动作对象
                acts = self.pet_conf.drag
                # 计算并设置拖拽动画的当前帧图像
                self.img_from_act(acts)
                # 如果图像有变化，发出更新图像信号
                if self.settings.previous_img != self.settings.current_img:
                    self.sig_setimg_inter.emit()
            # 如果停止拖拽 (settings.draging == 0)，则开始掉落
            elif self.settings.draging == 0:
                # 获取掉落动画对应的动作对象
                acts = self.pet_conf.fall
                # 计算并设置掉落动画的当前帧图像
                self.img_from_act(acts)

                # 如果需要向右镜像掉落图像
                if self.settings.fall_right:
                    # 保存原始图像引用
                    previous_img_state = self.settings.current_img
                    # 水平镜像当前图像
                    self.settings.current_img = self.settings.current_img.mirrored(True, False)

                # 如果图像（或其镜像状态）有变化，发出更新图像信号
                if self.settings.previous_img != self.settings.current_img:
                    self.sig_setimg_inter.emit()

                # 执行掉落位移计算
                self.drop()

        # 情况 3: 掉落启用但在地面上，或者其他未覆盖的情况
        else:
            # 清除动作名
            self.act_name = None
            # 重置播放帧索引
            self.settings.playid = 0

    def drop(self):
        """
        计算并发出掉落过程中的位移信号。
        模拟重力和速度衰减（线性阻力 F=-kv），但速度低于阈值时只加重力。
        """

        # 获取当前的垂直速度作为本次的 y 轴位移增量
        plus_y = self.settings.dragspeedy
        # 获取当前的水平速度作为本次的 x 轴位移增量
        plus_x = self.settings.dragspeedx

        # 只有速度大于阈值时才施加阻力
        if abs(self.settings.dragspeedx) > self.settings.drag_speed_threshold:
            self.settings.dragspeedx *= 1 - self.settings.drag_base_friction
        if abs(self.settings.dragspeedy) > self.settings.drag_speed_threshold:
            self.settings.dragspeedy *= 1 - self.settings.drag_base_friction
        # 更新垂直速度，模拟重力加速度
        self.settings.dragspeedy = self.settings.dragspeedy + self.pet_conf.gravity

        # 发出移动信号，请求主界面根据计算出的位移移动宠物
        self.sig_move_inter.emit(plus_x, plus_y)

    def _move(self, act) -> None:
        """
        根据动作(act)对象中定义的方和移动量，计算并发出移动信号。
        """

        # 初始化 x, y 轴位移量
        plus_x = 0.0
        plus_y = 0.0
        # 获取动作定义的方向
        direction = act.direction

        # 如果动作没有定义方向，则不移动
        if direction is None:
            pass
        # 根据方向字符串设置相应的位移量
        else:
            if direction == 'right':
                plus_x = act.frame_move
            elif direction == 'left':
                plus_x = -act.frame_move
            elif direction == 'up':
                plus_y = -act.frame_move
            elif direction == 'down':
                plus_y = act.frame_move

        # 发出移动信号，请求主界面移动宠物
        self.sig_move_inter.emit(plus_x, plus_y)


class Scheduler_worker(QObject):
    """
    调度器工作类，用于管理定时任务，如状态变化、番茄钟、专注模式和提醒事项。
    通常在单独的线程中运行，通过信号与主界面或其他组件通信。
    """

    # --- 信号定义 ---
    # 请求设置显示的对话文本 (文本内容)
    sig_settext_sche = pyqtSignal(str, name='sig_settext_sche')
    # 请求设置宠物的动作 (动作名称)
    sig_setact_sche = pyqtSignal(str, name='sig_setact_sche')
    # 请求设置宠物的状态值 (状态名称, 变化量)
    sig_setstat_sche = pyqtSignal(str, int, name='sig_setstat_sche')
    # 通知专注模式已结束
    sig_focus_end = pyqtSignal(name='sig_focus_end')
    # 通知番茄钟（系列）已结束或需要用户交互（如处理冲突）
    sig_tomato_end = pyqtSignal(name='sig_tomato_end')
    # 请求设置时间显示 (时间类型标识, 剩余时间/数值)
    sig_settime_sche = pyqtSignal(str, int, name='sig_settime_sche')

    # _get_city_from_gaode 方法将被完全删除
    # (下面的空行代表原方法位置，将被删除)

    # 新增异步获取天气信息的方法
    async def _get_weather_string(self):
        city_for_weather = None
        try:
            # --- 恢复使用 geocoder IP 定位代码 ---
            print("正在尝试通过 geocoder.ip('me') 获取地理位置...")
            g = geocoder.ip('me')
            if g.ok and g.city:
                print(f"Geocoder 定位城市: {g.city}")
                city_for_weather = g.city
            else:
                print("Geocoder IP定位失败或未返回城市信息。")
            # --- geocoder 逻辑结束 ---

            if city_for_weather:
                print(f"最终用于查询天气的城市: {city_for_weather}")
                async with python_weather.Client(unit=python_weather.METRIC) as client:
                    weather = await client.get(city_for_weather)
                    return f"当前城市：{city_for_weather}，天气：{weather.description}，温度：{weather.temperature}°C"
            else:
                return "未能获取到有效城市信息，无法查询天气。"

        except AttributeError as e:
            # 处理属性可能仍然缺失或名称不同的情况
            print(f"获取天气属性时出错: {e}. 尝试访问 forecasts[0] ...")
            try:
                # 备选方案: 尝试从第一个预报条目获取当前状况
                # 这里假设 'weather' 可能是一个带有 'forecasts' 列表的 Forecast 对象
                # 或者主 weather 对象有一个 'forecasts' 属性。
                if hasattr(weather, 'forecasts') and weather.forecasts:
                    first_forecast = weather.forecasts[0]
                    # 现在，尝试从 first_forecast 或其 hourly 子预报中获取温度和描述
                    current_temp = first_forecast.temperature
                    current_desc = (
                        first_forecast.description
                    )  # 或从 hourly[0].description 获取

                    # 如果 first_forecast 本身没有直接的 temp/desc，检查其 hourly 预报
                    if (
                        not hasattr(first_forecast, 'temperature')
                        and hasattr(first_forecast, 'hourly')
                        and first_forecast.hourly
                    ):
                        current_temp = first_forecast.hourly[0].temperature
                        current_desc = first_forecast.hourly[0].description

                    return f"当前城市：{city_for_weather}，天气：{current_desc}，温度：{current_temp}°C"
                else:
                    return f"获取天气信息失败: 无法从预报数据中提取当前天气 ({e})"
            except Exception as fallback_e:
                return f"获取天气信息失败 (备选方案尝试失败): {fallback_e}"
        except Exception as e:
            print(
                f"获取天气信息时发生错误: 城市='{city_for_weather}', 类型={type(e)}, 错误详情={repr(e)}"
            )
            return f"获取天气信息失败: 类型={type(e)}, 错误={repr(e)}"

    def __init__(self, pet_conf, parent=None, settings : Settings = None):
        """
        初始化 Scheduler_worker。
        """
        super(Scheduler_worker, self).__init__(parent)
        # 保存宠物配置对象的引用
        self.pet_conf = pet_conf

        self.is_killed = False
        self.is_paused = False

        self.new_task = False
        self.task_name = None
        self.n_tomato = None

        self.n_tomato_now = None
        self.focus_on = False
        self.tomato_list = []

        self.focus_time = 0
        self.tomato_timeleft = 0

        self.scheduler = QtScheduler()
        self.scheduler.add_job(
            self.change_hp, interval.IntervalTrigger(minutes=self.pet_conf.hp_interval)
        )
        self.scheduler.add_job(
            self.change_em, interval.IntervalTrigger(minutes=self.pet_conf.em_interval)
        )
        self.scheduler.start()

        self.settings = settings

    def run(self):
        """
        工作线程的入口点。
        修改为：先显示基本问候，然后获取并显示天气信息。
        """
        now_time = datetime.now().hour

        # 1. 准备并显示基本问候语
        base_greeting_text = ""
        '''if 6 <= now_time <= 10:
            base_greeting_text = '早上好!'
        elif 11 <= now_time <= 12:
            base_greeting_text = '中午好!'
        elif 13 <= now_time <= 17:
            base_greeting_text = '下午好！'
        else:
            base_greeting_text = '晚上好!'
        '''
        greeting_options = [
            "早上好，新的一天开始了！☀️",
            "早上好，愿你今天充满活力！💪",
            "早上好，希望你今天过得愉快！😊",
            "中午好，祝你午餐愉快！🍽️",
            "中午好，希望你有个轻松的午休！💤",
            "下午好，加油完成今天的工作！💪",
            "下午好，希望你精神满满！🚀",
            "晚上好，祝你有个美好的夜晚！🌟",
            "晚上好，放松一下吧！😌"
        ]
        if 6 <= now_time <= 10:
            filtered_greetings= [g for g in greeting_options if g.startswith("早上好")]
        elif 11 <= now_time <= 12:
            filtered_greetings= [g for g in greeting_options if g.startswith("中午好")]
        elif 13 <= now_time <= 17:
            filtered_greetings= [g for g in greeting_options if g.startswith("下午好")]
        else:
            filtered_greetings= [g for g in greeting_options if g.startswith("晚上好")]
        # 从筛选后的问候语中随机选择一个
        base_greeting_text= random.choice(filtered_greetings)

        print(f"[Petal Log] 显示快速问候: {base_greeting_text}")
        self.show_dialogue([base_greeting_text])  # 显示此部分，应较快出现

        # 2. 获取天气信息 (此部分可能耗时较长)
        print("[Petal Log] 开始获取天气信息...")
        # _get_weather_string 返回完整的用户可见字符串，例如 "当前城市：北京，天气：晴，温度：20°C" 或错误/状态信息
        weather_info_string = asyncio.run(self._get_weather_string())
        print(f"[Petal Log] 获取到的天气信息字符串: {weather_info_string}")

        # 3. 显示天气信息作为单独的对话
        #    (除非天气信息获取失败导致返回的是提示信息，否则才显示)
        if (
            weather_info_string
            and not weather_info_string.startswith("未能获取到有效城市信息")
            and not weather_info_string.startswith("获取天气信息失败")
            and not weather_info_string.startswith("高德API")
            and not weather_info_string.startswith("Geocoder IP定位失败")
        ):
            self.show_dialogue([weather_info_string])
        else:
            # 如果获取天气失败，可以考虑显示一个通用提示，或者不显示任何额外内容
            # 当前 _get_weather_string 已经会返回如 "未能获取到有效城市信息..." 的字符串，show_dialogue 会显示它
            # 所以这里可能不需要额外处理失败情况的显示，除非想改变失败时的提示方式
            # 为了避免重复显示错误，如果已经是错误信息，就不再调用 show_dialogue
            # 但由于 show_dialogue 内部有延迟，而且 _get_weather_string 已经返回了用户可见的错误信息，
            # 也许直接显示 weather_info_string 就好，让用户知道获取失败了。
            # 重新考虑：总是显示 _get_weather_string 的结果，因为它包含了成功或失败的信息。
            self.show_dialogue([weather_info_string])

    def kill(self):
        """
        停止工作线程的活动并关闭调度器。
        """
        # 清除暂停状态
        self.is_paused = False
        # 设置终止标志
        self.is_killed = True
        # 安全关闭调度器，停止所有任务
        self.scheduler.shutdown()

    def pause(self):
        """
        暂停调度器的活动。
        """
        # 设置暂停标志
        self.is_paused = True
        # 暂停调度器，任务将不会在暂停期间触发
        self.scheduler.pause()

    def resume(self):
        """
        恢复调度器的活动。
        """
        # 清除暂停标志
        self.is_paused = False
        # 恢复调度器，任务将按计划继续执行
        self.scheduler.resume()

    def greeting(self, time):
        """
        根据给定的小时数返回相应的问候语。
        """
        base_greeting = ''
        '''if 0 <= time <= 10:
            base_greeting = '早上好!'
        elif 11 <= time <= 12:
            base_greeting = '中午好!'
        elif 13 <= time <= 17:
            base_greeting = '下午好！'
        elif 18 <= time <= 24:
            base_greeting = '晚上好!'
        else:
            base_greeting = '你好!'  # 默认问候语，以防时间无效或未覆盖的情况'''
        greeting_options = [
            "早上好，新的一天开始了！☀️",
            "早上好，愿你今天充满活力！💪",
            "早上好，希望你今天过得愉快！😊",
            "中午好，祝你午餐愉快！🍽️",
            "中午好，希望你有个轻松的午休！💤",
            "下午好，加油完成今天的工作！💪",
            "下午好，希望你精神满满！🚀",
            "晚上好，祝你有个美好的夜晚！🌟",
            "晚上好，放松一下吧！😌"
        ]
        if 6 <= time <= 10:
            filtered_greetings = [g for g in greeting_options if g.startswith("早上好")]
        elif 11 <= time <= 12:
            filtered_greetings = [g for g in greeting_options if g.startswith("中午好")]
        elif 13 <= time <= 17:
            filtered_greetings = [g for g in greeting_options if g.startswith("下午好")]
        else:
            filtered_greetings = [g for g in greeting_options if g.startswith("晚上好")]
        # 从筛选后的问候语中随机选择一个
        base_greeting_text = random.choice(filtered_greetings)

        weather_info = asyncio.run(self._get_weather_string())
        return f"{base_greeting} {weather_info}"

    def show_dialogue(self, texts_toshow=[]):
        """
        依次显示一系列对话文本。
        使用全局标志位 `settings.showing_dialogue_now` 实现简单的排队机制，
        避免同时显示多个对话框造成混乱。
        """
        # 等待：如果当前已有对话框在显示，则循环等待
        while self.settings.showing_dialogue_now:
            time.sleep(1)  # 等待1秒再检查
        # 标记：设置全局标志，表示现在开始显示对话框
        self.settings.showing_dialogue_now = True

        # 遍历要显示的文本列表
        for text_toshow in texts_toshow:
            # 发出信号，请求主界面显示当前文本
            self.sig_settext_sche.emit(text_toshow)
            # 等待：让文本显示一段时间 (固定3秒)
            time.sleep(3)

        # 完成：所有文本显示完毕后，发出信号请求清除文本显示
        self.sig_settext_sche.emit('None')  # 'None' 作为清除文本的约定信号
        # 标记：清除全局标志，允许其他对话请求
        self.settings.showing_dialogue_now = False

    def add_tomato(self, n_tomato=None):
        """
        添加番茄钟任务。
        根据当前状态（是否已有专注/番茄任务）安排一系列定时任务。
        """
        # 条件1：当前没有专注任务 (focus_on is False) 且没有正在进行的番茄钟 (n_tomato_now is None)
        if self.focus_on == False and self.n_tomato_now is None:
            # 记录本次要进行的番茄钟总数
            self.n_tomato_now = n_tomato
            # 初始化时间累加器 (用于计算后续任务的触发时间)
            time_plus = 0  # 单位：分钟

            # --- 安排第一个番茄钟 ---
            # 1.1 安排 "开始第一个番茄钟" 的任务 (立即执行)
            task_text = 'tomato_first'  # 任务标识
            time_torun = datetime.now() + timedelta(seconds=1)  # 设定为1秒后执行
            # 添加一次性任务到调度器，使用 DateTrigger
            self.scheduler.add_job(
                self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text]
            )

            # 累加第一个番茄钟的工作时间 (25分钟)
            time_plus += 25

            # 1.2 安排 "第一个番茄钟结束" 的任务
            # 判断这是不是最后一个番茄钟
            if n_tomato == 1:
                task_text = 'tomato_last'  # 最后一个番茄钟结束的标识
            else:
                task_text = 'tomato_end'  # 非最后一个番茄钟结束的标识 (进入休息)
            # 计算触发时间 = 当前时间 + 累加的时间
            time_torun = datetime.now() + timedelta(minutes=time_plus)
            # 添加任务，并赋予 ID 以便后续可能取消
            job_id = 'tomato_0_end'
            self.scheduler.add_job(
                self.run_tomato,
                date.DateTrigger(run_date=time_torun),
                args=[task_text],
                id=job_id,
            )
            # 将任务ID存入列表，用于取消操作
            self.tomato_list.append(job_id)
            # 累加第一个番茄钟后的休息时间 (5分钟)
            time_plus += 5

            # --- 安排后续的番茄钟 (如果 n_tomato > 1) ---
            if n_tomato > 1:
                # 循环处理第 2 个到第 n_tomato 个番茄钟
                for i in range(1, n_tomato):
                    # 2.1 安排 "开始第 i+1 个番茄钟" 的任务
                    task_text = 'tomato_start'  # 后续番茄钟开始的标识
                    time_torun = datetime.now() + timedelta(minutes=time_plus)
                    job_id_start = 'tomato_%s_start' % i
                    self.scheduler.add_job(
                        self.run_tomato,
                        date.DateTrigger(run_date=time_torun),
                        args=[task_text],
                        id=job_id_start,
                    )
                    # 累加工作时间
                    time_plus += 25

                    # 2.2 安排 "第 i+1 个番茄钟结束" 的任务
                    # 判断是不是最后一个
                    if i == (n_tomato - 1):
                        task_text = 'tomato_last'  # 最后一个结束
                    else:
                        task_text = 'tomato_end'  # 非最后一个结束 (进入休息)
                    time_torun = datetime.now() + timedelta(minutes=time_plus)
                    job_id_end = 'tomato_%s_end' % i
                    self.scheduler.add_job(
                        self.run_tomato,
                        date.DateTrigger(run_date=time_torun),
                        args=[task_text],
                        id=job_id_end,
                    )
                    # 累加休息时间
                    time_plus += 5
                    # 将开始和结束任务的 ID 都存入列表
                    self.tomato_list.append(job_id_start)
                    self.tomato_list.append(job_id_end)

        # 条件2：如果当前正在进行专注模式
        elif self.focus_on:
            # 安排一个立即执行的任务，提示用户冲突
            task_text = "focus_on"  # 标识：因专注模式冲突
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(
                self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text]
            )
        # 条件3：如果已有番茄钟在进行中 (n_tomato_now is not None)
        else:
            # 安排一个立即执行的任务，提示用户冲突
            task_text = "tomato_exist"  # 标识：因已有番茄钟冲突
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(
                self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text]
            )

    def run_tomato(self, task_text):
        """
        执行由 add_tomato 安排的番茄钟相关任务。
        根据传入的 task_text 执行不同操作 (开始工作/休息、结束、处理冲突等)。
        """
        # 初始化要显示的文本
        text_toshow = 'None'  # 默认不显示文本

        # --- 根据 task_text 执行不同逻辑 ---
        if task_text == 'tomato_start':
            # 开始一个新的番茄工作时段 (非第一个)
            self.tomato_timeleft = 25  # 设置工作时间为25分钟
            # 添加/替换 'tomato_timer' 任务，每分钟调用 change_tomato 更新剩余时间
            self.scheduler.add_job(
                self.change_tomato,
                interval.IntervalTrigger(minutes=1),
                id='tomato_timer',
                replace_existing=True,
            )
            # 发送信号更新UI显示：开始工作，显示剩余时间
            self.sig_settime_sche.emit('tomato_start', self.tomato_timeleft)
            # 从任务ID列表中移除当前已执行的 'start' 任务ID (假定按顺序执行)
            self.tomato_list = self.tomato_list[1:]
            # 设置提示文本
            tomato_start_options = [
                "新的番茄时钟开始了哦！加油！🍅",
                "番茄时钟开始啦！专注起来吧！🍅",
                "新的番茄时钟开始，祝你高效完成任务！🍅",
                "番茄时钟启动，专注就是力量！💪🍅",
                "新的番茄时钟开始啦，一起努力吧！🚀🍅"
            ]

            # 随机选择一个番茄时钟提示文本
            text_tomato= random.choice(tomato_start_options)

        elif task_text == 'tomato_first':
            # 开始第一个番茄工作时段
            self.tomato_timeleft = 25  # 设置工作时间为25分钟
            # 添加/替换 'tomato_timer'，每分钟更新剩余时间
            self.scheduler.add_job(
                self.change_tomato,
                interval.IntervalTrigger(minutes=1),
                id='tomato_timer',
                replace_existing=True,
            )
            # 发送信号更新UI显示：开始工作，显示剩余时间
            self.sig_settime_sche.emit('tomato_start', self.tomato_timeleft)
            # 设置提示文本，包含总番茄数
            tomato_total_options = [
                "%s个番茄时钟设定完毕！开始了哦！🍅",
                "准备好了吗？%s个番茄时钟即将开始！🚀🍅",
                "一共%s个番茄时钟，加油完成它们！💪🍅",
                "新的挑战来了！%s个番茄时钟等你完成！🌟🍅",
                "%s个番茄时钟，祝你高效！🍅"
            ]
            # 随机选择一个总番茄数提示文本
            text_toshow = random.choice(tomato_total_options) % int(self.n_tomato_now)


        elif task_text == 'tomato_end':
            # 一个番茄工作时段结束，开始休息 (非最后一个)
            self.tomato_timeleft = 5  # 设置休息时间为5分钟
            # 添加/替换 'tomato_timer'，每分钟更新剩余休息时间
            self.scheduler.add_job(
                self.change_tomato,
                interval.IntervalTrigger(minutes=1),
                id='tomato_timer',
                replace_existing=True,
            )
            # 发送信号更新UI显示：开始休息，显示剩余时间
            self.sig_settime_sche.emit('tomato_rest', self.tomato_timeleft)
            # 从任务ID列表中移除当前已执行的 'end' 任务ID
            self.tomato_list = self.tomato_list[1:]
            # 设置提示文本
            tomato_end_options= [
                "叮叮~ 番茄时间到啦！休息5分钟！☕️",
                "番茄时间结束啦！放松一下，休息5分钟吧！🌿",
                "完成了一个番茄时钟！现在休息5分钟哦！🎉",
                "番茄时间结束！去喝杯水，休息5分钟吧！💧",
                "番茄时间到啦！休息5分钟，然后继续加油哦！💪"
            ]
            # 随机选择一个番茄时间结束提示文本
            text_toshow = random.choice(tomato_end_options)

        elif task_text == 'tomato_last':
            # 最后一个番茄工作时段结束
            try:
                # 尝试移除用于更新时间的 'tomato_timer' 任务
                self.scheduler.remove_job('tomato_timer')
            except Exception:  # 更具体的异常类型如 JobLookupError 会更好
                # 如果任务不存在 (可能已结束或从未添加)，则忽略错误
                pass
            # 重置状态变量
            self.tomato_timeleft = 0
            self.n_tomato_now = None  # 清除当前番茄钟系列标记
            self.tomato_list = []  # 清空任务ID列表
            # 发送信号通知UI番茄钟系列结束
            self.sig_tomato_end.emit()
            # 发送信号更新UI时间显示：结束状态
            self.sig_settime_sche.emit('tomato_end', self.tomato_timeleft)
            # 设置提示文本
            tomato_all_end_options = [
                "叮叮~ 番茄时间全部结束啦！🎉",
                "番茄时间全部完成！干得漂亮！👏",
                "所有番茄任务都完成了！现在好好放松一下吧！🌿",
                "番茄时间结束啦！今天辛苦了！去享受你的休息时间吧！☕️",
                "全部番茄时钟完成！祝你接下来的时间愉快！🌟"
            ]

            # 随机选择一个番茄时间全部结束的提示文本
            text_toshow = random.choice(tomato_all_end_options)

        elif task_text == 'tomato_exist':
            # 尝试添加番茄钟时，发现已有番茄钟在进行
            # 发送结束信号，让UI知道添加操作未成功
            self.sig_tomato_end.emit()
            # 设置提示文本
            tomato_in_progress_options = [
                "不行！还有番茄钟在进行哦~ 🍅",
                "等等，番茄时钟还没结束呢！继续加油！💪",
                "别着急，还有正在进行的番茄任务哦！🚀",
                "番茄时钟还在进行中，坚持一下！🌟",
                "别忘了，还有番茄钟没完成呢！一起努力哦！🎉"
            ]
            # 随机选择一个“还有番茄钟在进行”的提示文本
            text_toshow= random.choice(tomato_in_progress_options)

        elif task_text == 'focus_on':
            # 尝试添加番茄钟时，发现有专注任务在进行
            # 发送结束信号，让UI知道添加操作未成功
            self.sig_tomato_end.emit()
            # 设置提示文本
            tomato_in_progress_options = [
                "不行！还有专注任务在进行哦~ 🚀",
                "专注任务还没结束呢！再坚持一下！💪",
                "别分心哦，专注任务还在进行中！🌟",
                "任务还没完成呢！继续加油吧！🎉",
                "别忘了，还有专注任务没完成哦！一起努力！🌿"
            ]
            # 随机选择一个“还有专注任务在进行”的提示文本
            text_toshow= random.choice(tomato_in_progress_options)

        elif task_text == 'tomato_cancel':
            # 执行取消番茄钟的操作
            # 重置状态变量
            self.n_tomato_now = None
            # 遍历并移除所有计划中的番茄钟任务 (start 和 end)
            for job_id in self.tomato_list:
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    pass  # 忽略移除不存在任务的错误
            self.tomato_list = []  # 清空任务ID列表
            try:
                # 尝试移除时间更新器 'tomato_timer'
                self.scheduler.remove_job('tomato_timer')
            except Exception:
                pass
            # 重置时间并更新UI
            self.tomato_timeleft = 0
            self.sig_settime_sche.emit('tomato_end', self.tomato_timeleft)
            # 设置提示文本
            tomato_cancel_options = [
                "你的番茄时钟取消啦！👋",
                "番茄时钟已取消，下次再加油哦！🌟",
                "番茄时钟取消了，休息一下吧！🌿",
                "任务取消啦！随时可以重新开始哦！🎉",
                "番茄时钟已取消，祝你接下来的时间愉快！🌈"
            ]
            # 随机选择一个“番茄时钟取消”的提示文本
            text_toshow= random.choice(tomato_cancel_options)

        # 如果有文本需要显示，则调用 show_dialogue
        if text_toshow != 'None':
            self.show_dialogue([text_toshow])

    def cancel_tomato(self):
        """
        安排一个立即执行的任务来取消当前正在进行的番茄钟系列。
        实际的取消逻辑在 run_tomato 方法中处理 'tomato_cancel' 任务时执行。
        """
        task_text = "tomato_cancel"  # 设置任务标识为取消
        # 安排一个1秒后执行的任务，触发 run_tomato 处理取消逻辑
        time_torun_cancel = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(
            self.run_tomato,
            date.DateTrigger(run_date=time_torun_cancel),
            args=[task_text],
        )

    def change_hp(self):
        """
        由调度器定时调用，发出信号减少 HP 值。
        """
        # 发送信号，请求状态管理器将 'hp' 减少 1
        self.sig_setstat_sche.emit('hp', -1)

    def change_em(self):
        """
        由调度器定时调用，发出信号减少 EM (情绪/能量等) 值。
        """
        # 发送信号，请求状态管理器将 'em' 减少 1
        self.sig_setstat_sche.emit('em', -1)

    def change_tomato(self):
        """
        由调度器 ('tomato_timer' job) 定时调用，更新番茄钟/休息的剩余时间。
        """
        # 剩余时间减 1 分钟
        self.tomato_timeleft -= 1
        # 如果剩余时间小于等于1分钟 (意味着下一次触发时就结束了)
        if self.tomato_timeleft < 1:  # 使用 < 1 更安全，避免等于0时重复移除
            try:
                # 移除自身这个定时器任务 'tomato_timer'
                self.scheduler.remove_job('tomato_timer')
            except Exception:  # JobLookupError
                pass  # 忽略错误
        # 发送信号更新UI的时间显示 (类型为'tomato'，表示进行中)
        self.sig_settime_sche.emit('tomato', self.tomato_timeleft)

    def change_focus(self):
        """
        由调度器 ('focus_timer' job) 定时调用，更新专注模式的剩余时间。
        """
        # 剩余时间减 1 分钟
        self.focus_time -= 1
        # 如果剩余时间小于等于1分钟
        if self.focus_time < 1:
            try:
                # 移除自身这个定时器任务 'focus_timer'
                self.scheduler.remove_job('focus_timer')
            except Exception:
                pass  # 忽略错误
        # 发送信号更新UI的时间显示 (类型为'focus'，表示进行中)
        self.sig_settime_sche.emit('focus', self.focus_time)

    def add_focus(self, time_range=None, time_point=None):
        """
        添加专注模式任务。
        可以按持续时间 (time_range) 或结束时间点 (time_point) 设置。
        会检查是否与现有番茄钟或专注任务冲突。
        """
        # --- 冲突检查 ---
        # 1. 检查是否已有番茄钟在进行
        if self.n_tomato_now is not None:
            # 安排立即执行的任务提示冲突
            task_text = "tomato_exist"
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(
                self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text]
            )
            return  # 冲突，直接返回

        # 2. 检查是否已有专注任务在进行
        elif self.focus_on:
            # 安排立即执行的任务提示冲突
            task_text = "focus_exist"
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(
                self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text]
            )
            return  # 冲突，直接返回

        # --- 添加专注任务 ---
        # 模式一：按持续时间设置 (time_range)
        elif time_range is not None:
            # 检查总时间是否大于0
            if sum(time_range) <= 0:
                return  # 时间为0或负数，不添加任务

            # 设置专注模式状态
            self.focus_on = True
            # 计算总分钟数
            self.focus_time = int(time_range[0] * 60 + time_range[1])

            # 安排 "开始专注" 任务 (立即执行)
            task_text_start = "focus_start"
            time_torun_start = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(
                self.run_focus,
                date.DateTrigger(run_date=time_torun_start),
                args=[task_text_start],
            )

            # 安排 "结束专注" 任务 (在指定时间后)
            task_text_end = "focus_end"
            time_torun_end = datetime.now() + timedelta(
                hours=time_range[0], minutes=time_range[1]
            )
            # 添加任务，并设置ID 'focus' 以便取消
            self.scheduler.add_job(
                self.run_focus,
                date.DateTrigger(run_date=time_torun_end),
                args=[task_text_end],
                id='focus',
            )

        # 模式二：按结束时间点设置 (time_point)
        elif time_point is not None:
            now = datetime.now()
            # 构建目标结束时间的 datetime 对象 (同年同月同日)
            target_time = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=time_point[0],
                minute=time_point[1],
                second=now.second,
            )
            # 计算时间差
            time_diff = target_time - now
            # 计算总剩余分钟数 (向下取整)
            self.focus_time = time_diff.total_seconds() // 60

            # 情况A: 目标时间已过 (设定的是过去的时间点，或跨天)
            if time_diff <= timedelta(0):
                # 假设用户意图是明天的这个时间点，将目标时间加一天
                target_time = target_time + timedelta(days=1)
                # 重新计算剩余分钟数
                self.focus_time += 24 * 60  # 加上一天的分钟数

                # 设置专注状态
                self.focus_on = True
                # 安排 "开始专注(明天)" 任务 (立即执行提示)
                task_text_start = "focus_start_tomorrow"
                time_torun_start = datetime.now() + timedelta(seconds=1)
                self.scheduler.add_job(
                    self.run_focus,
                    date.DateTrigger(run_date=time_torun_start),
                    args=[task_text_start],
                )

                # 安排 "结束专注" 任务 (在明天的指定时间点)
                task_text_end = "focus_end"
                self.scheduler.add_job(
                    self.run_focus,
                    date.DateTrigger(run_date=target_time),
                    args=[task_text_end],
                    id='focus',
                )
            # 情况B: 目标时间在未来 (当天)
            else:
                # 设置专注状态
                self.focus_on = True
                # 安排 "开始专注" 任务 (立即执行)
                task_text_start = "focus_start"
                time_torun_start = datetime.now() + timedelta(seconds=1)
                self.scheduler.add_job(
                    self.run_focus,
                    date.DateTrigger(run_date=time_torun_start),
                    args=[task_text_start],
                )

                # 安排 "结束专注" 任务 (在指定的未来时间点)
                task_text_end = "focus_end"
                self.scheduler.add_job(
                    self.run_focus,
                    date.DateTrigger(run_date=target_time),
                    args=[task_text_end],
                    id='focus',
                )

    def run_focus(self, task_text):
        """
        执行由 add_focus 安排的专注模式相关任务。
        根据传入的 task_text 执行不同操作 (开始、结束、处理冲突、取消等)。
        """
        # 初始化要显示的对话文本列表 (因为可能有多个对话)
        texts_toshow = ['None']  # 默认不显示

        # --- 根据 task_text 执行不同逻辑 ---
        if task_text == 'tomato_exist':
            # 尝试添加专注时，发现有番茄钟冲突
            self.sig_focus_end.emit()  # 发送结束信号，通知UI添加失败
            #texts_toshow = ['不行！还有番茄钟在进行哦~']
            focuss_toshow = [
                "不行！还有番茄钟在进行哦~ 🍅",
                "番茄钟还没结束呢，再坚持一下！💪",
                "别着急，番茄任务还没完成哦！🌟",
                "番茄钟还在进行中，别分心哦！🌿",
                "等等，番茄任务还没结束呢！🚀"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(focuss_toshow)]
        elif task_text == 'focus_exist':
            # 尝试添加专注时，发现已有专注任务冲突
            self.sig_focus_end.emit()  # 发送结束信号，通知UI添加失败
            #texts_toshow = ["不行！还有专注任务在进行哦~"]
            focuss_toshow = [
                "不行！还有专注任务在进行哦~ 🚀",
                "专注任务还没结束呢！再坚持一下！💪",
                "别分心哦，专注任务还在进行中！🌟",
                "任务还没完成呢！继续加油吧！🎉",
                "别忘了，还有专注任务没完成哦！一起努力！🌿"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(focuss_toshow)]
        elif task_text == 'focus_start':
            # 开始专注任务 (当天或按时长)
            # 如果专注时间大于1分钟，启动分钟计时器
            if self.focus_time > 0:  # 检查大于0即可
                self.scheduler.add_job(
                    self.change_focus,
                    interval.IntervalTrigger(minutes=1),
                    id='focus_timer',
                    replace_existing=True,
                )
            # 发送信号更新UI：开始专注，显示总时间
            self.sig_settime_sche.emit('focus_start', self.focus_time)
            #texts_toshow = ["你的专注任务开始啦！"]
            focuss_toshow = [
                "你的专注任务开始啦！🚀",
                "专注时间到！开始你的任务吧！💪",
                "新的专注任务启动！加油哦！🌟",
                "专注任务开始，祝你高效完成！🌿",
                "开始专注啦！别让任何事情打扰你哦！🎉"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(focuss_toshow)]
        elif task_text == 'focus_start_tomorrow':
            # 开始专注任务 (设定在明天)
            # 如果专注时间大于1分钟，启动分钟计时器
            if self.focus_time > 0:
                self.scheduler.add_job(
                    self.change_focus,
                    interval.IntervalTrigger(minutes=1),
                    id='focus_timer',
                    replace_existing=True,
                )
            # 发送信号更新UI：开始专注，显示总时间
            self.sig_settime_sche.emit('focus_start', self.focus_time)
            # 显示两条提示信息
            #texts_toshow = ["专注任务开始啦！", "但设定在明天，请确认无误哦~"]
            focuss_toshow = [
                ["专注任务开始啦！🚀", "但设定在明天，请确认无误哦~ 📅"],
                ["专注时间到！🚀", "任务设定在明天，确认一下吧！🔍"],
                ["新的专注任务启动！🌟", "注意，任务时间是明天哦！📅"],
                ["开始专注啦！🎉", "任务设定在明天，请检查一下！👀"],
                ["专注任务准备就绪！🌿", "任务时间是明天，确认一下设置吧！📝"]
            ]
            # 随机选择一组提示文本
            texts_toshow = random.choice(focuss_toshow)
        elif task_text == 'focus_end':
            # 专注任务结束
            self.focus_time = 0  # 重置剩余时间
            try:
                # 尝试移除分钟计时器
                self.scheduler.remove_job('focus_timer')
            except Exception:
                pass  # 忽略错误
            # 发送信号更新UI：专注结束
            self.sig_settime_sche.emit('focus_end', self.focus_time)
            # 清除专注状态标志
            self.focus_on = False
            # 发送专注结束信号，通知相关组件
            self.sig_focus_end.emit()
            #texts_toshow = ["你的专注任务结束啦！"]
            focuss_toshow = [
                "你的专注任务结束啦！🎉",
                "专注任务完成！干得漂亮！👏",
                "任务结束啦！希望你收获满满！🌟",
                "专注时间结束，好好放松一下吧！🌿",
                "任务完成！祝你接下来的时间愉快！🌈"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(focuss_toshow)]
        elif task_text == 'focus_cancel':
            # 执行取消专注任务的操作
            self.focus_time = 0  # 重置剩余时间
            try:
                # 尝试移除分钟计时器
                self.scheduler.remove_job('focus_timer')
            except Exception:
                pass  # 忽略错误
            # 发送信号更新UI：专注结束 (取消也是一种结束)
            self.sig_settime_sche.emit('focus_end', self.focus_time)
            # 清除专注状态标志
            self.focus_on = False
            #texts_toshow = ["你的专注任务取消啦！"]
            focuss_toshow = [
                "你的专注任务取消啦！👋",
                "专注任务已取消，下次再加油哦！🌟",
                "任务取消啦！随时可以重新开始哦！🎉",
                "专注任务已取消，祝你接下来的时间愉快！🌈",
                "任务取消了，休息一下吧！🌿"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(focuss_toshow)]
        # 显示需要展示的对话文本
        if texts_toshow != ['None']:
            self.show_dialogue(texts_toshow)

    def cancel_focus(self):
        """
        取消当前正在进行的专注任务。
        首先移除计划中的结束任务，然后安排一个立即执行的任务来处理状态清理和提示。
        """
        try:
            # 尝试移除ID为 'focus' 的结束任务
            self.scheduler.remove_job('focus')
        except Exception:
            pass  # 忽略错误，可能任务已执行或不存在

        # 安排一个立即执行的任务来运行取消逻辑
        task_text = "focus_cancel"
        time_torun_cancel = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(
            self.run_focus,
            date.DateTrigger(run_date=time_torun_cancel),
            args=[task_text],
        )

    def add_remind(self, texts, time_range=None, time_point=None, repeat=False):
        """
        添加提醒事项。
        可以按相对时间 (time_range) 或绝对时间点 (time_point) 设置，
        支持一次性或重复提醒。
        """
        # 模式一：按绝对时间点 (time_point) 设置
        if time_point is not None:
            # 子模式 A: 重复提醒
            if repeat:
                certain_hour = int(time_point[0])  # 获取小时
                certain_minute = int(time_point[1])  # 获取分钟
                self.scheduler.add_job(
                    self.run_remind,
                    cron.CronTrigger(hour=certain_hour, minute=certain_minute),
                    args=[texts],
                )  # 参数是提醒文本
            # 子模式 B: 一次性提醒
            else:
                now = datetime.now()
                certain_hour = int(time_point[0])
                certain_minute = int(time_point[1])
                # 确定提醒的日期

                # 1. 计算今天的目标时间点 (时、分、秒、微秒替换为目标值)
                target_datetime = now.replace(
                    hour=certain_hour, minute=certain_minute, second=0, microsecond=0
                )

                # 2. 如果计算出的目标时间点在当前时间之前或就是当前时间，
                #    说明用户意图是明天的这个时间，将目标日期增加一天。
                if target_datetime <= now:
                    target_datetime += timedelta(days=1)

                # 3. 使用 DateTrigger 和计算好的完整日期时间对象来安排一次性任务，
                #    这样可以正确处理跨月和跨年的情况。
                self.scheduler.add_job(
                    self.run_remind,
                    date.DateTrigger(run_date=target_datetime),
                    args=[texts],
                )

        # 模式二：按相对时间 (time_range) 设置
        elif time_range is not None:
            # 子模式 A: 重复提醒
            if repeat:
                total_interval_minutes = int(time_range[0]) * 60 + int(
                    time_range[1]
                )  # 计算总间隔分钟数
                if total_interval_minutes <= 0:
                    return  # 间隔需大于0
                # 使用 IntervalTrigger 实现周期性提醒
                self.scheduler.add_job(
                    self.run_remind,
                    interval.IntervalTrigger(minutes=total_interval_minutes),
                    args=[texts],
                )  # 参数是提醒文本
            # 子模式 B: 一次性提醒
            else:
                # 检查总时间是否大于0
                if sum(time_range) <= 0:
                    return  # 时间为0或负数，不添加
                # 计算未来的触发时间点
                time_torun = datetime.now() + timedelta(
                    hours=time_range[0], minutes=time_range[1]
                )
                # 使用 DateTrigger 添加一次性任务
                self.scheduler.add_job(
                    self.run_remind, date.DateTrigger(run_date=time_torun), args=[texts]
                )  # 参数是提醒文本

        # --- 添加 "提醒设置完成" 的即时提示 ---
        # 无论哪种模式，都安排一个立即执行的任务来提示用户设置成功
        time_torun_confirm = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(
            self.run_remind,
            date.DateTrigger(run_date=time_torun_confirm),
            args=['remind_start'],
        )  # 特殊参数标识设置成功

    def run_remind(self, task_text):
        """
        执行由 add_remind 安排的提醒任务。
        区分是设置成功的提示还是实际的提醒内容。
        """
        # 情况1：是设置成功的即时提示
        if task_text == 'remind_start':
            #texts_toshow = ["提醒事项设定完成！"]
            reminds_toshow = [
                "提醒事项设定完成！🎉",
                "提醒事项已设定好啦！🚀",
                "提醒事项设置成功！随时准备提醒你哦！🔔",
                "提醒事项已设定，放心吧！🌟",
                "提醒事项设置完成，祝你不再错过重要时刻！📅"
            ]
            # 随机选择一个提示文本
            texts_toshow = [random.choice(reminds_toshow)]
        # 情况2：是实际的提醒任务触发
        else:
            # 显示固定的前缀和用户设定的提醒文本
            #texts_toshow = ['叮叮~ 时间到啦', '[ %s ]' % task_text]
            time_up_options = [
                "叮叮~ 时间到啦！⏰",
                "时间提醒：任务时间已到！🔔"
            ]
            # 随机选择一个“时间到啦”的提示文本
            time_up_text = random.choice(time_up_options)
            # 组合两条提示信息
            texts_toshow = [time_up_text, "[ %s ]" % task_text]
        # 调用对话显示方法
        self.show_dialogue(texts_toshow)
