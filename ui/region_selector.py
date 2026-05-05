
"""
UI模块 - OCR识别区域选择器
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QSpinBox, QSlider, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPixmap
import cv2
import numpy as np
from backup.screenshot import ScreenshotCapture

class RegionSelectorWidget(QWidget):
    """OCR识别区域选择器"""

    region_changed = Signal(dict)  # 区域变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.screenshot_capture = ScreenshotCapture()
        self.current_image = None
        self.selection_rect = None
        self.drawing = False
        self.start_point = QPoint()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 图像显示区域
        self.image_label = ImageLabel()
        self.image_label.setMinimumSize(400, 300)
        self.image_label.selection_changed.connect(self.on_selection_changed)
        layout.addWidget(self.image_label)

        # 控制区域
        controls_layout = QHBoxLayout()

        # 截取游戏窗口按钮
        self.capture_btn = QPushButton("截取游戏窗口")
        self.capture_btn.clicked.connect(self.capture_game_window)
        controls_layout.addWidget(self.capture_btn)

        # 手动选择区域按钮
        self.select_btn = QPushButton("手动选择区域")
        self.select_btn.clicked.connect(self.enable_selection_mode)
        self.select_btn.setEnabled(False)
        controls_layout.addWidget(self.select_btn)

        layout.addLayout(controls_layout)

        # 区域信息显示
        info_layout = QFormLayout()

        self.x_spinbox = QSpinBox()
        self.x_spinbox.setRange(0, 5000)
        self.x_spinbox.valueChanged.connect(self.on_spinbox_changed)
        info_layout.addRow("X1坐标:", self.x_spinbox)

        self.y_spinbox = QSpinBox()
        self.y_spinbox.setRange(0, 5000)
        self.y_spinbox.valueChanged.connect(self.on_spinbox_changed)
        info_layout.addRow("Y1坐标:", self.y_spinbox)

        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(10, 5000)
        self.width_spinbox.valueChanged.connect(self.on_spinbox_changed)
        info_layout.addRow("X2坐标:", self.width_spinbox)

        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(10, 5000)
        self.height_spinbox.valueChanged.connect(self.on_spinbox_changed)
        info_layout.addRow("Y2坐标:", self.height_spinbox)

        layout.addLayout(info_layout)

        # 提示信息
        self.info_label = QLabel("点击截取游戏窗口按钮开始")
        self.info_label.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(self.info_label)

    def capture_game_window(self):
        """截取游戏窗口"""
        try:
            # 查找游戏窗口
            if not self.screenshot_capture.find_game_window():
                self.info_label.setText("未找到游戏窗口，请确保游戏正在运行。")
                return

            # 截取游戏窗口
            image = self.screenshot_capture.capture_window()
            if image is None:
                self.info_label.setText("截取游戏窗口失败。")
                return

            # 转换为Qt图像
            self.current_image = self.convert_cv_to_qt(image)

            # 显示图像
            self.image_label.setPixmap(QPixmap.fromImage(self.current_image))
            self.image_label.set_selection(None)

            # 启用选择按钮
            self.select_btn.setEnabled(True)

            # 更新提示信息
            self.info_label.setText("点击手动选择区域按钮，然后在图像上拖动鼠标选择OCR识别区域。")

        except Exception as e:
            self.info_label.setText(f"截取游戏窗口失败: {str(e)}")

    def enable_selection_mode(self):
        """启用选择模式"""
        self.image_label.set_selection_mode(True)
        self.info_label.setText("在图像上拖动鼠标选择OCR识别区域。")

    def on_selection_changed(self, rect):
        """选择区域变更"""
        if rect:
            self.selection_rect = rect
            # 更新spinbox - 使用bbox格式 (x1, y1, x2, y2)
            self.x_spinbox.setValue(rect.x())
            self.y_spinbox.setValue(rect.y())
            self.width_spinbox.setValue(rect.x() + rect.width())  # x2
            self.height_spinbox.setValue(rect.y() + rect.height())  # y2

            # 发送区域变更信号 - 使用bbox格式
            region = {
                "bbox": [rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()]
            }
            self.region_changed.emit(region)

    def on_spinbox_changed(self):
        """spinbox值变更"""
        if self.current_image:
            # 更新选择区域 - 使用bbox格式 (x1, y1, x2, y2)
            x1 = self.x_spinbox.value()
            y1 = self.y_spinbox.value()
            x2 = self.width_spinbox.value()  # 这里存储的是x2坐标
            y2 = self.height_spinbox.value()  # 这里存储的是y2坐标

            # 计算宽度和高度
            width = x2 - x1
            height = y2 - y1

            # 更新图像上的选择区域
            rect = {
                "x": x1,
                "y": y1,
                "width": max(0, width),
                "height": max(0, height)
            }
            self.image_label.set_selection(rect)

            # 发送区域变更信号 - 使用bbox格式
            region = {
                "bbox": [x1, y1, x2, y2]
            }
            self.region_changed.emit(region)

    def set_region(self, region):
        """设置区域"""
        # 支持bbox格式 (x1, y1, x2, y2)
        if "bbox" in region:
            bbox = region["bbox"]
            self.x_spinbox.setValue(bbox[0])  # x1
            self.y_spinbox.setValue(bbox[1])  # y1
            self.width_spinbox.setValue(bbox[2])  # x2
            self.height_spinbox.setValue(bbox[3])  # y2

            # 转换为图像标签需要的格式
            rect = {
                "x": bbox[0],
                "y": bbox[1],
                "width": bbox[2] - bbox[0],
                "height": bbox[3] - bbox[1]
            }
            if self.current_image:
                self.image_label.set_selection(rect)
        # 支持旧的格式 (x, y, width, height)
        else:
            self.x_spinbox.setValue(region.get("x", 0))
            self.y_spinbox.setValue(region.get("y", 0))
            self.width_spinbox.setValue(region.get("x", 0) + region.get("width", 100))  # x2
            self.height_spinbox.setValue(region.get("y", 0) + region.get("height", 50))  # y2

            if self.current_image:
                self.image_label.set_selection(region)

    def convert_cv_to_qt(self, cv_img):
        """将OpenCV图像转换为Qt图像"""
        # 转换颜色空间
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        # 转换为Qt图像
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        return qt_image


class ImageLabel(QLabel):
    """图像标签，支持选择区域"""

    selection_changed = Signal(dict)  # 选择区域变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #CCCCCC; background-color: #F5F5F5;")
        self.setText("请截取游戏窗口")

        self.selection_mode = False
        self.selection_rect = None
        self.drawing = False
        self.start_point = QPoint()

    def set_selection_mode(self, enabled):
        """设置选择模式"""
        self.selection_mode = enabled

    def set_selection(self, rect):
        """设置选择区域"""
        if rect:
            self.selection_rect = {
                "x": rect.get("x", 0),
                "y": rect.get("y", 0),
                "width": rect.get("width", 0),
                "height": rect.get("height", 0)
            }
        else:
            self.selection_rect = None

        self.update()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.selection_mode and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.drawing:
            # 计算选择区域
            x = min(self.start_point.x(), event.pos().x())
            y = min(self.start_point.y(), event.pos().y())
            width = abs(event.pos().x() - self.start_point.x())
            height = abs(event.pos().y() - self.start_point.y())

            self.selection_rect = {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }

            self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self.drawing and event.button() == Qt.LeftButton:
            self.drawing = False
            self.selection_mode = False

            # 发送选择区域变更信号
            if self.selection_rect and self.selection_rect["width"] > 0 and self.selection_rect["height"] > 0:
                self.selection_changed.emit(self.selection_rect)

    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)

        # 绘制选择区域
        if self.selection_rect:
            painter = QPainter(self)

            # 设置半透明红色填充
            fill_color = QColor(255, 0, 0, 50)
            painter.setBrush(QBrush(fill_color))

            # 设置红色边框
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)

            # 绘制矩形
            painter.drawRect(
                self.selection_rect["x"],
                self.selection_rect["y"],
                self.selection_rect["width"],
                self.selection_rect["height"]
            )
