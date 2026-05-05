
"""
工作流编排模块 - 协调截图、OCR识别和数据匹配
"""
import logging
import os
import time
from typing import Optional, Tuple, List, Dict, Callable
from .screenshot import ScreenshotCapture
from .ocr import OCREngine
from .matcher import DataMatcher
from config import DEBUG, DEBUG_SCREENSHOT_DIR

# 配置日志
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING)
logger = logging.getLogger(__name__)


class Workflow:
    """工作流编排器 - 协调各个模块完成完整流程"""

    def __init__(self):
        # 初始化各个模块
        self.screenshot_capture = ScreenshotCapture()
        self.ocr_engine = OCREngine()
        self.data_matcher = DataMatcher()

        # 回调函数
        self.on_result_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None

        # 历史记录 - 只保留2次识别的记录
        self.recognition_history = []
        self.max_history_size = 2
        
        # 跟踪是否已经显示过"检测不到任务"的提示
        self.shown_no_task_warning = False
        
        # 清理旧的调试截图
        self.cleanup_old_screenshots()

    def cleanup_old_screenshots(self):
        """
        清理旧的调试截图，只保留最近的10张
        """
        try:
            if not os.path.exists(DEBUG_SCREENSHOT_DIR):
                os.makedirs(DEBUG_SCREENSHOT_DIR, exist_ok=True)
                return
            
            # 获取所有截图文件
            screenshot_files = []
            for filename in os.listdir(DEBUG_SCREENSHOT_DIR):
                if filename.endswith((".png", ".jpg", ".jpeg")):
                    filepath = os.path.join(DEBUG_SCREENSHOT_DIR, filename)
                    # 获取文件修改时间
                    mtime = os.path.getmtime(filepath)
                    screenshot_files.append((filepath, mtime))
            
            # 按修改时间排序（从新到旧）
            screenshot_files.sort(key=lambda x: x[1], reverse=True)
            
            # 只保留最近的10张
            max_screenshots = 10
            if len(screenshot_files) > max_screenshots:
                # 删除旧的截图
                for filepath, _ in screenshot_files[max_screenshots:]:
                    try:
                        os.remove(filepath)
                        logger.info(f"已删除旧截图: {filepath}")
                    except Exception as e:
                        logger.warning(f"删除截图失败 {filepath}: {str(e)}")
        except Exception as e:
            logger.warning(f"清理旧截图失败: {str(e)}")

    def set_callbacks(self, on_result: Optional[Callable] = None, on_error: Optional[Callable] = None):
        """
        设置回调函数

        Args:
            on_result: 结果回调函数，参数为 (monster_name, weapons)
            on_error: 错误回调函数，参数为 (error_message)
        """
        self.on_result_callback = on_result
        self.on_error_callback = on_error

    def execute(self) -> bool:
        """
        执行完整的工作流程：
        1. 检测游戏窗口
        2. 截取OCR区域
        3. OCR识别文字
        4. 与数据集比对
        5. 返回推荐武器信息

        Returns:
            是否执行成功
        """
        try:
            # 步骤1: 检测游戏窗口
            if not self.screenshot_capture.game_hwnd:
                if not self.screenshot_capture.find_game_window():
                    error_msg = "未找到游戏窗口，请启动怪物猎人崛起"
                    logger.warning(error_msg)
                    if self.on_error_callback:
                        self.on_error_callback(error_msg)
                    return False

            # 检查游戏窗口是否激活
            if not self.screenshot_capture.is_game_window_active():
                logger.info("游戏窗口未激活，跳过OCR识别")
                return False

            # 步骤2: 截取游戏窗口的OCR区域
            ocr_img = self.screenshot_capture.capture_ocr_region()
            if ocr_img is None:
                error_msg = "截图失败，无法进行OCR识别"
                logger.warning(error_msg)
                if self.on_error_callback:
                    self.on_error_callback(error_msg)
                return False

            # 步骤3: OCR识别文字
            text = self.ocr_engine.recognize_text(ocr_img)
            if not text:
                error_msg = "检测不到任务，请承接任务"
                logger.warning(error_msg)
                # 只在第一次显示警告
                if not self.shown_no_task_warning:
                    if self.on_error_callback:
                        self.on_error_callback(error_msg)
                    self.shown_no_task_warning = True
                return False

            logger.info(f"OCR识别结果: {text}")

            # 步骤4: 与数据集比对
            monster_name, weapons = self.data_matcher.get_recommendation(text)
            if not monster_name or not weapons:
                logger.info(f"识别到任务: {text}，但未找到匹配的武器推荐")
                # 即使没有找到武器推荐，也重置警告标志，因为我们已经识别到了任务
                self.shown_no_task_warning = False
                return False

            # 检查是否与历史记录重复
            current_result = {
                "monster_name": monster_name,
                "weapons": weapons,
                "text": text
            }

            is_duplicate = False
            for history in self.recognition_history:
                if (history["monster_name"] == monster_name and 
                    len(history["weapons"]) == len(weapons)):
                    # 检查武器是否相同
                    weapons_match = True
                    for i, weapon in enumerate(weapons):
                        if (weapon.get("weapon") != history["weapons"][i].get("weapon") or
                            weapon.get("type") != history["weapons"][i].get("type")):
                            weapons_match = False
                            break
                    if weapons_match:
                        is_duplicate = True
                        logger.info(f"识别结果与历史记录重复，跳过输出: {monster_name}")
                        break

            if not is_duplicate:
                # 添加到历史记录
                self.recognition_history.append(current_result)
                # 限制历史记录大小
                if len(self.recognition_history) > self.max_history_size:
                    self.recognition_history.pop(0)

                # 重置"检测不到任务"的警告标志
                self.shown_no_task_warning = False

                # 步骤5: 返回武器推荐信息
                logger.info(f"匹配成功: 怪物={monster_name}, 推荐武器数量={len(weapons)}")
                if self.on_result_callback:
                    self.on_result_callback(monster_name, weapons)
            else:
                logger.info(f"识别结果与历史记录重复，不触发回调")

            return True

        except Exception as e:
            error_msg = f"执行工作流失败: {str(e)}"
            logger.error(error_msg)
            if self.on_error_callback:
                self.on_error_callback(error_msg)
            return False

    def test_ocr(self, num_tests: int = 3) -> List[Dict]:
        """
        测试OCR功能 - 多次截图并识别

        Args:
            num_tests: 测试次数

        Returns:
            测试结果列表，每个元素包含 (success, text, screenshot_path)
        """
        results = []

        try:
            # 确保游戏窗口存在
            if not self.screenshot_capture.game_hwnd:
                if not self.screenshot_capture.find_game_window():
                    error_msg = "未找到游戏窗口，请确保游戏正在运行。"
                    logger.warning(error_msg)
                    if self.on_error_callback:
                        self.on_error_callback(error_msg)
                    return results

            # 测试多次
            for i in range(1, num_tests + 1):
                # 截取OCR区域
                ocr_img = self.screenshot_capture.capture_ocr_region()
                if ocr_img is None:
                    error_msg = f"第{i}次：截取OCR区域失败，请检查识别区域设置。"
                    logger.warning(error_msg)
                    if self.on_error_callback:
                        self.on_error_callback(error_msg)
                    results.append({
                        "success": False,
                        "text": "",
                        "screenshot_path": "",
                        "error": error_msg
                    })
                    continue

                # 保存截图用于显示
                import os
                import time
                from config import DEBUG_SCREENSHOT_DIR

                # 确保截图目录存在
                os.makedirs(DEBUG_SCREENSHOT_DIR, exist_ok=True)

                # 保存截图
                timestamp = int(time.time())
                screenshot_path = os.path.join(DEBUG_SCREENSHOT_DIR, f"ocr_test_{timestamp}_{i}.png")
                import cv2
                cv2.imwrite(screenshot_path, ocr_img)

                # 执行OCR识别
                text = self.ocr_engine.recognize_text(ocr_img)

                # 记录结果
                if text:
                    logger.info(f"OCR识别结果({i}): {text}")
                    results.append({
                        "success": True,
                        "text": text,
                        "screenshot_path": screenshot_path,
                        "error": ""
                    })
                else:
                    error_msg = f"第{i}次：未识别到文本"
                    logger.warning(error_msg)
                    results.append({
                        "success": False,
                        "text": "",
                        "screenshot_path": screenshot_path,
                        "error": error_msg
                    })

                # 短暂延迟
                time.sleep(0.5)

        except Exception as e:
            error_msg = f"测试OCR失败: {str(e)}"
            logger.error(error_msg)
            if self.on_error_callback:
                self.on_error_callback(error_msg)

        return results
