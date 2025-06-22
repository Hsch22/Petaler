# Petal 桌面宠物系统实验报告

## 一、项目背景与目标

### 1.1 项目初衷与设计理念

Petal 是一个基于 PyQt5 开发的桌面宠物应用系统，旨在为用户的数字办公环境提供情感陪伴与效率辅助功能。项目通过可爱的虚拟宠物形象，结合实用的时间管理工具，为长时间使用计算机的用户创造更加温馨和高效的工作体验。

项目设计理念体现在以下几个方面：
- **情感化交互**：通过拟人化的宠物形象和丰富的动画表现，为用户提供心理慰藉
- **功能性结合**：将娱乐性与实用性相结合，集成番茄钟、专注模式等效率工具
- **可扩展性**：采用配置文件驱动的设计，支持多种宠物类型和行为定制
- **技术实践**：作为学习项目，全面实践 GUI 开发、多线程编程、配置管理等技术

### 1.2 主要设计目标

1. **提供情感陪伴功能**
   - 实现多种宠物角色（Doggy、Kitty、Petal）
   - 丰富的动画表现和随机行为
   - 自然的用户交互体验

2. **集成效率管理工具**
   - 番茄钟工作法支持
   - 专注模式和时间管理
   - 灵活的提醒事项系统

3. **技术架构实践**
   - PyQt5 GUI 框架应用
   - 多线程并发处理
   - 配置文件系统设计
   - 模块化代码组织

### 1.3 目标用户群体

- 需要长时间使用计算机的办公人员
- 希望改善工作效率的学生和研究人员
- 对桌面定制和个性化有需求的用户
- 学习 PyQt5 和 GUI 开发的技术人员

---

## 二、系统功能介绍

### 2.1 双重系统架构

Petal 项目采用了双重系统架构设计：

#### 2.1.1 纯桌面宠物模式 (`run_Petal.py`)
- 直接启动桌面宠物窗口，支持多实例运行
- 轻量级设计，专注于宠物展示和基础交互
- 通过定时器支持批量创建多个宠物实例

#### 2.1.2 完整管理界面模式 (`run_Petaler.py`)
- 提供完整的主窗口管理系统
- 集成侧边栏导航和多页面切换
- 支持宠物创建、管理和系统设置
- 暗色主题界面设计

### 2.2 桌面宠物显示与动画系统

#### 2.2.1 动画播放机制
宠物动画由 `Animation_worker` 线程类负责管理：
- **随机动作选择**：基于概率分布 (`act_prob`) 自动选择动作序列
- **帧动画播放**：支持多帧图像序列播放，可配置帧刷新率
- **动作组合**：支持复合动作序列，如 `["fall_asleep", "sleep"]`
- **方向性移动**：支持左右行走等带方向的移动动作

#### 2.2.2 动画配置系统
每个宠物通过两个配置文件定义行为：
- `pet_conf.json`：基础参数（尺寸、缩放、刷新率、动作概率等）
- `act_conf.json`：具体动作定义（图像序列、移动参数、播放次数等）

### 2.3 宠物状态管理系统

#### 2.3.1 状态值类型
- **HP（生命值）**：红色进度条显示，定时自动减少
- **EM（情绪值/能量值）**：黄色进度条显示，定时自动减少
- **FC（专注值）**：蓝色进度条，专注模式时显示

#### 2.3.2 状态更新机制
由 `Scheduler_worker` 定时任务管理：
- 通过 `change_hp()` 和 `change_em()` 方法定时减少状态值
- 状态变化间隔由配置文件的 `hp_interval` 和 `em_interval` 控制
- 支持通过信号机制实时更新 UI 显示

### 2.4 用户交互功能

#### 2.4.1 鼠标拖拽交互
由 `Interaction_worker` 处理复杂的拖拽逻辑：
- **拖拽检测**：`mousePressEvent` 启动拖拽状态
- **实时跟随**：`mouseMoveEvent` 实现宠物跟随鼠标移动
- **物理模拟**：`mouseReleaseEvent` 触发掉落和惯性运动
- **速度计算**：基于鼠标移动历史计算拖拽速度和方向

