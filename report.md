## (1) 程序功能介绍——初稿

Petal 项目是一款桌面宠物应用程序，旨在为用户的桌面环境增添一位可爱的虚拟伴侣，并提供一些实用的小工具。

### 主要功能模块：

1.  **桌面宠物显示与动画**：
    *   在桌面上以无边框窗口形式显示一个宠物角色（例如 "Kitty"）。
    *   宠物拥有多种预设的动画效果，例如行走、跳跃、思考、被拖拽时的特定动作、掉落动画等。
    *   宠物会根据内部设定的概率随机执行不同的动画序列，使其看起来更具活力和自主性。

2.  **宠物状态管理**：
    *   **HP (生命值)**：通过界面上的进度条显示。HP会随着时间推移自动缓慢减少。该机制由 `Scheduler_worker` 中的 `change_hp` 方法和 `pet_conf.hp_interval` 配置控制。
    *   **EM (情绪值/能量值)**：同样通过界面进度条显示，并随时间自动缓慢减少。该机制由 `Scheduler_worker` 中的 `change_em` 方法和 `pet_conf.em_interval` 配置控制。
    *   *(当前版本主要实现了状态值的自动减少，通过物品或特定交互来恢复/提升状态的功能有待进一步开发。)*

3.  **用户交互**：
    *   **鼠标拖拽**：用户可以通过鼠标左键按住并拖动宠物在桌面上的位置。此功能由 `PetWidget` 中的 `mousePressEvent` 和 `mouseMoveEvent` 处理。
    *   **拖拽后抛出/掉落**：当用户释放鼠标后，宠物会根据释放时的速度和方向继续“滑行”一段距离，并模拟重力效果自然下落，直到接触屏幕边缘或预设的“地面”。此逻辑主要在 `Interaction_worker` 的 `mousedrag` 和 `drop` 方法中实现，并利用 `settings` 模块中的 `dragspeedx`, `dragspeedy`, `gravity` 等参数。
    *   **右键菜单 (ContextMenu)**：右键点击宠物会弹出一个上下文菜单。菜单项在 `PetWidget` 的 `_show_right_menu` 方法中定义，可能包含退出程序、切换宠物、打开设置等功能。

4.  **计划任务与实用工具 (由 `Scheduler_worker` 管理)**：
    *   **番茄钟**：
        *   用户可以启动一个或多个番茄钟序列。
        *   每个番茄钟包含一段工作时间（默认为25分钟）和一段休息时间（默认为5分钟）。
        *   程序会通过对话框和可能的UI更新（如计时器显示）来提醒用户工作开始、休息开始以及整个番茄钟序列的结束。
        *   支持在番茄钟进行中取消。
        *   如果用户在已有番茄钟或专注模式进行时尝试启动新的番茄钟，会收到冲突提示。
        *   相关方法：`add_tomato`, `run_tomato`, `change_tomato`, `cancel_tomato`。
    *   **专注模式**：
        *   用户可以设定一段专注时间，可以按持续时长（例如X小时Y分钟）或指定一个具体的结束时间点（例如HH:MM）。
        *   在专注模式期间，宠物可能会有特定表现（当前代码未明确，但框架已搭好）。
        *   专注开始和结束时，程序会通过对话框提醒用户。
        *   支持在专注模式进行中取消。
        *   如果用户在已有番茄钟或专注模式进行时尝试启动新的专注模式，会收到冲突提示。
        *   相关方法：`add_focus`, `run_focus`, `change_focus`, `cancel_focus`。
    *   **提醒事项**：
        *   用户可以添加提醒事项，并设定提醒时间。
        *   提醒时间可以是一次性的，也可以是重复性的。
        *   时间设定方式支持相对时间（例如X小时Y分钟后）或绝对时间点（例如每天的HH:MM，或特定日期的HH:MM）。
        *   到达设定时间后，宠物会通过对话框显示提醒内容。
        *   相关方法：`add_remind`, `run_remind`。
    *   **定时问候**：
        *   宠物会根据当前系统时间（早上、中午、下午、晚上）自动向用户发出相应的问候语。
        *   相关方法：`greeting`, `run` (在 `Scheduler_worker` 初始化时调用)。

