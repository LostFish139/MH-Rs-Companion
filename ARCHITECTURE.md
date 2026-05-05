# 项目架构说明

## 目录结构

```
my_mhr_companion/
├── main.py                 # 程序入口
├── config.py               # 配置文件
├── core/                   # 核心业务逻辑
│   ├── __init__.py
│   ├── workflow.py         # 工作流编排
│   ├── screenshot.py       # 截图模块
│   ├── ocr.py             # OCR识别模块
│   └── matcher.py         # 数据匹配模块
├── ui/                    # UI模块
│   ├── __init__.py
│   ├── chat_window.py     # 聊天窗口
│   ├── settings.py        # 设置界面
│   └── region_selector.py # 区域选择器
├── data/                  # 数据文件
│   ├── __init__.py
│   ├── task_weapon.json
│   └── monster_weakness.json
├── tools/                 # 测试工具
│   ├── __init__.py
│   └── ocr_tester.py     # OCR测试工具
├── requirements.txt        # 依赖文件
├── run.bat              # 启动脚本
├── run_ocr_tester.bat  # OCR测试工具启动脚本
├── README.md            # 项目说明
├── CHANGELOG.md         # 变更日志
└── REFACTOR_SUMMARY.md  # 重构总结
```

## 核心流程

```
游戏窗口 → 截图 → OCR识别 → 数据比对 → 武器推荐
```

## 文件说明

### 程序入口

#### main.py
- **作用**: 主程序入口，初始化应用程序
- **主要功能**:
  - 初始化Workflow和UI组件
  - 连接信号槽
  - 协调各个模块之间的交互
- **启动方式**: `python main.py` 或双击 `run.bat`

### 核心业务逻辑 (core/)

#### workflow.py
- **作用**: 工作流编排器，协调各个模块完成完整流程
- **主要功能**:
  - 协调截图、OCR识别和数据匹配
  - 提供回调机制处理结果和错误
  - 提供测试功能

#### screenshot.py
- **作用**: 截图模块，负责游戏窗口截图
- **主要功能**:
  - 查找游戏窗口
  - 检查窗口是否激活
  - 截取完整窗口
  - 截取OCR识别区域

#### ocr.py
- **作用**: OCR识别模块，负责文本识别
- **主要功能**:
  - 初始化OCR引擎（RapidOCR/Tesseract）
  - 识别图像中的文本
  - 支持多种OCR引擎

#### matcher.py
- **作用**: 数据匹配模块，负责任务和怪物数据匹配
- **主要功能**:
  - 加载JSON数据文件
  - 任务名称匹配（支持模糊匹配）
  - 怪物名称匹配（支持模糊匹配）
  - 返回武器推荐

### UI模块 (ui/)

#### chat_window.py
- **作用**: 聊天窗口，主界面
- **主要功能**:
  - 显示聊天气泡
  - 显示武器推荐
  - 提供手动触发OCR的按钮
  - 显示设置按钮

#### settings.py
- **作用**: 设置界面
- **主要功能**:
  - 窗口透明度设置
  - OCR引擎选择
  - OCR识别区域设置
  - 监控间隔设置
  - OCR测试功能

#### region_selector.py
- **作用**: OCR识别区域选择器
- **主要功能**:
  - 截取游戏窗口
  - 可视化选择OCR区域
  - 显示区域坐标信息

### 数据文件 (data/)

#### task_weapon.json
- **作用**: 存储任务与武器推荐数据
- **格式**: 任务名称 -> {targets: [], weapons: []}

#### monster_weakness.json
- **作用**: 存储怪物弱点数据
- **格式**: 怪物名称 -> {recommended_weapon: {type, weapon}}

### 测试工具 (tools/)

#### ocr_tester.py
- **作用**: 可视化OCR测试工具
- **主要功能**:
  - 实时查看截取的游戏窗口图像
  - 查看OCR识别区域
  - 测试OCR识别效果
  - 验证数据匹配和武器推荐
- **启动方式**: `python tools/ocr_tester.py` 或双击 `run_ocr_tester.bat`

## 使用说明

### 启动主程序
```bash
python main.py
```
或双击 `run.bat`

### 启动OCR测试工具
```bash
python tools/ocr_tester.py
```
或双击 `run_ocr_tester.bat`

## 配置文件 (config.py)

主要配置项：
- **数据文件路径**: TASK_WEAPON_FILE, MONSTER_WEAKNESS_FILE
- **游戏窗口配置**: GAME_WINDOW_TITLE, GAME_WINDOW_CLASS
- **OCR区域配置**: OCR_REGION
- **OCR引擎配置**: OCR_ENGINE, OCR_LANG, PADDLEOCR_USE_GPU
- **窗口配置**: WINDOW_CONFIG
- **监控配置**: MONITOR_CONFIG
- **UI配置**: UI_CONFIG
- **调试配置**: DEBUG, DEBUG_SAVE_SCREENSHOT, DEBUG_SCREENSHOT_DIR

## 依赖文件 (requirements.txt)

主要依赖：
- PySide6: GUI框架
- rapidocr_onnxruntime: OCR引擎
- pytesseract: 备选OCR引擎
- opencv-python: 图像处理
- numpy: 数值计算
- pywin32: Windows窗口操作
- fuzzywuzzy: 字符串模糊匹配
- python-Levenshtein: 字符串匹配算法