#### 2.4.2 物理模拟系统
实现了真实的物理效果：
```python
# 重力模拟
self.dragspeedy += self.pet_conf.gravity
# 摩擦力衰减
if speed > self.drag_speed_threshold:
    self.dragspeedx *= (1 - self.drag_base_friction)
    self.dragspeedy *= (1 - self.drag_base_friction)
```

#### 2.4.3 右键菜单系统
- 退出程序
- 宠物切换（支持多种宠物类型）
- 打开设置窗口
- 功能快捷入口

### 2.5 计划任务与效率工具

#### 2.5.1 番茄钟功能 (`Tomato` 类)
- **多周期支持**：用户可设置连续执行的番茄钟数量
- **标准时长**：默认 25 分钟工作 + 5 分钟休息
- **冲突检测**：防止与专注模式同时运行
- **状态提醒**：开始、结束、完成时的对话框提示
- **中途取消**：支持任意时刻取消当前番茄钟

#### 2.5.2 专注模式 (`Focus` 类)
提供两种专注模式：
- **持续时长模式**：设置专注持续的小时和分钟数
- **定时结束模式**：设置专注结束的具体时间点
- **专属动画**：专注期间可触发特定动画表现
- **结束提醒**：专注结束时的明确提示

#### 2.5.3 提醒事项系统 (`Remindme` 类)
支持多种提醒模式：
- **一次性提醒**：相对时间（如"30 分钟后"）或绝对时间
- **重复提醒**：每日定时、间隔重复等
- **文本编辑**：提供右侧文本区域编辑和保存提醒内容
- **自动保存**：提醒内容自动保存到 `remindme.txt`

#### 2.5.4 定时问候功能
- 基于系统时间的智能问候（早、午、晚）
- 天气信息集成（通过 `python_weather` 库）
- 地理位置自动识别（通过 `geocoder` 库）

### 2.6 多宠物支持系统

#### 2.6.1 宠物类型管理
- 通过 `data/pets.json` 文件定义可用宠物类型
- 每种宠物有独立的资源目录和配置文件
- 支持运行时动态切换宠物类型

#### 2.6.2 资源组织结构
```
res/role/{pet_name}/
├── img.png              # 宠物预览图
├── pet_conf.json        # 基础配置
├── act_conf.json        # 动作配置
└── action/              # 动画帧图片目录
    ├── stand_0.png
    ├── leftwalk_0.png
    └── ...
```

### 2.7 系统托盘功能

- 程序最小化到系统托盘
- 托盘右键菜单快速操作
- 托盘图标状态指示

---

## 三、系统架构与模块设计

### 3.1 总体架构设计

Petal 项目采用分层模块化架构，主要包含以下几个层次：

```
应用层 (Application Layer)
├── 主程序入口 (run_Petaler.py / run_Petal.py)
├── 主窗口管理 (MainWindow/)
└── 用户界面 (PetWidget, extra_windows)

业务逻辑层 (Business Logic Layer)  
├── 动画控制 (Animation_worker)
├── 交互处理 (Interaction_worker)
└── 任务调度 (Scheduler_worker)

数据层 (Data Layer)
├── 配置管理 (PetConfig, Act)
├── 状态管理 (PetData, Settings)
└── 资源管理 (utils, 图片加载)
```

### 3.2 主程序入口设计

#### 3.2.1 `run_Petaler.py` - 主管理程序
```python
class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = None
        self.init_platform_style()  # 设置 Fusion 暗色主题
        self.setup_logging()        # 配置日志系统
```

主要职责：
- 应用程序生命周期管理
- 全局样式设置（暗色主题）
- 主窗口单例模式管理
- 日志系统配置

#### 3.2.2 `run_Petal.py` - 纯宠物模式
```python
def create_pet_widget(pets_json_path, curr_pet_name: str = ''):
    pets_data = read_json(pets_json_path)
    pet = PetWidget(pets=pets_data, curr_pet_name=curr_pet_name)
    pet.show()
    return pet
```

