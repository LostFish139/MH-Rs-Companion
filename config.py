
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
HUNTING_TIPS_FILE = os.path.join(BASE_DIR, "data", "hunting_tips.json")
MONSTER_HUNT_INFO_FILE = os.path.join(BASE_DIR, "data", "monster_hunt_info.json")

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
PADDLEOCR_USE_GPU = False # 是否使用GPU加速（注意：PaddleOCR依赖复杂，默认使用RapidOCR）

# 武器配置
WEAPON_CONFIG = {
    "current_weapon": "盾斧",  # 当前使用的武器，用于提供针对性狩猎技巧
    "all_weapons": [
        "大剑", "太刀", "片手剑", "双刀", "长枪", "铳枪",
        "大锤", "狩猎笛", "斩斧", "盾斧", "操虫棍",
        "轻弩", "重弩", "弓"
    ],
    "prioritize_element_weapon": True  # 是否优先推荐属性武器（而非物理/固定伤害武器）
}

# 窗口配置
WINDOW_CONFIG = {
    "chat": {
        "title": "怪物猎人崛起 - 智能狩猎助手",
        "width": 380,
        "height": 500,
        "min_width": 250,     # 最小宽度
        "min_height": 120,    # 最小高度
        "opacity": 0.95,        # 默认透明度 (0.0-1.0)
        "always_on_top": True,  # 默认窗口置顶
        "resizable": True      # 是否允许调整窗口大小
    },
    "settings": {
        "title": "设置",
        "width": 520,
        "height": 550
    }
}

# 监控配置
MONITOR_CONFIG = {
    "check_interval": 1000,  # 窗口检查间隔 (毫秒)
    "ocr_interval": 3000,     # OCR识别间隔 (毫秒)
    "auto_start": True,      # 是否自动开始监控
    "show_no_window_warning_once": True,  # "未找到窗口"警告是否只显示一次
    "show_no_task_warning_once": True    # "未检测到任务"警告是否只显示一次
}

# UI配置
UI_CONFIG = {
    "bubble_max_width": 280,      # 聊天气泡最大宽度
    "bubble_spacing": 6,            # 气泡间距
    "font_size": 9,                 # 字体大小
    "font_family": "Microsoft YaHei",  # 字体
    "max_context_messages": 3,      # 简洁模式下保留的上下文消息数
    "default_mode": "clean",        # 默认显示模式: clean=简洁模式, debug=调试模式
    "auto_scroll_to_bottom": True,   # 是否自动滚动到底部
    "bubble_opacity": 0.95,         # 气泡背景透明度 (0.3-1.0)
    # 气泡样式配置
    "bubble": {
        "shape": "rounded",         # 气泡形状: rounded=圆角矩形
        "tail_position": "none",     # 小尾巴方位: none=无尾巴
        "radius": 12,                # 气泡圆角半径
        "padding": 8,               # 气泡内边距
        "tail_size": 8                 # 小尾巴大小
    },
    # 简洁模式配置
    "clean_mode": {
        "transparent_background": True,  # 简洁模式下背景是否完全透明
        "hide_title_bar": True,        # 简洁模式下是否隐藏标题栏
        "hide_status_bar": True,       # 简洁模式下是否隐藏状态栏
        "show_border": False            # 简洁模式下是否显示边框
    }
}

# 狩猎技巧配置
TIPS_CONFIG = {
    "show_general_tips": False,      # 是否显示通用技巧（简洁模式下建议关闭）
    "show_weapon_tips": False,       # 是否显示武器专属技巧
    "show_monster_tips": True,      # 是否显示怪物专属技巧
    "max_tips_per_category": 2,      # 每类技巧最多显示条数
    "include_monster_weakness": True, # 是否包含怪物弱点信息
    "weapon_recommendation_first": True  # 武器推荐是否优先于技巧显示
}

# 调试配置
DEBUG = True  # 是否开启调试模式
DEBUG_SAVE_SCREENSHOT = True  # 是否保存截图用于调试
DEBUG_SCREENSHOT_DIR = os.path.join(BASE_DIR, "debug_screenshots")  # 截图保存目录