5.  **多宠物支持 (基础)**：
    *   系统通过 `data/pets.json` 文件管理可用的宠物列表及其对应的配置文件路径。
    *   `PetWidget` 在初始化时可以接收一个包含所有可用宠物名称的元组，并加载指定的或默认的第一个宠物。
    *   理论上支持通过右键菜单或其他方式切换当前显示的宠物角色，但这部分UI交互逻辑在当前代码中未完全明确。

6.  **配置与资源管理**：
    *   宠物的外观、动画帧、行为参数（如移动速度、刷新率、HP/EM减少间隔等）通过JSON配置文件（例如 `data/Kitty.json`）进行定义。
    *   图像资源（动画帧、图标）、字体等存储在 `res/` 目录下。

## (2) 项目各模块与类设计细节

### 1. 主程序入口 (`run_Petaler.py`)

*   **功能**：作为应用程序的启动脚本。
*   **主要职责**：
    *   加载基础宠物数据 (从 `data/pets.json` 读取可用宠物列表)。
    *   初始化 `QApplication` 实例，这是所有 PyQt5 GUI应用的必需步骤。
    *   应用全局样式表 (QSS)，定义如进度条等UI元素的外观。
    *   创建并显示主宠物窗口 `PetWidget`。
    *   启动 Qt 事件循环 (`app.exec_()`)。

### 2. `Petaler` 包 (核心逻辑)

#### 2.1. `Petaler.py` -> `PetWidget(QWidget)` 类

*   **功能**：核心UI类，代表桌面上的宠物窗口。
*   **主要职责与设计**：
    *   **窗口设置**：初始化为一个无边框、总在最前、背景透明的窗口 (`_init_widget` 方法)。
    *   **宠物配置加载**：通过 `init_conf(pet_name)` 方法加载指定宠物的配置信息 (`PetConfig` 对象)、图像资源字典 (`pic_dict`) 和宠物特定数据 (如HP, EM初始值)。
    *   **UI元素**：包含用于显示宠物图像的 `QLabel` (`self.label`)，以及显示HP和EM的 `QProgressBar` (`self.PetHP`, `self.PetEM`)。这些在 `_init_ui` 和 `_setup_ui` 中设置。
    *   **事件处理**：
        *   `mousePressEvent`: 处理鼠标按下。左键按下时，记录拖拽起始位置，设置拖拽状态 (`settings.draging = 1`, `settings.onfloor = 0`)，暂停常规动画，并启动 `Interaction_worker` 的 `mousedrag` 交互。
        *   `mouseMoveEvent`: 处理鼠标移动。如果处于拖拽状态，则根据鼠标位移移动窗口，并记录鼠标轨迹点 (用于计算释放速度)。
        *   `mouseReleaseEvent`: 处理鼠标松开。结束拖拽状态 (`settings.draging = 0`)，根据释放时的速度和方向计算抛出效果 (更新 `settings.dragspeedx`, `settings.dragspeedy`)，恢复常规动画，并让 `Interaction_worker` 处理后续的掉落逻辑。
        *   `contextMenuEvent` / `_show_right_menu`: 实现右键点击宠物时显示上下文菜单的功能。
        *   `enterEvent` / `leaveEvent`: 处理鼠标进入/离开宠物窗口的事件 (当前代码中未见具体逻辑，但方法已定义)。
    *   **线程管理**：创建并管理三个核心后台工作线程：
        *   `Animation_worker`: 负责宠物的常规动画播放和随机行为。
        *   `Interaction_worker`: 负责处理用户交互（如拖拽、点击后的特定动画）和交互引发的物理效果（如掉落）。
        *   `Scheduler_worker`: 负责处理所有定时任务（HP/EM变化、番茄钟、专注模式、提醒、问候）。
        *   通过 `self.threads` (存储 `QThread` 对象) 和 `self.workers` (存储 Worker 对象) 进行管理。Worker对象会被移动到对应的 `QThread` 中执行。
    *   **信号与槽连接**：连接来自各个 Worker 线程的信号到 `PetWidget` 内部的槽函数，以更新UI（如设置图像 `_set_image_from_worker`，移动窗口 `_move_widget_from_worker`，显示对话框 `_set_text_from_worker` 等）。
    *   **系统托盘**：`_init_tray` 方法初始化系统托盘图标及其菜单 (当前代码中托盘菜单功能较简单，主要是退出)。