主要职责：
- 宠物数据加载
- 样式表应用
- 支持多实例创建
- 轻量级启动流程

### 3.3 核心类与模块设计

#### 3.3.1 `PetWidget` 类 - 主窗口控制器

**初始化流程：**
```python
def __init__(self, parent=None, curr_pet_name='', pets=()):
    # 1. 安全性检查
    if not curr_pet_name and not pets:
        raise ValueError("必须提供宠物名称或宠物列表")
    
    # 2. 基础属性初始化
    self.pets = pets
    self.settings = Settings()
    self.curr_pet_name = curr_pet_name
    
    # 3. UI 组件初始化
    self._init_ui()      # 创建进度条、标签等UI元素
    self._init_widget()  # 设置窗口属性
    
    # 4. 配置加载
    self.init_conf(initial_pet_name_to_load)
    
    # 5. 后台线程启动
    self.runAnimation()
    self.runInteraction() 
    self.runScheduler()
```

**核心方法：**
- `mousePressEvent/mouseMoveEvent/mouseReleaseEvent`：鼠标事件处理
- `init_conf()`：加载宠物配置和资源
- `set_img()`：更新显示图像
- 各种任务启动方法：`show_tomato()`, `show_focus()`, `show_remind()`

#### 3.3.2 `Animation_worker` 类 - 动画处理器

**核心运行逻辑：**
```python
def run(self):
    while not self.is_killed:
        self.random_act()  # 随机选择动作
        if self._check_pause_kill():
            break
        time.sleep(self.pet_conf.refresh)

def random_act(self):
    prob_num = random.uniform(0, 1)
    act_index = sum(int(prob_num > self.pet_conf.act_prob[i]) 
                   for i in range(len(self.pet_conf.act_prob)))
    acts = self.pet_conf.random_act[act_index]
    self._run_acts(acts)
```

**信号系统：**
- `sig_setimg_anim`：请求更新图像
- `sig_move_anim`：请求移动宠物
- `sig_repaint_anim`：请求重绘

#### 3.3.3 `Interaction_worker` 类 - 交互处理器

**核心交互方法：**
```python
def mousedrag(self, act_name):
    """处理鼠标拖拽动画"""
    while self.settings.draging:
        self.sig_setimg_inter.emit()
        time.sleep(self.pet_conf.interact_speed / 1000)

def drop(self):
    """处理拖拽释放后的掉落动画"""
    while not self.settings.onfloor:
        # 重力和速度计算
        self.settings.dragspeedy += self.pet_conf.gravity
        # 位置更新
        self.sig_move_inter.emit(self.settings.dragspeedx, self.settings.dragspeedy)
```

#### 3.3.4 `Scheduler_worker` 类 - 任务调度器

**基于 APScheduler 的任务管理：**
```python
def __init__(self, pet_conf, parent=None, settings=None):
    self.scheduler = QtScheduler()
    self.scheduler.start()

def add_tomato(self, n_tomato=None):
    """添加番茄钟任务"""
    self.scheduler.add_job(
        func=self.run_tomato,
        trigger=date.DateTrigger(run_date=start_time),
        args=[task_text],
        id=f'tomato_{start_time}',
        replace_existing=True
    )
```

**支持的任务类型：**
- 状态值定时减少（`change_hp`, `change_em`）
- 番茄钟计时和提醒
- 专注模式计时
- 自定义提醒事项
- 定时问候

### 3.4 配置与数据管理

#### 3.4.1 `PetConfig` 类 - 宠物配置管理

