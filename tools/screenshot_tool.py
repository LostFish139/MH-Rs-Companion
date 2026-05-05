
"""
简单的截图工具 - 用于截取游戏窗口
"""
import sys
import os
import cv2
import numpy as np
import logging
import mss
import pygetwindow as gw
from PIL import Image
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QFileDialog,
                              QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage

# 配置日志
logger = logging.getLogger(__name__)

# 游戏窗口配置
GAME_WINDOW_TITLE = "Monster Hunter Rise"

# 截图区域配置（相对于游戏窗口的坐标）
CROP_REGION = {
    "left": 0,
    "top": 0,
    "width": 400,
    "height": 200
}

# 添加项目根目录到Python路径
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from core.screenshot import ScreenshotCapture


class ScreenshotToolWindow(QMainWindow):
    """截图工具窗口"""

    def __init__(self):
        super().__init__()
        self.screenshot_capture = ScreenshotCapture()
        self.current_image = None
        self.capture_full_window = False  # 是否截取整个窗口
        self.auto_capture = False  # 是否自动截图
        self.auto_capture_timer = QTimer()  # 自动截图定时器
        self.auto_capture_timer.timeout.connect(self.auto_capture_game_window)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("游戏窗口截图工具")
        self.resize(1000, 700)

        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 图像显示区域
        self.create_image_panel(main_layout)

        # 控制按钮区域
        self.create_control_panel(main_layout)

    def create_image_panel(self, parent_layout):
        """创建图像显示面板"""
        # 标题
        title = QLabel("截图显示")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        parent_layout.addWidget(title)

        # 图像显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 500)
        self.image_label.setStyleSheet("border: 1px solid #CCCCCC; background-color: #F5F5F5;")
        self.image_label.setText("点击截取游戏窗口按钮开始")

        scroll_area.setWidget(self.image_label)
        parent_layout.addWidget(scroll_area)

    def create_control_panel(self, parent_layout):
        """创建控制按钮面板"""
        control_layout = QHBoxLayout()

        # 截图按钮
        capture_btn = QPushButton("📸 截取游戏窗口")
        capture_btn.setMinimumHeight(40)
        capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        capture_btn.clicked.connect(self.capture_game_window)
        control_layout.addWidget(capture_btn)

        # 保存截图按钮
        save_btn = QPushButton("💾 保存截图")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a6ec4;
            }
        """)
        save_btn.clicked.connect(self.save_screenshot)
        control_layout.addWidget(save_btn)

        # 切换截图区域按钮
        region_btn = QPushButton("🔄 切换截图区域")
        region_btn.setMinimumHeight(40)
        region_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
        """)
        region_btn.clicked.connect(self.toggle_capture_region)
        control_layout.addWidget(region_btn)

        # 自动截图按钮
        self.auto_capture_btn = QPushButton("⏱️ 开始自动截图")
        self.auto_capture_btn.setMinimumHeight(40)
        self.auto_capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e24aa;
            }
            QPushButton:pressed {
                background-color: #7b1fa2;
            }
        """)
        self.auto_capture_btn.clicked.connect(self.toggle_auto_capture)
        control_layout.addWidget(self.auto_capture_btn)

        parent_layout.addLayout(control_layout)

    def capture_game_window(self):
        """截取游戏窗口（使用mss + pygetwindow + Pillow）"""
        try:
            # 1. 定位游戏窗口
            windows = gw.getWindowsWithTitle(GAME_WINDOW_TITLE)
            if not windows:
                self.image_label.setText(f"未找到标题包含【{GAME_WINDOW_TITLE}】的窗口，请确认游戏已启动")
                return

            game_window = windows[0]
            logger.info(f"找到游戏窗口：{game_window.title}")
            logger.info(f"窗口位置：左{game_window.left} 上{game_window.top} 宽{game_window.width} 高{game_window.height}")

            # 2. 初始化mss截图器
            with mss.mss() as sct:
                # 3. 定义截图区域（游戏窗口的绝对坐标）
                monitor = {
                    "top": game_window.top,
                    "left": game_window.left,
                    "width": game_window.width,
                    "height": game_window.height
                }

                # 4. 捕获游戏窗口画面
                screenshot = sct.grab(monitor)

                # 转为PIL Image格式
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                # 5. 根据模式截取整个窗口或指定区域
                if self.capture_full_window:
                    # 截取整个窗口
                    final_img = img
                else:
                    # 截取指定区域
                    final_img = img.crop((
                        CROP_REGION["left"],
                        CROP_REGION["top"],
                        CROP_REGION["left"] + CROP_REGION["width"],
                        CROP_REGION["top"] + CROP_REGION["height"]
                    ))

                # 转换为OpenCV格式
                self.current_image = cv2.cvtColor(np.array(final_img), cv2.COLOR_RGB2BGR)

                logger.info(f"截图成功，尺寸：{self.current_image.shape[1]}x{self.current_image.shape[0]}")

                # 显示截图
                self.display_image(self.current_image)

        except Exception as e:
            self.image_label.setText(f"截取游戏窗口失败: {str(e)}")
            logger.error(f"截取游戏窗口失败: {str(e)}")

    def save_screenshot(self):
        """保存截图"""
        if self.current_image is None:
            self.image_label.setText("请先截取游戏窗口。")
            return

        try:
            # 打开文件保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存截图",
                "",
                "PNG文件 (*.png);;JPEG文件 (*.jpg);;所有文件 (*.*)"
            )

            if file_path:
                # 确保文件扩展名正确
                if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path += '.png'

                # 保存截图
                cv2.imwrite(file_path, self.current_image)
                self.image_label.setText(f"截图已保存到: {file_path}")

                # 重新显示截图
                self.display_image(self.current_image)

        except Exception as e:
            self.image_label.setText(f"保存截图失败: {str(e)}")

    def toggle_capture_region(self):
        """切换截图区域"""
        self.capture_full_window = not self.capture_full_window
        if self.capture_full_window:
            self.image_label.setText("已切换到截取整个窗口模式")
        else:
            self.image_label.setText(f"已切换到截取指定区域模式 (左上角 {CROP_REGION['width']}x{CROP_REGION['height']})")

    def toggle_auto_capture(self):
        """切换自动截图"""
        self.auto_capture = not self.auto_capture
        if self.auto_capture:
            self.auto_capture_btn.setText("⏱️ 停止自动截图")
            self.auto_capture_timer.start(100)  # 每100毫秒截图一次
            self.image_label.setText("自动截图已启动")
        else:
            self.auto_capture_btn.setText("⏱️ 开始自动截图")
            self.auto_capture_timer.stop()
            self.image_label.setText("自动截图已停止")

    def auto_capture_game_window(self):
        """自动截取游戏窗口"""
        self.capture_game_window()

    def display_image(self, cv_img):
        """显示OpenCV图像"""
        # 转换颜色空间
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        # 转换为Qt图像
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # 显示图像
        pixmap = QPixmap.fromImage(qt_image)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ScreenshotToolWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