#### 2.2. `modules.py` (后台工作逻辑)

包含三个核心的 Worker 类，它们都继承自 `QObject` 以便利用 Qt 的信号槽机制和线程支持。

*   **`Animation_worker(QObject)` 类**
    *   **功能**：驱动宠物的常规动画播放和随机行为。
    *   **主要职责与设计**：
        *   `run()`: 线程主循环。在此循环中，不断调用 `random_act()` 选择并执行一个随机的动作序列，然后根据宠物配置的刷新率 (`pet_conf.refresh`) 休眠。
        *   `random_act()`: 根据宠物配置中定义的动作概率 (`pet_conf.act_prob`) 随机选择一个动作序列 (`pet_conf.random_act[act_index]`)。
        *   `_run_acts(acts: List[Act])` 和 `_run_act(act: Act)`: 依次执行一个动作序列中的每个 `Act` 对象。对于每个 `Act`，循环播放其包含的所有图像帧 (`act.images`)。
        *   在播放每帧动画时，会更新全局的 `settings.current_img`，并通过 `sig_setimg_anim` 信号通知 `PetWidget` 更新显示。如果动作定义了移动 (`act.direction`, `act.frame_move`)，则通过 `sig_move_anim` 信号通知 `PetWidget` 移动。
        *   支持 `pause()`, `resume()`, `kill()` 方法来控制线程的执行状态。

*   **`Interaction_worker(QObject)` 类**
    *   **功能**：处理用户交互（如鼠标拖拽、点击特定区域）以及这些交互引发的后续行为（如抛出、掉落、特定动画序列）。
    *   **主要职责与设计**：
        *   使用 `QTimer` (`self.timer`) 以固定的间隔 (`pet_conf.interact_speed`) 调用 `run()` 方法。
        *   `run()`: 根据 `self.interact` (一个字符串，表示当前交互类型) 和 `self.act_name` (关联的动作名) 调用相应的处理方法。
        *   `start_interact(interact, act_name)`: 由 `PetWidget` 调用，用于设置当前要处理的交互类型和动作。
        *   `mousedrag(act_name)`: 处理鼠标拖拽时的动画（播放 `pet_conf.drag` 动画）和拖拽结束后的掉落逻辑。掉落时会播放 `pet_conf.fall` 动画，并根据 `settings.dragspeedx`, `settings.dragspeedy` 和 `pet_conf.gravity` 计算位移，通过 `sig_move_inter` 信号通知 `PetWidget` 移动，直到 `settings.onfloor` 变为1（接触地面）。
        *   `animat(act_name)`: 执行一个预定义的、完整的动画序列（由多个 `Act` 组成），例如用户点击某个按钮后触发的特定表演。通过 `sig_act_finished` 信号通知动画序列播放完毕。
        *   `img_from_act(act)`: 辅助方法，根据给定的 `Act` 对象和当前的播放进度 (`settings.playid`)，确定并设置 `settings.current_img`。
        *   同样支持 `pause()`, `resume()`, `kill()`。

