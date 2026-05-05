
"""
OCR识别模块 - 负责文本识别
"""
import cv2
import numpy as np
import logging
from typing import Optional
from config import OCR_ENGINE, OCR_LANG, PADDLEOCR_USE_GPU, DEBUG

# 配置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)


class OCREngine:
    """OCR引擎 - 负责图像文本识别"""

    def __init__(self):
        self.engine = None
        self.engine_type = None
        self._init_engine()

    def _init_engine(self):
        """初始化OCR引擎"""
        try:
            if OCR_ENGINE.lower() == "rapidocr":
                self._init_rapidocr()
            else:
                self._init_tesseract()
            logger.info(f"OCR引擎初始化成功: {OCR_ENGINE}")
        except Exception as e:
            logger.error(f"OCR引擎初始化失败: {str(e)}")
            raise

    def _init_rapidocr(self):
        """初始化RapidOCR引擎"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
            self.engine_type = "rapidocr"
            logger.info("使用RapidOCR作为OCR引擎")
        except ImportError:
            logger.error("RapidOCR未安装，尝试使用Tesseract")
            self._init_tesseract()

    def _init_tesseract(self):
        """初始化Tesseract引擎"""
        try:
            import pytesseract
            self.engine = pytesseract
            self.engine_type = "tesseract"
            logger.info("使用Tesseract作为OCR引擎")
        except ImportError:
            logger.error("Tesseract未安装，请先安装pytesseract和tesseract-ocr")
            raise

    def recognize_text(self, image: np.ndarray) -> str:
        """
        识别图像中的文本

        Args:
            image: 要识别的图像

        Returns:
            识别出的文本
        """
        if image is None:
            return ""

        try:
            if self.engine_type == "rapidocr":
                return self._recognize_with_rapidocr(image)
            else:
                return self._recognize_with_tesseract(image)
        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            return ""

    def _recognize_with_rapidocr(self, image: np.ndarray) -> str:
        """使用RapidOCR识别文本"""
        result, _ = self.engine(image)
        text_list = []

        if result:
            for line in result:
                if line and len(line) > 1:
                    text_list.append(line[1])

        return " ".join(text_list)

    def _recognize_with_tesseract(self, image: np.ndarray) -> str:
        """使用Tesseract识别文本"""
        # 预处理图像
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 使用Tesseract识别
        text = self.engine.image_to_string(binary, lang=OCR_LANG)
        return text.strip()
