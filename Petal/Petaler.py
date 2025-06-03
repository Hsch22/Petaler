# -*- coding: utf-8 -*-
"""
Petal 核心 UI 模块 - Petal.py
"""


import ctypes
import inspect
import math
import random
import sys
import time
import types
from typing import List


from PyQt5.QtCore import QEvent, QObject, QPoint, Qt, QThread, QTimer, pyqtSignal, QRect
from PyQt5.QtGui import QCursor, QFont, QFontDatabase, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import *


from Petal.modules import *
from Petal.utils import *
from Petal.conf import *
from Petal.extra_windows import *

from Petal.settings import Settings

# 修改 screen_scale 的获取方式
if sys.platform == "win32":
    try:
        screen_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
    except (AttributeError, OSError):
        screen_scale = 1.0
        print("警告：无法在Windows上获取屏幕缩放比例，将使用默认值 1.0")
else:
    # 对于非Windows平台 (如 macOS), 初始默认值设为 1.0。
    # Qt的AA_EnableHighDpiScaling会处理实际缩放。
    screen_scale = 1.0
    # 你也可以尝试通过Qt获取:
    # if QApplication.instance(): # 确保app实例已存在
    #     primary_screen = QApplication.primaryScreen()
    #     if primary_screen:
    #         screen_scale = primary_screen.devicePixelRatio()


