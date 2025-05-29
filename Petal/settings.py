from PyQt5.QtGui import QImage

class Settings:
    def __init__(self):
        """
        初始化应用程序所需的全局状态变量。
        """
        self.current_img = QImage()
        self.previous_img = QImage()

        # 物理、拖拽与掉落相关
        self.onfloor = 1  # 初始状态在地面上
        self.draging = 0  # 初始状态未被拖拽
        self.set_fall = 1  # 默认允许拖拽/掉落
        self.playid = 0

        # 鼠标历史位置
        self.mouseposx1 = 0
        self.mouseposx2 = 0
        self.mouseposx3 = 0
        self.mouseposx4 = 0
        self.mouseposx5 = 0
        self.mouseposy1 = 0
        self.mouseposy2 = 0
        self.mouseposy3 = 0
        self.mouseposy4 = 0
        self.mouseposy5 = 0

        # 拖拽速度与参数
        self.dragspeedx = 0.0
        self.dragspeedy = 0.0
        self.fixdragspeedx = 4.0  # 用于计算拖拽速度的常量X
        self.fixdragspeedy = 2.5  # 用于计算拖拽速度的常量Y
        self.drag_base_friction: float = 0.1  # 速度衰减系数，越大衰减越快
        self.drag_speed_threshold: float = 20.0  # 速度阈值，大于该值才施加阻力
        self.fall_right = 0  # 初始掉落方向状态

        # 动画相关
        self.act_id = 0  # 默认动作ID
        self.current_act = None
        self.previous_act = None

        # 对话框相关
        self.showing_dialogue_now = False  # 初始不显示对话框