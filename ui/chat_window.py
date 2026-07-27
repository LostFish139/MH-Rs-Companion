
"""
UI模块 - 聊天窗口
支持简洁模式和调试模式，多怪物显示，狩猎技巧展示
气泡支持4方位小尾巴和无尾巴样式
简洁模式下背景透明，仅显示气泡信息
"""
import sys
import re
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QScrollArea,
                              QFrame, QSizePolicy, QComboBox, QMenu, QSizeGrip)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint, QRect, QSize
from PySide6.QtGui import (QFont, QColor, QPalette, QAction, QPainter, QPainterPath,
                           QPen, QBrush, QPolygon, QMouseEvent)
from config import WINDOW_CONFIG, UI_CONFIG, MONITOR_CONFIG, WEAPON_CONFIG, TIPS_CONFIG


class ChatBubble(QWidget):
    """聊天气泡组件 - 圆角矩形样式"""

    def __init__(self, message: str, is_user: bool = False, message_type: str = "normal",
                 bubble_config: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_user = is_user
        self.message_type = message_type  # normal, warning, success, info, error
        self.bubble_config = bubble_config or UI_CONFIG.get("bubble", {})
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 气泡颜色（带透明度）
        bg_color = self._get_bubble_color_rgba()
        radius = self.bubble_config.get("radius", 14)
        padding = self.bubble_config.get("padding", 10)

        # 气泡容器
        bubble = QFrame()
        bubble.setObjectName("bubbleFrame")
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setStyleSheet(f"""
            QFrame#bubbleFrame {{
                background-color: {bg_color};
                border-radius: {radius}px;
                padding: 0px;
            }}
        """)

        # 气泡内容布局
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(padding, padding, padding, padding)
        bubble_layout.setSpacing(2)

        # 消息标签
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setFont(QFont(UI_CONFIG["font_family"], UI_CONFIG["font_size"]))
        message_label.setMaximumWidth(UI_CONFIG["bubble_max_width"])
        message_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        message_label.setTextFormat(Qt.PlainText)
        message_label.setStyleSheet("background: transparent; color: #333333;")

        bubble_layout.addWidget(message_label)

        # 对齐
        if self.is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._bubble_frame = bubble

    def _get_bubble_color_rgba(self) -> str:
        """根据消息类型获取气泡背景色（RGBA格式，支持透明度）"""
        opacity = UI_CONFIG.get("bubble_opacity", 0.95)
        alpha = int(opacity * 255)

        if self.is_user:
            r, g, b = 220, 248, 198
        elif self.message_type == "warning":
            r, g, b = 255, 224, 178
        elif self.message_type == "success":
            r, g, b = 200, 230, 201
        elif self.message_type == "info":
            r, g, b = 187, 222, 251
        elif self.message_type == "error":
            r, g, b = 255, 205, 210
        else:
            r, g, b = 240, 240, 240

        return f"rgba({r}, {g}, {b}, {alpha})"

    def update_opacity(self, opacity: float):
        """更新气泡透明度"""
        UI_CONFIG["bubble_opacity"] = opacity
        bg_color = self._get_bubble_color_rgba()
        radius = self.bubble_config.get("radius", 14)
        self._bubble_frame.setStyleSheet(f"""
            QFrame#bubbleFrame {{
                background-color: {bg_color};
                border-radius: {radius}px;
                padding: 0px;
            }}
        """)


class ChatWindow(QMainWindow):
    """聊天窗口 - 主窗口"""

    # 定义信号
    settings_requested = Signal()
    weapon_changed = Signal(str)
    mode_changed = Signal(str)  # clean / debug
    bubble_style_changed = Signal(str)  # 气泡样式变化信号

    def __init__(self):
        super().__init__()
        self.display_mode = UI_CONFIG.get("default_mode", "clean")
        self.current_weapon = WEAPON_CONFIG.get("current_weapon", "盾斧")
        self.max_context_messages = UI_CONFIG.get("max_context_messages", 3)
        self.message_bubbles = []  # 存储消息气泡引用
        self.small_hints = []  # 存储小字提示气泡引用（独立管理，不占用上下文气泡名额）
        self.last_shown_monsters = set()  # 最后显示的怪物集合

        # 去重标记 - 用于简洁模式下只显示一次警告
        self._no_window_warned = False
        self._no_task_warned = False

        # 窗口拖动相关
        self.drag_position = None
        self.is_dragging = False

        # 定时器
        self.window_check_timer = None
        self.ocr_timer = None

        self.init_ui()
        self.apply_mode_style()
        self.setup_timers()

    def init_ui(self):
        """初始化UI"""
        chat_cfg = WINDOW_CONFIG["chat"]

        # 窗口基础设置
        self.setWindowTitle(chat_cfg["title"])
        self.resize(chat_cfg["width"], chat_cfg["height"])
        self.setMinimumSize(chat_cfg.get("min_width", 250), chat_cfg.get("min_height", 120))

        # 无边框 + 置顶
        flags = Qt.FramelessWindowHint
        if chat_cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        # 背景透明支持
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主部件
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # 主布局
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 标题栏
        self.title_bar = self._create_title_bar()
        self.main_layout.addWidget(self.title_bar)

        # 聊天区域
        self.chat_area = self._create_chat_area()
        self.main_layout.addWidget(self.chat_area, 1)

        # 状态栏
        self.status_bar = self._create_status_bar()
        self.main_layout.addWidget(self.status_bar)

        # 右下角调整大小手柄
        size_grip = QSizeGrip(self)
        size_grip.setStyleSheet("background: transparent;")
        size_grip.setFixedSize(16, 16)
        self.size_grip = size_grip

        # 设置右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _create_title_bar(self) -> QWidget:
        """创建标题栏"""
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(36)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(4)

        # 标题
        title = QLabel("狩猎助手")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addStretch()

        # 武器选择
        self.weapon_combo = QComboBox()
        self.weapon_combo.addItems(WEAPON_CONFIG.get("all_weapons", []))
        self.weapon_combo.setCurrentText(self.current_weapon)
        self.weapon_combo.setObjectName("weaponCombo")
        self.weapon_combo.currentTextChanged.connect(self._on_weapon_changed)
        layout.addWidget(self.weapon_combo)

        # 模式切换按钮
        self.mode_btn = QPushButton("🔍")
        self.mode_btn.setFixedSize(24, 24)
        self.mode_btn.setToolTip("切换显示模式")
        self.mode_btn.setObjectName("modeBtn")
        self.mode_btn.clicked.connect(self.toggle_display_mode)
        layout.addWidget(self.mode_btn)

        # 设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(24, 24)
        settings_btn.setToolTip("设置")
        settings_btn.setObjectName("iconBtn")
        settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(settings_btn)

        # 最小化
        min_btn = QPushButton("─")
        min_btn.setFixedSize(24, 24)
        min_btn.setObjectName("iconBtn")
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)

        # 关闭
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return title_bar

    def _create_chat_area(self) -> QScrollArea:
        """创建聊天区域"""
        scroll_area = QScrollArea()
        scroll_area.setObjectName("chatScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 聊天内容容器
        chat_content = QWidget()
        chat_content.setObjectName("chatContent")
        chat_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.chat_layout = QVBoxLayout(chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(UI_CONFIG["bubble_spacing"])
        self.chat_layout.setContentsMargins(6, 8, 6, 8)
        self.chat_layout.addStretch()

        scroll_area.setWidget(chat_content)
        self.chat_content = chat_content

        return scroll_area

    def _create_status_bar(self) -> QWidget:
        """创建状态栏"""
        bar = QWidget()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(24)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 2, 10, 2)

        self.status_label = QLabel("等待游戏窗口...")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.mode_label = QLabel("简洁模式")
        self.mode_label.setObjectName("modeLabel")
        layout.addWidget(self.mode_label)

        return bar

    def apply_mode_style(self):
        """根据当前模式应用样式"""
        clean_cfg = UI_CONFIG.get("clean_mode", {})

        if self.display_mode == "clean":
            # 简洁模式
            self.mode_btn.setText("💬")
            self.mode_btn.setToolTip("切换到调试模式")
            self.mode_label.setText("简洁模式")

            # 隐藏标题栏和状态栏
            if clean_cfg.get("hide_title_bar", True):
                self.title_bar.hide()
            if clean_cfg.get("hide_status_bar", True):
                self.status_bar.hide()
            if clean_cfg.get("show_border", False):
                self.setStyleSheet(self._get_border_style())
            else:
                self.setStyleSheet(self._get_clean_style())

            # 裁剪消息
            self._trim_messages()
        else:
            # 调试模式
            self.mode_btn.setText("🔍")
            self.mode_btn.setToolTip("切换到简洁模式")
            self.mode_label.setText("调试模式")

            self.title_bar.show()
            self.status_bar.show()
            self.setStyleSheet(self._get_debug_style())

        self.size_grip.setVisible(self.display_mode == "debug")

    def _get_clean_style(self) -> str:
        """简洁模式样式 - 背景透明"""
        return """
            QMainWindow { background: transparent; }
            #centralWidget { background: transparent; }
            #chatScrollArea {
                background: transparent;
                border: none;
            }
            #chatScrollArea > QWidget > QWidget {
                background: transparent;
            }
            #chatContent { background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
            QScrollBar::handle:vertical { background: transparent; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """

    def _get_border_style(self) -> str:
        """简洁模式带边框样式"""
        return """
            QMainWindow { background: transparent; }
            #centralWidget {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            #chatScrollArea {
                background: transparent;
                border: none;
            }
            #chatScrollArea > QWidget > QWidget {
                background: transparent;
            }
            #chatContent { background: transparent; }
            QScrollBar:vertical { width: 0px; background: transparent; }
            QScrollBar::handle:vertical { background: transparent; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """

    def _get_debug_style(self) -> str:
        """调试模式样式"""
        return """
            QMainWindow {
                background-color: #FAFAFA;
                border: 1px solid #BDBDBD;
                border-radius: 6px;
            }
            #centralWidget { background: #FAFAFA; }
            #titleBar {
                background-color: #2C3E50;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            #titleLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            #weaponCombo {
                background-color: #34495E;
                color: white;
                border: 1px solid #4A6785;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                min-width: 60px;
            }
            #weaponCombo:hover { background-color: #3D566E; }
            #weaponCombo::drop-down { border: none; width: 16px; }
            #iconBtn {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 12px;
            }
            #iconBtn:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            #closeBtn {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 12px;
            }
            #closeBtn:hover {
                background-color: #E74C3C;
                border-radius: 4px;
            }
            #chatScrollArea {
                background-color: #FAFAFA;
                border: none;
            }
            #chatContent { background: #FAFAFA; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover { background: #9E9E9E; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            #statusBar { background-color: #ECF0F1; }
            #statusLabel { color: #7F8C8D; font-size: 10px; }
            #modeLabel { color: #95A5A6; font-size: 9px; }
        """

    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)

        # 模式切换
        if self.display_mode == "clean":
            mode_action = QAction("切换到调试模式", self)
            mode_action.triggered.connect(lambda: self._set_mode("debug"))
        else:
            mode_action = QAction("切换到简洁模式", self)
            mode_action.triggered.connect(lambda: self._set_mode("clean"))
        menu.addAction(mode_action)

        menu.addSeparator()

        # 自动滚动开关
        scroll_action = QAction("自动滚动到底部", self)
        scroll_action.setCheckable(True)
        scroll_action.setChecked(UI_CONFIG.get("auto_scroll_to_bottom", True))
        scroll_action.triggered.connect(self._toggle_auto_scroll)
        menu.addAction(scroll_action)

        menu.addSeparator()

        # 设置
        settings_action = QAction("设置...", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.exec(self.mapToGlobal(pos))

    def _toggle_auto_scroll(self, checked: bool):
        """切换自动滚动"""
        UI_CONFIG["auto_scroll_to_bottom"] = checked
        if checked:
            self._scroll_to_bottom()

    def _set_mode(self, mode: str):
        """设置显示模式"""
        if self.display_mode != mode:
            self.toggle_display_mode()

    def toggle_display_mode(self):
        """切换显示模式"""
        if self.display_mode == "clean":
            self.display_mode = "debug"
        else:
            self.display_mode = "clean"
        self.apply_mode_style()
        self.mode_changed.emit(self.display_mode)

    def _on_weapon_changed(self, weapon: str):
        """武器选择改变"""
        self.current_weapon = weapon
        self.weapon_changed.emit(weapon)
        self.last_shown_monsters.clear()
        if self.display_mode == "debug":
            self.add_assistant_message(f"已切换到{weapon}，狩猎技巧将针对{weapon}生成。", "info")

    # ===== 消息添加 =====

    def add_user_message(self, message: str):
        """添加用户消息"""
        self._add_bubble(ChatBubble(message, is_user=True))

    def add_assistant_message(self, message: str, message_type: str = "normal"):
        """添加助手消息"""
        # 简洁模式下，过滤掉不重要的消息
        if self.display_mode == "clean":
            # 只显示 info 和 success 类型的重要消息
            # normal 和 warning 类型的消息可能是冗余提示
            if message_type in ("normal",):
                return
            if message_type == "warning":
                # 警告类消息去重处理
                if "未找到游戏窗口" in message or "未检测到窗口" in message:
                    if self._no_window_warned:
                        return
                    self._no_window_warned = True
                if "未识别到任务" in message or "请承接任务" in message:
                    if self._no_task_warned:
                        return
                    self._no_task_warned = True

        bubble = ChatBubble(message, is_user=False, message_type=message_type,
                          bubble_config=UI_CONFIG.get("bubble", {}).copy())
        self._add_bubble(bubble)

    def _add_bubble(self, bubble: ChatBubble):
        """添加气泡到布局"""
        layout_count = self.chat_layout.count()
        if layout_count > 0 and self.chat_layout.itemAt(layout_count - 1).spacerItem():
            self.chat_layout.insertWidget(layout_count - 1, bubble)
        else:
            self.chat_layout.addWidget(bubble)

        self.message_bubbles.append(bubble)
        self._trim_messages()
        self._scroll_to_bottom()

    def _trim_messages(self):
        """裁剪消息数量，严格控制上下文气泡数"""
        max_messages = self.max_context_messages if self.display_mode == "clean" else 50

        # 从列表头部移除超出数量的气泡
        while len(self.message_bubbles) > max_messages:
            oldest = self.message_bubbles.pop(0)
            # 从布局中移除
            self.chat_layout.removeWidget(oldest)
            oldest.deleteLater()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        if not UI_CONFIG.get("auto_scroll_to_bottom", True):
            return
        # 使用QTimer延迟滚动，确保布局更新完成
        QTimer.singleShot(30, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self):
        """实际执行滚动到底部"""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 再次确保滚动到底部（布局可能还在更新）
        QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def update_status(self, status: str):
        """更新状态标签"""
        self.status_label.setText(status)
        # 检测到任务时重置警告标记
        if "识别成功" in status or "监控中" in status:
            self._no_window_warned = False
            self._no_task_warned = False

    # ===== 推荐显示 =====

    def show_full_recommendation(self, full_result: Dict):
        """显示完整推荐信息（多怪物+武器推荐+狩猎技巧）"""
        monsters = full_result.get("monsters", [])
        if not monsters:
            return

        monster_names = [m.get("name", "") for m in monsters if m.get("found", False)]
        monster_set = set(monster_names)

        if monster_set == self.last_shown_monsters:
            return
        self.last_shown_monsters = monster_set

        # 重置警告标记（检测到新任务了）
        self._no_task_warned = False

        # 检测到新任务时，清理之前的小字提示（它们是临时信息）
        self._clear_small_hints()

        is_multi = full_result.get("is_multi_monster", False)

        if self.display_mode == "clean":
            message = self._format_clean_recommendation(monsters, is_multi)
            self.add_assistant_message(message, "info")
        else:
            message = self._format_debug_recommendation(monsters, is_multi)
            self.add_assistant_message(message, "info")

    def _format_clean_recommendation(self, monsters: List[Dict], is_multi: bool) -> str:
        """格式化简洁模式推荐 - 展示完整核心信息"""
        lines = []

        if is_multi:
            names = "、".join([m.get("name", "") for m in monsters])
            lines.append(f"🎯 目标：{names}")
            for m in monsters:
                if not m.get("found", False):
                    continue
                name = m.get("name", "")
                weakest = m.get("weakest_element", "")
                lines.append(f"  弱{weakest}")
        else:
            monster = monsters[0]
            monster_name = monster.get("name", "")
            weakest = monster.get("weakest_element", "")

            # 第一行：怪物名 + 最弱属性
            lines.append(f"🎯 {monster_name} | 弱{weakest}")

            # 讨伐建议（完整显示，不截断）
            hunt_info = monster.get("hunt_info", {})
            hunt_suggestion = hunt_info.get("hunt_suggestion", "")
            if hunt_suggestion:
                # 去掉开头的序号前缀（如 "1."、"2."、"一、" 等）
                hunt_suggestion = re.sub(r'^[\d一二三四五六七八九十]+[.、．]\s*', '', hunt_suggestion)
                lines.append(f"📌 讨伐建议：{hunt_suggestion}")

            # 白给招式
            free_moves = hunt_info.get("free_moves", "")
            if free_moves:
                lines.append(f"🎁 白给招：{free_moves}")

            # 倒地机制
            stun_mech = hunt_info.get("stun_mechanism", "")
            if stun_mech:
                lines.append(f"💥 倒地机制：{stun_mech}")

            # 特殊机制
            special_mech = hunt_info.get("special_mechanism", "")
            if special_mech:
                lines.append(f"⚡ 特殊机制：{special_mech}")

            # 武器专属技巧（针对当前武器对该怪物的特定操作建议）
            tips = monster.get("tips", {})
            weapon_tips = tips.get("weapon_specific", [])
            if weapon_tips:
                for tip in weapon_tips[:TIPS_CONFIG.get("max_tips_per_category", 2)]:
                    lines.append(f"💡 技巧：{tip}")

        return "\n".join(lines)

    def _get_element_weapon_name(self, monster: Dict) -> str:
        """获取属性武器名称（优先属性瓶/属性武器，跳过榴弹瓶等物理武器）"""
        weapons = monster.get("weapons", [])
        prioritize_element = WEAPON_CONFIG.get("prioritize_element_weapon", True)

        # 先找当前武器的属性武器
        for w in weapons:
            if w.get("weapon_type") == self.current_weapon:
                weapon_name = w.get("weapon", "")
                # 如果优先属性武器，检查是否是属性武器
                if prioritize_element:
                    # 盾斧：属性瓶算属性武器，榴弹瓶不算
                    if self.current_weapon == "盾斧":
                        if "榴弹瓶" not in weapon_name and "榴弹" not in weapon_name:
                            return weapon_name
                        # 是榴弹瓶，继续找下一个
                        continue
                    # 其他武器：默认有属性值就算属性武器
                    element = w.get("element", "")
                    if element and element not in ("物理", "无"):
                        return weapon_name
                    continue
                else:
                    return weapon_name

        # 如果没有找到属性武器，退而求其次返回第一个当前武器
        for w in weapons:
            if w.get("weapon_type") == self.current_weapon:
                return w.get("weapon", "")

        # 没有当前武器，返回第一个
        if weapons:
            return weapons[0].get("weapon", "")

        return ""

    def _get_clean_tips(self, monster: Dict) -> str:
        """获取简洁模式下的狩猎技巧 - 怪物技巧优先"""
        tips = monster.get("tips", {})
        max_tips = TIPS_CONFIG.get("max_tips_per_category", 2)
        lines = []

        # 怪物专属技巧优先（针对怪物特点的核心提示）
        if TIPS_CONFIG.get("show_monster_tips", True):
            monster_tips = tips.get("monster_specific", [])
            if monster_tips:
                for tip in monster_tips[:max_tips]:
                    lines.append(f"💡 {tip}")

        # 武器专属技巧（针对当前武器的操作建议）
        if TIPS_CONFIG.get("show_weapon_tips", True):
            weapon_tips = tips.get("weapon_specific", [])
            if weapon_tips:
                remaining = max(1, max_tips - len(lines))
                for tip in weapon_tips[:remaining]:
                    lines.append(f"⚔️ {tip}")

        return "\n".join(lines)

    def _format_debug_recommendation(self, monsters: List[Dict], is_multi: bool) -> str:
        """格式化调试模式推荐 - 详细显示"""
        lines = []

        if is_multi:
            lines.append("【多怪物任务】")
            for m in monsters:
                lines.append(f"  - {m.get('name', '')} ({m.get('type', '未知')})")
            lines.append("")
        else:
            m = monsters[0]
            lines.append(f"【怪物信息】{m.get('name', '')} ({m.get('type', '未知')})")
            lines.append("")

        for monster in monsters:
            if not monster.get("found", False):
                lines.append(f"⚠️ {monster.get('name', '')} 未找到数据")
                continue

            m_name = monster.get("name", "")
            if is_multi:
                lines.append(f"=== {m_name} ===")

            # 属性弱点
            weakness = monster.get("weakness", {})
            weakest = monster.get("weakest_element", "")
            weakest_parts = monster.get("weakest_parts", [])
            status_weak = monster.get("status_weakness", {})

            lines.append(f"【属性弱点】最弱: {weakest}")
            weak_str = "  ".join([f"{k}:{v}" for k, v in weakness.items()])
            lines.append(f"  详细: {weak_str}")
            lines.append(f"【弱点部位】{', '.join(weakest_parts) if weakest_parts else '未知'}")
            if status_weak:
                status_str = "  ".join([f"{k}:{v}" for k, v in status_weak.items()])
                lines.append(f"【状态异常】{status_str}")
            lines.append("")

            # 武器推荐（属性武器标★）
            weapons = monster.get("weapons", [])
            lines.append("【推荐武器】")
            for i, w in enumerate(weapons, 1):
                w_type = w.get("weapon_type", "未知")
                w_name = w.get("weapon", "未知武器")
                w_element = w.get("element", "未知属性")
                marker = " ★当前" if w_type == self.current_weapon else ""
                # 标记属性武器
                is_elem = self._is_element_weapon(w, w_type)
                elem_marker = " 属性" if is_elem else " 物理"
                lines.append(f"  {i}. {w_type}{marker}{elem_marker}: {w_name} ({w_element})")
            lines.append("")

            # 讨伐建议（核心）
            hunt_info = monster.get("hunt_info", {})
            if hunt_info.get("found", False):
                grade = hunt_info.get("grade", "")
                grade_str = f" ({grade})" if grade else ""
                lines.append(f"【讨伐建议】{grade_str}")
                hunt_suggestion = hunt_info.get("hunt_suggestion", "")
                if hunt_suggestion:
                    lines.append(f"  {hunt_suggestion}")

                free_moves = hunt_info.get("free_moves", "")
                if free_moves:
                    lines.append("")
                    lines.append(f"【白给招式】{free_moves}")

                stun_mech = hunt_info.get("stun_mechanism", "")
                if stun_mech:
                    lines.append("")
                    lines.append(f"【倒地机制】{stun_mech}")

                special_mech = hunt_info.get("special_mechanism", "")
                if special_mech:
                    lines.append("")
                    lines.append(f"【特殊机制】{special_mech}")

                lines.append("")

            # 狩猎技巧
            tips = monster.get("tips", {})
            has_tips = False

            monster_tips = tips.get("monster_specific", [])
            if monster_tips:
                has_tips = True
                lines.append("【怪物技巧】")
                for tip in monster_tips[:3]:
                    lines.append(f"  • {tip}")

            weapon_tips = tips.get("weapon_specific", [])
            if weapon_tips:
                has_tips = True
                lines.append(f"【{self.current_weapon}技巧】")
                for tip in weapon_tips[:3]:
                    lines.append(f"  • {tip}")

            general_tips = tips.get("general", [])
            if TIPS_CONFIG.get("show_general_tips", False) and general_tips:
                has_tips = True
                lines.append("【通用技巧】")
                for tip in general_tips[:2]:
                    lines.append(f"  • {tip}")

            if has_tips:
                lines.append("")

        return "\n".join(lines).rstrip()

    def _is_element_weapon(self, weapon: Dict, weapon_type: str) -> bool:
        """判断是否为属性武器"""
        w_name = weapon.get("weapon", "")
        element = weapon.get("element", "")

        if weapon_type == "盾斧":
            # 盾斧：属性瓶是属性武器，榴弹瓶不是
            return "榴弹瓶" not in w_name and "榴弹" not in w_name

        # 其他武器：有属性值且不是物理/无，就算属性武器
        return bool(element) and element not in ("物理", "无", "")

    def show_weapon_recommendation(self, monster_name: str, weapons: List[Dict]):
        """兼容旧接口"""
        if not monster_name or not weapons:
            return
        if monster_name in self.last_shown_monsters and len(self.last_shown_monsters) == 1:
            return
        self.last_shown_monsters = {monster_name}
        message = f"🎯 {monster_name}\n💡 推荐武器:"
        for w in weapons[:3]:
            message += f"\n  • {w.get('weapon', '')}"
        self.add_assistant_message(message, "info")

    # ===== 窗口拖动 =====

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 简洁模式下整个窗口都可以拖动
            if self.display_mode == "clean":
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.is_dragging = True
                event.accept()
            else:
                # 调试模式下只有标题栏可以拖动
                if self.title_bar.geometry().contains(event.position().toPoint()):
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self.is_dragging = True
                    event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.is_dragging = False
        self.drag_position = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 调整大小手柄位置
        self.size_grip.move(self.width() - 16, self.height() - 16)

    def setup_timers(self):
        """设置定时器"""
        from PySide6.QtCore import QTimer
        # 游戏窗口检查定时器
        self.window_check_timer = QTimer()
        self.window_check_timer.start(MONITOR_CONFIG["check_interval"])

        # OCR识别定时器
        self.ocr_timer = QTimer()

        # 如果配置为自动开始，则启动OCR定时器
        if MONITOR_CONFIG["auto_start"]:
            self.start_monitoring()

        # 延迟显示欢迎消息，方便用户定位窗口
        QTimer.singleShot(500, self._show_welcome_message)

    def _show_welcome_message(self):
        """显示欢迎消息，方便用户定位透明窗口"""
        welcome = "系统启动成功！请承接任务，开始狩猎吧！"
        self.add_assistant_message(welcome, "success")

    def set_bubble_opacity(self, opacity: float):
        """设置所有气泡的背景透明度"""
        UI_CONFIG["bubble_opacity"] = max(0.3, min(1.0, opacity))
        for bubble in self.message_bubbles:
            if hasattr(bubble, 'update_opacity'):
                bubble.update_opacity(UI_CONFIG["bubble_opacity"])
        # 同时更新小字提示气泡的透明度
        bg_alpha = int(UI_CONFIG["bubble_opacity"] * 180)
        text_alpha = int(UI_CONFIG["bubble_opacity"] * 230)
        font_size = max(7, UI_CONFIG["font_size"] - 2)
        radius = max(6, UI_CONFIG["bubble"].get("radius", 12) - 4)
        for hint in self.small_hints:
            bubble = hint.findChild(QFrame, "smallHintBubble")
            if bubble:
                bubble.setStyleSheet(f"""
                    QFrame#smallHintBubble {{
                        background-color: rgba(230, 230, 230, {bg_alpha});
                        border-radius: {radius}px;
                    }}
                """)
            label = hint.findChild(QLabel)
            if label:
                label.setStyleSheet(f"""
                    color: rgba(100, 100, 100, {text_alpha});
                    font-size: {font_size}pt;
                    font-family: {UI_CONFIG['font_family']};
                    background: transparent;
                """)

    def _add_small_hint(self, message: str):
        """添加小字提示气泡（简洁模式下的低调小气泡）"""
        from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget, QFrame
        from PySide6.QtCore import Qt

        opacity = UI_CONFIG.get("bubble_opacity", 0.95)
        bg_alpha = int(opacity * 180)  # 比正常气泡更淡一点
        text_alpha = int(opacity * 230)
        font_size = max(7, UI_CONFIG["font_size"] - 2)
        radius = max(6, UI_CONFIG["bubble"].get("radius", 12) - 4)
        padding_v = 4
        padding_h = 10

        hint_widget = QWidget()
        hint_widget.setProperty("smallHint", True)
        layout = QHBoxLayout(hint_widget)
        layout.setContentsMargins(0, 2, 0, 2)

        # 小气泡容器（有背景色的小气泡）
        bubble = QFrame()
        bubble.setObjectName("smallHintBubble")
        bubble.setStyleSheet(f"""
            QFrame#smallHintBubble {{
                background-color: rgba(230, 230, 230, {bg_alpha});
                border-radius: {radius}px;
            }}
        """)

        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(padding_h, padding_v, padding_h, padding_v)

        label = QLabel(message)
        label.setStyleSheet(f"""
            color: rgba(100, 100, 100, {text_alpha});
            font-size: {font_size}pt;
            font-family: {UI_CONFIG['font_family']};
            background: transparent;
        """)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setMaximumWidth(int(UI_CONFIG["bubble_max_width"] * 0.85))

        bubble_layout.addWidget(label)

        layout.addStretch()
        layout.addWidget(bubble)
        layout.addStretch()

        hint_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.chat_layout.addWidget(hint_widget)
        self.small_hints.append(hint_widget)
        # 限制小字提示数量，最多保留3条
        self._trim_small_hints()
        self._scroll_to_bottom()

    def _trim_small_hints(self):
        """裁剪小字提示数量，最多保留3条"""
        max_hints = 3
        while len(self.small_hints) > max_hints:
            oldest = self.small_hints.pop(0)
            self.chat_layout.removeWidget(oldest)
            oldest.deleteLater()

    def _clear_small_hints(self):
        """清理所有小字提示"""
        for hint in self.small_hints:
            self.chat_layout.removeWidget(hint)
            hint.deleteLater()
        self.small_hints.clear()

    def check_game_window(self):
        """检查游戏窗口状态（由外部连接实现）"""
        pass

    def perform_ocr(self):
        """执行OCR识别（由外部连接实现）"""
        pass

    def start_monitoring(self):
        """开始监控"""
        if self.ocr_timer:
            self.ocr_timer.start(MONITOR_CONFIG["ocr_interval"])
        self.update_status("监控中...")

    def stop_monitoring(self):
        """停止监控"""
        if self.ocr_timer:
            self.ocr_timer.stop()
        self.update_status("已停止")