class PetWidget(QWidget):

    def __init__(
        self, parent: Optional[QWidget] = None, curr_pet_name: str = '', pets: tuple = (), main_window : QMainWindow = None
    ):
        """
        初始化宠物窗口部件。

        Args:
            parent: 可选的父窗口部件。默认为 None。
            curr_pet_name: 初始化时要加载的宠物名称。
                           如果为空字符串，则尝试使用 'pets' 元组中的第一个名称。
            pets: 包含所有可用宠物名称的元组 (例如, ('pet1', 'pet2'))。
        """
        super().__init__(parent, flags=Qt.WindowFlags())

        # --- 安全性检查：确保有宠物可加载 ---
        if not curr_pet_name and not pets:
            raise ValueError(
                "必须提供 'curr_pet_name' 或非空的 'pets' 元组来初始化 PetWidget。"
            )

        # --- 核心数据属性初始化 ---
        self.pets: tuple = pets  # 存储所有可用宠物的名称元组
        self.settings: Settings = Settings()
        self.curr_pet_name = curr_pet_name  # 当前激活的宠物名称 (将在 init_conf 中设置)
        self.pet_conf: PetConfig = (
            PetConfig()
        )  # 宠物配置对象 (将在 init_conf 中加载实际配置)
        self.main_window = main_window

        self.image: Optional[QImage] = None  # 当前用于显示的 QImage 对象
        self.tray: Optional[QSystemTrayIcon]= None  # 系统托盘图标实例

        # --- 窗口交互状态属性 ---
        self.is_follow_mouse: bool = False  # 标志位：窗口当前是否跟随鼠标拖动
        self.mouse_drag_pos: QPoint = self.pos()  # 鼠标按下时相对于窗口左上角的偏移量

        # 获取屏幕尺寸，用于计算窗口边界等
        self.screen_geo: QRect = QDesktopWidget().screenGeometry()  # QRect 对象
        self.screen_width: int = self.screen_geo.width()
        self.screen_height: int = self.screen_geo.height()

        # --- 初始化UI元素和窗口基础设置 ---
        self._init_ui()  # 创建UI元素 (QLabel, QProgressBar 等)
        self._init_widget()  # 设置窗口属性 (无边框, 总在最前, 背景透明等)

        # --- 加载指定的宠物配置 ---
        # 如果未直接指定当前宠物名称，则使用 pets 列表中的第一个
        initial_pet_name_to_load = curr_pet_name if curr_pet_name else pets[0]
        self.init_conf(initial_pet_name_to_load)  # 加载配置、图片字典、宠物数据等

        # --- 显示窗口 ---
        self.show()

        # --- 后台任务管理初始化 ---
        self.threads: dict[str, QThread] = {}  # 用于管理后台任务的线程对象
        self.workers: dict[str, QObject] = {}  # 用于管理后台任务的工作器对象

        # --- 启动核心后台任务 ---
        self.runAnimation()  # 启动动画播放与随机行为线程
        self.runInteraction()  # 启动用户交互（如拖拽）响应线程
        self.runScheduler()  # 启动计划任务（提醒、番茄钟等）线程

        # --- 根据加载的宠物数据配置UI ---
        self._setup_ui(self.pic_dict)  # 设置UI元素尺寸、初始值等

        # super().__init__(parent, flags=Qt.WindowFlags())
        # # --- 安全性检查 ---
        # if not curr_pet_name and not pets:
        #     raise ValueError(
        #         "必须提供 'curr_pet_name' 或非空的 'pets' 元组来初始化 PetWidget。"
        #     )

        # self.pets: tuple = pets
        # # 1. 先加载配置和图片
        # initial_pet_name_to_load = curr_pet_name if curr_pet_name else pets[0]
        # self.curr_pet_name = initial_pet_name_to_load
        # self.pic_dict = _load_all_pic(self.curr_pet_name)
        # self.pet_conf = PetConfig.init_config(self.curr_pet_name, self.pic_dict)
        # self.margin_value = 0.5 * max(self.pet_conf.width, self.pet_conf.height)
        # self.pet_data = PetData(self.curr_pet_name)

        # # 2. 再初始化UI
        # self._init_ui()
        # self._init_widget()
        # self._setup_ui(self.pic_dict)

        # # 3. 后续线程和显示
        # self.show()
        # self.threads: dict[str, QThread] = {}
        # self.workers: dict[str, QObject] = {}
        # self.runAnimation()
        # self.runInteraction()
        # self.runScheduler()

    # 在 PetWidget 类定义内部

    def mousePressEvent(self, event) -> None:
        """
        处理鼠标按钮按下事件。

        根据按下的按钮执行不同操作：
        - 右键：准备并显示上下文菜单。
        - 左键：启动窗口拖动逻辑。
        """
        button = event.button()  # 获取按下的按钮

        # --- 处理鼠标右键点击 ---
        if button == Qt.RightButton:
            # 设置窗口的上下文菜单策略为自定义，允许通过信号触发菜单显示
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            # 连接 customContextMenuRequested 信号到 _show_right_menu 槽函数

            try:
                # 尝试断开之前的连接，避免重复连接
                self.customContextMenuRequested.disconnect(self._show_right_menu)
            except TypeError:
                # 如果之前未连接，disconnect 会抛出 TypeError，忽略即可
                pass

            self.customContextMenuRequested.connect(self._show_right_menu)

        # --- 处理鼠标左键点击 ---
        elif button == Qt.LeftButton:

            # 1. 标记窗口开始跟随鼠标
            self.is_follow_mouse = True
            # 2. 计算并存储鼠标按下时相对于窗口左上角的偏移量
            self.mouse_drag_pos = event.globalPos() - self.pos()

            # 3. 更新全局状态 (通过 settings 模块)
            # - onfloor=0: 表示宠物离开地面（被提起）
            # - draging=1: 表示拖动状态开始
            self.settings.onfloor = 0
            self.settings.draging = 1

            # 4. 控制动画/交互工作线程
            #    - 暂停常规动画循环
            if 'Animation' in self.workers:  # 增加检查，避免KeyError
                self.workers['Animation'].pause()
            #    - 启动专门处理鼠标拖动的交互逻辑
            if 'Interaction' in self.workers: #  增加检查，避免KeyError
                self.workers['Interaction'].start_interact('mousedrag')

            # 5. 接受事件，表示已处理，阻止其进一步传播
            event.accept()
            # 6. 设置鼠标光标为标准箭头样式（拖动时）
            self.setCursor(QCursor(Qt.ArrowCursor))

        # 如果是其他鼠标按钮（例如中键），则不执行任何操作

    def mouseMoveEvent(self, event) -> None:
        print(f"[{self.curr_pet_name}] moving")
        """
        处理鼠标移动事件，核心功能是实现窗口拖动。

        当左键按下且处于拖动状态 (`self.is_follow_mouse`) 时：
        1. 更新窗口位置以跟随鼠标。
        2. 记录最近的鼠标位置历史，用于后续（在 mouseReleaseEvent 中）
           计算释放时的拖拽速度。
        """
        # 核心条件：仅在由 mousePressEvent 启动的拖动模式下响应
        if not self.is_follow_mouse:
            return  # 如果不是拖动状态，直接忽略移动事件

        # --- 窗口移动 ---
        # 计算窗口的新左上角位置：
        #   鼠标当前全局位置 - 鼠标按下时相对于窗口左上角的偏移量
        new_window_pos = event.globalPos() - self.mouse_drag_pos
        self.move(new_window_pos)

        # --- 更新鼠标位置历史 (用于计算释放速度) ---
        # 这个队列记录了最近几次鼠标事件的坐标，形成一个简易的滑动窗口。
        # mousepos*1 是最新位置, mousepos*2 是上一次位置, 以此类推。
        current_cursor_pos = QCursor.pos()  # 获取一次当前位置，避免重复调用

        # 更新 X 坐标历史
        self.settings.mouseposx4 = self.settings.mouseposx3
        self.settings.mouseposx3 = self.settings.mouseposx2
        self.settings.mouseposx2 = self.settings.mouseposx1
        self.settings.mouseposx1 = current_cursor_pos.x()

        # 更新 Y 坐标历史
        self.settings.mouseposy4 = self.settings.mouseposy3
        self.settings.mouseposy3 = self.settings.mouseposy2
        self.settings.mouseposy2 = self.settings.mouseposy1
        self.settings.mouseposy1 = current_cursor_pos.y()

        # --- 事件处理完毕 ---
        # 接受事件，表示我们已经处理了这次移动，阻止它被其他组件处理。
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """
        处理鼠标按钮松开事件，主要用于结束拖动操作。

        当松开的是鼠标左键时：
        1. 结束窗口拖动状态 (`self.is_follow_mouse = False`)。
        2. 根据全局设置 `settings.set_fall` 决定后续行为：
           - 如果启用掉落：计算拖拽速度，设置掉落方向，准备掉落动画。
           - 如果禁用掉落：将宠物移回地面，设置为默认站立图像，恢复常规动画。
        """
        # 只响应左键的松开事件
        if event.button() != Qt.LeftButton:
            return  # 忽略非左键的释放

        # --- 步骤 1: 结束拖动状态 (通用操作) ---
        self.is_follow_mouse = False
        self.setCursor(QCursor(Qt.ArrowCursor))  # 恢复标准箭头光标

        # 更新全局拖动状态标记
        # settings.onfloor 保持为 0 (可能仍在空中)，落地状态由后续逻辑处理
        self.settings.draging = 0  # 明确标记拖动已结束

        # --- 步骤 2: 根据是否启用掉落，执行不同逻辑 ---
        self.fall_enabled = self.settings.set_fall == 1

        if self.fall_enabled:
            # === 情况 A: 启用掉落 (set_fall == 1) ===
            self._handle_fall_on_release()
        else:
            # === 情况 B: 禁用掉落 (set_fall == 0) ===
            self._handle_no_fall_on_release()

        # 左键释放事件通常不需要 event.accept()

    def _handle_fall_on_release(self) -> None:
        """处理启用掉落时，鼠标左键释放的逻辑。"""
        # 1. 计算释放时的瞬时速度
        #    使用历史位置点 (1 和 3) 来估算速度，并应用修正系数。
        self.delta_x = self.settings.mouseposx1 - self.settings.mouseposx3
        self.delta_y = self.settings.mouseposy1 - self.settings.mouseposy3
        # 注意：这里的 '/ 2' 可能代表时间间隔（假设两次采样间隔固定），
        # 或者只是一个经验性的平滑因子。
        self.settings.dragspeedx = (self.delta_x / 2) * self.settings.fixdragspeedx
        self.settings.dragspeedy = (self.delta_y / 2) * self.settings.fixdragspeedy

        # 2. 重置用于计算速度的历史位置 (避免影响下次拖动)
        self.settings.mouseposx1 = self.settings.mouseposx3 = 0
        self.settings.mouseposy1 = self.settings.mouseposy3 = 0
        # 注意：只重置了 1 和 3，可能 2/4/5 在其他地方仍有用途？(按原逻辑保留)

        # 3. 确定掉落动画的初始方向
        self.settings.fall_right = 1 if self.settings.dragspeedx > 0 else 0

        # 后续的掉落动画和物理效果应由 Interaction_worker 或类似机制接管处理

    def _handle_no_fall_on_release(self) -> None:
        """处理禁用掉落时，鼠标左键释放的逻辑。"""
        # 1. 尝试将宠物精确移动到地面位置
        #    _move_customized(0, 0) 内部会检查 Y 坐标是否低于 floor_pos，
        #    如果是，则将其设置为 floor_pos，并可能触发 onfloor=1 和恢复动画。
        self._move_customized(0, 0)

        # 2. 显式设置回默认图像 (以防 _move_customized 未触发图像更新)
        try:
            # 确保配置和图像列表存在
            self.default_image = self.pet_conf.default.images[0]
            self.settings.current_img = self.default_image
            self.set_img()  # 更新显示的图像
        except (AttributeError, IndexError, TypeError) as e:
            # 更详细的错误处理
            print(f"警告: 无法设置默认图像。配置或图像列表可能无效。错误: {e}")

        # 3. 确保常规动画已恢复
        #    虽然 _move_customized 落地时会尝试恢复动画，
        #    但这里再次调用 resume() 作为保障，以防宠物释放时已经在地面上。
        try:
            if 'Animation' in self.workers:
                self.workers['Animation'].resume()
            else:
                print(
                    f"警告: 无法恢复动画，'Animation' worker 不存在于 self.workers 中。"
                )
        except Exception as e:
            # 捕获调用 resume() 时可能发生的任何异常
            print(f"警告: 尝试恢复动画时发生错误: {e}")

    def _init_widget(self) -> None:
        """
        初始化窗口的基本属性：设置为无边框、总在最前、半透明的子窗口。
        同时初始化与鼠标拖动相关的状态变量。
        """
        # --- 窗口样式与行为设置 ---
        # 组合窗口标志：无边框，总在最前，作为子窗口（通常用于不显示在任务栏）
        # 使用 "|" 操作符合并多个标志位
        self.window_flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow
        self.setWindowFlags(self.window_flags)

        # 设置背景透明
        self.setAutoFillBackground(False)  # 禁用自动填充背景，配合下面的透明属性
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 启用窗口透明效果

        # --- 鼠标交互状态初始化 ---
        # 这两个变量用于实现窗口拖动功能
        self.is_follow_mouse: bool = False  # 初始状态：不跟随鼠标
        # mouse_drag_pos 在 mousePressEvent 中会被正确设置，这里初始化为当前位置
        self.mouse_drag_pos: QPoint = self.pos()

        self.repaint()

    def _init_ui(self):
        """
        初始化用户界面元素及其布局。
        """

        # ============================================================
        # 1. 宠物动画显示区域
        # ============================================================
        # 用于显示宠物动画的主要标签
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.label.installEventFilter(self)  # 安装事件过滤器

        # ============================================================
        # 2. 状态信息框 (包含健康、心情、番茄钟、专注时间)
        # ============================================================
        # 创建状态信息的容器 Frame
        self.status_frame = QFrame()

        # 垂直布局，用于放置所有状态信息
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # --- 2.1 健康值 (HP) ---
        h_box1 = QHBoxLayout()
        h_box1.setContentsMargins(0, 3, 0, 0)  # 上边距为3
        h_box1.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        # 健康值图标
        self.hpicon = QLabel(self)
        self.hpicon.setFixedSize(17, 15)
        image = QImage()
        image.load('res/icons/HP_icon.png')
        self.hpicon.setScaledContents(True)  # 图片自适应
        self.hpicon.setPixmap(QPixmap.fromImage(image))
        self.hpicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box1.addWidget(self.hpicon)

        # 健康值进度条
        self.pet_hp = QProgressBar(
            self, minimum=0, maximum=100, objectName='PetHP'
        )  # 设置objectName，便于样式表选择
        self.pet_hp.setFormat('50/100')  # 显示格式
        self.pet_hp.setValue(50)  # 初始值
        self.pet_hp.setAlignment(Qt.AlignCenter)
        h_box1.addWidget(self.pet_hp)

        # --- 2.2 心情值 (Emotion) ---
        h_box2 = QHBoxLayout()
        h_box2.setContentsMargins(0, 3, 0, 0)  # 上边距为3
        h_box2.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        # 心情值图标
        self.emicon = QLabel(self)
        self.emicon.setFixedSize(17, 15)
        image = QImage()
        image.load('res/icons/emotion_icon.png')  # 加载图片
        self.emicon.setScaledContents(True)
        self.emicon.setPixmap(QPixmap.fromImage(image))
        self.emicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box2.addWidget(self.emicon)

        # 心情值进度条
        self.pet_em = QProgressBar(self, minimum=0, maximum=100, objectName='PetEM')
        self.pet_em.setFormat('50/100')
        self.pet_em.setValue(50)
        self.pet_em.setAlignment(Qt.AlignCenter)
        h_box2.addWidget(self.pet_em)

        # --- 2.3 番茄时钟 ---
        h_box3 = QHBoxLayout()
        h_box3.setContentsMargins(0, 0, 0, 0)
        h_box3.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        # 番茄时钟图标
        self.tomatoicon = QLabel(self)
        self.tomatoicon.setFixedSize(17, 15)
        image = QImage()
        image.load('res/icons/Tomato_icon.png')
        self.tomatoicon.setScaledContents(True)
        self.tomatoicon.setPixmap(QPixmap.fromImage(image))
        self.tomatoicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box3.addWidget(self.tomatoicon)

        # 番茄时钟进度条
        self.tomato_time = QProgressBar(self, minimum=0, maximum=25, objectName='PetHP')
        self.tomato_time.setFormat('无')
        self.tomato_time.setValue(0)
        self.tomato_time.setAlignment(Qt.AlignCenter)
        self.tomato_time.hide()
        self.tomatoicon.hide()
        h_box3.addWidget(self.tomato_time)

        # --- 2.4 专注时间 ---
        h_box4 = QHBoxLayout()
        h_box4.setContentsMargins(0, 3, 0, 0)
        h_box4.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        # 专注时间图标
        self.focusicon = QLabel(self)
        self.focusicon.setFixedSize(17, 15)
        image = QImage()
        image.load('res/icons/Timer_icon.png')
        self.focusicon.setScaledContents(True)
        self.focusicon.setPixmap(QPixmap.fromImage(image))
        self.focusicon.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        h_box4.addWidget(self.focusicon)

        # 专注时间进度条
        self.focus_time = QProgressBar(self, minimum=0, maximum=100, objectName='PetFC')
        self.focus_time.setFormat('无')
        self.focus_time.setValue(0)
        self.focus_time.setAlignment(Qt.AlignCenter)
        self.focus_time.hide()
        self.focusicon.hide()
        h_box4.addWidget(self.focus_time)

        # 将所有布局添加到垂直布局中
        vbox.addLayout(h_box3)  # 番茄时钟
        vbox.addLayout(h_box4)  # 专注时间
        vbox.addLayout(h_box1)  # 健康值
        vbox.addLayout(h_box2)  # 心情值

        # 将垂直布局设置给 status_frame
        self.status_frame.setLayout(vbox)
        self.status_frame.setContentsMargins(0, 0, 0, 0)
        self.status_frame.hide()

        # ============================================================
        # 3. 对话框显示区域
        # ============================================================
        self.dialogue_box = QHBoxLayout()
        self.dialogue_box.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.dialogue_box.setContentsMargins(0, 0, 0, 0)

        # 对话框背景
        self.dialogue = QLabel(self)
        self.dialogue.setAlignment(Qt.AlignCenter)

        # 对话框背景，并设置大小
        image = QImage()
        image.load('res/icons/text_framex2.png')
        self.dialogue.setFixedWidth(image.width())
        self.dialogue.setFixedHeight(image.height())

        # 设置字体
        QFontDatabase.addApplicationFont('res/font/MFNaiSi_Noncommercial-Regular.otf')
        self.dialogue.setFont(QFont('造字工房奈思体（非商用）', int(11 / screen_scale)))

        self.dialogue.setWordWrap(
            False
        )  # 每行最多8个汉字长度，需要自定义function进行换行

        self._set_dialogue_dp()
        self.dialogue.setStyleSheet(
            "background-image : url(res/icons/text_framex2.png)"
        )  # ; border : 2px solid blue")

        self.dialogue_box.addWidget(self.dialogue)

        # ============================================================
        # 4. 主窗口布局设置
        # ============================================================
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 宠物布局
        self.petlayout = QVBoxLayout()
        self.petlayout.addWidget(self.status_frame)
        self.petlayout.addWidget(self.label)
        self.petlayout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.petlayout.setContentsMargins(0, 0, 0, 0)

        # 将对话框布局和宠物布局添加到主布局中
        # 注意添加顺序：对话框在上方 (视觉上可能在旁边，取决于整体窗口设计)，宠物布局在下方
        self.layout.addLayout(self.dialogue_box, Qt.AlignBottom | Qt.AlignHCenter)
        self.layout.addLayout(self.petlayout, Qt.AlignBottom | Qt.AlignHCenter)

        # 设置主布局
        self.setLayout(self.layout)

        # ============================================================
        # 5. 子窗口实例化与信号连接
        # ============================================================

        # --- 番茄钟设置窗口 ---
        try:
            self.tomato_window = Tomato()
            # 连接信号到槽函数
            self.tomato_window.close_tomato.connect(self.show_tomato)
            self.tomato_window.confirm_tomato.connect(self.run_tomato)
        except ImportError:
            print(f"警告：没有找到番茄钟，或导入失败。")
            self.tomato_window = None

        # --- 专注时间设置窗口 ---
        try:
            self.focus_window = Focus()
            self.focus_window.close_focus.connect(self.show_focus)
            self.focus_window.confirm_focus.connect(self.run_focus)
        except ImportError:
            print("警告：没有找到专注时间，或导入失败。")
            self.focus_window = None

        # --- 提醒设置窗口 ---
        try:
            self.remind_window = Remindme()
            self.remind_window.close_remind.connect(self.show_remind)
            self.remind_window.confirm_remind.connect(self.run_remind)
        except ImportError:
            print("警告：没有找到提醒事项，或导入失败。")
            self.remind_window = None

    def _set_menu(self, pets=()):
        """
        初始化并设置右键菜单及其所有动作和子菜单。
        """
        # 1. 创建主菜单对象
        menu = QMenu(self)

        # ============================================================
        # 2. 添加 "切换角色" 子菜单
        # ============================================================
        # --- 创建子菜单 ---
        change_menu = QMenu(menu)
        change_menu.setTitle('切换角色')

        # --- 动态创建并添加角色动作 ---
        # 使用辅助函数 _build_act 为每个宠物名称创建一个 QAction
        # 并将其连接到 self._change_pet 槽函数
        change_acts = [_build_act(name, change_menu, self._change_pet) for name in pets]
        change_menu.addActions(change_acts)

        # --- 将子菜单添加到主菜单 ---
        menu.addMenu(change_menu)

        # ============================================================
        # 3. 添加 "计划任务" 子菜单
        # ============================================================
        # --- 创建子菜单 ---
        task_menu = QMenu(menu)
        task_menu.setTitle('计划任务')

        # --- 添加 "番茄时钟" 动作 ---
        self.tomato_clock = QAction('番茄时钟', task_menu)  # 创建动作
        self.tomato_clock.triggered.connect(self.show_tomato)  # 连接信号
        task_menu.addAction(self.tomato_clock)  # 添加到子菜单

        # --- 添加 "专注时间" 动作 ---
        self.focus_clock = QAction('专注时间', task_menu)
        self.focus_clock.triggered.connect(self.show_focus)
        task_menu.addAction(self.focus_clock)

        # --- 添加 "提醒我" 动作 ---
        self.remind_clock = QAction('提醒我', task_menu)
        self.remind_clock.triggered.connect(self.show_remind)
        task_menu.addAction(self.remind_clock)

        # --- 将子菜单添加到主菜单 ---
        menu.addMenu(task_menu)

        # ============================================================
        # 4. 添加 "选择动作" 子菜单 (条件性添加)
        # ============================================================
        # 仅当 self.pet_conf.random_act_name 存在时才添加此子菜单
        if self.pet_conf.random_act_name is not None:
            # --- 创建子菜单 ---
            act_menu = QMenu(menu)
            act_menu.setTitle('选择动作')

            # --- 动态创建并添加动作 ---
            # 使用辅助函数 _build_act 为每个动作名称创建一个 QAction
            # 并将其连接到 self._show_act 槽函数
            select_acts = [
                _build_act(name, act_menu, self._show_act)
                for name in self.pet_conf.random_act_name
            ]
            act_menu.addActions(select_acts)

            # --- 将子菜单添加到主菜单 ---
            menu.addMenu(act_menu)

        # ============================================================
        # 5. 添加直接操作到主菜单
        # ============================================================
        # --- 添加 "禁用掉落" 动作 ---
        switch_fall = QAction('禁用掉落', menu)  # 创建动作
        switch_fall.triggered.connect(self.fall_onoff)  # 连接信号
        menu.addAction(switch_fall)  # 直接添加到主菜单

        # ============================================================
        # 6. 添加分隔符
        # ============================================================
        menu.addSeparator()

        # ============================================================
        # 7. 添加 "退出" 动作
        # ============================================================
        quit_act = QAction('退出', menu)  # 创建动作
        quit_act.triggered.connect(self.quit)  # 连接信号
        menu.addAction(quit_act)  # 直接添加到主菜单

        # ============================================================
        # 8. 将构建好的菜单赋给实例变量
        # ============================================================
        self.menu = menu

    def _show_right_menu(self):
        """
        在当前鼠标光标的位置弹出预先设置好的右键菜单 (self.menu)。
        确保 self.menu 对象已在调用此方法前被正确创建和配置。
        """
        # 光标位置弹出菜单
        self.menu.popup(QCursor.pos())

    def _change_pet(self, pet_name: str) -> None:
        """
        切换当前显示的宠物。

        此过程按顺序执行以下操作：
        1. 停止与当前宠物相关的所有活动线程。
        2. 加载并初始化新选定宠物的配置和资源。
        3. 请求界面重绘。
        4. 启动新宠物的核心活动线程。
        5. 更新 UI 元素以匹配新宠物。
        """
        # 步骤 1: 停止当前宠物的所有相关活动线程
        # -----------------------------------------
        # 确保在加载新宠物配置前，旧宠物的后台任务已停止
        self.main_window.pet_counts[self.curr_pet_name] -= 1
        self.main_window.update_controls(self.curr_pet_name)
        self.stop_thread('Animation')  # 停止动画线程
        self.stop_thread('Interaction')  # 停止交互线程
        self.stop_thread('Scheduler')  # 停止计划线程

        # 清除可能存在的旧对话框
        self._set_dialogue_dp('None')
        self.settings.showing_dialogue_now = False

        # 步骤 2: 加载并初始化新宠物的配置和资源
        self.init_conf(pet_name)

        # 步骤 3: 请求界面重绘
        self.repaint()

        # 步骤 4: 启动新宠物的核心活动线程
        # -----------------------------------------
        self.runAnimation()
        self.runInteraction()
        self.runScheduler()

        self.main_window.pet_counts[self.curr_pet_name] += 1
        self.main_window.update_controls(self.curr_pet_name)

        # 步骤 5: 更新 UI 元素以匹配新宠物
        if hasattr(self, '_setup_ui') and callable(getattr(self, '_setup_ui')):
            self._setup_ui(self.pic_dict)
        else:
            print(
                f"警告：方法 _setup_ui 未找到或不可调用。跳过 _change_pet 中的 UI 初始化步骤。 "
            )

    def init_conf(self, pet_name: str) -> None:
        """
        根据指定的宠物名称，初始化窗口和宠物的核心配置。
        1. 设置当前宠物名称 (`self.curr_pet_name`)。
        2. 加载该宠物的所有图像资源 (`self.pic_dict`)。
        3. 加载或创建该宠物的配置对象 (`self.pet_conf`)。
        4. 计算用于布局调整的边距值 (`self.margin_value`)。
        5. 加载或初始化该宠物的状态数据 (`self.pet_data`)。
        6. 更新依赖于当前宠物配置的UI组件 (菜单 `self._set_menu` 和系统托盘 `self._set_tray`)。
        """
        # 1. 设置当前宠物标识与加载核心资源/配置
        # -----------------------------------------
        self.curr_pet_name = pet_name
        self.pic_dict = _load_all_pic(pet_name)
        self.pet_conf = PetConfig.init_config(self.curr_pet_name, self.pic_dict)

        # 2. 计算用于布局调整的边距值
        # -----------------------------------------
        self.margin_value = 0.5 * max(
            self.pet_conf.width, self.pet_conf.height
        )  # 用于将widgets调整到合适的大小

        # 3. 加载或初始化该宠物的状态数据
        # -----------------------------------------
        self.pet_data = PetData(self.curr_pet_name)

        # 4. 更新依赖于当前宠物配置的UI组件
        # -----------------------------------------
        if hasattr(self, 'pets'):
            self._set_menu(self.pets)
        else:
            print(f"警告：未找到self.pets属性，无法在init_conf中更新菜单。")

        # 更新系统托盘
        self._set_tray()

    def _setup_ui(self, pic_dict):
        """
        根据当前宠物的配置 (self.pet_conf) 和传入的图片字典 (pic_dict)，
        调整界面元素的尺寸、设置初始值、更新显示图片、定位窗口，并初始化特定子任务。
        通常在宠物切换或初始化时调用。
        """

        # 1. 调整进度条尺寸
        # ---------------------
        # 将健康、心情、番茄钟、专注时间的进度条宽度设置为宠物配置宽度的 75%
        self.pet_hp.setFixedSize(int(0.75 * self.pet_conf.width), 15)
        self.pet_em.setFixedSize(int(0.75 * self.pet_conf.width), 15)
        self.tomato_time.setFixedSize(int(0.75 * self.pet_conf.width), 15)
        self.focus_time.setFixedSize(int(0.75 * self.pet_conf.width), 15)

        # 2. 调整主窗口尺寸
        # -------------------
        # 设置整个窗口的固定尺寸。
        # 宽度 = 宠物宽度 + 边距值
        # 高度 = 对话框高度 + 边距值 + 固定偏移(60) + 宠物高度
        self.setFixedSize(
            int(self.pet_conf.width + self.margin_value),
            int(self.dialogue.height() + self.margin_value + 60 + self.pet_conf.height),
        )

        # 3. 更新宠物状态进度条的显示
        # ---------------------------
        # 根据 self.pet_data 中当前的健康值和心情值，更新对应进度条的显示文本和数值
        self.pet_hp.setFormat('%s/100' % (int(self.pet_data.current_hp)))
        self.pet_hp.setValue(int(self.pet_data.current_hp))
        self.pet_em.setFormat('%s/100' % (int(self.pet_data.current_em)))
        self.pet_em.setValue(int(self.pet_data.current_em))

        # 4. 更新宠物显示的图片
        # -----------------------
        self.settings.previous_img = self.settings.current_img
        if pic_dict:  # 确保 pic_dict 不为空
            self.settings.current_img = list(pic_dict.values())[0]
        else:
            print("警告：pic_dict 为空，无法设置当前图片。")

        self.set_img()
        self.border = self.pet_conf.width / 2
        self.hpicon.adjustSize()

        # 5. 设置窗口的初始位置
        # ---------------------
        # 获取屏幕可用几何区域 (排除任务栏等)
        screen_geo = QDesktopWidget().availableGeometry()
        screen_width = screen_geo.width()
        work_height = screen_geo.height()

        # 计算窗口的初始位置
        x = int(screen_width * 0.8)
        # y 坐标计算方式使得窗口底部与屏幕可用区域的底部对齐
        y = work_height - self.height()

        self.floor_pos = work_height - self.height()
        self.move(x, y)

        # 6. 初始化外部任务
        # -------------------
        self.remind_window.initial_task()

    def eventFilter(self, watched_object, event):
        """
        事件过滤器，用于捕获安装了此过滤器的对象 (watched_object) 上的特定事件。

        在此实现中，主要处理鼠标进入和离开事件：
        - 当鼠标光标进入 `watched_object` 的区域时，显示 `self.status_frame`。
        - 当鼠标光标离开 `watched_object` 的区域时，隐藏 `self.status_frame`。
        """
        # 检查事件类型是否为鼠标进入事件 (QEvent.Enter)
        if event.type() == QEvent.Enter:
            # 如果是鼠标进入事件，则显示状态信息框 (self.status_frame)
            self.status_frame.show()
            # 返回 True 表示我们已经处理了这个事件，不需要Qt再做其他处理或传递给父级
            return True

        # 检查事件类型是否为鼠标离开事件 (QEvent.Leave)
        elif event.type() == QEvent.Leave:
            # 如果是鼠标离开事件，则隐藏状态信息框 (self.status_frame)
            self.status_frame.hide()

        # 对于所有其他未在此处处理的事件类型
        # 返回 False 表示这个过滤器没有处理该事件，
        # 事件应该被传递给被观察对象 (watched_object) 的父对象或进行默认处理。
        return False

    def _set_tray(self) -> None:
        """
        设置或更新应用程序在系统托盘中的图标及其关联菜单。

        - 如果 `self.tray` 尚未初始化 (值为 `None`)，则进行首次创建和设置。
        - 如果 `self.tray` 已存在，则仅更新其上下文菜单 (`self.menu`) 并确保其可见。

        依赖 `self.menu` 已经被正确设置。
        """
        if self.tray is None:
            self.tray = QSystemTrayIcon(self)
            self.tray.setIcon(QIcon('res/icons/icon.png'))
            # 将预设的右键菜单 (self.menu) 关联到托盘图标
            self.tray.setContextMenu(self.menu)
            self.tray.show()
        else:
            # 1. 仅更新托盘图标关联的右键菜单
            #    这允许在程序运行时动态改变菜单内容（例如切换宠物后更新菜单项）
            self.tray.setContextMenu(self.menu)

            # 2. 确保托盘图标是可见的
            #    即使之前已经调用过 show(), 再次调用通常无害，
            #    可以确保图标处于显示状态（以防万一被隐藏）。
            self.tray.show()

    def set_img(self):  # , img: QImage) -> None:
        """
        根据 `settings.current_img` 中存储的图像数据 (预期为 QImage)，
        更新 `self.label` 控件以显示该图片，并调整其尺寸。

        同时，将该图像数据也存储在 `self.image` 属性中。
        """
        # 1. 调整 QLabel (self.label) 的尺寸以完全匹配新图像的宽度和高度
        #    确保标签大小正好能容纳整个图片
        try:
            image_width = self.settings.current_img.width()
            image_height = self.settings.current_img.height()
            self.label.resize(image_width, image_height)
        except AttributeError:
            print(
                f"错误：无法从 self.settings.current_img 获取尺寸。请确保它是一个有效的 QImage 对象。"
            )
            # 可以选择在这里返回或设置一个默认图片/尺寸
            return

        # 2. 将 QImage (settings.current_img) 转换为 QPixmap 并设置为 QLabel 的内容
        #    QPixmap 是专门用于在屏幕上显示的优化图像格式
        self.label.setPixmap(QPixmap.fromImage(self.settings.current_img))

        # 3. 将当前的 QImage 对象也保存到实例变量 self.image 中
        #    这个副本的具体用途需要结合其他使用 self.image 的代码来理解
        self.image = self.settings.current_img

    def _set_dialogue_dp(self, texts='None'):
        """
        设置或隐藏对话框标签 (self.dialogue) 的文本内容。

        - 如果传入的 `texts` 参数是字符串 'None' (区分大小写)，则隐藏对话框。
        - 否则，使用 `text_wrap` 函数处理传入的文本（例如自动换行），
          然后将处理后的文本设置到对话框标签上，并显示该标签。

        依赖外部函数 `text_wrap` 来进行文本格式化处理。
        """
        # 检查传入的文本是否等于特定的哨兵字符串 'None'
        if texts == 'None':
            # 如果 texts 是 'None'，则隐藏对话框控件
            self.dialogue.hide()

        else:
            # 1. 使用外部函数 text_wrap 处理文本格式 (例如：自动换行)
            #    确保 text_wrap 函数已定义或导入，并且能正确处理输入
            try:
                texts_wrapped = text_wrap(texts)
            except NameError:
                print(f"错误：text_wrap 函数未定义！将使用原始文本。")
                texts_wrapped = texts  # 如果 text_wrap 不可用，则回退到原始文本
            except Exception as e:
                print(f"错误：调用 text_wrap 时出错: {e}。将使用原始文本。")
                texts_wrapped = texts  # 其他异常也回退

            # 2. 将处理（或原始）后的文本设置到对话框标签上
            self.dialogue.setText(texts_wrapped)

            # 3. 显示对话框标签，使其可见
            self.dialogue.show()

    def _change_status(self, status: str, change_value: float):
        """
        根据指定的宠物状态 ('hp' 或 'em') 和变化值，更新状态及其UI显示。

        核心逻辑：
        1. 检查 `status` 参数是否为 'hp' 或 'em'，如果不是则直接返回。
        2. 如果 `status` 是 'hp'：
           - 计算新值，更新进度条 `self.pet_hp` 的值。
           - 从进度条重新读取确认后的值。
           - 更新进度条的显示格式。
           - 更新数据模型 `self.pet_data.current_hp`。
        3. 如果 `status` 是 'em'：
           - 检查是否满足应用变化的条件：
             - 如果 `change_value` 为正（增加心情），则应用。
             - 如果 `change_value` 为负（减少心情），仅当 `self.pet_data.current_hp < 60` 时应用。
           - 如果条件满足，则执行与 'hp' 类似的更新步骤（针对 `self.pet_em` 和 `self.pet_data.current_em`）。
        4. 如果状态 ('hp' 或 'em') 被有效处理（即没有在步骤1返回），则调用 `self.pet_data.save_data()` 保存更新后的数据。
        """

        # 1. 输入验证：检查 status 是否为有效值 ('hp' 或 'em')
        # ----------------------------------------------------
        if status not in ['hp', 'em']:
            print(f"警告：尝试修改无效状态 '{status}'，操作被忽略。")
            # 如果状态无效，则不执行任何后续操作
            return

        status_changed = False  # 标志位，记录状态是否真的发生了有效变化

        # 2. 处理健康值 (HP) 变化
        # --------------------------
        if status == 'hp':
            # a. 计算理论新值
            target_value = self.pet_hp.value() + change_value
            # b. 更新进度条的值
            self.pet_hp.setValue(int(target_value))
            # c. 从进度条获取实际设置后的值
            current_value = self.pet_hp.value()
            # d. 更新进度条显示的文本格式
            self.pet_hp.setFormat('%s/100' % (current_value))
            # e. 更新数据模型中的值
            self.pet_data.current_hp = current_value

            status_changed = True  # 标记 HP 状态已处理

        # 3. 处理心情值 (EM) 变化
        # --------------------------
        elif status == 'em':
            # a. 判断是否满足应用心情变化的条件
            can_change_em = False
            if change_value > 0:
                # 增加心情值时，总是允许
                can_change_em = True
            elif self.pet_data.current_hp < 60:
                # 减少心情值时，仅当 HP < 60 时允许
                can_change_em = True
            else:
                # 其他情况 (减少心情值且 HP >= 60)，不允许
                print(
                    f"(条件不满足：减少心情值，但 HP ({self.pet_data.current_hp}) >= 60)，操作被忽略。"
                )

            # b. 如果条件允许，则执行更新
            if can_change_em:
                # i. 计算理论新值
                target_value = self.pet_em.value() + change_value
                # ii. 更新进度条的值
                self.pet_em.setValue(int(target_value))
                # iii. 从进度条获取实际设置后的值
                current_value = self.pet_em.value()
                # iv. 更新进度条显示的文本格式
                self.pet_em.setFormat('%s/100' % (current_value))
                # v. 更新数据模型中的值
                self.pet_data.current_em = current_value

                status_changed = True  # 标记 EM 状态已处理

        # 4. 保存数据 (当 status 有效且可能发生变化时调用)
        # ------------------------------------------------
        if status_changed:  # 可以选择仅在状态实际改变时保存
            self.pet_data.save_data()

    def _change_time(self, status, timeleft):
        """
        根据指定的任务状态和剩余时间，更新对应的时间显示控件（番茄钟或专注时间）。

        根据 `status` 参数的不同值，执行不同的更新操作：
        - 'tomato_start': 初始化番茄钟工作时间显示 (通常 25 分钟)。
        - 'tomato_rest': 初始化番茄钟休息时间显示 (通常 5 分钟)。
        - 'tomato': 更新番茄钟进行中的剩余时间。
        - 'tomato_end': 重置番茄钟显示为"无"。
        - 'focus_start': 初始化专注时间显示 (最大值和当前值设为 timeleft)。
        - 'focus': 更新专注时间进行中的剩余时间。
        - 'focus_end': 重置专注时间显示为"无"。
        """
        # 定义有效的状态列表
        valid_statuses = [
            'tomato_start',
            'tomato_rest',
            'tomato',
            'tomato_end',
            'focus_start',
            'focus',
            'focus_end',
        ]

        # 1. 输入验证：检查 status 是否在有效列表中
        # ----------------------------------------
        if status not in valid_statuses:
            # 如果 status 无效，打印错误信息到终端并直接返回
            print(f"[错误] _change_time: 接收到无效的状态 '{status}'。操作被忽略。")
            return

        # 2. 根据有效的 status 执行相应的 UI 更新
        # ----------------------------------------
        try:
            if status == 'tomato_start':
                # 初始化番茄钟工作时间
                self.tomato_time.setMaximum(25)
                self.tomato_time.setValue(timeleft)
                self.tomato_time.setFormat('%s min' % (int(timeleft)))

            elif status == 'tomato_rest':
                # 初始化番茄钟休息时间
                self.tomato_time.setMaximum(5)
                self.tomato_time.setValue(timeleft)
                self.tomato_time.setFormat('%s min' % (int(timeleft)))

            elif status == 'tomato':
                # 更新番茄钟进行中的时间
                self.tomato_time.setValue(timeleft)
                self.tomato_time.setFormat('%s min' % (int(timeleft)))

            elif status == 'tomato_end':
                # 结束番茄钟，重置显示
                self.tomato_time.setValue(0)
                self.tomato_time.setFormat('无')

            elif status == 'focus_start':
                # 初始化专注时间
                self.focus_time.setMaximum(timeleft)
                self.focus_time.setValue(timeleft)
                self.focus_time.setFormat('%s min' % (int(timeleft)))

            elif status == 'focus':
                self.focus_time.setValue(timeleft)
                self.focus_time.setFormat('%s min' % (int(timeleft)))

            elif status == 'focus_end':
                self.focus_time.setValue(0)
                self.focus_time.setFormat('无')

        except AttributeError as e:
            print(f"[错误] _change_time: 更新UI元素时出错，可能控件未正确初始化: {e}")

        except (ValueError, TypeError) as e:
            print(
                f"[错误] _change_time: 提供的 timeleft 值 ('{timeleft}') 无法转换为整数: {e}"
            )

        except Exception as e:
            print(f"[错误] _change_time: 执行更新时发生未知错误: {e}")

    def quit(self) -> None:
        """
        关闭应用程序窗口并终止整个Python进程。

        执行顺序：
        1. 调用 `self.close()` 来关闭与此对象关联的窗口（通常是主窗口）。
           这会触发窗口的关闭事件 (closeEvent)，允许进行清理操作。
        2. 调用 `sys.exit()` 来请求Python解释器退出。
        """
        try:
            # 步骤 1: 关闭窗口
            # 这会发送一个关闭事件给窗口，允许正常的清理流程
            self.close()

            # 步骤 2: 退出应用程序进程
            # 强制终止 Python 解释器
            sys.exit()

        except Exception as e:
            print(f"[错误] quit: 在尝试关闭窗口或退出程序时发生错误: {e}")
            # 即使出错，可能仍需尝试强制退出
            try:
                sys.exit(1)  # 尝试以非零状态码退出，表示异常终止
            except SystemExit:
                pass  # 忽略 sys.exit() 本身引发的 SystemExit 异常
            except Exception as exit_e:
                print(f"[严重错误] quit: 尝试强制退出也失败了: {exit_e}")

    def stop_thread(self, module_name):
        """
        停止指定模块关联的后台工作线程。

        执行步骤：
        1. 尝试调用工作者对象 (`self.workers[module_name]`) 的 `kill()` 方法 (如果存在)。
           这通常用于通知工作者内部逻辑停止。
        2. 尝试调用线程对象 (`self.threads[module_name]`) 的 `terminate()` 方法。
           这是一个更强制的停止方式，可能不会进行清理。
        3. 调用线程对象 (`self.threads[module_name]`) 的 `wait()` 方法。
           阻塞当前流程，直到目标线程完全终止。
        """
        try:
            # 检查 worker 和 thread 是否存在于字典中
            if module_name not in self.workers:
                print(f"[错误] stop_thread: 未找到名为 '{module_name}' 的工作者对象。")
                # 根据需要决定是否继续尝试停止线程，或者直接返回
                # 此处假设如果 worker 不存在，可能 thread 也不可靠或不需停止
                # return
            if module_name not in self.threads:
                print(f"[错误] stop_thread: 未找到名为 '{module_name}' 的线程对象。")
                return  # 如果线程对象不存在，无法继续

            worker = self.workers[module_name]
            thread = self.threads[module_name]

            # 步骤 1: 尝试调用 worker 的 kill 方法
            if hasattr(worker, 'kill') and callable(worker.kill):
                worker.kill()
            else:
                # 如果没有 kill 方法，可能无法停止，依赖 terminate
                pass

            # 步骤 2: 终止线程 (强制停止)
            if hasattr(thread, 'terminate') and callable(thread.terminate):
                thread.terminate()
            else:
                print(
                    f"[错误] stop_thread: 线程对象 '{module_name}' 没有 terminate 方法。"
                )
                # 如果无法 terminate，可能也无法 wait，但仍尝试 wait

            # 步骤 3: 等待线程结束
            if hasattr(thread, 'wait') and callable(thread.wait):
                thread.wait()
            else:
                print(f"[错误] stop_thread: 线程对象 '{module_name}' 没有 wait 方法。")

        except KeyError:
            print(
                f"[错误] stop_thread: 提供的模块名 '{module_name}' 在 workers 或 threads 字典中不存在。"
            )
        except AttributeError as e:
            print(
                f"[错误] stop_thread: 尝试调用 kill/terminate/wait 时出错，对象可能不符合预期结构: {e}"
            )
        except Exception as e:
            print(f"[错误] stop_thread: 停止线程 '{module_name}' 时发生意外错误: {e}")

    def fall_onoff(self):
        """
        切换"掉落"功能的开关状态。

        此方法通常作为菜单项或按钮的槽函数被调用。它会：
        1. 获取触发此操作的发送者对象 (sender)。
        2. 检查发送者当前的文本，判断当前是"禁用"还是"开启"状态。
        3. 将发送者的文本切换到相反的状态。
        4. 更新全局 `settings.set_fall` 变量 (0 代表关闭/禁用，1 代表开启)。
        """

        try:
            sender = self.sender()

            if sender is None:
                print(
                    "[错误] fall_onoff: 无法获取发送者对象 (sender is None)。操作中止。"
                )
                return

            if not (
                hasattr(sender, 'text')
                and callable(sender.text)
                and hasattr(sender, 'setText')
                and callable(sender.setText)
            ):
                print(
                    f"[错误] fall_onoff: 发送者对象 '{sender}' 缺少 text 或 setText 方法。操作中止。"
                )
                return

            current_text = sender.text()

            if current_text == "禁用掉落":
                sender.setText("开启掉落")
                self.settings.set_fall = 0

            elif current_text == "开启掉落":
                sender.setText("禁用掉落")
                self.settings.set_fall = 1

            else:
                print(
                    f"[错误] fall_onoff: 发送者对象的文本为非预期的 '{current_text}'。状态未改变。"
                )

        except AttributeError as e:
            # 捕获访问 settings.set_fall 可能出现的属性错误
            print(
                f"[错误] fall_onoff: 访问 self.settings.set_fall 时出错: {e}。请确保 self.settings 对象及其属性已正确初始化。"
            )
        except NameError as e:
            # 捕获 settings 对象本身未定义的情况
            print(f"[错误] fall_onoff: 全局 self.settings 对象未定义: {e}。")
        except Exception as e:
            # 捕获其他在尝试获取或设置 sender 文本，或设置 settings 时发生的意外错误
            print(f"[错误] fall_onoff: 执行切换时发生未知错误: {e}")

    def _calculate_popup_position(self, popup_window: QWidget) -> QPoint:
        """
        计算弹出窗口的理想位置，确保其完整显示在屏幕内，并优先置于宠物上方。

        Args:
            popup_window: 需要定位的弹出窗口 (QWidget)。

        Returns:
            QPoint: 计算得到的最佳左上角位置。
        """
        try:
            screen_rect = QApplication.desktop().screenGeometry()
            pet_rect = self.geometry()  # 获取宠物主窗口的几何信息
            popup_rect = (
                popup_window.frameGeometry()
            )  # 使用 frameGeometry 获取包含窗口边框的尺寸

            # 理想的X: 使弹出窗口在宠物上方水平居中
            ideal_x = pet_rect.x() + (pet_rect.width() - popup_rect.width()) // 2
            # 理想的Y: 使弹出窗口的底部在宠物图像的顶部
            # 这里假设宠物图像是 PetWidget 的主要内容，或者 PetWidget 本身就是宠物图像
            ideal_y = pet_rect.y() - popup_rect.height()

            # 确保窗口在屏幕范围内
            # 调整X坐标
            if ideal_x < screen_rect.x():
                ideal_x = screen_rect.x()
            elif ideal_x + popup_rect.width() > screen_rect.x() + screen_rect.width():
                ideal_x = screen_rect.x() + screen_rect.width() - popup_rect.width()

            # 调整Y坐标
            if ideal_y < screen_rect.y():
                ideal_y = screen_rect.y()
            elif ideal_y + popup_rect.height() > screen_rect.y() + screen_rect.height():
                # 如果宠物上方空间不够，尝试放到宠物下方
                alternative_y = pet_rect.y() + pet_rect.height()
                if (
                    alternative_y + popup_rect.height()
                    <= screen_rect.y() + screen_rect.height()
                ):
                    ideal_y = alternative_y
                else:  # 如果下方空间也不够，则尽量贴近屏幕底部
                    ideal_y = (
                        screen_rect.y() + screen_rect.height() - popup_rect.height()
                    )

            # 再次检查，确保Y不会导致窗口顶部跑到屏幕外或底部超出
            if ideal_y < screen_rect.y():
                ideal_y = screen_rect.y()
            if ideal_y + popup_rect.height() > screen_rect.y() + screen_rect.height():
                ideal_y = screen_rect.y() + screen_rect.height() - popup_rect.height()

            return QPoint(ideal_x, ideal_y)

        except Exception as e:
            print(f"[错误] _calculate_popup_position: 计算位置时发生错误: {e}")
            # 出错时，返回宠物当前位置作为备用
            return self.pos()

    def show_tomato(self):
        """
        控制番茄钟设置窗口的显示或取消正在运行的番茄钟。
        """
        try:
            if not hasattr(self, 'tomato_window') or self.tomato_window is None:
                print("[警告] show_tomato: tomato_window 未初始化或为 None。")
                # 可以选择在这里尝试重新初始化，或者直接返回
                # self.tomato_window = Tomato() # 示例：尝试重新初始化
                # if self.tomato_window:
                #     self.tomato_window.close_tomato.connect(self.show_tomato)
                #     self.tomato_window.confirm_tomato.connect(self.run_tomato)
                # else:
                #     print("[严重错误] show_tomato: 无法重新初始化 tomato_window。")
                return

            if self.tomato_window.isVisible():
                # 场景 1: 设置窗口可见，直接隐藏它
                self.tomato_window.hide()

            # 场景 2 & 3: 设置窗口不可见
            elif self.tomato_clock.text() == "取消番茄时钟":
                # 场景 2: 正在运行番茄钟，执行取消操作
                self.tomato_clock.setText("番茄时钟")
                # 尝试调用取消方法
                if 'Scheduler' in self.workers and hasattr(
                    self.workers['Scheduler'], 'cancel_tomato'
                ):
                    self.workers['Scheduler'].cancel_tomato()
                else:
                    print(
                        "[警告] show_tomato: 无法取消番茄钟，因为 'Scheduler' worker 或其 'cancel_tomato' 方法未找到。"
                    )
                # 隐藏相关UI元素
                self.tomatoicon.hide()
                self.tomato_time.hide()

            else:
                # 场景 3: 未运行番茄钟，显示设置窗口
                # current_pos = self.pos()  # 获取当前窗口位置 # 旧代码
                # self.tomato_window.move(current_pos)  # 移动设置窗口到该位置 # 旧代码
                new_pos = self._calculate_popup_position(self.tomato_window)
                self.tomato_window.move(new_pos)
                self.tomato_window.show()  # 显示设置窗口

        except AttributeError as e:
            print(
                f"[错误] show_tomato: 访问必要的UI元素或属性时出错: {e}。请检查是否所有相关对象 (tomato_window, tomato_clock, tomatoicon, tomato_time, workers) 都已正确初始化。"
            )
        except KeyError as e:
            print(
                f"[错误] show_tomato: 无法访问 'Scheduler' worker: {e}。请确保 workers 字典中包含此键。"
            )
        except Exception as e:
            print(f"[错误] show_tomato: 执行操作时发生未知错误: {e}")

    def run_tomato(self, nt):
        """
        启动一个新的番茄钟会话。

        如果当前番茄钟状态为"未运行"（通过 `self.tomato_clock` 的文本 "番茄时钟" 判断），则：
        1. 将 `self.tomato_clock` 的文本更改为 "取消番茄时钟"。
        2. 隐藏番茄钟设置窗口 (`self.tomato_window`)。
        3. 调用调度器 (`self.workers['Scheduler']`) 的 `add_tomato` 方法，传入番茄钟数量 `nt`。
        4. 显示番茄钟相关的图标 (`self.tomatoicon`) 和时间显示 (`self.tomato_time`)。
        """
        try:
            # 检查当前是否可以启动 (状态是否为"未运行")
            self.tomato_clock.text() == "番茄时钟"

            # 1. 更改菜单/按钮文本，表示正在运行
            self.tomato_clock.setText("取消番茄时钟")

            # 2. 隐藏设置窗口 (如果它还显示着的话)
            self.tomato_window.hide()

            # 3. 尝试启动番茄钟任务
            if 'Scheduler' in self.workers and hasattr(
                self.workers['Scheduler'], 'add_tomato'
            ):
                try:
                    num_tomatoes = int(nt)  # 尝试转换输入为整数
                    self.workers['Scheduler'].add_tomato(n_tomato=num_tomatoes)
                except (ValueError, TypeError):
                    print(
                        f"[错误] run_tomato: 无法启动番茄钟，因为提供的数量 '{nt}' 不是有效的整数。"
                    )
                    return  # 停止执行后续步骤
            else:
                print(
                    "[警告] run_tomato: 无法启动番茄钟，因为 'Scheduler' worker 或其 'add_tomato' 方法未找到。"
                )
                return

            # 4. 显示进行中的UI元素
            self.tomatoicon.show()
            self.tomato_time.show()

        except AttributeError as e:
            print(
                f"[错误] run_tomato: 访问必要的UI元素或属性时出错: {e}。请检查是否所有相关对象 (tomato_clock, tomato_window, tomatoicon, tomato_time, workers) 都已正确初始化。"
            )
        except KeyError as e:
            print(
                f"[错误] run_tomato: 无法访问 'Scheduler' worker: {e}。请确保 workers 字典中包含此键。"
            )
        except Exception as e:
            print(f"[错误] run_tomato: 执行启动时发生未知错误: {e}")

    def change_tomato_menu(self):
        """
        重置番茄钟菜单项/按钮的显示状态，通常在番茄钟被外部取消或结束后调用。

        如果番茄钟当前状态为"正在运行"（通过 `self.tomato_clock` 的文本 "取消番茄时钟" 判断），则：
        1. 将 `self.tomato_clock` 的文本改回 "番茄时钟"。
        2. 隐藏番茄钟相关的图标 (`self.tomatoicon`) 和时间显示 (`self.tomato_time`)。

        此方法主要负责UI状态的同步，不直接影响番茄钟的运行逻辑。
        """
        try:
            # 检查是否需要重置 (即当前是否处于"正在运行"的显示状态)
            self.tomato_clock.text() == "取消番茄时钟"

            # 1. 恢复文本为"未运行"状态
            self.tomato_clock.setText("番茄时钟")

            # 2. 隐藏进行中的UI元素
            self.tomatoicon.hide()
            self.tomato_time.hide()

        except AttributeError as e:
            print(
                f"[错误] change_tomato_menu: 访问必要的UI元素 (tomato_clock, tomatoicon, tomato_time) 时出错: {e}。请检查它们是否已正确初始化。"
            )
        except Exception as e:
            print(f"[错误] change_tomato_menu: 执行菜单状态更改时发生未知错误: {e}")

    def show_focus(self):
        """
        控制专注时间设置窗口的显示或取消正在运行的专注任务。

        行为逻辑：
        1. 如果专注设置窗口 (`self.focus_window`) 当前可见，则将其隐藏。
        2. 如果设置窗口不可见，并且专注状态为"正在运行"（通过 `self.focus_clock` 的文本判断为 "取消专注任务"），则：
           - 将 `self.focus_clock` 文本改回 "专注时间"。
           - 调用调度器 (`self.workers['Scheduler']`) 的 `cancel_focus` 方法。
           - 隐藏专注任务相关的图标 (`self.focusicon`) 和时间显示 (`self.focus_time`)。
        3. 如果设置窗口不可见，并且专注状态为"未运行"（文本为 "专注时间"），则：
           - 将设置窗口移动到当前主窗口的位置 (`self.pos()`)。
           - 显示设置窗口 (`self.focus_window`)。
        """
        try:
            # 检查必要的 UI 元素是否存在 (防御性检查)
            required_attrs = [
                'focus_window',
                'focus_clock',
                'focusicon',
                'focus_time',
                'workers',
            ]
            for attr in required_attrs:
                if not hasattr(self, attr):
                    print(
                        f"[错误] show_focus: 缺少必要的属性 'self.{attr}'。操作中止。"
                    )
                    return
            if 'Scheduler' not in self.workers:
                print(
                    f"[错误] show_focus: 'self.workers' 字典中缺少 'Scheduler' 键。操作中止。"
                )
                return

            # 开始核心逻辑
            if self.focus_window.isVisible():
                # 场景 1: 设置窗口可见，直接隐藏它
                self.focus_window.hide()

            # 场景 2 & 3: 设置窗口不可见
            elif self.focus_clock.text() == "取消专注任务":
                # 场景 2: 正在运行专注任务，执行取消操作
                self.focus_clock.setText("专注时间")

                # 尝试调用取消方法
                scheduler = self.workers['Scheduler']
                if hasattr(scheduler, 'cancel_focus') and callable(
                    scheduler.cancel_focus
                ):
                    scheduler.cancel_focus()
                else:
                    print(
                        "[警告] show_focus: 无法取消专注任务，因为 'Scheduler' worker 没有 'cancel_focus' 方法。"
                    )

                # 隐藏相关UI元素
                self.focusicon.hide()
                self.focus_time.hide()

            else:
                # 场景 3: 未运行专注任务，显示设置窗口
                # (隐含条件: self.focus_clock.text() == "专注时间")
                new_pos = self._calculate_popup_position(self.focus_window)
                self.focus_window.move(new_pos)
                self.focus_window.show()  # 显示设置窗口

        except AttributeError as e:
            # 捕获访问方法（如 isVisible, hide, text, setText, pos, move, show）时的属性错误
            print(
                f"[错误] show_focus: 访问UI元素的方法或属性时出错: {e}。请确保对象已正确初始化且类型正确。"
            )
        except KeyError as e:
            # 这个理论上被入口检查覆盖了，但保留以防万一
            print(f"[错误] show_focus: 访问 'Scheduler' worker 时出错: {e}。")
        except Exception as e:
            # 捕获其他意外错误，例如 self.pos() 返回无效值等
            print(f"[错误] show_focus: 执行操作时发生未知错误: {e}")

    def run_focus(self, task: str, hs, ms):
        """
        启动一个新的专注时间任务。

        如果当前专注状态为"未运行"（通过 `self.focus_clock` 的文本 "专注时间" 判断），则：
        1. 将 `self.focus_clock` 的文本更改为 "取消专注任务"。
        2. 隐藏专注设置窗口 (`self.focus_window`)。
        3. 根据 `task` 参数 ('range' 或 'point') 调用调度器 (`self.workers['Scheduler']`) 的 `add_focus` 方法，
           并传递对应的时间参数 (`time_range=[hs, ms]` 或 `time_point=[hs, ms]`)。
        4. 显示专注任务相关的图标 (`self.focusicon`) 和时间显示 (`self.focus_time`)。

        如果 `task` 参数无效，则打印错误并中止。
        """
        try:
            # 检查必要的 UI 元素和 worker 是否存在
            required_attrs = [
                'focus_clock',
                'focus_window',
                'focusicon',
                'focus_time',
                'workers',
            ]
            for attr in required_attrs:
                if not hasattr(self, attr):
                    print(f"[错误] run_focus: 缺少必要的属性 'self.{attr}'。操作中止。")
                    return
            if 'Scheduler' not in self.workers:
                print(
                    f"[错误] run_focus: 'self.workers' 字典中缺少 'Scheduler' 键。操作中止。"
                )
                return
            scheduler = self.workers['Scheduler']
            if not (hasattr(scheduler, 'add_focus') and callable(scheduler.add_focus)):
                print(
                    f"[错误] run_focus: 'Scheduler' worker 没有 'add_focus' 方法。操作中止。"
                )
                return

            # 检查当前是否可以启动 (状态是否为"未运行")
            if self.focus_clock.text() == "专注时间":

                # 1. 验证 task 参数
                if task not in ['range', 'point']:
                    print(
                        f"[错误] run_focus: 无效的任务类型 '{task}'。任务类型必须是 'range' 或 'point'。"
                    )
                    return  # 中止执行

                # 2. 更改菜单/按钮文本，表示正在运行
                self.focus_clock.setText("取消专注任务")

                # 3. 隐藏设置窗口
                self.focus_window.hide()

                # 4. 根据 task 类型调用 add_focus
                if task == 'range':
                    scheduler.add_focus(time_range=[hs, ms])
                elif task == 'point':
                    scheduler.add_focus(time_point=[hs, ms])

                # 5. 显示进行中的UI元素
                self.focusicon.show()
                self.focus_time.show()

        except AttributeError as e:
            # 捕获访问方法（如 text, setText, hide, show）时的属性错误
            print(
                f"[错误] run_focus: 访问UI元素的方法或属性时出错: {e}。请确保对象已正确初始化且类型正确。"
            )
        except KeyError as e:
            # 这个理论上被入口检查覆盖了，但保留
            print(f"[错误] run_focus: 访问 'Scheduler' worker 时出错: {e}。")
        except TypeError as e:
            # 捕获调用 add_focus 时可能因 hs, ms 类型不匹配引发的错误
            print(
                f"[错误] run_focus: 调用 add_focus 时参数类型错误: {e}。请检查 hs ('{hs}') 和 ms ('{ms}') 是否为预期类型。"
            )
        except Exception as e:
            # 捕获 add_focus 内部可能抛出的其他异常，或其他未知错误
            print(f"[错误] run_focus: 执行启动时发生未知错误: {e}")

    def change_focus_menu(self):
        """
        重置专注时间菜单项/按钮的显示状态，通常在专注任务被外部取消或结束后调用。

        如果专注任务当前状态为"正在运行"（通过 `self.focus_clock` 的文本 "取消专注任务" 判断），则：
        1. 将 `self.focus_clock` 的文本改回 "专注时间"。
        2. 隐藏专注任务相关的图标 (`self.focusicon`) 和时间显示 (`self.focus_time`)。

        此方法主要负责UI状态的同步，不直接影响专注任务的运行逻辑。
        """
        try:
            # 入口检查：确保必要的UI元素存在
            required_attrs = ['focus_clock', 'focusicon', 'focus_time']
            for attr in required_attrs:
                if not hasattr(self, attr):
                    print(
                        f"[错误] change_focus_menu: 缺少必要的属性 'self.{attr}'。操作中止。"
                    )
                    return
            if not (
                hasattr(self.focus_clock, 'text')
                and callable(self.focus_clock.text)
                and hasattr(self.focus_clock, 'setText')
                and callable(self.focus_clock.setText)
            ):
                print(
                    f"[错误] change_focus_menu: 'self.focus_clock' 对象缺少 text 或 setText 方法。操作中止。"
                )
                return
            if not (
                hasattr(self.focusicon, 'hide')
                and callable(self.focusicon.hide)
                and hasattr(self.focus_time, 'hide')
                and callable(self.focus_time.hide)
            ):
                print(
                    f"[错误] change_focus_menu: 'self.focusicon' 或 'self.focus_time' 对象缺少 hide 方法。操作中止。"
                )
                return

            # 核心逻辑：检查是否需要重置
            if self.focus_clock.text() == "取消专注任务":

                # 1. 恢复文本为"未运行"状态
                self.focus_clock.setText("专注时间")

                # 2. 隐藏进行中的UI元素
                self.focusicon.hide()
                self.focus_time.hide()

        except AttributeError as e:
            # 这个捕获主要用于防御性，以防hasattr检查后对象状态改变或其他属性访问错误
            print(f"[错误] change_focus_menu: 访问UI元素的方法或属性时出错: {e}。")
        except Exception as e:
            # 捕获其他在 getText, setText, hide 调用中可能发生的未知错误
            print(f"[错误] change_focus_menu: 执行菜单状态更改时发生未知错误: {e}")

    def show_remind(self):
        """
        切换提醒设置窗口 (`self.remind_window`) 的可见性。

        - 如果窗口可见，则隐藏它。
        - 如果窗口隐藏，则计算一个新位置（通常在主窗口上方居中），然后显示窗口。
        """
        try:
            if self.remind_window.isVisible():
                # 场景 1: 窗口可见，隐藏它
                self.remind_window.hide()
            else:
                # 场景 2: 窗口隐藏，计算位置并显示
                try:
                    new_pos = self._calculate_popup_position(self.remind_window)
                    self.remind_window.move(new_pos)
                    self.remind_window.show()

                except (TypeError, ValueError) as e:
                    print(
                        f"[错误] show_remind: 在计算窗口位置时发生类型或值错误: {e}。检查 width/height 和 pos 的返回值。"
                    )
                except Exception as e:
                    print(
                        f"[错误] show_remind: 在尝试定位并显示提醒窗口时发生错误: {e}"
                    )

        except AttributeError as e:
            print(f"[错误] show_remind: 访问UI元素属性时出错: {e}。")
        except Exception as e:
            # 捕获其他意外的基础错误
            print(f"[错误] show_remind: 执行切换可见性操作时发生未知错误: {e}")

    def run_remind(self, task_type, hs=0, ms=0, texts=''):
        """
        向调度器添加一个提醒任务。

        根据 `task_type` 调用 `self.workers['Scheduler'].add_remind` 方法，
        并传递相应的参数来定义提醒的时间（范围、特定时间点）和是否重复。

        支持的 `task_type`:
        - 'range': 在指定时间范围 [hs, ms] 后提醒一次。
        - 'point': 在指定时间点 [hs, ms] 提醒一次。
        - 'repeat_interval': 每隔 [hs, ms] 时间重复提醒。
        - 'repeat_point': 在每天的指定时间点 [hs, ms] 重复提醒。

        如果 `task_type` 无效，则打印错误信息。
        """
        try:
            # 入口检查：确保 worker 和 add_remind 方法存在
            if not hasattr(self, 'workers') or not isinstance(self.workers, dict):
                print(
                    f"[错误] run_remind: 'self.workers' 字典不存在或类型错误。操作中止。"
                )
                return

            if 'Scheduler' not in self.workers:
                print(
                    f"[错误] run_remind: 'self.workers' 字典中缺少 'Scheduler' 键。操作中止。"
                )
                return
            scheduler = self.workers['Scheduler']

            if not (
                hasattr(scheduler, 'add_remind') and callable(scheduler.add_remind)
            ):
                print(
                    f"[错误] run_remind: 'Scheduler' worker 没有 'add_remind' 方法。操作中止。"
                )
                return

            # 核心逻辑：根据 task_type 调用 add_remind
            if task_type == 'range':
                scheduler.add_remind(texts=texts, time_range=[hs, ms])
            elif task_type == 'point':
                scheduler.add_remind(texts=texts, time_point=[hs, ms])
            elif task_type == 'repeat_interval':
                # 注意: 'time_range' 用于重复间隔可能不直观，请确认 add_remind 的实现
                scheduler.add_remind(texts=texts, time_range=[hs, ms], repeat=True)
            elif task_type == 'repeat_point':
                scheduler.add_remind(texts=texts, time_point=[hs, ms], repeat=True)
            else:
                print(
                    f"[错误] run_remind: 无效的任务类型 '{task_type}'。无法添加提醒。"
                )

        except TypeError as e:
            # 捕获调用 add_remind 时因参数类型错误 (hs, ms, texts, repeat) 引发的异常
            print(
                f"[错误] run_remind: 调用 add_remind 时参数类型错误: {e}。检查 hs='{hs}', ms='{ms}', texts='{texts}' 类型。"
            )
        except Exception as e:
            # 捕获 add_remind 内部可能抛出的其他异常，或未知错误
            print(f"[错误] run_remind: 添加提醒任务时发生未知错误: {e}")

    def runAnimation(self):
        """
        初始化并启动动画处理的后台线程和工作者对象。

        执行步骤：
        1. 创建一个新的 QThread 对象并存储在 `self.threads['Animation']`。
        2. 创建一个 `Animation_worker` 实例 (传入宠物配置) 并存储在 `self.workers['Animation']`。
        3. 将 `Animation_worker` 移动到新创建的线程中。
        4. 连接线程的 `started` 信号到工作者的 `run` 方法。
        5. 连接工作者发出的信号 (`sig_setimg_anim`, `sig_move_anim`, `sig_repaint_anim`)
           到主线程中对应的槽函数 (`self.set_img`, `self._move_customized`, `self.repaint`)。
        6. 启动线程。
        7. 允许线程被外部终止 (setTerminationEnabled)。
        """
        module_name = 'Animation'

        try:
            # --- 核心逻辑 ---
            # 1. 创建线程对象
            self.threads[module_name] = QThread()

            # 2. 创建工作者对象
            #    需要确保 Animation_worker 类可用且构造函数接受 self.pet_conf
            if (
                'Animation_worker' not in globals()
                and 'Animation_worker' not in locals()
            ):
                print(
                    f"[错误] runAnimation: 'Animation_worker' 类未定义或导入。无法创建工作者。"
                )
                # 清理已创建的线程对象
                del self.threads[module_name]
                return
            try:
                self.workers[module_name] = Animation_worker(self.pet_conf, settings = self.settings)
            except Exception as e:
                print(f"[错误] runAnimation: 创建 'Animation_worker' 实例失败: {e}")
                del self.threads[module_name]  # 清理线程
                return

            # 3. 移动到线程
            self.workers[module_name].moveToThread(self.threads[module_name])

            # 4. 连接线程启动信号到工作者运行方法
            self.threads[module_name].started.connect(self.workers[module_name].run)

            # 5. 连接工作者信号到主线程槽函数
            #    需要确保 worker 有这些信号，主线程有这些槽函数
            self.worker = self.workers[module_name]
            if hasattr(self.worker, 'sig_setimg_anim'):
                self.worker.sig_setimg_anim.connect(self.set_img)
            else:
                print(
                    f"[警告] runAnimation: Animation_worker 缺少 sig_setimg_anim 信号。"
                )

            if hasattr(self.worker, 'sig_move_anim'):
                self.worker.sig_move_anim.connect(self._move_customized)
            else:
                print(
                    f"[警告] runAnimation: Animation_worker 缺少 sig_move_anim 信号。"
                )

            if hasattr(self.worker, 'sig_repaint_anim'):
                self.worker.sig_repaint_anim.connect(self.repaint)
            else:
                print(
                    f"[警告] runAnimation: Animation_worker 缺少 sig_repaint_anim 信号。"
                )

            # 6. 启动线程
            self.threads[module_name].start()

            # 7. 设置线程可终止
            self.threads[module_name].setTerminationEnabled()

        except KeyError as e:
            print(
                f"[错误] runAnimation: 访问字典 key 时出错: {e}。可能发生在线程/worker未成功创建。"
            )
        except TypeError as e:
            # 例如，connect 时信号或槽不匹配，或 moveToThread 参数错误
            print(
                f"[错误] runAnimation: 类型错误: {e}。可能发生在信号槽连接或对象移动时。"
            )
        except Exception as e:
            # 捕获其他所有意外错误
            print(f"[错误] runAnimation: 启动动画线程时发生未知错误: {e}")
            # 尝试清理，防止留下部分初始化的状态
            if module_name in self.threads:
                del self.threads[module_name]
            if module_name in self.workers:
                del self.workers[module_name]


    def runInteraction(self):
        """
        初始化并启动交互处理的后台线程和工作者对象。

        执行步骤：
        1. 创建一个新的 QThread 对象并存储在 `self.threads['Interaction']`。
        2. 创建一个 `Interaction_worker` 实例 (传入宠物配置) 并存储在 `self.workers['Interaction']`。
        3. 将 `Interaction_worker` 移动到新创建的线程中。
        4. 连接工作者发出的信号 (`sig_setimg_inter`, `sig_move_inter`, `sig_act_finished`)
           到主线程中对应的槽函数 (`self.set_img`, `self._move_customized`, `self.resume_animation`)。
        5. 启动线程。
        6. 允许线程被外部终止 (setTerminationEnabled)。
        """
        module_name = 'Interaction'
        try:
            # --- 核心逻辑 ---
            # 1. 创建线程
            self.threads[module_name] = QThread()

            # 2. 创建
            try:
                self.workers[module_name] = Interaction_worker(self.pet_conf, settings = self.settings)
            except Exception as e:
                print(f"[错误] runInteraction: 创建 'Interaction_worker' 实例失败: {e}")
                del self.threads[module_name]
                return

            # 3. 移动到线程
            self.workers[module_name].moveToThread(self.threads[module_name])

            # 4. 连接工作者信号到主线程槽
            self.worker = self.workers[module_name]
            if hasattr(self.worker, 'sig_setimg_inter'):
                self.worker.sig_setimg_inter.connect(self.set_img)
            else:
                print(
                    f"[警告] runInteraction: Interaction_worker 缺少 sig_setimg_inter 信号。"
                )

            if hasattr(self.worker, 'sig_move_inter'):
                self.worker.sig_move_inter.connect(self._move_customized)
            else:
                print(
                    f"[警告] runInteraction: Interaction_worker 缺少 sig_move_inter 信号。"
                )

            if hasattr(self.worker, 'sig_act_finished'):
                self.worker.sig_act_finished.connect(self.resume_animation)
            else:
                print(
                    f"[警告] runInteraction: Interaction_worker 缺少 sig_act_finished 信号。"
                )

            # 6. 启动线程
            self.threads[module_name].start()

            # 7. 设置线程可终止
            self.threads[module_name].setTerminationEnabled()

        except KeyError as e:
            print(f"[错误] runInteraction: 访问字典 key 时出错: {e}。")
        except TypeError as e:
            print(f"[错误] runInteraction: 类型错误: {e}。")
        except Exception as e:
            print(f"[错误] runInteraction: 启动交互线程时发生未知错误: {e}")
            if module_name in self.threads:
                del self.threads[module_name]
            if module_name in self.workers:
                del self.workers[module_name]

    def runScheduler(self):
        """
        初始化并启动计划任务处理的后台线程和工作者对象。
        执行步骤：
        1. 创建一个新的 QThread 对象并存储在 `self.threads['Scheduler']`。
        2. 创建一个 `Scheduler_worker` 实例 (传入宠物配置) 并存储在 `self.workers['Scheduler']`。
        3. 连接调度器线程(`self.threads['Scheduler']`) 的 `started` 信号到工作者的 `run` 方法。
        4. 连接 `Scheduler_worker` 发出的多个信号到主线程中对应的槽函数。
        5. 启动调度器线程(`self.threads['Scheduler']`)。
        6. 允许调度器线程被外部终止。
        """
        scheduler_module_name = 'Scheduler'
        interaction_thread_name = 'Interaction'

        try:
            # --- 核心逻辑 ---
            # 1. 创建调度器线程
            self.threads[scheduler_module_name] = QThread()

            # 2. 创建调度器工作者
            try:
                self.workers[scheduler_module_name] = Scheduler_worker(self.pet_conf, settings = self.settings)
            except Exception as e:
                print(f"[错误] runScheduler: 创建 'Scheduler_worker' 实例失败: {e}")
                del self.threads[scheduler_module_name]
                return

            self.workers[scheduler_module_name].moveToThread(
                self.threads[interaction_thread_name]
            )

            # 3. 连接调度器线程的 started 到 run (可能行为异常，见步骤3注释)
            self.threads[scheduler_module_name].started.connect(
                self.workers[scheduler_module_name].run
            )

            # 4. 连接工作者信号到主线程槽
            self.worker = self.workers[scheduler_module_name]
            signals_to_connect = {
                'sig_settext_sche': self._set_dialogue_dp,
                'sig_setact_sche': self._show_act,
                'sig_setstat_sche': self._change_status,
                'sig_focus_end': self.change_focus_menu,
                'sig_tomato_end': self.change_tomato_menu,
                'sig_settime_sche': self._change_time,
            }
            for signal_name, slot_func in signals_to_connect.items():
                if hasattr(self.worker, signal_name):
                    getattr(self.worker, signal_name).connect(slot_func)
                else:
                    print(
                        f"[警告] runScheduler: Scheduler_worker 缺少 {signal_name} 信号。"
                    )

            # 5. 启动调度器线程
            self.threads[scheduler_module_name].start()

            # 6. 设置调度器线程可终止
            self.threads[scheduler_module_name].setTerminationEnabled()

        except KeyError as e:
            print(
                f"[错误] runScheduler: 访问字典 key 时出错: {e} (可能是 '{interaction_thread_name}' 线程不存在，或线程/worker未成功创建)。"
            )
        except TypeError as e:
            print(f"[错误] runScheduler: 类型错误: {e}。")
        except Exception as e:
            print(f"[错误] runScheduler: 启动计划任务线程时发生未知错误: {e}")
            if scheduler_module_name in self.threads:
                del self.threads[scheduler_module_name]
            if scheduler_module_name in self.workers:
                del self.workers[scheduler_module_name]

    def _move_customized(self, plus_x, plus_y):
        """
        根据给定的偏移量 (`plus_x`, `plus_y`) 移动窗口，并处理边界碰撞逻辑。

        行为包括：
        - 水平方向：如果窗口移出屏幕边界，则实现循环滚动（从一边消失，从另一边出现）。
        - 垂直方向：
            - 如果窗口尝试移动到屏幕顶部以上，则限制其位置。 (原代码逻辑是限制在 y=0 以下)
            - 如果窗口移动到或低于预设的"地面"位置 (`self.floor_pos`)，则将其固定在地面上。
            - 当首次接触地面时 (`settings.onfloor == 0` 变为 1)，会重置宠物图片为默认站立图，
              并尝试恢复动画 (`self.workers['Animation'].resume()`)。
        """
        try:
            # --- 核心逻辑 ---
            current_pos = self.pos()

            # 计算初步的新坐标
            new_x = current_pos.x() + plus_x
            new_y = current_pos.y() + plus_y

            # 1. 水平边界处理 (循环滚动)
            # -------------------------
            win_width = self.width()  # 获取窗口宽度

            # 判断是否超出左边界 (考虑边距 self.border)
            if new_x + win_width < self.border:
                new_x = self.screen_width + self.border - win_width

            # 判断是否超出右边界 (考虑边距 self.border)
            elif new_x > self.screen_width + self.border - win_width:
                new_x = self.border - win_width

            # 2. 垂直边界处理
            # -----------------
            # 限制不能移到屏幕顶部以上 (原代码判断 y+border < 0，可能依赖border含义)
            if new_y + self.border < 0:  # 简单的顶部限制
                new_y = self.floor_pos  # 固定在顶部
                # print(f"[调试信息] 碰到上边界, new_y 重置为 {new_y}") # 仅用于调试，发布时删除

            # 判断是否接触或低于地面
            elif new_y >= self.floor_pos:
                new_y = self.floor_pos  # 固定在地面上

                try:
                    if self.settings.onfloor == 0:
                        self.settings.onfloor = 1  # 标记为在地面上
                        # 设置默认站立图片
                        self.settings.current_img = self.pet_conf.default.images[0]
                        self.set_img()  # 更新显示图片
                        # 恢复动画
                        self.workers['Animation'].resume()

                except AttributeError as e:
                    print(
                        f"[错误] _move_customized: 访问 settings 或 pet_conf 属性时出错: {e}。落地状态更新失败。"
                    )
                except IndexError as e:
                    print(
                        f"[错误] _move_customized: 访问默认图片列表时索引错误 (可能列表为空): {e}。落地状态更新失败。"
                    )
                except Exception as e:
                    print(f"[错误] _move_customized: 处理落地逻辑时发生未知错误: {e}。")

            # 3. 应用最终计算出的位置
            # -----------------------
            self.move(int(new_x), int(new_y))  # 确保传入整数

        except (TypeError, ValueError) as e:
            # 捕获 plus_x/y 非数值，或 int() 转换失败等错误
            print(
                f"[错误] _move_customized: 计算新位置时发生类型或值错误: {e}。输入: plus_x={plus_x}, plus_y={plus_y}"
            )
        except AttributeError as e:
            # 捕获 前置检查 后，实际访问 self 属性/方法时仍可能发生的错误
            print(f"[错误] _move_customized: 访问对象属性或方法时出错: {e}。")
        except KeyError as e:
            # 捕获访问 self.workers['Animation'] 时 key 不存在的错误
            print(f"[错误] _move_customized: 访问 workers 字典时键错误: {e}。")
        except Exception as e:
            # 捕获其他所有意外错误
            print(f"[错误] _move_customized: 执行移动时发生未知错误: {e}")

    def _show_act(self, random_act_name):
        """
        触发一个特定的交互动作。

        执行步骤：
        1. 暂停当前的常规动画 (`self.workers['Animation'].pause()`)。
        2. 启动交互工作者 (`self.workers['Interaction']`) 来执行指定的动作 (`random_act_name`)。
           交互动作通常是临时的，完成后会通过信号 (`sig_act_finished`) 通知主流程恢复常规动画。
        """
        # 1. 暂停动画
        self.workers['Animation'].pause()
        # 2. 启动交互
        self.workers['Interaction'].start_interact('animat', random_act_name)

    def resume_animation(self):
        """
        恢复（或继续执行）常规的动画循环。

        通常在交互动作完成 (`sig_act_finished` 信号触发) 后被调用，
        或者在需要手动恢复动画的场景下使用。
        """
        self.workers['Animation'].resume()

    def __del__(self):
        self.stop_thread('Animation')
        self.stop_thread('Interaction')
        self.stop_thread('Scheduler')
        pass



