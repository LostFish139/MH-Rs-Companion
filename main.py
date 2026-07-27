
"""
怪物猎人崛起智能狩猎助手 - 主程序入口
"""
import os
import sys
import logging

# 禁用PaddlePaddle的oneDNN加速以解决兼容性问题
# 注意：当前默认使用RapidOCR，PaddlePaddle相关环境变量仅作兼容保留
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_use_new_executor'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Slot, Qt
from core.workflow import Workflow
from ui.chat_window import ChatWindow
from ui.settings import SettingsDialog
from config import DEBUG, WINDOW_CONFIG, MONITOR_CONFIG

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

        # 设置工作流回调（完整结果回调 + 兼容旧接口）
        self.workflow.set_callbacks(
            on_result=self.on_workflow_result,
            on_full_result=self.on_workflow_full_result,
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
        self.chat_window.weapon_changed.connect(self.on_weapon_changed)
        self.chat_window.mode_changed.connect(self.on_mode_changed)

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

    @Slot(str)
    def on_weapon_changed(self, weapon: str):
        """武器选择改变"""
        self.workflow.set_current_weapon(weapon)
        logger.info(f"武器已切换为: {weapon}")

    @Slot(str)
    def on_mode_changed(self, mode: str):
        """显示模式改变"""
        logger.info(f"显示模式已切换为: {mode}")

    def on_workflow_result(self, monster_name: str, weapons: list):
        """工作流结果回调（兼容旧接口）"""
        logger.info(f"匹配成功: 怪物={monster_name}, 推荐武器数量={len(weapons)}")
        # 注意：主要使用on_workflow_full_result，这个是兼容回调
        # self.chat_window.show_weapon_recommendation(monster_name, weapons)

    def on_workflow_full_result(self, full_result: dict):
        """工作流完整结果回调（新接口）"""
        monsters = full_result.get("monsters", [])
        monster_names = [m.get("name", "") for m in monsters]
        logger.info(f"完整匹配成功: 怪物={monster_names}, 多怪物={full_result.get('is_multi_monster', False)}")
        self.chat_window.show_full_recommendation(full_result)

    def on_workflow_error(self, error_message: str):
        """工作流错误回调"""
        logger.warning(error_message)
        self.chat_window.add_assistant_message(error_message, "warning")

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

            # 简洁模式下调节的是气泡透明度，调试模式下是窗口透明度
            if self.chat_window.display_mode == "clean":
                # 简洁模式：设置气泡透明度
                if hasattr(self.chat_window, 'set_bubble_opacity'):
                    self.chat_window.set_bubble_opacity(settings["window"]["opacity"])
            else:
                # 调试模式：设置窗口透明度
                self.chat_window.setWindowOpacity(WINDOW_CONFIG["chat"]["opacity"])

            # 保存窗口可见性状态
            was_visible = self.chat_window.isVisible()

            # 设置窗口标志（注意：自定义无边框窗口，需要保留FramelessWindowHint）
            from PySide6.QtCore import Qt
            if WINDOW_CONFIG["chat"]["always_on_top"]:
                self.chat_window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            else:
                self.chat_window.setWindowFlags(Qt.FramelessWindowHint)

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
            # 简洁模式下用小字提示
            if self.chat_window.display_mode == "clean" and hasattr(self.chat_window, '_add_small_hint'):
                self.chat_window._add_small_hint("已完成更改")
            else:
                self.chat_window.add_assistant_message("设置已保存并应用。", "success")
        except Exception as e:
            logger.error(f"应用设置失败: {str(e)}")
            if self.chat_window.display_mode == "clean" and hasattr(self.chat_window, '_add_small_hint'):
                self.chat_window._add_small_hint(f"设置失败: {str(e)}")
            else:
                self.chat_window.add_assistant_message(f"应用设置失败: {str(e)}", "warning")

    @Slot()
    def test_ocr(self):
        """测试OCR功能 - 多次截图并识别"""
        self.chat_window.add_assistant_message("开始测试OCR识别，将进行3次截图和识别...")

        results = self.workflow.test_ocr(num_tests=3)

        for i, result in enumerate(results, 1):
            if result["success"]:
                result_message = f"第{i}次：识别成功\n识别结果: {result['text']}\n截图已保存: {result['screenshot_path']}"
                self.chat_window.add_assistant_message(result_message, "success")
                logger.info(f"OCR识别结果({i}): {result['text']}")
            else:
                result_message = f"第{i}次：{result['error']}\n截图已保存: {result['screenshot_path']}" if result['screenshot_path'] else f"第{i}次：{result['error']}"
                self.chat_window.add_assistant_message(result_message, "warning")
                logger.warning(result['error'])

        self.chat_window.add_assistant_message("测试完成！", "success")


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
