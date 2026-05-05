
"""
OCR测试工具 - 可视化测试OCR识别功能
"""
import sys
import os

# 添加项目根目录到Python路径
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QTextEdit,
                              QScrollArea, QFrame, QSplitter)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
import cv2
import numpy as np
from core.screenshot import ScreenshotCapture
from core.ocr import OCREngine
from core.matcher import DataMatcher
from config import OCR_REGION, DEBUG_SCREENSHOT_DIR


class OCRTesterWindow(QMainWindow):
    """OCR测试工具窗口"""

    def __init__(self):
        super().__init__()
        self.screenshot_capture = ScreenshotCapture()
        self.ocr_engine = OCREngine()
        self.data_matcher = DataMatcher()
        self.current_image = None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("OCR测试工具")
        self.resize(1200, 800)

        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：图像显示区域
        left_widget = self.create_image_panel()
        splitter.addWidget(left_widget)

        # 右侧：结果显示区域
        right_widget = self.create_result_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # 底部：控制按钮
        control_layout = QHBoxLayout()

        # 截图按钮
        capture_btn = QPushButton("📸 截取游戏窗口")
        capture_btn.clicked.connect(self.capture_game_window)
        control_layout.addWidget(capture_btn)

        # OCR识别按钮
        ocr_btn = QPushButton("🔍 OCR识别")
        ocr_btn.clicked.connect(self.perform_ocr)
        control_layout.addWidget(ocr_btn)

        # 完整测试按钮
        test_btn = QPushButton("🚀 完整测试（截图+OCR+匹配）")
        test_btn.clicked.connect(self.full_test)
        control_layout.addWidget(test_btn)

        main_layout.addLayout(control_layout)

    def create_image_panel(self):
        """创建图像显示面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # 标题
        title = QLabel("截图显示")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # 图像显示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 1px solid #CCCCCC; background-color: #F5F5F5;")
        self.image_label.setText("点击截取游戏窗口按钮开始")

        scroll_area.setWidget(self.image_label)
        layout.addWidget(scroll_area)

        # OCR区域信息
        self.ocr_region_label = QLabel()
        self.ocr_region_label.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.ocr_region_label)

        return panel

    def create_result_panel(self):
        """创建结果显示面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # 标题
        title = QLabel("识别结果")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # OCR识别结果
        ocr_label = QLabel("OCR识别结果:")
        layout.addWidget(ocr_label)

        self.ocr_result_text = QTextEdit()
        self.ocr_result_text.setReadOnly(True)
        self.ocr_result_text.setMaximumHeight(150)
        layout.addWidget(self.ocr_result_text)

        # 匹配结果
        match_label = QLabel("数据匹配结果:")
        layout.addWidget(match_label)

        self.match_result_text = QTextEdit()
        self.match_result_text.setReadOnly(True)
        layout.addWidget(self.match_result_text)

        # 武器推荐
        weapon_label = QLabel("武器推荐:")
        layout.addWidget(weapon_label)

        self.weapon_result_text = QTextEdit()
        self.weapon_result_text.setReadOnly(True)
        layout.addWidget(self.weapon_result_text)

        return panel

    def capture_game_window(self):
        """截取游戏窗口"""
        try:
            # 查找游戏窗口
            if not self.screenshot_capture.find_game_window():
                self.ocr_result_text.setText("未找到游戏窗口，请确保游戏正在运行。")
                return

            # 截取游戏窗口
            self.current_image = self.screenshot_capture.capture_window()
            if self.current_image is None:
                self.ocr_result_text.setText("截取游戏窗口失败。")
                return

            # 显示完整截图
            self.display_image(self.current_image)

            # 显示OCR区域信息
            if "bbox" in OCR_REGION:
                bbox = OCR_REGION["bbox"]
                self.ocr_region_label.setText(
                    f"OCR区域: X1={bbox[0]}, Y1={bbox[1]}, X2={bbox[2]}, Y2={bbox[3]}"
                )
            else:
                self.ocr_region_label.setText(
                    f"OCR区域: X={OCR_REGION['x']}, Y={OCR_REGION['y']}, "
                    f"宽度={OCR_REGION['width']}, 高度={OCR_REGION['height']}"
                )

            # 清空结果
            self.ocr_result_text.clear()
            self.match_result_text.clear()
            self.weapon_result_text.clear()

        except Exception as e:
            self.ocr_result_text.setText(f"截取游戏窗口失败: {str(e)}")

    def perform_ocr(self):
        """执行OCR识别"""
        if self.current_image is None:
            self.ocr_result_text.setText("请先截取游戏窗口。")
            return

        try:
            # 截取OCR区域
            ocr_img = self.screenshot_capture.capture_ocr_region()
            if ocr_img is None:
                self.ocr_result_text.setText("截取OCR区域失败。")
                return

            # 显示OCR区域图像
            self.display_image(ocr_img)

            # 执行OCR识别
            text = self.ocr_engine.recognize_text(ocr_img)
            self.ocr_result_text.setText(text if text else "未识别到文本")

        except Exception as e:
            self.ocr_result_text.setText(f"OCR识别失败: {str(e)}")

    def full_test(self):
        """完整测试：截图+OCR+匹配"""
        try:
            # 步骤1：截图
            self.capture_game_window()
            if self.current_image is None:
                return

            # 步骤2：OCR识别
            ocr_img = self.screenshot_capture.capture_ocr_region()
            if ocr_img is None:
                return

            # 显示OCR区域图像
            self.display_image(ocr_img)

            # 执行OCR识别
            text = self.ocr_engine.recognize_text(ocr_img)
            self.ocr_result_text.setText(text if text else "未识别到文本")

            if not text:
                return

            # 步骤3：数据匹配
            monster_name, weapons = self.data_matcher.get_recommendation(text)

            if monster_name:
                match_result = f"匹配成功！\n怪物名称: {monster_name}"
                self.match_result_text.setText(match_result)

                # 显示武器推荐
                if weapons:
                    weapon_text = "\n".join([
                        f"{i+1}. {w.get('weapon', '未知')} ({w.get('type', '未知')})"
                        for i, w in enumerate(weapons)
                    ])
                    self.weapon_result_text.setText(weapon_text)
                else:
                    self.weapon_result_text.setText("未找到武器推荐")
            else:
                self.match_result_text.setText("未找到匹配的怪物")
                self.weapon_result_text.clear()

        except Exception as e:
            self.ocr_result_text.setText(f"测试失败: {str(e)}")

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

    window = OCRTesterWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