**配置加载流程：**
```python
@classmethod
def init_config(cls, pet_name: str, pic_dict: dict):
    config_instance = cls()
    
    # 1. 加载基础配置 (pet_conf.json)
    with open(pet_conf_path, 'r', encoding='UTF-8') as f:
        conf_params = json.load(f)
    
    # 2. 加载动作配置 (act_conf.json)
    with open(act_conf_path, 'r', encoding='UTF-8') as f:
        act_conf = json.load(f)
    
    # 3. 创建 Act 实例
    act_dict = {
        act_name: Act.init_act(act_params, pic_dict, scale, pet_name)
        for act_name, act_params in act_conf.items()
    }
    
    return config_instance
```

**配置参数类型：**
- 基础参数：尺寸、缩放、刷新率
- 物理参数：重力、拖拽速度、掉落速度
- 动作映射：default, up, down, left, right, drag, fall
- 随机动作：动作组合、概率分布、显示名称
- 状态间隔：HP和EM的减少间隔

#### 3.4.2 `Act` 类 - 动作定义

**动作属性：**
```python
class Act:
    def __init__(self, images, act_num=1, need_move=False, 
                 direction=None, frame_move=10.0, frame_refresh=0.04):
        self.images = images        # QImage 序列
        self.act_num = act_num      # 重复次数
        self.need_move = need_move  # 是否需要移动
        self.direction = direction  # 移动方向
        self.frame_move = frame_move    # 每帧移动距离
        self.frame_refresh = frame_refresh  # 帧刷新间隔
```

#### 3.4.3 `Settings` 类 - 全局状态管理

**状态变量分类：**
```python
class Settings:
    def __init__(self):
        # 图像状态
        self.current_img = QImage()
        self.previous_img = QImage()
        
        # 物理状态
        self.onfloor = 1      # 是否在地面
        self.draging = 0      # 是否正在拖拽
        self.set_fall = 1     # 是否允许掉落
        
        # 拖拽参数
        self.dragspeedx = 0.0
        self.dragspeedy = 0.0
        self.drag_base_friction = 0.1
        
        # 鼠标历史位置（用于速度计算）
        self.mouseposx1-5 = 0
        self.mouseposy1-5 = 0
```

### 3.5 辅助窗口系统

#### 3.5.1 `extra_windows.py` 模块

**包含的窗口类：**
- `Tomato`：番茄钟设置窗口
- `Focus`：专注模式设置窗口  
- `Remindme`：提醒事项设置窗口

**共同特性：**
- 自动字体缩放适配
- 信号驱动的数据传递
- 响应式布局设计
- 统一的样式规范

#### 3.5.2 窗口交互模式

```python
class Tomato(QWidget):
    close_tomato = pyqtSignal()
    confirm_tomato = pyqtSignal(int)
    
    def confirm(self):
        n_tomato = self.n_tomato.value()
        self.confirm_tomato.emit(n_tomato)
        self.close()
```

### 3.6 主窗口管理系统

#### 3.6.1 `MainWindow` 类设计

**主要组件：**
- `SideBar`：侧边导航栏
- `QStackedWidget`：多页面容器
- 宠物管理页面：添加、删除、计数管理
- 设置页面：系统配置选项

**宠物实例管理：**
```python
def add_pet(self, pet_type):
    # 创建新的宠物实例
    pet_instance = petal.create_pet_widget('data/pets.json', pet_type)
    self.pet_instances.append(pet_instance)
    self.pet_counts[pet_type] += 1
    self.update_controls(pet_type)

def remove_pet(self, pet_type):
    # 安全移除宠物实例
    for inst in reversed(self.pet_instances):
        if inst.curr_pet_name == pet_type:
            inst.close()
            inst.deleteLater()
            self.pet_instances.remove(inst)
            break
```

---

## 四、关键技术实现细节

### 4.1 多线程架构设计

#### 4.1.1 线程间通信机制
```python
# 主线程中连接信号与槽
self.workers['Animation'].sig_setimg_anim.connect(self.set_img)
self.workers['Animation'].sig_move_anim.connect(self._move_customized)
self.workers['Interaction'].sig_move_inter.connect(self._move_customized)
```

