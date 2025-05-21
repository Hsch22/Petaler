# -*- coding: utf-8 -*-
"""
定义宠物配置、动作和状态数据的类。

PetConfig: 加载和管理宠物的静态配置（外观、行为、动作）。
Act: 代表宠物的一个具体动作，包含动画帧和参数。
PetData: 管理宠物的动态状态（HP、EM、物品），并进行持久化存储。
"""

import json
import glob
import os.path
import time
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage 

RES_ROLE_PATH_TPL = 'res/role/{pet_name}/'
PET_CONF_FILENAME = 'pet_conf.json'
ACT_CONF_FILENAME = 'act_conf.json'
ACTION_IMG_PATH_TPL = 'action/{image_base_name}'
DATA_PATH_TPL = 'data/{pet_name}.json'

class Act:
    """
    代表宠物的一个具体动作。

    封装了执行该动作所需的动画帧图像序列和相关参数。
    """
    def __init__(self,
                 images: tuple[QImage, ...], 
                 act_num: int = 1,
                 need_move: bool = False,
                 direction: Optional[str] = None,
                 frame_move: float = 10.0, 
                 frame_refresh: float = 0.04):
        """
        初始化一个动作实例。
        """
        self.images = images
        self.act_num = act_num
        self.need_move = need_move
        self.direction = direction
        self.frame_move = frame_move
        self.frame_refresh = frame_refresh

    @classmethod
    def init_act(cls,
                 conf_param: dict,
                 pic_dict: dict[str, QImage],
                 scale: float,
                 pet_name: str) -> 'Act': 
        """
        从配置参数和预加载图片创建并初始化一个 Act 实例。
        """
        image_base_name = conf_param['images'] # 动作图片的基础名称
        role_path = RES_ROLE_PATH_TPL.format(pet_name=pet_name)
        action_img_path = ACTION_IMG_PATH_TPL.format(image_base_name=image_base_name)
        img_dir_pattern = os.path.join(role_path, action_img_path) # 使用 os.path.join 构造路径

        # 使用 glob 查找所有帧图片文件
        list_image_files = sorted(glob.glob(f'{img_dir_pattern}_*.png')) # 排序确保帧顺序
        if not list_image_files:
            raise FileNotFoundError(f"在 '{os.path.dirname(img_dir_pattern)}' 目录下找不到名为 '{os.path.basename(img_dir_pattern)}_*.png' 的图片文件。")

        n_images = len(list_image_files)
        processed_images = []
        for i in range(n_images):
            image_key = f"{image_base_name}_{i}"
            try:
                original_image = pic_dict[image_key]
            except KeyError:
                raise KeyError(f"图片字典 (pic_dict) 中缺少键 '{image_key}'，无法加载动作 '{image_base_name}' 的第 {i} 帧。")

            # 应用缩放
            scaled_image = original_image.scaled(
                int(original_image.width() * scale),
                int(original_image.height() * scale),
                aspectRatioMode=Qt.KeepAspectRatio,
                transformMode=Qt.SmoothTransformation # 添加平滑变换以获得更好的效果
            )
            processed_images.append(scaled_image)


        act_num = conf_param.get('act_num', 1)
        need_move = conf_param.get('need_move', False)
        direction = conf_param.get('direction', None)
        frame_move = float(conf_param.get('frame_move', 10.0)) * scale
        frame_refresh = float(conf_param.get('frame_refresh', 0.5))

        # 返回创建的 Act 实例，使用元组存储图片
        return cls(images=tuple(processed_images),
                   act_num=act_num,
                   need_move=need_move,
                   direction=direction,
                   frame_move=frame_move,
                   frame_refresh=frame_refresh)