*   **`Scheduler_worker(QObject)` 类**
    *   **功能**：管理所有基于时间的计划任务。
    *   **主要职责与设计**：
        *   使用 `APScheduler` (specifically `QtScheduler`) 来安排和触发任务。
        *   **HP/EM 自动减少**：在 `__init__` 中通过 `scheduler.add_job` 添加周期性任务 (`interval.IntervalTrigger`)，分别调用 `change_hp()` 和 `change_em()`。这两个方法会发出 `sig_setstat_sche` 信号，通知 `PetWidget` 更新状态值。
        *   **问候语**：在 `run()` 方法（通常在线程启动时执行一次）中调用 `greeting(time)` 获取当前时间的问候语，并通过 `show_dialogue` 显示。
        *   **番茄钟** (`add_tomato`, `run_tomato`, `change_tomato`, `cancel_tomato`)：
            *   `add_tomato`: 根据用户设定的番茄数量，使用 `scheduler.add_job` 和 `date.DateTrigger` 安排一系列任务：开始第一个番茄、第一个番茄结束（进入休息）、开始后续番茄、后续番茄结束、最后一个番茄结束。
            *   `run_tomato`: 作为这些定时任务的回调函数。根据传入的 `task_text`（如 'tomato_start', 'tomato_end', 'tomato_last'）执行相应逻辑，如设置 `self.tomato_timeleft`，添加/移除用于每分钟更新时间的 `change_tomato` 任务，发出 `sig_settime_sche` 信号更新UI显示，以及通过 `show_dialogue` 显示提示信息。
            *   `change_tomato`: 由一个 `interval.IntervalTrigger` 任务每分钟调用，减少 `self.tomato_timeleft` 并更新UI。
        *   **专注模式** (`add_focus`, `run_focus`, `change_focus`, `cancel_focus`)：逻辑与番茄钟类似，但通常是一个连续的时间段。`add_focus` 可以按时长或结束时间点设置。`run_focus` 处理开始、结束、冲突等情况。`change_focus` 每分钟更新剩余专注时间。
        *   **提醒事项** (`add_remind`, `run_remind`)：
            *   `add_remind`: 允许用户设置一次性或重复性的提醒。重复提醒使用 `cron.CronTrigger` (按时分) 或 `interval.IntervalTrigger` (按时间间隔)。一次性提醒使用 `date.DateTrigger`。
            *   `run_remind`: 作为提醒任务的回调，通过 `show_dialogue` 显示提醒内容。
        *   `show_dialogue(texts_toshow)`: 辅助方法，用于依次显示一系列对话文本。它会发出 `sig_settext_sche` 信号通知 `PetWidget` 显示文本，并在每条文本后暂停一段时间。使用 `settings.showing_dialogue_now` 作为简单的锁，避免对话框重叠。
        *   同样支持 `pause()`, `resume()`, `kill()`，这些方法会相应地暂停/恢复/关闭内部的 `scheduler`。

#### 2.3. `conf.py` (配置类定义)

*   **`PetConfig` 类**
    *   **功能**：封装从JSON配置文件中读取的宠物所有配置信息。
    *   **主要属性**：`petname`, `refresh` (动画刷新间隔), `interact_speed` (交互逻辑刷新间隔), `size` (宠物图像基本尺寸), `hp_interval`, `em_interval` (HP/EM减少间隔), `gravity` (重力加速度), `drag` (拖拽动画对应的 `Act` 对象), `fall` (掉落动画对应的 `Act` 对象), `random_act` (随机动作列表，每个元素是一个 `Act` 对象或 `Act` 对象列表), `act_prob` (随机动作的概率分布) 等。
    *   可能包含加载JSON文件并解析到类属性的逻辑。

*   **`Act` 类**
    *   **功能**：表示一个具体的动作单元，例如一次行走、一次跳跃。
    *   **主要属性**：`act_name`, `images` (组成该动作的图像帧列表，通常是图像文件名或 `QPixmap` 对象), `frame_refresh` (该动作内部帧之间的刷新间隔), `frame_move` (每帧的移动距离), `direction` (移动方向: 'left', 'right', 'up', 'down', None), `act_num` (该动作重复执行的次数) 等。