#### 4.1.2 线程生命周期管理
```python
def stop_thread(self, module_name):
    if module_name in self.workers:
        self.workers[module_name].kill()
        self.threads[module_name].quit()
        self.threads[module_name].wait()
        del self.workers[module_name]
        del self.threads[module_name]
```

### 4.2 动画系统实现

#### 4.2.1 帧动画播放
```python
def _run_act(self, act: Act):
    for _ in range(act.act_num):
        for img in act.images:
            self.settings.current_img = img
            self.sig_setimg_anim.emit()
            time.sleep(act.frame_refresh)
            self._move(act)
```

#### 4.2.2 概率驱动的行为选择
```python
# 配置示例 (pet_conf.json)
{
    "random_act": [
        ["default"],
        ["left_walk", "right_walk", "default"], 
        ["fall_asleep", "sleep"]
    ],
    "act_prob": [0.85, 0.1, 0.15]
}
```

### 4.3 物理模拟系统

#### 4.3.1 鼠标速度计算
```python
# 基于历史位置计算拖拽速度
self.settings.dragspeedx = (
    (self.settings.mouseposx1 - self.settings.mouseposx5) / 
    self.settings.fixdragspeedx
)
```

#### 4.3.2 重力和摩擦力模拟
```python
# 重力影响
self.settings.dragspeedy += self.pet_conf.gravity

# 摩擦力衰减
if speed > self.settings.drag_speed_threshold:
    self.settings.dragspeedx *= (1 - self.settings.drag_base_friction)
    self.settings.dragspeedy *= (1 - self.settings.drag_base_friction)
```

### 4.4 配置文件系统

#### 4.4.1 动态图片加载
```python
def _load_all_pic(pet_name: str) -> dict:
    """加载指定宠物的所有图片资源"""
    pic_dict = {}
    role_path = f'res/role/{pet_name}'
    
    # 遍历 action 目录下的所有图片文件
    action_path = os.path.join(role_path, 'action')
    for img_file in os.listdir(action_path):
        if img_file.endswith('.png'):
            img_path = os.path.join(action_path, img_file)
            img_name = os.path.splitext(img_file)[0]
            pic_dict[img_name] = QImage(img_path)
    
    return pic_dict
```

#### 4.4.2 配置验证和错误处理
```python
# Act.init_act 中的安全检查
if not list_image_files:
    raise FileNotFoundError(f"找不到动作图片文件: {img_dir_pattern}_*.png")

try:
    original_image = pic_dict[image_key]
except KeyError:
    raise KeyError(f"图片字典缺少键 '{image_key}'")
```

---

## 五、项目总结与反思

### 5.1 项目成果总结

#### 5.1.1 功能实现成果
本项目成功实现了一个功能完整的桌面宠物系统，具备以下核心能力：

1. **完善的动画系统**：支持多帧动画、概率驱动的随机行为、流畅的动作切换
2. **丰富的交互体验**：真实的物理拖拽、重力模拟、摩擦力衰减
3. **实用的效率工具**：番茄钟、专注模式、提醒系统的完整实现
4. **灵活的配置机制**：JSON 驱动的宠物定义、支持多种宠物类型
5. **稳定的多线程架构**：动画、交互、调度三线程并行，信号槽通信

#### 5.1.2 技术架构优势

1. **模块化设计**：清晰的职责分离，便于维护和扩展
2. **配置文件驱动**：支持非开发人员定制宠物行为
3. **多线程并发**：避免界面阻塞，提供流畅的用户体验
4. **错误处理机制**：完善的异常捕获和日志记录
5. **跨平台兼容**：基于 PyQt5，支持 Windows、macOS、Linux

### 5.2 技术亮点分析

#### 5.2.1 动画系统设计亮点

**概率驱动的行为模式**：
```python
# 通过累积概率实现加权随机选择
act_index = sum(int(prob_num > self.pet_conf.act_prob[i]) 
               for i in range(len(self.pet_conf.act_prob)))
```
这种设计使得宠物行为看起来更加自然和随机，避免了固定模式的单调感。