class PetConfig:
    """
    存储和管理特定种类宠物的静态配置信息。

    从 JSON 文件加载配置，并初始化所有相关的动作 (Act 实例)。
    """

    def __init__(self):
        """初始化一个空的 PetConfig 实例，所有属性设为默认值。"""
        self.petname: Optional[str] = None
        self.width: float = 128.0
        self.height: float = 128.0
        self.scale: float = 1.0

        self.refresh: int = 5 
        self.interact_speed: float = 20.0 
        self.dropspeed: float = 1.0 
        self.gravity: float = 4.0 

        # 核心动作属性，将在 init_config 中被赋值为 Act 实例
        self.default: Optional[Act] = None
        self.up: Optional[Act] = None
        self.down: Optional[Act] = None
        self.left: Optional[Act] = None
        self.right: Optional[Act] = None
        self.drag: Optional[Act] = None
        self.fall: Optional[Act] = None

        # 随机动作相关属性
        self.random_act: list[list[Act]] = [] # 存储分组的随机动作 Act 实例列表
        self.act_prob: list[float] = []      # 存储随机动作组的累积概率
        self.random_act_name: list[str] = [] 

        # 状态相关间隔
        self.hp_interval: int = 15 
        self.em_interval: int = 15 


    @classmethod
    def init_config(cls, pet_name: str, pic_dict: dict[str, QImage]) -> 'PetConfig':
        """
        加载指定宠物的配置并创建一个完全初始化的 PetConfig 实例。
        """
        config_instance = cls() # 创建一个 PetConfig 的空实例
        config_instance.petname = pet_name

        role_path = RES_ROLE_PATH_TPL.format(pet_name=pet_name)
        pet_conf_path = os.path.join(role_path, PET_CONF_FILENAME)
        act_conf_path = os.path.join(role_path, ACT_CONF_FILENAME)

        # 1. 加载基础宠物配置 (pet_conf.json)
        try:
            with open(pet_conf_path, 'r', encoding='UTF-8') as f:
                conf_params = json.load(f)
        except FileNotFoundError:
            print(f"错误：找不到宠物配置文件 '{pet_conf_path}'")
            raise # 重新抛出异常，让上层处理
        except json.JSONDecodeError as e:
            print(f"错误：解析宠物配置文件 '{pet_conf_path}'失败: {e}")
            raise # 重新抛出异常

        # 从配置中读取参数，使用 .get() 提供默认值
        config_instance.scale = float(conf_params.get('scale', 1.0))
        # 尺寸应用缩放
        config_instance.width = float(conf_params.get('width', 128)) * config_instance.scale
        config_instance.height = float(conf_params.get('height', 128)) * config_instance.scale

        config_instance.refresh = int(conf_params.get('refresh', 5))
        config_instance.interact_speed = float(conf_params.get('interact_speed', 0.02)) * 1000
        config_instance.dropspeed = float(conf_params.get('dropspeed', 1.0))
        config_instance.gravity = float(conf_params.get('gravity', 4.0))

        config_instance.hp_interval = int(conf_params.get('hp_interval', 15))
        config_instance.em_interval = int(conf_params.get('em_interval', 15))

        # 2. 加载动作配置 (act_conf.json) 并创建 Act 实例
        try:
            with open(act_conf_path, 'r', encoding='UTF-8') as f:
                act_conf = json.load(f) # 直接加载为字典
        except FileNotFoundError:
            print(f"错误：找不到动作配置文件 '{act_conf_path}'")
            raise
        except json.JSONDecodeError as e:
            print(f"错误：解析动作配置文件 '{act_conf_path}' 失败: {e}")
            raise

        try:
            act_dict = {
                act_name: Act.init_act(act_params, pic_dict, config_instance.scale, pet_name)
                for act_name, act_params in act_conf.items()
            }
        except (FileNotFoundError, KeyError) as e:
            print(f"错误：在为宠物 '{pet_name}' 初始化动作时发生错误: {e}")
            raise # 将图片加载或键错误传播出去

        # 3. 分配核心动作
        # 使用 try-except 块捕获可能的 KeyError，如果 pet_conf.json 引用了不存在的动作
        try:
            config_instance.default = act_dict[conf_params['default']]
            config_instance.up = act_dict[conf_params['up']]
            config_instance.down = act_dict[conf_params['down']]
            config_instance.left = act_dict[conf_params['left']]
            config_instance.right = act_dict[conf_params['right']]
            config_instance.drag = act_dict[conf_params['drag']]
            config_instance.fall = act_dict[conf_params['fall']]
        except KeyError as e:
            print(f"错误：宠物配置文件 '{pet_conf_path}' 中指定的核心动作 '{e}' 在动作配置 '{act_conf_path}' 中未定义。")
            raise

        # 4. 初始化随机动作
        random_act_groups = []
        try:
            for act_name_list in conf_params.get('random_act', []): # 使用 .get 提供空列表默认值
                act_group = [act_dict[act_name] for act_name in act_name_list]
                random_act_groups.append(act_group)
            config_instance.random_act = random_act_groups
        except KeyError as e:
            print(f"错误：宠物配置文件 '{pet_conf_path}' 的 'random_act' 中引用的动作 '{e}' 在动作配置 '{act_conf_path}' 中未定义。")
            raise

        # 5. 处理随机动作概率
        num_random_groups = len(config_instance.random_act)
        if num_random_groups > 0:
            act_prob_raw = conf_params.get('act_prob', None)

            if act_prob_raw is None or len(act_prob_raw) != num_random_groups:
                # 如果未提供概率或长度不匹配，则使用均等概率
                if act_prob_raw is not None:
                     print(f"警告：'{pet_conf_path}' 中的 'act_prob' 长度与 'random_act' 组数不匹配。将使用均等概率。")
                probabilities = [1.0 / num_random_groups] * num_random_groups
            else:
                # 归一化提供的概率
                prob_sum = sum(act_prob_raw)
                if prob_sum <= 0:
                     print(f"警告：'{pet_conf_path}' 中的 'act_prob' 总和非正。将使用均等概率。")
                     probabilities = [1.0 / num_random_groups] * num_random_groups
                else:
                     probabilities = [p / prob_sum for p in act_prob_raw]

            # 计算累积概率
            cumulative_prob = 0.0
            config_instance.act_prob = []
            for p in probabilities:
                cumulative_prob += p
                config_instance.act_prob.append(cumulative_prob)
            # 确保最后一个累积概率严格为 1.0，避免浮点数误差
            if config_instance.act_prob:
                config_instance.act_prob[-1] = 1.0

        # 6. 加载随机动作名称 (可选)
        config_instance.random_act_name = conf_params.get('random_act_name', [])
        if len(config_instance.random_act_name) != num_random_groups:
             if config_instance.random_act_name: # 只有提供了名字但不匹配时才警告
                 print(f"警告：'{pet_conf_path}' 中的 'random_act_name' 数量与 'random_act' 组数不匹配。")



        return config_instance



