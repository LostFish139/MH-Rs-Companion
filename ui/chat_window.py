
"""
UI模块 - 聊天窗口
"""
import sys
from typing import List, Dict
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QScrollArea,
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette
from config import WINDOW_CONFIG, UI_CONFIG, MONITOR_CONFIG

class ChatBubble(QWidget):
    """聊天气泡组件"""

    def __init__(self, message: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_user = is_user
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # 创建气泡
        bubble = QFrame()
        bubble.setFrameShape(QFrame.StyledPanel)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {'#DCF8C6' if self.is_user else '#E5E5EA'};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

        # 气泡内容布局
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(10, 10, 10, 10)

        # 消息标签
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont(UI_CONFIG["font_family"], UI_CONFIG["font_size"]))
        message_label.setMaximumWidth(UI_CONFIG["bubble_max_width"])
        message_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        bubble_layout.addWidget(message_label)

        # 添加气泡到布局
        if self.is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

class ChatWindow(QMainWindow):
    """聊天窗口 - 主窗口"""

    # 定义信号
    settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timers()
        # 记录最后显示的怪物名称，避免重复显示
        self.last_shown_monster = None

    def init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle(WINDOW_CONFIG["chat"]["title"])
        self.resize(WINDOW_CONFIG["chat"]["width"], WINDOW_CONFIG["chat"]["height"])
        self.setWindowFlags(Qt.WindowStaysOnTopHint if WINDOW_CONFIG["chat"]["always_on_top"] else Qt.Window)
        self.setWindowOpacity(WINDOW_CONFIG["chat"]["opacity"])

        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标题栏
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)

        # 创建聊天区域
        chat_area = self.create_chat_area()
        main_layout.addWidget(chat_area)

        # 创建控制区域
        control_area = self.create_control_area()
        main_layout.addWidget(control_area)

        # 设置样式
        self.set_style()

    def create_title_bar(self) -> QWidget:
        """创建标题栏"""
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: #2C3E50;")

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 0, 10, 0)

        # 标题
        title = QLabel("智能狩猎助手")
        title.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(24, 24)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(settings_btn)

        # 最小化按钮
        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(24, 24)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(minimize_btn)

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.8);
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return title_bar

    def create_chat_area(self) -> QScrollArea:
        """创建聊天区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 聊天内容容器
        chat_content = QWidget()
        chat_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chat_content_layout = QVBoxLayout(chat_content)
        chat_content_layout.setAlignment(Qt.AlignTop)
        chat_content_layout.setSpacing(UI_CONFIG["bubble_spacing"])
        # 添加弹性空间，使新消息显示在底部
        chat_content_layout.addStretch()

        scroll_area.setWidget(chat_content)

        # 保存引用
        self.chat_content = chat_content
        self.chat_content_layout = chat_content_layout

        # 添加欢迎消息
        self.add_assistant_message("欢迎来到怪物猎人崛起智能狩猎助手！\n\n我会帮你识别任务并推荐合适的武器。")

        return scroll_area

    def create_control_area(self) -> QWidget:
        """创建控制区域"""
        control_area = QWidget()
        control_area.setFixedHeight(30)
        control_area.setStyleSheet("background-color: #ECF0F1;")

        layout = QHBoxLayout(control_area)
        layout.setContentsMargins(10, 5, 10, 5)

        # 状态标签
        self.status_label = QLabel("等待游戏窗口...")
        self.status_label.setStyleSheet("color: #7F8C8D; font-size: 10px;")
        layout.addWidget(self.status_label)
        layout.addStretch()

        return control_area

    def setup_timers(self):
        """设置定时器"""
        # 游戏窗口检查定时器
        self.window_check_timer = QTimer()
        self.window_check_timer.timeout.connect(self.check_game_window)
        self.window_check_timer.start(MONITOR_CONFIG["check_interval"])

        # OCR识别定时器
        self.ocr_timer = QTimer()
        self.ocr_timer.timeout.connect(self.perform_ocr)

        # 如果配置为自动开始，则启动OCR定时器
        if MONITOR_CONFIG["auto_start"]:
            self.start_monitoring()

    def check_game_window(self):
        """检查游戏窗口状态"""
        # 这个方法将由外部通过信号槽连接实现
        pass

    def perform_ocr(self):
        """执行OCR识别"""
        # 这个方法将由外部通过信号槽连接实现
        pass

    def add_user_message(self, message: str):
        """添加用户消息"""
        bubble = ChatBubble(message, is_user=True)
        # 获取布局中的项目数量
        layout_count = self.chat_content_layout.count()
        # 如果最后一个项目是弹性空间，则在它之前插入新消息
        if layout_count > 0 and self.chat_content_layout.itemAt(layout_count - 1).spacerItem():
            self.chat_content_layout.insertWidget(layout_count - 1, bubble)
        else:
            self.chat_content_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def add_assistant_message(self, message: str):
        """添加助手消息"""
        bubble = ChatBubble(message, is_user=False)
        # 获取布局中的项目数量
        layout_count = self.chat_content_layout.count()
        # 如果最后一个项目是弹性空间，则在它之前插入新消息
        if layout_count > 0 and self.chat_content_layout.itemAt(layout_count - 1).spacerItem():
            self.chat_content_layout.insertWidget(layout_count - 1, bubble)
        else:
            self.chat_content_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """滚动到底部"""
        # 使用QTimer延迟滚动，确保UI更新完成
        QTimer.singleShot(10, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self):
        """实际执行滚动到底部的操作"""
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def update_status(self, status: str):
        """更新状态标签"""
        self.status_label.setText(status)

    def set_style(self):
        """设置窗口样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)

    def start_monitoring(self):
        """开始监控"""
        self.ocr_timer.start(MONITOR_CONFIG["ocr_interval"])
        self.update_status("监控中...")

    def stop_monitoring(self):
        """停止监控"""
        self.ocr_timer.stop()
        self.update_status("已停止")

    def show_weapon_recommendation(self, monster_name: str, weapons: List[Dict]):
        """显示武器推荐"""
        if not monster_name or not weapons:
            # 不在聊天窗口显示错误信息，只在终端记录
            return

        # 检查是否与上次显示的怪物相同
        if self.last_shown_monster == monster_name:
            # 相同则不显示，避免重复
            return

        # 更新最后显示的怪物名称
        self.last_shown_monster = monster_name

        # 构建推荐消息
        message = f"检测到任务目标: {monster_name}\n\n推荐武器:\n"
        for i, weapon in enumerate(weapons, 1):
            weapon_type = weapon.get("type", "未知属性")
            weapon_name = weapon.get("weapon", "未知武器")
            message += f"{i}. {weapon_name} ({weapon_type})\n"

        # 只在聊天窗口显示新的有用信息
        self.add_assistant_message(message)
