
"""
怪物猎人崛起智能狩猎助手 - 主程序入口
"""
import os
import sys
import logging

# 禁用PaddlePaddle的oneDNN加速以解决兼容性问题
os.environ['FLAGS_use_mkldnn'] = '0'
# 禁用PaddlePaddle的新执行器
os.environ['FLAGS_use_new_executor'] = '0'
# 禁用PaddlePaddle的IR优化
os.environ['FLAGS_enable_pir_api'] = '0'

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Slot, Qt
from core.workflow import Workflow
from ui.chat_window import ChatWindow
from ui.settings import SettingsDialog
from config import DEBUG, WINDOW_CONFIG, OCR_REGION, MONITOR_CONFIG, OCR_ENGINE, PADDLEOCR_USE_GPU

# 配置日志
logging.basicConfig(
    level=logging.INFO if DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MainWindowController(QObject):
    """主窗口控制器 - 协调各个模块之间的交互"""

    def __init__(self, app):
        super().__init__()
        self.app = app

        # 初始化工作流
        self.workflow = Workflow()

        # 初始化UI
        self.chat_window = ChatWindow()
        self.settings_dialog = None

        # 设置工作流回调
        self.workflow.set_callbacks(
            on_result=self.on_workflow_result,
            on_error=self.on_workflow_error
        )

        # 连接信号槽
        self.connect_signals()

        # 显示主窗口
        self.chat_window.show()

        # 初始化游戏窗口检查
        self.check_game_window()

    def connect_signals(self):
        """连接信号槽"""
        # 聊天窗口信号
        self.chat_window.settings_requested.connect(self.show_settings)

        # 定时器信号
        self.chat_window.window_check_timer.timeout.connect(self.check_game_window)
        self.chat_window.ocr_timer.timeout.connect(self.perform_ocr)

    @Slot()
    def check_game_window(self):
        """检查游戏窗口状态"""
        try:
            # 查找游戏窗口
            if self.workflow.screenshot_capture.find_game_window():
                # 检查游戏窗口是否激活
                if self.workflow.screenshot_capture.is_game_window_active():
                    self.chat_window.update_status("游戏窗口激活 - 监控中")
                    # 如果OCR定时器未运行，则启动它
                    if not self.chat_window.ocr_timer.isActive():
                        self.chat_window.start_monitoring()
                else:
                    self.chat_window.update_status("游戏窗口未激活")
            else:
                self.chat_window.update_status("未找到游戏窗口")
                # 如果OCR定时器正在运行，则停止它
                if self.chat_window.ocr_timer.isActive():
                    self.chat_window.stop_monitoring()
        except Exception as e:
            logger.error(f"检查游戏窗口失败: {str(e)}")

    @Slot()
    def perform_ocr(self):
        """执行OCR识别 - 通过Workflow协调各个模块"""
        self.workflow.execute()

    def on_workflow_result(self, monster_name: str, weapons: list):
        """工作流结果回调"""
        logger.info(f"匹配成功: 怪物={monster_name}, 推荐武器数量={len(weapons)}")
        self.chat_window.show_weapon_recommendation(monster_name, weapons)

    def on_workflow_error(self, error_message: str):
        """工作流错误回调"""
        logger.warning(error_message)
        self.chat_window.add_assistant_message(error_message)

    def show_settings(self):
        """显示设置对话框"""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.chat_window)

            # 连接信号
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.ocr_test_requested.connect(self.test_ocr)

        self.settings_dialog.show()

    @Slot(dict)
    def apply_settings(self, settings):
        """应用设置"""
        try:
            # 应用窗口设置
            WINDOW_CONFIG["chat"]["opacity"] = settings["window"]["opacity"]
            WINDOW_CONFIG["chat"]["always_on_top"] = settings["window"]["always_on_top"]
            self.chat_window.setWindowOpacity(WINDOW_CONFIG["chat"]["opacity"])

            # 保存窗口可见性状态
            was_visible = self.chat_window.isVisible()

            # 设置窗口标志
            self.chat_window.setWindowFlags(
                Qt.WindowStaysOnTopHint if WINDOW_CONFIG["chat"]["always_on_top"] else Qt.Window
            )

            # 重新显示窗口
            if was_visible:
                self.chat_window.show()

            # 应用监控设置
            MONITOR_CONFIG["check_interval"] = settings["monitor"]["check_interval"]
            MONITOR_CONFIG["ocr_interval"] = settings["monitor"]["ocr_interval"]
            MONITOR_CONFIG["auto_start"] = settings["monitor"]["auto_start"]

            # 更新定时器间隔
            self.chat_window.window_check_timer.setInterval(MONITOR_CONFIG["check_interval"])
            self.chat_window.ocr_timer.setInterval(MONITOR_CONFIG["ocr_interval"])

            logger.info("设置已应用")
            self.chat_window.add_assistant_message("设置已保存并应用。")
        except Exception as e:
            logger.error(f"应用设置失败: {str(e)}")
            self.chat_window.add_assistant_message(f"应用设置失败: {str(e)}")

    @Slot()
    def test_ocr(self):
        """测试OCR功能 - 多次截图并识别"""
        self.chat_window.add_assistant_message("开始测试OCR识别，将进行3次截图和识别...")

        results = self.workflow.test_ocr(num_tests=3)

        for i, result in enumerate(results, 1):
            if result["success"]:
                result_message = f"第{i}次：识别成功\n识别结果: {result['text']}\n截图已保存: {result['screenshot_path']}"
                self.chat_window.add_assistant_message(result_message)
                logger.info(f"OCR识别结果({i}): {result['text']}")
            else:
                result_message = f"第{i}次：{result['error']}\n截图已保存: {result['screenshot_path']}" if result['screenshot_path'] else f"第{i}次：{result['error']}"
                self.chat_window.add_assistant_message(result_message)
                logger.warning(result['error'])

        self.chat_window.add_assistant_message("测试完成！")


def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    # 创建主窗口控制器
    controller = MainWindowController(app)

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