def tran_idx_img(start_idx: int, end_idx: int, pic_dict: dict[str, QImage]) -> list[QImage]:
    """
    从图片字典中提取指定索引范围的图像。

    假设 pic_dict 的键是数字的字符串表示形式 (e.g., '0', '1', ...)。
    """
    res = []
    # 使用 range(start, end + 1) 来包含 end_idx
    for i in range(start_idx, end_idx + 1):
        try:
            # 将索引转换为字符串作为键进行查找
            res.append(pic_dict[str(i)])
        except KeyError:
            print(f"警告/错误：在 tran_idx_img 中, 图片字典缺少键 '{str(i)}'")
    return res


class PetData:
    """
    管理单个宠物实例的动态状态数据 (HP, EM, 物品)。

    负责数据的初始化、从文件加载以及保存到文件。
    """

    def __init__(self, pet_name: str):
        """
        初始化宠物数据管理器。
        """
        if not isinstance(pet_name, str) or not pet_name:
            raise ValueError("Pet name must be a non-empty string.")

        self.petname: str = pet_name
        self.current_hp: int = 100
        self.current_em: int = 100
        self.items: dict[str, int] = {}

        self.file_path: str = os.path.join(DATA_PATH_TPL.format(pet_name=self.petname))

        self._init_data() # 使用下划线表示内部调用

    def _init_data(self):
        """
        尝试从文件加载数据，如果文件不存在则初始化默认数据并保存。
        """
        try:
            # 检查文件是否存在
            if os.path.isfile(self.file_path):
                with open(self.file_path, 'r', encoding='UTF-8') as f:
                    data_params = json.load(f)

                self.current_hp = int(data_params.get('HP', 100))
                self.current_em = int(data_params.get('EM', 100))
                loaded_items = data_params.get('items', {})

                self.items = {str(k): int(v) for k, v in loaded_items.items() if isinstance(v, (int, float))}

                print(f"成功从 '{self.file_path}' 加载宠物 '{self.petname}' 的数据。")

            else:
                print(f"未找到宠物 '{self.petname}' 的数据文件 '{self.file_path}'。将使用默认值创建新文件。")
                self.current_hp = 100
                self.current_em = 100
                self.items = {'汉堡': 1, '薯条': 2}
                self.save_data()

        except (json.JSONDecodeError, IOError, ValueError, TypeError) as e:
            # 捕获可能的加载错误 (文件损坏, 读写问题, 类型转换失败)
            print(f"加载或初始化宠物 '{self.petname}' 数据时出错: {e}。将使用默认值。")
            # 即使出错也保证有默认值
            self.current_hp = 100
            self.current_em = 100
            self.items = {'汉堡': 1, '薯条': 2}



    def save_data(self):
        """将当前宠物的状态数据保存到 JSON 文件中。"""
        # 准备要保存的数据字典，使用加载时对应的键名
        data_to_save = {
            'HP': self.current_hp,
            'EM': self.current_em,
            'items': self.items
        }

        try:
            # 确保数据目录存在
            data_dir = os.path.dirname(self.file_path)
            if data_dir: # 检查目录名是否为空 (如果就在当前目录下)
                os.makedirs(data_dir, exist_ok=True) # exist_ok=True 避免目录已存在时报错

            # 以写入模式打开文件，使用 utf-8 编码
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)


        except IOError as e:
            print(f"错误：无法将宠物 '{self.petname}' 的数据保存到 '{self.file_path}': {e}")
        except Exception as e: # 捕获其他可能的意外错误
             print(f"保存宠物 '{self.petname}' 数据时发生意外错误: {e}")
