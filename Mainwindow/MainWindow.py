from Mainwindow.common import *

from Mainwindow.SideBar import SideBar
from Mainwindow.Signals import Signals
from Mainwindow.FontSetting import set_font

import Petal.run_Petaler as petal
from Petal.utils import read_json

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):

	def __init__(self, app, width=3000, height=2000):

		super().__init__()
		self.i = 1
		self.setWindowTitle("Petal")
		self.setWindowIcon(QIcon("res/icons/icon.png"))

		pet_data = read_json("data/pets.json")
		self.pet_types = {}
		for pet in pet_data:
			self.pet_types[pet] = f"res/role/{pet}/img.png"

		# 初始化各类型桌宠数量
		self.pet_counts = {ptype: 0 for ptype in self.pet_types}
		# 保存每种类型的控件引用
		self.count_labels = {}
		self.remove_buttons = {}

		# 获取屏幕尺寸，设置主窗口位置
		self.resize(width, height)
		screen_geometry = app.primaryScreen().availableGeometry()
		self.move(screen_geometry.width() // 2 - width // 2, screen_geometry.height() // 2 - height // 2)

		# 动画管理集
		self.animations: dict[str, QPropertyAnimation] = {}

		# 主窗口中心部件（容纳 main_layout）
		self.central_widget = QWidget()
		self.setCentralWidget(self.central_widget)

		# 主布局 main_layout（容纳侧边栏和主窗口）
		self.main_layout = QHBoxLayout()
		self.main_layout.setContentsMargins(0, 10, 0, 0)
		self.main_layout.setSpacing(0)

		# 添加主区域布局
		self.central_widget.setLayout(self.main_layout)

		# 侧边栏
		self.sidebar = SideBar(self)
		self.sidebar.setMaximumWidth(230)
		self.main_layout.addWidget(self.sidebar)
		self.sidebar_visible = True
		self.setup_sidebar_animation()

		# 主窗口（设计为堆叠窗口，有多个界面）
		self.main_stack = QStackedWidget()
		self.main_layout.addWidget(self.main_stack)

		# 连接sidebar的信号
		Signals.instance().page_change_signal.connect(
			lambda page_name: self.navigate_to(page_name, stack=self.main_stack)
		)

		# 通过名称记录页面，使用字典映射
		self.main_stack_map = {}

		# 设置 main_stack各页面的内容，注意初始化顺序
		self.chat_inputs = {}
		self.chat_lists = {}
		self.setup_chatting_window()

		self.pet_instances = []


	def show_login_window(self):
		pass

	def show_register_window(self):
		pass

	def create_choose_window(self):
		chat_widget = QWidget()
		main_layout = QVBoxLayout(chat_widget)
		main_layout.setContentsMargins(20, 5, 20, 20)

		# 宠物选择框内的字体设置
		default_font = QFont()
		default_font.setPointSize(15)

		# 折叠/展开侧边栏按钮
		sidebar_btn = QPushButton('<')
		sidebar_btn.setStyleSheet("""
		            QPushButton { background-color: transparent; border: none; padding: 0; margin: 0; text-align: center; color: #a0a0a0; }
		            QPushButton:hover { color: #07C160; }
		            QPushButton:pressed { color: #05974C; }
		        """)
		set_font(sidebar_btn)
		sidebar_btn.clicked.connect(lambda checked, btn=sidebar_btn: self.toggle_sidebar(btn))
		main_layout.addWidget(sidebar_btn, alignment=Qt.AlignLeft | Qt.AlignTop)

		# 滚动区域及其容器
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)
		container = QWidget()
		container_layout = QVBoxLayout(container)
		container_layout.setSpacing(10)
		container_layout.setContentsMargins(0, 0, 0, 0)

		# 为每种桌宠类型创建带边框的选择框
		for ptype, img_path in self.pet_types.items():
			row_widget = QWidget()
			row_widget.setStyleSheet(
				"border: 1px solid #cccccc; border-radius: 8px; padding: 8px;"
			)
			row_layout = QHBoxLayout(row_widget)
			row_layout.setContentsMargins(5, 5, 5, 5)

			# 桌宠形象
			icon_label = QLabel()
			icon_label.setFixedSize(128, 128)
			icon_label.setScaledContents(True)
			pixmap = QPixmap(img_path)
			icon_label.setPixmap(pixmap)
			row_layout.addWidget(icon_label)

			# 添加按钮
			add_btn = QPushButton('添加')
			add_btn.setStyleSheet("""
			                QPushButton { background-color: transparent; border: none;padding: 25px; text-align: center; }
			                QPushButton:hover { background-color: palette(midlight); /*轻微高亮*/ border-radius: 4px; }
			                QPushButton:pressed { background-color: palette(mid);}
			            """)
			add_btn.setFont(default_font)
			add_btn.clicked.connect(lambda _, t=ptype: self.add_pet(t))
			row_layout.addWidget(add_btn)

			# 移除按钮
			remove_btn = QPushButton('移除')
			remove_btn.setStyleSheet("""
						    QPushButton { background-color: transparent; border: none;padding: 25px; text-align: center; }
						    QPushButton:hover { background-color: palette(midlight); /*轻微高亮*/ border-radius: 4px; }
						    QPushButton:pressed { background-color: palette(mid);}
						""")
			remove_btn.setFont(default_font)
			remove_btn.clicked.connect(lambda _, t=ptype: self.remove_pet(t))
			remove_btn.setEnabled(False)
			self.remove_buttons[ptype] = remove_btn
			row_layout.addWidget(remove_btn)

			# 数量信息
			count_label = QLabel(f"{ptype}数量：{self.pet_counts[ptype]}")
			count_label.setFont(default_font)
			self.count_labels[ptype] = count_label
			row_layout.addWidget(count_label)

			container_layout.addWidget(row_widget)

		scroll_area.setWidget(container)
		main_layout.addWidget(scroll_area)

		return chat_widget

	def add_pet(self, pet_type):
		# 实际创建桌宠逻辑，根据项目实现补充
		self.pet_instances.append(petal.create_pet_widget('data/pets.json', pet_type))
		self.pet_counts[pet_type] += 1
		self.update_controls(pet_type)

	def remove_pet(self, pet_type):
		if self.pet_counts[pet_type] > 0:
			# 实际移除桌宠逻辑，根据项目实现补充
			for inst in reversed(self.pet_instances):
				if inst.curr_pet_name == pet_type:
					inst.close()  # 关闭窗口（但对象还没释放）
					inst.deleteLater()  # 安排 Qt 安全释放（防止立刻销毁崩溃）
					self.pet_instances.remove(inst)
					self.pet_counts[pet_type] -= 1
					self.update_controls(pet_type)
					break

	def update_controls(self, pet_type):
		# 更新数量标签并切换移除按钮状态
		self.count_labels[pet_type].setText(f"{pet_type}数量：{self.pet_counts[pet_type]}")
		self.remove_buttons[pet_type].setEnabled(self.pet_counts[pet_type] > 0)

	def create_setting_window(self):
		chat_widget = QWidget()
		main_layout = QVBoxLayout(chat_widget)
		main_layout.setContentsMargins(20, 5, 20, 20)
		main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

		# 宠物选择框内的字体设置
		default_font = QFont()
		default_font.setPointSize(15)

		# 折叠/展开侧边栏按钮
		sidebar_btn = QPushButton('<')
		sidebar_btn.setStyleSheet("""
				            QPushButton { background-color: transparent; border: none; padding: 0; margin: 0; text-align: center; color: #a0a0a0; }
				            QPushButton:hover { color: #07C160; }
				            QPushButton:pressed { color: #05974C; }
				        """)
		set_font(sidebar_btn)
		sidebar_btn.clicked.connect(lambda checked, btn=sidebar_btn: self.toggle_sidebar(btn))
		main_layout.addWidget(sidebar_btn, alignment=Qt.AlignLeft | Qt.AlignTop)

		# 滚动区域及其容器
		scroll_area = QScrollArea()
		scroll_area.setWidgetResizable(True)

		container = QWidget()
		container.setStyleSheet(
			"border: 1px solid #cccccc; border-radius: 8px; padding: 8px;"
		)
		container_layout = QVBoxLayout(container)
		container_layout.setSpacing(10)
		container_layout.setContentsMargins(5, 5, 5, 5)
		container_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

		self.toggle_box = QCheckBox("启动聊天框")

		self.toggle_box.setLayoutDirection(Qt.RightToLeft)
		self.toggle_box.setFont(default_font)
		self.toggle_box.stateChanged.connect(self.toggle_feature)
		container_layout.addWidget(self.toggle_box)

		# 滑动条控件
		self.slider = QSlider(Qt.Horizontal)
		self.slider.setStyleSheet("")
		self.slider.setRange(1, 300)
		self.slider.setValue(50)
		self.slider.valueChanged.connect(self.slider_changed)
		slider_container = QWidget()
		slider_layout = QVBoxLayout(slider_container)
		slider_layout.setContentsMargins(0, 0, 0, 0)
		slider_layout.setSpacing(2)

		slider_label = QLabel("桌宠大小（%）")
		slider_label.setFont(default_font)
		slider_label.setAlignment(Qt.AlignRight)

		slider_label.setStyleSheet("border: none;")
		self.slider.setStyleSheet("border: none;")
		slider_layout.addWidget(slider_label)
		slider_layout.addWidget(self.slider)

		container_layout.addWidget(slider_container)

		scroll_area.setWidget(container)
		main_layout.addWidget(scroll_area)

		return chat_widget

	def toggle_feature(self, state):
		# 开关回调逻辑
		print("特效启用" if state == Qt.Checked else "特效关闭")

	def slider_changed(self, value):
		# 滑动条逻辑
		print(f"大小设置为：{value}%")

	def setup_chatting_window(self):
		"""
		main_window创建
		"""
		# 页面1
		self.choose_window = self.create_choose_window()
		self.chat_inputs["ChattingWindow1"] = None
		self.chat_lists["ChattingWindow1"] = None
		self.add_page(self.main_stack, self.choose_window, "ChattingWindow1")

		# 页面2
		self.setting_window = self.create_setting_window()
		self.chat_inputs["ChattingWindow2"] = None
		self.chat_lists["ChattingWindow2"] = None
		self.add_page(self.main_stack, self.setting_window, "ChattingWindow2")

	def add_page(self, stack: QStackedWidget, widget: QWidget, name: str):
		""""
		向 stack 中添加页面
		"""
		self.main_stack_map[name] = stack.addWidget(widget)

	def navigate_to(self, name: str, stack: QStackedWidget):
		"""
		通过名称跳转页面
		"""
		if name in self.main_stack_map:
			current_index = stack.currentIndex()
			target_index = self.main_stack_map[name]

			if current_index == target_index:
				# 重复点击，不切换，不清空
				return

			# 切换页面
			stack.setCurrentIndex(target_index)

		else:
			print(f"MainWindow @ navigate_to: 错误：未知页面 {name}!")

	def setup_sidebar_animation(self) -> None:
		"""侧边栏展开动画设置"""
		self.animations["sidebar"] = QPropertyAnimation(self.sidebar, b"maximumWidth")
		self.animations["sidebar"].setDuration(300)
		self.animations["sidebar"].setEasingCurve(QEasingCurve.Type.InOutQuad)

	def toggle_sidebar(self, btn) -> None:
		"""处理sidebar的变化"""
		self.sidebar_visible = not self.sidebar_visible

		if self.sidebar_visible:
			self.animations["sidebar"].setStartValue(0)
			self.animations["sidebar"].setEndValue(230)
			btn.setText("<")
		else:
			self.animations["sidebar"].setStartValue(230)
			self.animations["sidebar"].setEndValue(0)
			btn.setText(">")

		self.animations["sidebar"].start()

	def send_message(self, input_box, chat_list):
		# print("in send_message!")
		text = input_box.toPlainText().strip()
		if text:
			input_box.clear()
			chat_list.receive_message(text)