def _load_all_pic(pet_name: str) -> dict:
    """
    加载指定宠物名称对应的所有动作图片资源。

    函数会查找 'res/role/{pet_name}/action/' 目录下的所有图片文件，
    并将它们加载为图片对象 (通过 `_get_q_img` 函数)。
    返回一个字典，其中键是动作名称 (通常是去掉扩展名的文件名)，值是加载的图片对象。
    """
    # 1. 构建图片目录路径
    img_dir = 'res/role/{}/action/'.format(pet_name)
    # 2. 列出目录中的所有文件/目录
    images = os.listdir(img_dir)
    # 3. 返回成功加载的图片字典
    return {image.split('.')[0]: _get_q_img(img_dir + image) for image in images}


def _build_act(name: str, parent: QObject, act_func) -> QAction:
    """
    构建一个 QAction 对象（菜单项或工具栏按钮）。
    """
    try:
        # 1. 创建 QAction 实例
        act = QAction(name, parent)

        # 2. 连接 triggered 信号到 lambda 函数
        act.triggered.connect(lambda: act_func(name))

        # 3. 返回创建的 Action
        return act

    except TypeError as e:
        # 主要捕获 QAction 构造或 connect 时因参数类型错误引发的问题
        print(f"[错误] _build_act: 创建 QAction '{name}' 失败，类型错误: {e}")
        return None
    except Exception as e:
        # 捕获其他未知错误
        print(f"[错误] _build_act: 创建 QAction '{name}' 时发生未知错误: {e}")
        return None


