
"""
配置文件 - 存储应用程序的所有配置参数
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据文件路径
TASK_WEAPON_FILE = os.path.join(BASE_DIR, "data", "task_weapon.json")
MONSTER_WEAKNESS_FILE = os.path.join(BASE_DIR, "data", "monster_weakness.json")

# 游戏窗口配置
GAME_WINDOW_TITLE = "Monster Hunter Rise"  # 游戏窗口标题
GAME_WINDOW_CLASS = "MonsterHunterRise"    # 游戏窗口类名

# OCR识别区域配置 (相对于游戏窗口的坐标)
# 使用bbox格式: [x1, y1, x2, y2]
OCR_REGION = {
    "bbox": [100, 170, 780, 240]  # 左上角(x1,y1)和右下角(x2,y2)坐标
}

# OCR引擎配置
OCR_ENGINE = "rapidocr"  # 可选: "rapidocr" 或 "tesseract"
OCR_LANG = "ch"           # 识别语言: ch=中文, en=英文
PADDLEOCR_USE_GPU = False # 是否使用GPU加速

# 窗口配置
WINDOW_CONFIG = {
    "chat": {
        "title": "怪物猎人崛起 - 智能狩猎助手",
        "width": 400,
        "height": 600,
        "opacity": 0.9,  # 默认透明度 (0.0-1.0)
        "always_on_top": True  # 默认窗口置顶
    },
    "settings": {
        "title": "设置",
        "width": 500,
        "height": 400
    }
}

# 监控配置
MONITOR_CONFIG = {
    "check_interval": 1000,  # 窗口检查间隔 (毫秒)
    "ocr_interval": 3000,     # OCR识别间隔 (毫秒)
    "auto_start": True        # 是否自动开始监控
}

# UI配置
UI_CONFIG = {
    "bubble_max_width": 300,  # 聊天气泡最大宽度
    "bubble_spacing": 10,     # 气泡间距
    "font_size": 10,          # 字体大小
    "font_family": "Microsoft YaHei"  # 字体
}

# 调试配置
DEBUG = True  # 是否开启调试模式
DEBUG_SAVE_SCREENSHOT = True  # 是否保存截图用于调试
DEBUG_SCREENSHOT_DIR = os.path.join(BASE_DIR, "debug_screenshots")  # 截图保存目录
