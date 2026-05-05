
"""
UI模块 - 设置界面
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget,
                              QLabel, QSlider, QPushButton, QGroupBox,
                              QSpinBox, QDoubleSpinBox, QCheckBox, QTabWidget,
                              QFormLayout, QFileDialog, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from config import WINDOW_CONFIG, MONITOR_CONFIG

class SettingsDialog(QDialog):
    """设置对话框"""

    # 定义信号
    settings_changed = Signal(dict)
    ocr_test_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_settings = self._get_current_settings()
        self.init_ui()

    def _get_current_settings(self) -> dict:
        """获取当前设置"""
        return {
            "window": {
                "opacity": WINDOW_CONFIG["chat"]["opacity"],
                "always_on_top": WINDOW_CONFIG["chat"]["always_on_top"]
            },
            "monitor": MONITOR_CONFIG.copy()
        }

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(WINDOW_CONFIG["settings"]["title"])
        self.resize(WINDOW_CONFIG["settings"]["width"], WINDOW_CONFIG["settings"]["height"])

        # 主布局
        main_layout = QVBoxLayout(self)

        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 窗口设置页面
        window_tab = self.create_window_tab()
        tab_widget.addTab(window_tab, "窗口设置")

        # 监控设置页面
        monitor_tab = self.create_monitor_tab()
        tab_widget.addTab(monitor_tab, "监控设置")

        # 按钮区域
        button_layout = QHBoxLayout()

        # 测试OCR按钮
        test_ocr_btn = QPushButton("测试OCR")
        test_ocr_btn.clicked.connect(self.ocr_test_requested.emit)
        button_layout.addWidget(test_ocr_btn)

        button_layout.addStretch()

        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

    def create_window_tab(self) -> QWidget:
        """创建窗口设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 窗口透明度设置
        opacity_group = QGroupBox("窗口透明度")
        opacity_layout = QVBoxLayout()

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(30)  # 0.3
        self.opacity_slider.setMaximum(100)  # 1.0
        self.opacity_slider.setValue(int(self.current_settings["window"]["opacity"] * 100))
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)

        opacity_value_layout = QHBoxLayout()
        self.opacity_label = QLabel(f"{self.current_settings['window']['opacity']:.2f}")
        opacity_value_layout.addWidget(QLabel("透明度:"))
        opacity_value_layout.addWidget(self.opacity_label)
        opacity_value_layout.addStretch()

        opacity_layout.addLayout(opacity_value_layout)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_group.setLayout(opacity_layout)
        layout.addWidget(opacity_group)

        # 窗口置顶设置
        self.always_on_top_checkbox = QCheckBox("窗口置顶")
        self.always_on_top_checkbox.setChecked(self.current_settings["window"]["always_on_top"])
        layout.addWidget(self.always_on_top_checkbox)

        layout.addStretch()

        return widget



    def create_monitor_tab(self) -> QWidget:
        """创建监控设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 监控间隔设置
        interval_group = QGroupBox("监控间隔")
        interval_layout = QFormLayout()

        # 窗口检查间隔
        self.window_check_spinbox = QSpinBox()
        self.window_check_spinbox.setRange(100, 10000)
        self.window_check_spinbox.setSuffix(" 毫秒")
        self.window_check_spinbox.setValue(self.current_settings["monitor"]["check_interval"])
        interval_layout.addRow("窗口检查间隔:", self.window_check_spinbox)

        # OCR识别间隔
        self.ocr_interval_spinbox = QSpinBox()
        self.ocr_interval_spinbox.setRange(1000, 60000)
        self.ocr_interval_spinbox.setSuffix(" 毫秒")
        self.ocr_interval_spinbox.setValue(self.current_settings["monitor"]["ocr_interval"])
        interval_layout.addRow("OCR识别间隔:", self.ocr_interval_spinbox)

        interval_group.setLayout(interval_layout)
        layout.addWidget(interval_group)

        # 自动启动设置
        self.auto_start_checkbox = QCheckBox("自动开始监控")
        self.auto_start_checkbox.setChecked(self.current_settings["monitor"]["auto_start"])
        layout.addWidget(self.auto_start_checkbox)

        layout.addStretch()

        return widget

    def update_opacity_label(self, value):
        """更新透明度标签"""
        opacity = value / 100.0
        self.opacity_label.setText(f"{opacity:.2f}")

    def save_settings(self):
        """保存设置"""
        # 收集设置值
        new_settings = {
            "window": {
                "opacity": self.opacity_slider.value() / 100.0,
                "always_on_top": self.always_on_top_checkbox.isChecked()
            },
            "monitor": {
                "check_interval": self.window_check_spinbox.value(),
                "ocr_interval": self.ocr_interval_spinbox.value(),
                "auto_start": self.auto_start_checkbox.isChecked()
            }
        }

        # 发送设置变更信号
        self.settings_changed.emit(new_settings)

        # 更新当前设置
        self.current_settings = new_settings

        # 关闭对话框
        self.accept()

    def get_settings(self) -> dict:
        """获取当前设置"""
        return self.current_settings.copy()