def _get_q_img(img_path: str) -> Optional[QImage]:
    """
    从指定的路径加载图片为 QImage 对象。
    """
    try:
        # 1. 创建空的 QImage 对象
        image = QImage()

        # 2. 尝试加载图片
        #    QImage.load() 会返回 bool 值指示成功与否
        if image.load(img_path):
            # 3. 加载成功，返回 QImage 对象
            return image
        else:
            # 4. 加载失败 (文件格式不支持、文件损坏等)
            print(
                f"[警告] _get_q_img: 无法加载图片 (可能格式不支持或文件损坏): '{img_path}'"
            )
            return None  # 返回 None 表示失败

    except Exception as e:
        # 捕获 QImage 构造、load 或 os.path.isfile 中可能发生的其他意外错误
        print(f"[错误] _get_q_img: 加载图片 '{img_path}' 时发生未知错误: {e}")
        return None


def text_wrap(texts: str, line_length: int = 7) -> str:
    """
    将输入字符串按指定行长度进行换行处理。
    """
    try:
        n_char = len(texts)
        # 计算需要的行数 (向上取整)
        n_line = (n_char + line_length - 1) // line_length

        texts_wrapped = ''
        # 逐行构建包装后的文本
        for i in range(n_line):
            start_index = line_length * i
            # 使用切片获取当前行的子字符串，min() 确保不会超出字符串末尾
            end_index = min(start_index + line_length, n_char)
            texts_wrapped += texts[start_index:end_index] + '\n'

        # 移除末尾多余的换行符
        texts_wrapped = texts_wrapped.rstrip('\n')

        return texts_wrapped

    except Exception as e:
        # 捕获在长度计算、切片或拼接中可能出现的意外错误
        print(f"[错误] text_wrap: 处理文本换行时发生未知错误: {e}")
        return ''  # 返回空字符串表示失败


