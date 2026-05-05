
"""
截图模块 - 负责游戏窗口截图
"""
import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import win32api
import logging
from ctypes import windll
from typing import Optional, Tuple
from config import GAME_WINDOW_TITLE, GAME_WINDOW_CLASS, OCR_REGION, DEBUG, DEBUG_SAVE_SCREENSHOT, DEBUG_SCREENSHOT_DIR
import os

# 配置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """截图捕获器 - 负责游戏窗口截图"""

    def __init__(self):
        self.game_hwnd = None
        self.last_window_rect = None

        # 创建调试截图目录
        if DEBUG and DEBUG_SAVE_SCREENSHOT:
            os.makedirs(DEBUG_SCREENSHOT_DIR, exist_ok=True)

        # 限制保存的截图数量为4张（2次识别）
        self.max_screenshots = 4
        self.screenshot_files = []

    def find_game_window(self) -> bool:
        """
        查找游戏窗口

        Returns:
            是否找到游戏窗口
        """
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                # 记录所有可见窗口用于调试
                if title:
                    logger.debug(f"找到窗口: {title} (类名: {class_name})")
                if GAME_WINDOW_TITLE in title or GAME_WINDOW_CLASS in class_name:
                    windows.append((hwnd, title, class_name))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.game_hwnd = windows[0][0]
            title = windows[0][1]
            class_name = windows[0][2]
            logger.info(f"找到游戏窗口: {title} (类名: {class_name})")
            return True
        else:
            self.game_hwnd = None
            logger.warning(f"未找到游戏窗口 (查找标题包含: {GAME_WINDOW_TITLE}, 类名: {GAME_WINDOW_CLASS})")
            return False

    def is_game_window_active(self) -> bool:
        """
        检查游戏窗口是否激活

        Returns:
            游戏窗口是否激活
        """
        if not self.game_hwnd:
            return False

        try:
            active_hwnd = win32gui.GetForegroundWindow()
            return active_hwnd == self.game_hwnd
        except Exception as e:
            logger.error(f"检查窗口状态失败: {str(e)}")
            return False

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        获取游戏窗口矩形区域

        Returns:
            (left, top, right, bottom) 或 None
        """
        if not self.game_hwnd:
            return None

        try:
            rect = win32gui.GetWindowRect(self.game_hwnd)
            self.last_window_rect = rect
            return rect
        except Exception as e:
            logger.error(f"获取窗口区域失败: {str(e)}")
            return None

    def capture_window(self) -> Optional[np.ndarray]:
        """
        截取游戏窗口

        Returns:
            图像数组或None
        """
        if not self.game_hwnd:
            return None

        try:
            # 获取窗口区域
            left, top, right, bottom = self.get_window_rect()
            width = right - left
            height = bottom - top

            logger.info(f"窗口位置: ({left}, {top}), 尺寸: {width}x{height}")

            if width <= 0 or height <= 0:
                logger.error(f"窗口尺寸无效: width={width}, height={height}")
                return None

            # 首选方法: 使用mss + win32gui捕获窗口
            try:
                logger.debug("尝试方法1: 使用mss + win32gui捕获窗口")
                import mss

                # 获取窗口客户区域
                try:
                    client_rect = win32gui.GetClientRect(self.game_hwnd)
                    client_width = client_rect[2] - client_rect[0]
                    client_height = client_rect[3] - client_rect[1]
                    logger.info(f"窗口客户区域尺寸: {client_width}x{client_height}")
                except Exception as e:
                    logger.warning(f"获取客户区域失败，使用窗口尺寸: {str(e)}")
                    client_width = width
                    client_height = height

                # 获取窗口客户区域相对于屏幕的位置
                try:
                    window_rect = win32gui.GetWindowRect(self.game_hwnd)
                    # 计算客户区域相对于屏幕的位置
                    client_left = window_rect[0] + (width - client_width) // 2
                    client_top = window_rect[1] + (height - client_height) // 2
                    logger.info(f"窗口客户区域位置: ({client_left}, {client_top})")
                except Exception as e:
                    logger.warning(f"获取窗口位置失败: {str(e)}")
                    client_left = left
                    client_top = top

                # 定义捕获区域
                monitor = {
                    "top": client_top,
                    "left": client_left,
                    "width": client_width,
                    "height": client_height
                }
                logger.info(f"捕获区域: top={client_top}, left={client_left}, width={client_width}, height={client_height}")

                with mss.mss() as sct:
                    # 捕获窗口区域
                    screenshot = sct.grab(monitor)

                    # 转换为numpy数组
                    img = np.array(screenshot)

                    # 转换BGRA到BGR
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    logger.info(f"捕获的图像尺寸: {img.shape[1]}x{img.shape[0]}")

                    # 检查图像是否全黑
                    if np.all(img == 0):
                        raise Exception("mss返回了全黑图像")

                    logger.info("方法1成功: 使用mss + win32gui捕获窗口")
                    return self._save_debug_screenshot(img, "method1_mss_win32gui")

            except Exception as e:
                logger.warning(f"方法1失败: {str(e)}")

            # 备用方法1: 使用窗口DC的BitBlt
            try:
                logger.debug("尝试方法2: 使用窗口DC的BitBlt")
                # 获取窗口客户区域DC
                hwndDC = win32gui.GetDC(self.game_hwnd)
                if not hwndDC:
                    raise Exception("无法获取窗口DC")

                # 获取窗口客户区域尺寸
                try:
                    client_rect = win32gui.GetClientRect(self.game_hwnd)
                    client_width = client_rect[2] - client_rect[0]
                    client_height = client_rect[3] - client_rect[1]
                    logger.info(f"窗口客户区域尺寸: {client_width}x{client_height}")
                except Exception as e:
                    logger.warning(f"获取客户区域失败，使用窗口尺寸: {str(e)}")
                    client_width = width
                    client_height = height

                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, client_width, client_height)
                saveDC.SelectObject(saveBitMap)

                result = saveDC.BitBlt((0, 0), (client_width, client_height), mfcDC, (0, 0), win32con.SRCCOPY)

                if not result:
                    raise Exception("BitBlt返回失败")

                bmpstr = saveBitMap.GetBitmapBits(True)
                img = np.frombuffer(bmpstr, dtype='uint8')
                img.shape = (client_height, client_width, 4)

                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(self.game_hwnd, hwndDC)
                win32gui.DeleteObject(saveBitMap.GetHandle())

                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                logger.info("方法2成功: 使用窗口DC的BitBlt")
                return self._save_debug_screenshot(img, "method2_blt")

            except Exception as e:
                logger.warning(f"方法2失败: {str(e)}")

            # 备用方法2: 使用PrintWindow
            try:
                logger.debug("尝试方法3: 使用PrintWindow")
                hwndDC = win32gui.GetWindowDC(self.game_hwnd)
                mfcDC = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
                saveDC.SelectObject(saveBitMap)

                # 尝试使用PW_CLIENTONLY标志 (0x00000001)
                result = windll.user32.PrintWindow(self.game_hwnd, saveDC.GetSafeHdc(), 1)

                if not result:
                    raise Exception("PrintWindow返回失败")

                bmpstr = saveBitMap.GetBitmapBits(True)
                img = np.frombuffer(bmpstr, dtype='uint8')
                img.shape = (height, width, 4)

                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(self.game_hwnd, hwndDC)
                win32gui.DeleteObject(saveBitMap.GetHandle())

                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 检查图像是否全黑
                if np.all(img == 0):
                    raise Exception("PrintWindow返回了全黑图像")

                logger.info("方法3成功: 使用PrintWindow")
                return self._save_debug_screenshot(img, "method3_printwindow")

            except Exception as e:
                logger.warning(f"方法3失败: {str(e)}")

            # 备用方法3: 使用Windows Graphics Capture API (d3dshot)捕获窗口
            try:
                logger.debug("尝试方法4: 使用Windows Graphics Capture API捕获窗口")
                try:
                    import d3dshot
                except ImportError:
                    raise Exception("d3dshot模块未安装，请运行: pip install d3dshot")

                # 创建d3dshot实例
                d3d = d3dshot.create(capture_output="numpy")

                # 获取窗口客户区域
                try:
                    client_rect = win32gui.GetClientRect(self.game_hwnd)
                    client_width = client_rect[2] - client_rect[0]
                    client_height = client_rect[3] - client_rect[1]
                    logger.info(f"窗口客户区域尺寸: {client_width}x{client_height}")
                except Exception as e:
                    logger.warning(f"获取客户区域失败，使用窗口尺寸: {str(e)}")
                    client_width = width
                    client_height = height

                # 捕获窗口
                img = d3d.capture(region=self.game_hwnd)
                if img is None:
                    raise Exception("d3dshot返回了None")

                logger.info(f"捕获的图像尺寸: {img.shape[1]}x{img.shape[0]}")

                # 检查图像是否全黑
                if np.all(img == 0):
                    raise Exception("d3dshot返回了全黑图像")

                logger.info("方法4成功: 使用Windows Graphics Capture API捕获窗口")
                return self._save_debug_screenshot(img, "method4_d3dshot")

            except Exception as e:
                logger.warning(f"方法4失败: {str(e)}")

            logger.error("所有截图方法都失败了")
            return None

        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def capture_ocr_region(self) -> Optional[np.ndarray]:
        """
        截取OCR识别区域

        Returns:
            OCR区域的图像数组或None
        """
        img = self.capture_window()
        if img is None:
            return None

        try:
            if "bbox" in OCR_REGION:
                bbox = OCR_REGION["bbox"]
                x1, y1, x2, y2 = bbox
                ocr_img = img[y1:y2, x1:x2]
            else:
                x = OCR_REGION["x"]
                y = OCR_REGION["y"]
                width = OCR_REGION["width"]
                height = OCR_REGION["height"]
                ocr_img = img[y:y+height, x:x+width]

            return self._save_debug_screenshot(ocr_img, "ocr_region")
        except Exception as e:
            logger.error(f"截取OCR区域失败: {str(e)}")
            return None

    def _save_debug_screenshot(self, img: np.ndarray, method_name: str) -> np.ndarray:
        """保存调试截图"""
        if DEBUG and DEBUG_SAVE_SCREENSHOT:
            import time
            os.makedirs(DEBUG_SCREENSHOT_DIR, exist_ok=True)
            timestamp = int(time.time())
            screenshot_path = os.path.join(DEBUG_SCREENSHOT_DIR, f"screenshot_{method_name}_{timestamp}.png")
            cv2.imwrite(screenshot_path, img)
            logger.info(f"截图已保存: {screenshot_path}")

            # 添加到截图文件列表
            self.screenshot_files.append(screenshot_path)

            # 如果超过最大数量，删除最旧的截图
            while len(self.screenshot_files) > self.max_screenshots:
                oldest_file = self.screenshot_files.pop(0)
                try:
                    if os.path.exists(oldest_file):
                        os.remove(oldest_file)
                        logger.info(f"已删除旧截图: {oldest_file}")
                except Exception as e:
                    logger.warning(f"删除旧截图失败: {oldest_file}, 错误: {str(e)}")
        return img
