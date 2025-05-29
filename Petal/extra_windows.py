import os
import sys
import time
import math
import random
import inspect
import types
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer, QPoint, QEvent, QThread
from PyQt5.QtGui import QFont, QFontDatabase, QImage, QPixmap, QIcon, QCursor, QPainter
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from typing import List

import ctypes

try:
    # 尝试获取屏幕缩放比例 (仅 Windows)
    # ctypes 可能在非 Windows 系统上失败，或 GetScaleFactorForDevice 不存在
    screen_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
except (AttributeError, OSError):
    # 在非 Windows 或无法获取缩放时，使用默认值 1.0
    print("[警告] 无法获取 Windows 屏幕缩放比例，使用默认值 1.0。字体大小可能不适配。")
    screen_scale = 1.0
except Exception as e:
    print(f"[警告] 获取屏幕缩放时发生未知错误: {e}。使用默认值 1.0。")
    screen_scale = 1.0

# 根据缩放计算字体大小 (确保 screen_scale 不为 0)
if screen_scale <= 0:
    print("[警告] 屏幕缩放比例计算结果无效 (<=0)，强制设为 1.0。")
    screen_scale = 1.0
all_font_size = int(10 / screen_scale)


# --- Tomato 类定义 ---
class Tomato(QWidget):
    """
    一个用于设置番茄钟个数的弹出式小部件。

    该窗口提供一个 QSpinBox 供用户选择要执行的番茄钟数量，
    并通过"确定"和"取消"按钮进行操作。
    窗口设计为有边框、始终置顶。

    信号:
        close_tomato: 当用户点击"取消"按钮时发出，通知父级关闭此窗口。
        confirm_tomato (int): 当用户点击"确定"按钮时发出，携带用户选择的番茄钟数量。
    """

    # 定义信号
    close_tomato = pyqtSignal(name='close_tomato')
    confirm_tomato = pyqtSignal(int, name='confirm_tomato')

    def __init__(self, parent=None):
        """
        初始化番茄钟设置窗口。
        """
        super(Tomato, self).__init__(parent)

        try:
            # --- 配置常量 ---
            self._fixed_width = 250
            self._fixed_height = 100
            self._font_path = '../res/font/MFNaiSi_Noncommercial-Regular.otf'
            # 字体名称最好是字体文件实际包含的名称，或者是一个可靠的回退字体
            self._font_family_primary = 'MF NaiSi (Noncommercial)'
            self._font_family_fallback = '宋体'  # 回退字体

            # --- 加载并设置字体 ---
            self._setup_font()

            # --- 初始化 UI ---
            self._init_ui()

            # --- 设置窗口属性 ---
            self.resize(self._fixed_width, self._fixed_height)  # 设置窗口初始大小
            self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 窗口保持在顶部
            # 设置窗口在关闭时自动删除，避免内存泄漏
            self.setAttribute(Qt.WA_DeleteOnClose)

        except Exception as e:
            print(f"[严重错误] Tomato.__init__: 初始化番茄钟窗口失败: {e}")

    def _setup_font(self):
        """加载并准备应用程序字体。"""
        font_id = -1
        effective_font_family = self._font_family_fallback  # 默认使用回退字体

        # 尝试加载自定义字体文件
        if os.path.exists(self._font_path):
            font_id = QFontDatabase.addApplicationFont(self._font_path)
            if font_id != -1:
                # 加载成功，尝试获取字体家族名称
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    # 如果字体文件提供了名称，则优先使用第一个名称
                    effective_font_family = font_families[0]
                    print(
                        f"字体 '{effective_font_family}' 从 '{self._font_path}' 加载成功。"
                    )
                else:
                    print(
                        f"[警告] 字体文件 '{self._font_path}' 加载成功但无法获取字体家族名称，将使用 '{effective_font_family}'。"
                    )
            else:
                print(
                    f"[警告] 无法从 '{self._font_path}' 加载字体 (文件可能无效)。将使用 '{effective_font_family}'。"
                )
        else:
            print(
                f"[警告] 字体文件未找到: '{self._font_path}'。将使用 '{effective_font_family}'。"
            )

        # 创建 QFont 对象，后续 UI 元素将使用此字体
        self._widget_font = QFont(effective_font_family, 12)  # 默认字体大小为 12

    def _init_ui(self):
        """创建并布局窗口中的 UI 元素。"""
        # 初始化字体大小
        self.font_size = 12

        # --- 番茄钟数量选择 ---
        self.n_tomato_label = QLabel("请选择要进行番茄钟的个数:")
        self.n_tomato_label.setFont(self._widget_font)

        self.n_tomato = QSpinBox()
        self.n_tomato.setMinimum(1)  # 至少选择 1 个
        self.n_tomato.setFont(self._widget_font)  # 统一字体
        self.n_tomato.setAlignment(Qt.AlignCenter)  # 数字居中显示

        # --- 确认和取消按钮 ---
        self.button_confirm = QPushButton("确定")
        self.button_confirm.setFont(self._widget_font)
        self.button_confirm.clicked.connect(self.confirm)  # 连接到确认方法

        self.button_cancel = QPushButton("取消")
        self.button_cancel.setFont(self._widget_font)
        self.button_cancel.clicked.connect(self.close_tomato)  # 直接连接到关闭信号

        # --- 使用 QGridLayout 布局 ---
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(self.n_tomato_label, 0, 0, 1, 2)  # 占据第一行两列
        self.grid_layout.addWidget(self.n_tomato, 0, 2, 1, 1)  # 占据第一行第三列
        self.grid_layout.addWidget(self.button_confirm, 1, 1, 1, 1)  # 占据第二行第二列
        self.grid_layout.addWidget(self.button_cancel, 1, 2, 1, 1)  # 占据第二行第三列

        self.grid_layout.setRowStretch(0, 1)  # 第一行可以伸缩
        self.grid_layout.setRowStretch(1, 1)  # 第二行可以伸缩
        self.grid_layout.setColumnStretch(0, 1)  # 第一列可以伸缩
        self.grid_layout.setColumnStretch(1, 1)  # 第二列可以伸缩
        self.grid_layout.setColumnStretch(2, 1)  # 第三列可以伸缩

        self.setLayout(self.grid_layout)  # 设置布局到当前窗口

        self.setWindowTitle("番茄钟设置")  # 设置窗口标题

    def resizeEvent(self, event):
        """窗口大小变化时动态调整字体大小和布局元素大小"""
        try:
            super().resizeEvent(event)
            self.update_font_size()
            self.adjust_layout_elements()
        except Exception as e:
            print(f"[错误] resizeEvent: 发生错误: {e}")

    def adjust_layout_elements(self):
        """根据窗口大小动态调整布局中的元素大小"""
        try:
            width, height = self.width(), self.height()

            # 动态调整 QLabel 的大小
            label_width = int(width * 0.60)  # QLabel 占据约 60% 宽度
            label_height = height // 3  # QLabel 占据三分之一高度
            self.n_tomato_label.setFixedSize(label_width, label_height)

            # 动态调整 QSpinBox 的大小
            spinbox_width = int(width * 0.30)  # QSpinBox 占据约 30% 宽度
            spinbox_height = height // 3  # QSpinBox 占据三分之一高度
            self.n_tomato.setFixedSize(spinbox_width, spinbox_height)

            # 动态调整按钮大小
            button_width = width // 4  # 按钮占据四分之一宽度
            button_height = height // 4  # 按钮占据四分之一高度
            self.button_confirm.setFixedSize(button_width, button_height)
            self.button_cancel.setFixedSize(button_width, button_height)
        except Exception as e:
            print(f"[错误] adjust_layout_elements: 发生错误: {e}")

    def update_font_size(self):
        """根据窗口大小动态调整字体大小"""
        try:
            width, height = self.width(), self.height()
            new_font_size = max(
                10, min(width // 40, height // 20)
            )  # 限制字体大小在合理范围内
            if new_font_size != self.font_size:
                self.font_size = new_font_size
                font = QFont("Arial", self.font_size)
                self.n_tomato_label.setFont(font)
                self.n_tomato.setFont(font)
                self.button_confirm.setFont(font)
                self.button_cancel.setFont(font)
                # 直接调整 QSpinBox 内部 QLineEdit 的字体大小
                line_edit = self.n_tomato.lineEdit()
                if line_edit:
                    line_edit.setFont(font)
        except Exception as e:
            print(f"[错误] update_font_size: 发生错误: {e}")

    def confirm(self):
        """
        处理"确定"按钮点击事件。

        获取 QSpinBox 中的当前值，并发出 `confirm_tomato` 信号。
        注意：此方法本身不关闭窗口，关闭逻辑通常由接收信号的父级处理。
        """
        try:
            # QSpinBox.value() 通常是安全的，总能返回一个整数
            num_tomatoes = self.n_tomato.value()
            self.confirm_tomato.emit(num_tomatoes)
        except AttributeError:
            # 理论上，如果 __init__ 成功，self.n_tomato 应该存在
            print(
                "[错误] Tomato.confirm: 无法访问 'self.n_tomato'。窗口可能未正确初始化。"
            )
        except Exception as e:
            # 捕获信号发射过程中可能出现的其他错误
            print(f"[错误] Tomato.confirm: 发送确认信号时出错: {e}")


class Focus(QWidget):
    """
    一个用于设置专注模式（持续时间或定时结束）的弹出式小部件。

    该窗口允许用户选择两种模式之一：
    1. 持续一段时间：设置小时和分钟数。
    2. 定时结束：设置结束的小时和分钟。
    用户通过复选框选择模式，并通过相应的 SpinBox 输入时间。
    窗口设计为有边框、始终置顶。

    信号:
        close_focus: 当用户点击"取消"按钮时发出，通知父级关闭此窗口。
        confirm_focus (str, int, int): 当用户点击"确定"按钮时发出。
            - 第一个参数 (str): 模式标识符 ('range' 或 'point')。
            - 第二个参数 (int): 小时数。
            - 第三个参数 (int): 分钟数。
    """

    # 定义信号
    close_focus = pyqtSignal(name='close_focus')
    confirm_focus = pyqtSignal(str, int, int, name='confirm_focus')

    def __init__(self, parent=None):
        """
        初始化专注设置窗口。
        """
        super(Focus, self).__init__(parent)

        try:
            # --- 配置常量 ---
            self._fixed_width = 150
            self._fixed_height = 100
            self._font_path = 'res/font/MFNaiSi_Noncommercial-Regular.otf'
            self._font_family_primary = 'MF NaiSi (Noncommercial)'
            self._font_family_fallback = '宋体'  # 回退字体

            # --- 加载并设置字体 ---
            self._setup_font()

            # --- 初始化 UI 组件 ---
            self._init_ui()

            # --- 连接信号与槽 ---
            self._connect_signals()

            # --- 设置窗口属性 ---
            self._setup_window()

        except Exception as e:
            print(f"[严重错误] Focus.__init__: 初始化专注设置窗口失败: {e}")

    def _setup_font(self):
        """加载并准备应用程序字体。"""
        font_id = -1
        effective_font_family = self._font_family_fallback  # 默认使用回退字体

        # 尝试加载自定义字体文件
        if os.path.exists(self._font_path):
            font_id = QFontDatabase.addApplicationFont(self._font_path)
            if font_id != -1:
                # 加载成功，尝试获取字体家族名称
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    effective_font_family = font_families[0]
                    print(
                        f"字体 '{effective_font_family}' 从 '{self._font_path}' 加载成功。"
                    )
                else:
                    print(
                        f"[警告] 字体文件 '{self._font_path}' 加载成功但无法获取字体家族名称，将使用 '{effective_font_family}'。"
                    )
            else:
                print(
                    f"[警告] 无法从 '{self._font_path}' 加载字体 (文件可能无效)。将使用 '{effective_font_family}'。"
                )
        else:
            print(
                f"[警告] 字体文件未找到: '{self._font_path}'。将使用 '{effective_font_family}'。"
            )

        # 创建 QFont 对象，后续 UI 元素将使用此字体
        self._font = QFont(effective_font_family, 8)  # 默认字体大小为 8

    def _init_ui(self):
        """创建并布局窗口中的 UI 元素。"""
        self.font_size = 8  # 初始化字体大小

        main_layout = QVBoxLayout()  # 主垂直布局

        # --- 模式选择 ---
        self.label_method = QLabel('设置方式')
        self.label_method.setFont(self._font)
        self.label_method.setStyleSheet("color: grey")  # 保持灰色样式
        main_layout.addWidget(self.label_method)

        # 水平分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)  # 设置为水平线
        line.setFrameShadow(QFrame.Sunken)  # 设置阴影效果
        main_layout.addWidget(line)

        # --- 模式A: 持续一段时间 ---
        self.checkA = QCheckBox("持续一段时间", self)
        self.checkA.setFont(self._font)

        hbox_f1 = QHBoxLayout()  # 持续时间输入行布局
        self.countdown_h = QSpinBox()
        self.countdown_h.setMinimum(0)
        self.countdown_h.setMaximum(23)
        self.countdown_h.setFont(self._font)  # 应用统一字体
        self.countdown_h.setAlignment(Qt.AlignCenter)  # 数字居中

        self.countdown_m = QSpinBox()
        self.countdown_m.setMinimum(0)
        self.countdown_m.setMaximum(59)
        self.countdown_m.setSingleStep(5)  # 保持5分钟步进
        self.countdown_m.setFont(self._font)  # 应用统一字体
        self.countdown_m.setAlignment(Qt.AlignCenter)  # 数字居中

        self.label_h1 = QLabel('小时')
        self.label_h1.setFont(self._font)
        self.label_m1 = QLabel('分钟后')
        self.label_m1.setFont(self._font)

        hbox_f1.addWidget(self.countdown_h)
        hbox_f1.addWidget(self.label_h1)
        hbox_f1.addWidget(self.countdown_m)
        hbox_f1.addWidget(self.label_m1)
        hbox_f1.addStretch(1)  # 使用 addStretch(1) 即可，不需要很大的值

        main_layout.addWidget(self.checkA)
        main_layout.addLayout(hbox_f1)
        main_layout.addStretch(1)  # 在两组选项之间添加弹性空间

        # --- 模式B: 定时结束 ---
        self.checkB = QCheckBox("定时结束", self)
        self.checkB.setFont(self._font)

        hbox_f2 = QHBoxLayout()  # 定时结束输入行布局
        self.time_h = QSpinBox()
        self.time_h.setMinimum(0)
        self.time_h.setMaximum(23)
        self.time_h.setFont(self._font)  # 应用统一字体
        self.time_h.setAlignment(Qt.AlignCenter)  # 数字居中

        self.time_m = QSpinBox()
        self.time_m.setMinimum(0)
        self.time_m.setMaximum(59)
        self.time_m.setFont(self._font)  # 应用统一字体
        self.time_m.setAlignment(Qt.AlignCenter)  # 数字居中

        self.label_d2 = QLabel('到')
        self.label_d2.setFont(self._font)
        self.label_h2 = QLabel('点')
        self.label_h2.setFont(self._font)
        self.label_m2 = QLabel('分')
        self.label_m2.setFont(self._font)

        hbox_f2.addWidget(self.label_d2)
        hbox_f2.addWidget(self.time_h)
        hbox_f2.addWidget(self.label_h2)
        hbox_f2.addWidget(self.time_m)
        hbox_f2.addWidget(self.label_m2)
        hbox_f2.addStretch(1)  # 使用 addStretch(1)

        main_layout.addWidget(self.checkB)
        main_layout.addLayout(hbox_f2)
        main_layout.addStretch(1)  # 在选项和按钮之间添加弹性空间

        # --- 确认和取消按钮 ---
        hbox_f3 = QHBoxLayout()  # 按钮行布局
        self.button_confirm = QPushButton("确定")
        self.button_confirm.setFont(self._font)

        self.button_cancel = QPushButton("取消")
        self.button_cancel.setFont(self._font)

        hbox_f3.addStretch(1)  # 将按钮推向右侧或居中（取决于是否再加 stretch）
        hbox_f3.addWidget(self.button_confirm)
        hbox_f3.addWidget(self.button_cancel)

        main_layout.addLayout(hbox_f3)
        self.setLayout(main_layout)

    def _connect_signals(self):
        """连接所有信号与槽。"""
        # 复选框状态改变时，调用 self.uncheck
        self.checkA.stateChanged.connect(self.uncheck)
        self.checkB.stateChanged.connect(self.uncheck)

        # 点击确定按钮，调用 self.confirm
        self.button_confirm.clicked.connect(self.confirm)

        # 点击取消按钮，直接发射 close_focus 信号
        self.button_cancel.clicked.connect(self.close_focus)

    def _setup_window(self):
        """设置窗口的固定大小和标志。"""
        self.resize(self._fixed_width, self._fixed_height)  # 设置窗口初始大小
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 窗口保持在顶部
        self.setWindowTitle("专注模式设置")  # 设置窗口标题

    def resizeEvent(self, event):
        """窗口大小变化时动态调整字体大小和布局元素大小"""
        try:
            super().resizeEvent(event)
            self.updateDynamicFontSize()
            self.adjust_layout_elements()
        except Exception as e:
            print(f"[错误] resizeEvent: 发生错误: {e}")

    def adjust_layout_elements(self):
        """根据窗口大小动态调整布局中的元素大小"""
        try:
            width, height = self.width(), self.height()

            # 动态调整 QSpinBox 的大小
            spinbox_width = width // 4  # 每个 QSpinBox 占据四分之一宽度
            spinbox_height = height // 8  # QSpinBox 占据六分之一高度
            self.countdown_h.setFixedSize(spinbox_width, spinbox_height)
            self.countdown_m.setFixedSize(spinbox_width, spinbox_height)
            self.time_h.setFixedSize(spinbox_width, spinbox_height)
            self.time_m.setFixedSize(spinbox_width, spinbox_height)

            # 动态调整按钮大小
            button_width = width // 4  # 每个按钮占据四分之一宽度
            button_height = height // 8  # 按钮占据六分之一高度
            self.button_confirm.setFixedSize(button_width, button_height)
            self.button_cancel.setFixedSize(button_width, button_height)

            # 动态调整 QLabel 的大小
            label_width = width // 2  # QLabel 占据一半宽度
            label_height = height // 10  # QLabel 占据十分之一高度
            self.label_method.setFixedSize(label_width, label_height)
            self.label_h1.setFixedSize(label_width // 4, label_height)
            self.label_m1.setFixedSize(label_width // 4, label_height)
            self.label_d2.setFixedSize(label_width // 4, label_height)
            self.label_h2.setFixedSize(label_width // 4, label_height)
            self.label_m2.setFixedSize(label_width // 4, label_height)
        except Exception as e:
            print(f"[错误] adjust_layout_elements: 发生错误: {e}")

    def updateDynamicFontSize(self):
        """根据窗口大小动态调整字体大小"""
        try:
            width, height = self.width(), self.height()
            new_font_size = max(
                8, min(width // 60, height // 30)
            )  # 调整字体大小计算公式
            if new_font_size != self.font_size:
                self.font_size = new_font_size
                font = QFont(
                    self._font.family(), self.font_size
                )  # 使用当前字体家族和新的字体大小
                self.label_method.setFont(font)
                self.checkA.setFont(font)
                self.checkB.setFont(font)
                self.countdown_h.setFont(font)
                self.countdown_m.setFont(font)
                self.time_h.setFont(font)
                self.time_m.setFont(font)
                self.label_h1.setFont(font)
                self.label_m1.setFont(font)
                self.label_d2.setFont(font)
                self.label_h2.setFont(font)
                self.label_m2.setFont(font)
                self.button_confirm.setFont(font)
                self.button_cancel.setFont(font)
                # 直接调整 QSpinBox 内部 QLineEdit 的字体大小
                line_edit = self.time_h.lineEdit()
                if line_edit:
                    line_edit.setFont(font)
                line_edit1 = self.time_m.lineEdit()
                if line_edit1:
                    line_edit1.setFont(font)
                line_edit2 = self.countdown_h.lineEdit()
                if line_edit2:
                    line_edit2.setFont(font)
                line_edit3 = self.countdown_m.lineEdit()
                if line_edit3:
                    line_edit3.setFont(font)
        except Exception as e:
            print(f"[错误] updateDynamicFontSize: 发生错误: {e}")

    def uncheck(self, state):
        """
        处理复选框状态改变事件，确保只有一个复选框被选中。

        参数:
            state (int): Qt.Checked 或 Qt.Unchecked。
        """
        if state == Qt.Checked:
            sender = self.sender()  # 获取信号的发送者 (哪个复选框被点击了)
            if sender == self.checkA:
                self.checkB.setChecked(False)
            elif sender == self.checkB:
                self.checkA.setChecked(False)

    def confirm(self):
        """
        处理"确定"按钮点击事件。

        根据当前选中的复选框，获取对应的时间值，
        并发射 `confirm_focus` 信号。
        如果两个复选框都未选中，则不执行任何操作。
        """
        try:
            if self.checkA.isChecked():
                self.confirm_focus.emit(
                    'range', self.countdown_h.value(), self.countdown_m.value()
                )
            elif self.checkB.isChecked():
                self.confirm_focus.emit(
                    'point', self.time_h.value(), self.time_m.value()
                )
        except Exception as e:
            print(f"[错误] Focus.confirm: 确认操作时发生错误: {e}")


class QHLine(QFrame):
    """一个简单的水平分割线小部件 (继承自 QFrame)。"""

    def __init__(self, parent=None):
        super(QHLine, self).__init__(parent)
        self.setFrameShape(QFrame.HLine)  # 设置形状为水平线
        self.setFrameShadow(QFrame.Sunken)  # 设置阴影效果为凹陷


class QVLine(QFrame):
    """一个简单的垂直分割线小部件 (继承自 QFrame)。"""

    def __init__(self, parent=None):
        super(QVLine, self).__init__(parent)
        self.setFrameShape(QFrame.VLine)  # 设置形状为垂直线
        self.setFrameShadow(QFrame.Sunken)  # 设置阴影效果为凹陷


class Remindme(QWidget):
    """
    一个用于设置提醒事项的弹出式小部件。

    提供三种提醒模式：
    1. 一段时间后提醒 ('range')
    2. 定时提醒 ('point')
    3. 间隔重复提醒 ('repeat_point' 或 'repeat_interval')

    用户可以选择模式、设置时间、输入提醒内容。
    右侧提供一个文本编辑区域，用于显示和编辑所有提醒事项（自动保存）。
    窗口设计为有边框、始终置顶。

    信号:
        close_remind: 当用户点击"关闭"按钮时发出。
        confirm_remind (str, int, int, str): 当用户点击"确定"按钮设置新提醒时发出。
            - 参数1 (str): 模式标识符 ('range', 'point', 'repeat_point', 'repeat_interval')。
            - 参数2 (int): 主要时间值 (小时或 0)。
            - 参数3 (int): 次要时间值 (分钟)。
            - 参数4 (str): 提醒文本。
    """

    # 定义信号
    close_remind = pyqtSignal(name='close_remind')
    confirm_remind = pyqtSignal(str, int, int, str, name='confirm_remind')

    def __init__(self, parent=None):
        """
        初始化提醒设置窗口。
        """
        super(Remindme, self).__init__(parent)

        try:
            # --- 配置常量 ---
            self._fixed_width = 350
            self._fixed_height = 200
            self._font_path = 'res/font/MFNaiSi_Noncommercial-Regular.otf'
            self._font_family_primary = 'MF NaiSi (Noncommercial)'
            self._font_family_fallback = '宋体'  # 回退字体
            self._remind_file_path = 'data/remindme.txt'  # 提醒文件路径
            self._max_line_edit_length = 14  # 单行提醒输入框最大长度

            # --- 加载并设置字体 ---
            self._setup_font()

            # --- 初始化 UI 组件 ---
            self._init_ui()

            # --- 连接信号与槽 ---
            self._connect_signals()

            # --- 设置窗口属性 ---
            self._setup_window()

            # --- 加载初始提醒文本 ---
            self._load_initial_text()

        except Exception as e:
            print(f"[严重错误] Remindme.__init__: 初始化提醒设置窗口失败: {e}")

    def _setup_font(self):
        """加载并准备应用程序字体。"""
        font_id = -1
        effective_font_family = self._font_family_fallback  # 默认使用回退字体

        # 尝试加载自定义字体文件
        if os.path.exists(self._font_path):
            font_id = QFontDatabase.addApplicationFont(self._font_path)
            if font_id != -1:
                # 加载成功，尝试获取字体家族名称
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    effective_font_family = font_families[0]
                    print(
                        f"字体 '{effective_font_family}' 从 '{self._font_path}' 加载成功。"
                    )
                else:
                    print(
                        f"[警告] 字体文件 '{self._font_path}' 加载成功但无法获取字体家族名称，将使用 '{effective_font_family}'。"
                    )
            else:
                print(
                    f"[警告] 无法从 '{self._font_path}' 加载字体 (文件可能无效)。将使用 '{effective_font_family}'。"
                )
        else:
            print(
                f"[警告] 字体文件未找到: '{self._font_path}'。将使用 '{effective_font_family}'。"
            )

        # 创建 QFont 对象，后续 UI 元素将使用此字体
        self._font = QFont(effective_font_family, 8)  # 默认字体大小为 12

    def _init_ui(self):
        """创建并布局窗口中的 UI 元素。"""
        self.font_size = 8  # 初始化字体大小

        hbox_all = QHBoxLayout()  # 整体水平布局（左右两栏）

        # --- 左侧布局 (设置新提醒) ---
        vbox_r = QVBoxLayout()  # 左侧垂直布局

        # 提醒方式标签和分隔线
        self.label_method = QLabel('提醒方式')
        self.label_method.setFont(self._font)
        self.label_method.setStyleSheet("color: grey")
        vbox_r.addWidget(self.label_method)
        vbox_r.addWidget(QHLine())  # 使用自定义的水平线

        # 模式A: 一段时间后提醒
        self.checkA = QCheckBox("一段时间后提醒", self)
        self.checkA.setFont(self._font)
        hbox_r1 = self._create_countdown_layout()  # 创建倒计时输入布局
        vbox_r.addWidget(self.checkA)
        vbox_r.addLayout(hbox_r1)
        vbox_r.addStretch(1)

        # 模式B: 定时提醒
        self.checkB = QCheckBox("定时提醒", self)
        self.checkB.setFont(self._font)
        hbox_r2 = self._create_timepoint_layout()  # 创建时间点输入布局
        vbox_r.addWidget(self.checkB)
        vbox_r.addLayout(hbox_r2)
        vbox_r.addStretch(1)

        # 模式C: 间隔重复
        self.checkC = QCheckBox("间隔重复", self)
        self.checkC.setFont(self._font)
        hbox_r5 = self._create_repeat_layout()  # 创建重复设置布局
        vbox_r.addWidget(self.checkC)
        vbox_r.addLayout(hbox_r5)
        vbox_r.addStretch(2)  # 保持原来的拉伸比例

        # 提醒内容输入标签和分隔线
        self.label_r = QLabel(f'提醒我（限{self._max_line_edit_length}个字以内）')
        self.label_r.setFont(self._font)
        self.label_r.setStyleSheet("color: grey")
        vbox_r.addWidget(self.label_r)
        vbox_r.addWidget(QHLine())

        # 提醒内容输入框 (QLineEdit)
        hbox_r4 = QHBoxLayout()
        self.e1 = QLineEdit()
        self.e1.setMaxLength(self._max_line_edit_length)  # 设置最大长度
        self.e1.setAlignment(Qt.AlignLeft)
        self.e1.setFont(self._font)
        hbox_r4.addWidget(self.e1)
        hbox_r4.addStretch(1)  # 拉伸使输入框不占满整行
        vbox_r.addLayout(hbox_r4)

        # 确定和关闭按钮
        hbox_r3 = self._create_button_layout()  # 创建按钮布局
        vbox_r.addStretch(1)  # 在输入框和按钮间添加空间
        vbox_r.addLayout(hbox_r3)

        # --- 右侧布局 (显示/编辑所有提醒) ---
        vbox_r2 = QVBoxLayout()  # 右侧垂直布局

        self.label_on = QLabel('提醒事项（内容自动保存）')  # 修改了提示，强调自动保存
        self.label_on.setFont(self._font)
        self.label_on.setStyleSheet("color: grey")
        vbox_r2.addWidget(self.label_on)
        vbox_r2.addWidget(QHLine())  # 水平线

        self.e2 = QTextEdit()  # 文本编辑区域
        self.e2.setAlignment(Qt.AlignLeft)
        self.e2.setFont(self._font)
        vbox_r2.addWidget(self.e2)

        # --- 组合左右布局 ---
        hbox_all.addLayout(vbox_r)  # 添加左侧布局
        hbox_all.addWidget(QVLine())  # 添加垂直分割线
        hbox_all.addLayout(vbox_r2)  # 添加右侧布局

        self.setLayout(hbox_all)
        if self.label_on is None:
            print("[错误] self.label_on 未被正确初始化！")
        else:
            print(f"[调试] self.label_on 初始化成功！对象地址: {id(self.label_on)}")

    def _create_countdown_layout(self):
        """创建"持续时间"输入的布局 (模式A)。"""
        hbox = QHBoxLayout()
        self.countdown_h = QSpinBox()
        self.countdown_h.setMinimum(0)
        self.countdown_h.setMaximum(23)
        self.countdown_h.setFont(self._font)
        self.countdown_h.setAlignment(Qt.AlignCenter)

        self.countdown_m = QSpinBox()
        self.countdown_m.setMinimum(0)
        self.countdown_m.setMaximum(59)
        self.countdown_m.setSingleStep(5)
        self.countdown_m.setFont(self._font)
        self.countdown_m.setAlignment(Qt.AlignCenter)

        self.label_hh = QLabel('小时')
        self.label_hh.setFont(self._font)
        self.label_mm = QLabel('分钟后')
        self.label_mm.setFont(self._font)

        hbox.addWidget(self.countdown_h)
        hbox.addWidget(self.label_hh)
        hbox.addWidget(self.countdown_m)
        hbox.addWidget(self.label_mm)
        hbox.addStretch(1)
        return hbox

    def _create_timepoint_layout(self):
        """创建"定时"输入的布局 (模式B)。"""
        hbox = QHBoxLayout()
        self.time_h = QSpinBox()
        self.time_h.setMinimum(0)
        self.time_h.setMaximum(23)
        self.time_h.setFont(self._font)
        self.time_h.setAlignment(Qt.AlignCenter)

        self.time_m = QSpinBox()
        self.time_m.setMinimum(0)
        self.time_m.setMaximum(59)
        self.time_m.setFont(self._font)
        self.time_m.setAlignment(Qt.AlignCenter)

        self.label_d = QLabel('到')
        self.label_d.setFont(self._font)
        self.label_h = QLabel('点')
        self.label_h.setFont(self._font)
        self.label_m = QLabel('分')
        self.label_m.setFont(self._font)

        hbox.addWidget(self.label_d)
        hbox.addWidget(self.time_h)
        hbox.addWidget(self.label_h)
        hbox.addWidget(self.time_m)
        hbox.addWidget(self.label_m)
        hbox.addStretch(1)
        return hbox

    def _create_repeat_layout(self):
        """创建"重复"输入的布局 (模式C)。"""
        hbox = QHBoxLayout()
        self.check1 = QCheckBox("在", self)  # xx 分时
        self.check1.setFont(self._font)
        self.check2 = QCheckBox("每", self)
        self.check2.setFont(self._font)

        self.every_min = QSpinBox()  # xx 分时 的分钟输入
        self.every_min.setMinimum(0)
        self.every_min.setMaximum(59)
        self.every_min.setFont(self._font)
        self.every_min.setAlignment(Qt.AlignCenter)
        self.label_em = QLabel('分时')
        self.label_em.setFont(self._font)

        self.interval_min = QSpinBox()  # 每隔 xx 分钟 的分钟输入
        self.interval_min.setMinimum(1)  # 至少间隔1分钟
        self.interval_min.setFont(self._font)
        self.interval_min.setAlignment(Qt.AlignCenter)
        self.label_im = QLabel('分钟')
        self.label_im.setFont(self._font)

        hbox.addWidget(self.check1)
        hbox.addWidget(self.every_min)
        hbox.addWidget(self.label_em)
        hbox.addSpacing(10)  # 添加一点间距
        hbox.addWidget(self.check2)
        hbox.addWidget(self.interval_min)
        hbox.addWidget(self.label_im)
        hbox.addStretch(1)
        return hbox

    def _create_button_layout(self):
        """创建"确定"和"关闭"按钮的布局。"""
        hbox = QHBoxLayout()
        self.button_confirm = QPushButton("确定")
        self.button_confirm.setFont(self._font)

        self.button_cancel = QPushButton("关闭")  # 保持 "关闭" 文本
        self.button_cancel.setFont(self._font)

        hbox.addStretch(1)  # 将按钮推到中间或右边
        hbox.addWidget(self.button_confirm)
        hbox.addWidget(self.button_cancel)
        hbox.addStretch(1)  # 使按钮居中
        return hbox

    def _connect_signals(self):
        """连接所有信号与槽。"""
        # 主要模式复选框互斥
        self.checkA.stateChanged.connect(self.uncheck)
        self.checkB.stateChanged.connect(self.uncheck)
        self.checkC.stateChanged.connect(self.uncheck)

        # 重复模式内部复选框互斥
        self.check1.stateChanged.connect(self.uncheck)
        self.check2.stateChanged.connect(self.uncheck)

        # 按钮点击
        self.button_confirm.clicked.connect(self.confirm)
        self.button_cancel.clicked.connect(self.close_remind)  # 直接连接关闭信号

        # 文本编辑框内容改变时，自动保存
        self.e2.textChanged.connect(self.save_remindme)

    def _setup_window(self):
        """设置窗口的固定大小和标志。"""
        self.resize(self._fixed_width, self._fixed_height)  # 设置窗口初始大小
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 窗口保持在顶部
        self.setWindowTitle("提醒事项设置")  # 设置窗口标题

    def _load_initial_text(self):
        """从文件中加载初始提醒文本到 QTextEdit (self.e2)。"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._remind_file_path), exist_ok=True)

            if os.path.isfile(self._remind_file_path):
                with open(self._remind_file_path, 'r', encoding='UTF-8') as f:
                    texts = f.read()
                self.e2.setPlainText(texts)
            else:
                # 如果文件不存在，则创建一个空文件
                with open(self._remind_file_path, 'w', encoding='UTF-8') as f:
                    f.write('')
                self.e2.setPlainText('')  # 确保文本框为空
        except IOError as e:
            print(
                f"[错误] Remindme._load_initial_text: 无法加载提醒文件 '{self._remind_file_path}': {e}"
            )
            # 即使加载失败，也设置为空文本
            self.e2.setPlainText('')
        except Exception as e:
            print(
                f"[严重错误] Remindme._load_initial_text: 加载提醒时发生意外错误: {e}"
            )
            self.e2.setPlainText('')

    def initial_task(self):
        """
        从提醒文件中读取内容，查找以 '#重复' 开头的行，
        并为这些行发射 confirm_remind 信号。
        通常用于程序启动时恢复之前的重复任务。
        """
        texts_to_emit = []
        try:
            if os.path.isfile(self._remind_file_path):
                with open(self._remind_file_path, 'r', encoding='UTF-8') as f:
                    texts = f.readlines()

                for line in texts:
                    line = line.rstrip('\n')
                    if line.startswith('#重复'):
                        parts = line.split(' ')
                        if len(parts) >= 4:
                            mode_str = parts[1]  # '每到' 或 '每隔'
                            value_str = parts[2]  # 分钟数
                            # 提醒文本可能是剩余的部分，用 ' - ' 分隔
                            reminder_parts = line.split(' - ', 1)
                            remind_text = (
                                reminder_parts[1] if len(reminder_parts) > 1 else ''
                            )

                            try:
                                minute_value = int(value_str)
                                if mode_str == '每到' and parts[3] == '分时':
                                    texts_to_emit.append(
                                        ('repeat_point', 0, minute_value, remind_text)
                                    )
                                elif mode_str == '每隔' and parts[3] == '分钟':
                                    texts_to_emit.append(
                                        (
                                            'repeat_interval',
                                            0,
                                            minute_value,
                                            remind_text,
                                        )
                                    )
                                else:
                                    print(
                                        f"[警告] initial_task: 无法解析重复行格式: {line}"
                                    )
                            except ValueError:
                                print(f"[警告] initial_task: 重复行分钟值无效: {line}")
                            except Exception as e_parse:
                                print(
                                    f"[错误] initial_task: 解析重复行时出错 '{line}': {e_parse}"
                                )

            else:
                print(
                    f"[信息] initial_task: 提醒文件 '{self._remind_file_path}' 不存在，无重复任务加载。"
                )

        except IOError as e:
            print(
                f"[错误] Remindme.initial_task: 读取提醒文件 '{self._remind_file_path}' 时出错: {e}"
            )
        except Exception as e:
            print(f"[严重错误] Remindme.initial_task: 处理初始任务时发生意外错误: {e}")

        # 在所有文件读取和解析完成后，再发射信号
        for args in texts_to_emit:
            try:
                self.confirm_remind.emit(*args)
            except Exception as e_emit:
                print(
                    f"[错误] initial_task: 发射恢复的重复任务信号时出错 ({args}): {e_emit}"
                )

    def uncheck(self, state):
        """
        处理复选框状态改变事件，确保组内的互斥性。
        组1: checkA, checkB, checkC (主要提醒模式)
        组2: check1, check2 (重复模式内部选项)
        """
        # 检查状态是否为"选中"
        if state == Qt.Checked:
            sender = self.sender()  # 获取信号发送者

            # --- 检查主要模式组 (A, B, C) ---
            if sender == self.checkA:
                self.checkB.setChecked(False)
                self.checkC.setChecked(False)
            elif sender == self.checkB:
                self.checkA.setChecked(False)
                self.checkC.setChecked(False)
            elif sender == self.checkC:
                self.checkA.setChecked(False)
                self.checkB.setChecked(False)

            # --- 检查重复模式内部组 (1, 2) ---
            elif sender == self.check1:
                self.check2.setChecked(False)
            elif sender == self.check2:
                self.check1.setChecked(False)

    def confirm(self):
        """
        处理"确定"按钮点击事件。
        根据选中的模式 (A, B, 或 C)，执行相应的操作：
        - 计算时间或获取设置值。
        - 获取提醒文本 (从 self.e1)。
        - (对于 A 和 B) 格式化时间字符串并追加到 self.e2。
        - (对于 C) 格式化重复任务字符串并追加到 self.e2。
        - 发射 `confirm_remind` 信号，携带模式、时间值和提醒文本。
        """
        try:
            remind_text = self.e1.text()  # 获取单行提醒文本
            current_text = self.e2.toPlainText()  # 获取当前多行文本内容

            if self.checkA.isChecked():  # 模式A: 一段时间后
                hs = self.countdown_h.value()
                ms = self.countdown_m.value()
                # 计算未来时间点
                timeset_dt = datetime.now() + timedelta(hours=hs, minutes=ms)
                timeset_str = timeset_dt.strftime("%m/%d %H:%M")  # 格式化时间
                # 更新文本编辑区
                new_line = f'{timeset_str} - {remind_text}\n'
                self.e2.setPlainText(current_text + new_line)
                # 发射信号
                self.confirm_remind.emit('range', hs, ms, remind_text)

            elif self.checkB.isChecked():  # 模式B: 定时
                hs = self.time_h.value()
                ms = self.time_m.value()
                # 计算下一个时间点
                now = datetime.now()
                time_torun = datetime(
                    year=now.year,
                    month=now.month,
                    day=now.day,
                    hour=hs,
                    minute=ms,
                    second=0,
                )  # 秒设为0更稳定
                if time_torun <= now:  # 如果时间已过，则设为明天
                    time_torun += timedelta(days=1)
                timeset_str = time_torun.strftime("%m/%d %H:%M")  # 格式化时间
                # 更新文本编辑区
                new_line = f'{timeset_str} - {remind_text}\n'
                self.e2.setPlainText(current_text + new_line)
                # 发射信号
                self.confirm_remind.emit('point', hs, ms, remind_text)

            elif self.checkC.isChecked():  # 模式C: 重复
                new_line = ""  # 初始化新行文本
                emit_args = None  # 初始化要发射的信号参数

                if self.check1.isChecked():  # 重复子模式: 每到 xx 分时
                    minute_value = self.every_min.value()
                    new_line = f'#重复 每到 {minute_value} 分时 - {remind_text}\n'
                    emit_args = ('repeat_point', 0, minute_value, remind_text)
                elif self.check2.isChecked():  # 重复子模式: 每隔 xx 分钟
                    interval_value = self.interval_min.value()
                    new_line = f'#重复 每隔 {interval_value} 分钟 - {remind_text}\n'
                    emit_args = ('repeat_interval', 0, interval_value, remind_text)

                if new_line and emit_args:  # 确保选中了子模式且参数有效
                    # 更新文本编辑区
                    self.e2.setPlainText(current_text + new_line)
                    # 发射信号
                    self.confirm_remind.emit(*emit_args)

        except Exception as e:
            # 捕获并打印确认过程中可能出现的任何意外错误
            print(f"[错误] Remindme.confirm: 处理确认操作时发生错误: {e}")

    def save_remindme(self):
        """
        当 QTextEdit (self.e2) 的内容改变时被调用。
        将 self.e2 的全部内容写入到提醒文件中。
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._remind_file_path), exist_ok=True)
            with open(self._remind_file_path, 'w', encoding='UTF-8') as f:
                f.write(self.e2.toPlainText())
        except IOError as e:
            print(
                f"[错误] Remindme.save_remindme: 无法保存提醒文件 '{self._remind_file_path}': {e}"
            )
        except Exception as e:
            print(f"[严重错误] Remindme.save_remindme: 保存提醒时发生意外错误: {e}")

    def resizeEvent(self, event):
        """窗口大小变化时动态调整字体大小"""
        try:
            super().resizeEvent(event)
            self.update_font_size()
        except Exception as e:
            print(f"[错误] resizeEvent: 发生错误: {e}")

    def update_font_size(self):
        """根据窗口大小动态调整字体大小"""
        try:
            width, height = self.width(), self.height()
            new_font_size = max(
                10, min(width // 60, height // 30)
            )  # 调整字体大小计算公式
            if new_font_size != self.font_size:
                self.font_size = new_font_size
                font = QFont(
                    self._font.family(), self.font_size
                )  # 使用当前字体家族和新的字体大小

                self.checkA.setFont(font)
                self.checkB.setFont(font)
                self.checkC.setFont(font)
                self.countdown_h.setFont(font)
                self.countdown_m.setFont(font)
                self.time_h.setFont(font)
                self.time_m.setFont(font)
                self.every_min.setFont(font)
                self.interval_min.setFont(font)
                self.button_confirm.setFont(font)
                self.button_cancel.setFont(font)
                self.e1.setFont(font)
                self.e2.setFont(font)
                self.label_d.setFont(font)
                self.label_h.setFont(font)
                self.label_m.setFont(font)
                self.label_im.setFont(font)
                self.label_em.setFont(font)
                self.check1.setFont(font)
                self.check2.setFont(font)
                self.label_hh.setFont(font)
                self.label_mm.setFont(font)
                self.label_r.setFont(font)
                line_edit = self.time_h.lineEdit()
                if line_edit:
                    line_edit.setFont(font)
                line_edit1 = self.time_m.lineEdit()
                if line_edit1:
                    line_edit1.setFont(font)
                line_edit2 = self.countdown_h.lineEdit()
                if line_edit2:
                    line_edit2.setFont(font)
                line_edit3 = self.countdown_m.lineEdit()
                if line_edit3:
                    line_edit3.setFont(font)
                line_edit4 = self.every_min.lineEdit()
                if line_edit4:
                    line_edit4.setFont(font)
                line_edit5 = self.interval_min.lineEdit()
                if line_edit5:
                    line_edit5.setFont(font)
        except Exception as e:
            print(f"[错误] update_font_size: 发生错误: {e}")