if __name__ == '__main__':
    """
    应用程序主入口点。
    加载宠物数据，创建并显示宠物窗口。
    """
    pets_data = None
    app = None  # 初始化为 None，便于 finally 中检查

    try:
        # 1. 加载宠物数据
        pets_file = 'data/pets.json'
        try:
            pets_data = read_json(pets_file)
            if not pets_data:
                print(f"[错误] 未能从 '{pets_file}' 加载有效的宠物数据。")
                sys.exit(1)  # 数据加载失败，无法继续，退出
        except FileNotFoundError:
            print(f"[错误] 宠物数据文件未找到: '{pets_file}'")
            sys.exit(1)
        except Exception as e:  # 捕获 JSON 解析错误或其他 read_json 内部错误
            print(f"[错误] 加载或解析宠物数据 '{pets_file}' 时失败: {e}")
            sys.exit(1)

        # 2. 创建 Qt Application 实例
        app = QApplication(sys.argv)

        # 3. 创建主窗口部件 (PetWidget)
        p = PetWidget(pets=pets_data)

        # 4. 启动 Qt 事件循环
        exit_code = app.exec_()
        sys.exit(exit_code)  # 使用 Qt 应用的退出码退出

    except ImportError as e:
        print(f"[严重错误] 缺少必要的库: {e}。")
        sys.exit(1)
    except NameError as e:
        print(f"[严重错误] 必要的类或函数未定义: {e}。")
        sys.exit(1)
    except Exception as e:
        print(f"[严重错误] 应用程序启动或运行时发生未知错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)  # 发生严重错误，以错误码退出