**帧动画与移动结合**：
每个 `Act` 不仅包含图像序列，还包含移动参数，实现了动画与位移的同步。

#### 5.2.2 物理模拟系统亮点

**真实的拖拽体验**：
- 基于鼠标移动历史计算速度
- 重力、摩擦力的物理模拟
- 边界碰撞检测

这种实现让用户感受到宠物具有真实的"重量感"和"惯性"。

#### 5.2.3 任务调度系统亮点

**基于 APScheduler 的灵活任务管理**：
- 支持一次性、重复性、定时任务
- 任务冲突检测和优雅取消
- 异步执行不阻塞主界面

### 5.3 存在的不足与局限

#### 5.3.1 功能层面的不足

1. **状态恢复机制缺失**：HP 和 EM 值只减不增，缺乏通过互动或物品恢复的机制
2. **多宠物交互有限**：多个宠物实例之间缺乏互动
3. **个性化定制不足**：用户无法通过界面直接修改宠物配置
4. **音效系统缺失**：缺乏音频反馈增强用户体验

#### 5.3.2 技术层面的改进空间

1. **内存管理**：长时间运行可能存在内存泄漏风险
2. **配置热更新**：修改配置后需要重启程序才能生效
3. **错误恢复能力**：部分异常情况下可能导致线程死锁
4. **性能优化**：动画刷新频率较高，在低性能设备上可能卡顿

#### 5.3.3 代码质量方面

1. **文档不够完善**：部分复杂算法缺乏详细注释
2. **测试覆盖不足**：缺乏单元测试和集成测试
3. **代码重复**：某些功能在不同模块中有重复实现
4. **依赖管理**：第三方库版本管理有待完善

### 5.4 经验教训与收获

#### 5.4.1 技术学习收获

1. **GUI 开发经验**：熟练掌握 PyQt5 的信号槽机制、布局管理、事件处理
2. **多线程编程**：深入理解线程间通信、同步机制、生命周期管理
3. **配置系统设计**：学会设计灵活可扩展的配置文件系统
4. **项目组织经验**：掌握大型 Python 项目的模块化组织方法

#### 5.4.2 开发过程经验

1. **需求分析重要性**：前期需求分析不充分导致后期多次重构
2. **测试驱动开发**：缺乏测试导致后期调试困难
3. **版本控制意识**：重要功能开发前应该创建分支
4. **文档先行原则**：代码文档应该与开发同步进行

### 5.5 未来发展方向

#### 5.5.1 功能扩展计划

1. **AI 行为系统**：
   - 集成简单的机器学习模型，让宠物根据用户习惯调整行为
   - 增加情感识别，根据用户状态提供不同反应

2. **社交功能**：
   - 多用户宠物互访
   - 宠物状态云同步
   - 社区分享功能

3. **增强现实集成**：
   - 摄像头集成，让宠物"看到"用户
   - 语音交互功能
   - 手势识别

#### 5.5.2 技术优化方向

1. **性能优化**：
   - 动画帧率自适应调节
   - 内存使用优化
   - GPU 加速渲染

2. **架构升级**：
   - 微服务化改造
   - 插件系统设计
   - 热更新机制

3. **用户体验提升**：
   - 更丰富的视觉效果
   - 触觉反馈支持
   - 无障碍设计

### 5.6 结语

Petal 桌面宠物系统作为一个技术学习项目，成功地将理论知识转化为实际可用的软件产品。项目不仅实现了既定的功能目标，更重要的是在开发过程中积累了宝贵的工程经验。

通过这个项目，我们深入实践了 GUI 开发、多线程编程、系统设计等核心技术，同时也认识到了软件工程中测试、文档、版本控制等环节的重要性。项目的成功之处在于创造了一个真正能为用户带来价值的产品，而不足之处则为我们指明了持续改进的方向。

未来，随着技术的不断发展和用户需求的变化，Petal 系统具备了良好的扩展性基础，可以在现有架构上持续演进，最终成为一个更加智能、友好、实用的桌面伴侣系统。