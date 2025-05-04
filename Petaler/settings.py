from PyQt5.QtGui import QImage

current_img: QImage = None
previous_img: QImage = None

# 物理、拖拽与掉落状态
onfloor: int = 1        # 是否在“地面”上 
draging: int = 0        # 是否正在被拖拽 
set_fall: int = 1       # 是否允许掉落/拖拽
playid: int = 0        
mouseposx1: int = 0     # 鼠标历史位置 X 
mouseposx2: int = 0
mouseposx3: int = 0
mouseposx4: int = 0
mouseposx5: int = 0
mouseposy1: int = 0     # 鼠标历史位置 Y
mouseposy2: int = 0
mouseposy3: int = 0
mouseposy4: int = 0
mouseposy5: int = 0
dragspeedx: float = 0.0 # 当前拖拽速度 X 
dragspeedy: float = 0.0 # 当前拖拽速度 Y
fixdragspeedx: float = 4.0 # 用于计算拖拽速度的固定值 X
fixdragspeedy: float = 2.5 # 用于计算拖拽速度的固定值 Y 
fall_right: int = 0      

# 动画状态
act_id: int = 0          # 当前选中的动作ID 
current_act = None       # 当前动作对象/数据 
previous_act = None      # 上一个动作对象/数据

# 对话框状态 
showing_dialogue_now: bool = False # 当前是否正在显示对话框 


def init():
    """
    初始化应用程序所需的全局状态变量。
    """
    global current_img, previous_img,\
        onfloor, draging, set_fall, playid,\
        mouseposx1, mouseposx2, mouseposx3, mouseposx4, mouseposx5,\
        mouseposy1, mouseposy2, mouseposy3, mouseposy4, mouseposy5,\
        dragspeedx, dragspeedy, fixdragspeedx, fixdragspeedy, fall_right,\
        act_id, current_act, previous_act,\
        showing_dialogue_now 
    

    current_img = QImage()
    previous_img = QImage()

    # 物理、拖拽与掉落相关
    onfloor = 1         # 初始状态在地面上
    draging = 0         # 初始状态未被拖拽
    set_fall = 1        # 默认允许拖拽/掉落
    playid = 0

    # 鼠标历史位置
    mouseposx1 = 0
    mouseposx2 = 0
    mouseposx3 = 0
    mouseposx4 = 0
    mouseposx5 = 0
    mouseposy1 = 0
    mouseposy2 = 0
    mouseposy3 = 0
    mouseposy4 = 0
    mouseposy5 = 0

    # 拖拽速度与参数
    dragspeedx = 0.0
    dragspeedy = 0.0
    fixdragspeedx = 4.0 # 用于计算拖拽速度的常量X
    fixdragspeedy = 2.5 # 用于计算拖拽速度的常量Y 
    fall_right = 0      # 初始掉落方向状态

    # 动画相关
    act_id = 0          # 默认动作ID 
    current_act = None
    previous_act = None

    # 对话框相关
    showing_dialogue_now = False # 初始不显示对话框