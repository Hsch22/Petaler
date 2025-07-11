from Mainwindow.common import *

from Mainwindow.Signals import Signals
from Mainwindow.FontSetting import set_font


class SideBar(QFrame):
	def __init__(self, parent):
		super().__init__(parent)
		self.setFrameShape(QFrame.StyledPanel)

		# ===侧边栏内容===
		layout = QVBoxLayout()
		layout.setContentsMargins(10, 10, 10, 20)

		name_label=QLabel("Petal\n————————")
		name_label.setAlignment(Qt.AlignCenter)
		set_font(name_label,2)
		layout.addWidget(name_label)

		#把sidebar撑开
		spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
		layout.addItem(spacer)

		# ===添加功能按钮===
		names = ("选择角色","设置")
		_names=("ChattingWindow1","ChattingWindow2")
		for i in range(len(names)):
			btn = QPushButton(f"{names[i]}")
			btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    padding: 25px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: palette(midlight); /*轻微高亮*/
                    border-radius: 4px;
                }
                QPushButton:pressed {
					background-color: palette(mid);
				}
            """)
			set_font(btn,1)
			layout.addWidget(btn)
			# 连接按钮与切换页面信号
			btn.clicked.connect(
				lambda checked, name=_names[i]: Signals.instance().send_page_change_signal(name)
			)
		layout.addStretch()
		self.setLayout(layout)