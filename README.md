# 怪物猎人崛起智能狩猎助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)

一个基于Python开发的桌面应用，通过OCR识别游戏任务信息，分析怪物弱点，推荐最优盾斧武器。

## 功能特点

- **游戏窗口监听**: 实时检测《怪物猎人崛起》游戏窗口是否激活
- **智能OCR识别**: 对游戏窗口任务信息区域进行文本识别
- **武器推荐**: 根据怪物弱的属性推荐最优武器
- **聊天界面**: 以聊天气泡形式展示武器推荐信息
- **设置界面**: 支持透明度调节、OCR测试、检测区域自定义等功能

## 核心流程

```
游戏窗口 → 截图 → OCR识别 → 数据比对 → 武器推荐
```

1. **游戏窗口检测**: 检测游戏窗口是否激活
2. **截图**: 截取游戏窗口的OCR识别区域
3. **OCR识别**: 识别截图中的文本信息
4. **数据比对**: 将识别到的文本与数据集进行比对
5. **武器推荐**: 返回匹配的武器推荐信息

## 项目结构

```
my_mhr_companion/
├── main.py                 # 程序入口
├── config.py               # 配置文件（路径、区域参数、窗口配置）
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
│   ├── task_weapon.json
│   └── monster_weakness.json
├── tools/                 # 测试工具
│   ├── __init__.py
|   ├── screenshot_tool.py  # 截图工具（测试用的，应该与其他主要文件没关系）
│   └── ocr_tester.py     # OCR测试工具
├── requirements.txt        # 依赖文件
└── README.md               # 项目说明
```

## 安装步骤

### 1. 环境要求

- Python 3.8 或更高版本
- Windows 操作系统
- 《怪物猎人崛起》游戏

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Tesseract（备选OCR引擎）

如果需要使用Tesseract作为OCR引擎，需要额外安装Tesseract OCR：

1. 下载Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
2. 安装后，将安装路径添加到系统环境变量PATH中

## 运行说明

### 启动程序

```bash
python main.py
```

### OCR测试工具

项目提供了一个可视化的OCR测试工具，可以帮助您：
- 实时查看截取的游戏窗口图像
- 查看OCR识别区域
- 测试OCR识别效果
- 验证数据匹配和武器推荐

启动测试工具：

```bash
python tools/ocr_tester.py
```

测试工具功能：
1. **截取游戏窗口**：点击按钮截取当前游戏窗口
2. **OCR识别**：对截取的图像进行OCR识别
3. **完整测试**：执行完整的流程（截图→OCR→匹配→推荐）
4. **可视化显示**：实时显示截图和识别结果

### 使用说明

1. 启动程序后，会显示一个聊天窗口
2. 启动《怪物猎人崛起》游戏
3. 程序会自动检测游戏窗口并开始监控
4. 当游戏窗口激活时，程序会自动对任务信息区域进行OCR识别
5. 识别到任务后，会在聊天窗口中显示武器推荐

### 设置说明

1. 点击聊天窗口右上角的设置按钮（⚙️）打开设置界面
2. 在"窗口设置"选项卡中，可以调整窗口透明度和置顶设置
3. 在"OCR设置"选项卡中，可以调整OCR识别区域和引擎设置
4. 在"监控设置"选项卡中，可以调整监控间隔和自动启动设置
5. 点击"测试OCR"按钮可以测试OCR识别功能

### OCR识别区域设置

OCR识别区域是相对于游戏窗口左上角的坐标，默认设置为：
- X坐标: 50
- Y坐标: 50
- 宽度: 600
- 高度: 100

如果识别不准确，可以根据实际情况调整这些参数。

## 技术栈

- **开发语言**: Python
- **GUI框架**: PySide6
- **OCR引擎**: PaddleOCR / Tesseract
- **图像处理**: OpenCV
- **窗口操作**: pywin32
- **字符串匹配**: fuzzywuzzy

## 注意事项

1. 确保游戏窗口标题为"Monster Hunter Rise"，否则可能无法检测到游戏窗口
2. OCR识别区域需要根据游戏分辨率和UI布局进行调整
3. 首次使用PaddleOCR时，会自动下载模型文件，可能需要一些时间
4. 如果使用GPU加速，需要安装CUDA版本的PaddlePaddle

## 常见问题

### Q: 程序无法检测到游戏窗口

A: 请确保游戏正在运行，并且窗口标题包含"Monster Hunter Rise"。

### Q: OCR识别不准确

A: 可以尝试调整OCR识别区域，或者在设置中切换OCR引擎。

### Q: 程序运行缓慢

A: 可以尝试增加监控间隔，或者使用GPU加速（需要安装CUDA版本的PaddlePaddle）。

## 许可证

本项目仅供学习和交流使用。

## 贡献

欢迎提交问题和建议！