#### 2.4. `settings.py` (全局状态与变量)

*   **功能**：提供一个全局共享状态的模块。由于Python模块的单例特性，这里定义的变量可以在项目的不同部分被访问和修改。
*   **主要变量 (推测与观察到的)**：
    *   `current_img`, `previous_img`: 当前和上一帧显示的宠物图像 (可能是 `QPixmap` 或图像路径)。
    *   `current_act`, `previous_act`: 当前和上一个执行的 `Act` 对象。
    *   `playid`: 当前 `Act` 中图像帧的播放索引。
    *   `act_id`: 在一个由多个 `Act` 组成的动画序列中，当前执行到第几个 `Act` 的索引。
    *   `draging`: 标志位，表示宠物是否正在被鼠标拖拽 (1=是, 0=否)。
    *   `onfloor`: 标志位，表示宠物是否在“地面”上 (1=是, 0=否)。用于控制掉落行为。
    *   `set_fall`: 标志位，是否启用掉落行为。
    *   `fall_right`: 掉落时图像是否需要水平镜像。
    *   `dragspeedx`, `dragspeedy`: 宠物在X轴和Y轴的当前速度（用于抛出和掉落）。
    *   `mouseposx1`...`mouseposx4`, `mouseposy1`...`mouseposy4`: 最近几次鼠标事件的X, Y坐标，用于计算拖拽释放时的速度。
    *   `showing_dialogue_now`: 布尔值，用于 `Scheduler_worker` 的 `show_dialogue` 方法，防止对话框重叠。
    *   `init()`: 可能是一个初始化这些全局变量的函数。

#### 2.5. `utils.py` (工具函数)

*   **功能**：提供项目中通用的辅助函数。
*   **主要函数 (已知与推测)**：
    *   `read_json(filepath)`: 读取并解析JSON文件。
    *   `load_pet_conf(conf_path)`: (可能存在) 专门用于加载宠物JSON配置并返回 `PetConfig` 对象的函数。
    *   `get_abs_path(filename, path)`: (可能存在) 用于获取资源文件的绝对路径。
    *   图像加载和处理函数 (例如，将图像文件列表转换为 `QPixmap` 对象列表)。

#### 2.6. `extra_windows.py` (额外窗口)

*   **功能**：可能包含项目中除主宠物窗口外的其他独立窗口，例如设置窗口、关于窗口等。
*   **设计细节**：具体内容需要查看该文件。如果存在设置窗口，它可能会允许用户修改宠物的行为参数、选择宠物、管理提醒事项等，并通过信号或直接修改配置文件/`settings`模块与主程序交互。

### 3. `data` 目录 (数据文件)

*   `pets.json`: 一个JSON文件，通常是一个列表或字典，定义了所有可用的宠物及其对应的详细配置文件路径。例如：
    ```json
    {
        "pets": [
            {"name": "Kitty", "config": "data/Kitty.json"},
            {"name": "Doggy", "config": "data/Doggy.json"}
        ]
    }
    ```
*   `Kitty.json` (及其他宠物配置文件): 每个宠物详细的JSON配置文件，其结构对应 `PetConfig` 类所期望的格式。包含HP/EM初始值、动画定义、行为参数等。
*   `remindme.txt`: 用于持久化存储用户设置的提醒事项。其具体格式需要分析 `Scheduler_worker` 中加载和保存提醒的逻辑（如果已实现）。

### 4. `res` 目录 (资源文件)

*   `font/`: 存放应用程序使用的自定义字体文件 (如 `.otf`, `.ttf`)。
*   `icons/`: 存放各种图标文件 (如 `.png`)，用于系统托盘、按钮、状态显示等。
*   `role/PetName/`: 每个宠物角色独立的资源文件夹，存放该角色的所有图像帧、动画序列对应的图片等。        