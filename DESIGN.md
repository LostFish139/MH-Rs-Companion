
# 怪物猎人崛起智能狩猎助手 - 设计文档

## 1. 项目概述

### 1.1 项目简介
怪物猎人崛起智能狩猎助手是一个基于Python开发的桌面应用程序，通过OCR识别游戏任务信息，分析怪物弱点，推荐最优盾斧武器。该应用程序实时监控《怪物猎人崛起》游戏窗口，自动识别任务信息，并根据怪物弱点数据提供武器推荐。

### 1.2 核心功能
- 游戏窗口监听：实时检测游戏窗口是否激活
- 智能OCR识别：对游戏窗口任务信息区域进行文本识别
- 武器推荐：根据怪物弱点属性推荐最优武器
- 聊天界面：以聊天气泡形式展示武器推荐信息
- 设置界面：支持透明度调节、OCR测试、检测区域自定义等功能

### 1.3 技术栈
- 开发语言：Python 3.8+
- GUI框架：PySide6
- OCR引擎：RapidOCR / Tesseract
- 图像处理：OpenCV
- 窗口操作：pywin32
- 字符串匹配：fuzzywuzzy

## 2. 系统架构

### 2.1 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                        主程序 (main.py)                      │
│                    MainWindowController                      │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│  UI   │ │ Core  │ │ Config │
└───────┘ └───────┘ └───────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
┌───────┐┌───────┐┌───────┐
│Screen-││  OCR  ││Matcher│
│  shot ││       ││       │
└───────┘└───────┘└───────┘
```

### 2.2 模块划分
1. **主程序模块** (main.py)
   - 程序入口
   - 协调各模块交互
   - 处理应用生命周期

2. **核心业务模块** (core/)
   - workflow.py：工作流编排
   - screenshot.py：截图模块
   - ocr.py：OCR识别模块
   - matcher.py：数据匹配模块

3. **UI模块** (ui/)
   - chat_window.py：聊天窗口
   - settings.py：设置界面
   - region_selector.py：区域选择器

4. **配置模块** (config.py)
   - 应用配置管理
   - 参数配置

5. **数据模块** (data/)
   - 任务武器数据
   - 怪物弱点数据

6. **工具模块** (tools/)
   - screenshot_tool.py：截图工具
   - ocr_tester.py：OCR测试工具

## 3. 核心模块设计

### 3.1 工作流编排模块 (workflow.py)

#### 3.1.1 功能描述
工作流编排模块负责协调截图、OCR识别和数据匹配等核心功能，实现完整的业务流程。

#### 3.1.2 类设计
```python
class Workflow:
    """工作流编排器 - 协调各个模块完成完整流程"""

    属性:
        - screenshot_capture: ScreenshotCapture  # 截图捕获器
        - ocr_engine: OCREngine                  # OCR引擎
        - data_matcher: DataMatcher              # 数据匹配器
        - on_result_callback: Callable           # 结果回调函数
        - on_error_callback: Callable            # 错误回调函数
        - recognition_history: List[Dict]        # 识别历史记录
        - max_history_size: int                  # 最大历史记录数量
        - shown_no_task_warning: bool            # 是否已显示无任务警告

    方法:
        - set_callbacks(on_result, on_error)     # 设置回调函数
        - execute() -> bool                      # 执行完整工作流
        - test_ocr(num_tests) -> List[Dict]      # 测试OCR功能
        - cleanup_old_screenshots()              # 清理旧截图
```

#### 3.1.3 工作流程
```
1. 检测游戏窗口
   ↓
2. 检查游戏窗口是否激活
   ↓
3. 截取OCR区域
   ↓
4. OCR识别文字
   ↓
5. 与数据集比对
   ↓
6. 返回推荐武器信息
```

### 3.2 截图模块 (screenshot.py)

#### 3.2.1 功能描述
截图模块负责查找游戏窗口并截取指定区域的图像，支持多种截图方法以确保兼容性。

#### 3.2.2 类设计
```python
class ScreenshotCapture:
    """截图捕获器 - 负责游戏窗口截图"""

    属性:
        - game_hwnd: int                          # 游戏窗口句柄
        - last_window_rect: Tuple[int, int, int, int]  # 上次窗口位置
        - max_screenshots: int                   # 最大截图数量
        - screenshot_files: List[str]            # 截图文件列表

    方法:
        - find_game_window() -> bool             # 查找游戏窗口
        - is_game_window_active() -> bool        # 检查游戏窗口是否激活
        - get_window_rect() -> Optional[Tuple]   # 获取窗口矩形区域
        - capture_window() -> Optional[np.ndarray]  # 截取游戏窗口
        - capture_ocr_region() -> Optional[np.ndarray]  # 截取OCR区域
        - _save_debug_screenshot(img, method)    # 保存调试截图
```

#### 3.2.3 截图方法
1. **方法1**：使用mss + win32gui捕获窗口
2. **方法2**：使用窗口DC的BitBlt
3. **方法3**：使用PrintWindow API
4. **方法4**：使用mss + pygetwindow

### 3.3 OCR识别模块 (ocr.py)

#### 3.3.1 功能描述
OCR识别模块负责对图像进行文本识别，支持RapidOCR和Tesseract两种OCR引擎。

#### 3.3.2 类设计
```python
class OCREngine:
    """OCR引擎 - 负责图像文本识别"""

    属性:
        - engine: Union[RapidOCR, pytesseract]   # OCR引擎实例
        - engine_type: str                       # 引擎类型

    方法:
        - _init_engine()                         # 初始化OCR引擎
        - _init_rapidocr()                       # 初始化RapidOCR
        - _init_tesseract()                      # 初始化Tesseract
        - recognize_text(image) -> str            # 识别图像文本
        - _recognize_with_rapidocr(image) -> str  # 使用RapidOCR识别
        - _recognize_with_tesseract(image) -> str  # 使用Tesseract识别
```

#### 3.3.3 OCR引擎选择
- 默认使用RapidOCR，速度快且识别准确
- 如果RapidOCR不可用，自动降级使用Tesseract
- 可通过配置文件切换OCR引擎

### 3.4 数据匹配模块 (matcher.py)

#### 3.4.1 功能描述
数据匹配模块负责将OCR识别到的任务名称与数据库进行匹配，返回对应的武器推荐信息。

#### 3.4.2 类设计
```python
class DataMatcher:
    """数据匹配器 - 负责任务与武器数据的匹配"""

    属性:
        - task_data: Dict                         # 任务武器数据
        - monster_data: Dict                      # 怪物弱点数据

    方法:
        - _load_data()                           # 加载数据文件
        - match_task(task_name) -> Optional[Dict]  # 匹配任务名称
        - match_monster(monster_name) -> Optional[Dict]  # 匹配怪物名称
        - get_recommendation(task_name) -> Tuple[str, List[Dict]]  # 获取武器推荐
        - get_all_task_names() -> List[str]       # 获取所有任务名称
        - get_all_monster_names() -> List[str]    # 获取所有怪物名称
```

#### 3.4.3 匹配策略
1. **精确匹配**：首先尝试精确匹配任务名称
2. **模糊匹配**：如果精确匹配失败，使用fuzzywuzzy进行模糊匹配
3. **相似度阈值**：相似度达到70%以上才认为匹配成功

## 4. UI模块设计

### 4.1 聊天窗口 (chat_window.py)

#### 4.1.1 功能描述
聊天窗口是程序的主界面，以聊天气泡形式展示武器推荐信息和系统消息。

#### 4.1.2 类设计
```python
class ChatBubble(QWidget):
    """聊天气泡组件"""

    属性:
        - message: str                           # 消息内容
        - is_user: bool                          # 是否为用户消息

    方法:
        - init_ui()                              # 初始化UI

class ChatWindow(QMainWindow):
    """聊天窗口 - 主窗口"""

    信号:
        - settings_requested                     # 设置请求信号

    属性:
        - chat_content: QWidget                  # 聊天内容容器
        - chat_content_layout: QVBoxLayout       # 聊天内容布局
        - window_check_timer: QTimer             # 窗口检查定时器
        - ocr_timer: QTimer                      # OCR定时器
        - last_shown_monster: str                # 最后显示的怪物名称

    方法:
        - init_ui()                              # 初始化UI
        - create_title_bar() -> QWidget          # 创建标题栏
        - create_chat_area() -> QScrollArea      # 创建聊天区域
        - create_control_area() -> QWidget       # 创建控制区域
        - setup_timers()                         # 设置定时器
        - add_user_message(message)              # 添加用户消息
        - add_assistant_message(message)         # 添加助手消息
        - show_weapon_recommendation(monster, weapons)  # 显示武器推荐
        - update_status(status)                  # 更新状态
        - start_monitoring()                     # 开始监控
        - stop_monitoring()                      # 停止监控
```

#### 4.1.3 界面布局
```
┌─────────────────────────────────────┐
│ 标题栏 (标题 + 设置 + 最小化 + 关闭) │
├─────────────────────────────────────┤
│                                     │
│         聊天内容区域                 │
│      (可滚动，消息气泡)              │
│                                     │
├─────────────────────────────────────┤
│        控制区域 (状态显示)           │
└─────────────────────────────────────┘
```

### 4.2 设置界面 (settings.py)

#### 4.2.1 功能描述
设置界面提供应用程序的各种配置选项，包括窗口设置、OCR设置和监控设置。

#### 4.2.2 类设计
```python
class SettingsDialog(QDialog):
    """设置对话框"""

    信号:
        - settings_changed                       # 设置更改信号
        - ocr_test_requested                    # OCR测试请求信号

    属性:
        - current_settings: Dict                # 当前设置

    方法:
        - init_ui()                             # 初始化UI
        - create_tabs()                         # 创建选项卡
        - create_window_tab()                   # 创建窗口设置选项卡
        - create_ocr_tab()                     # 创建OCR设置选项卡
        - create_monitor_tab()                 # 创建监控设置选项卡
        - load_settings()                      # 加载设置
        - save_settings()                      # 保存设置
        - apply_settings()                     # 应用设置
        - reset_settings()                     # 重置设置
```

#### 4.2.3 设置选项
1. **窗口设置**
   - 窗口透明度
   - 窗口置顶

2. **OCR设置**
   - OCR识别区域
   - OCR引擎选择
   - OCR测试

3. **监控设置**
   - 窗口检查间隔
   - OCR识别间隔
   - 自动启动监控

### 4.3 区域选择器 (region_selector.py)

#### 4.3.1 功能描述
区域选择器提供可视化的界面，用于选择和调整OCR识别区域。

#### 4.3.2 类设计
```python
class RegionSelector(QWidget):
    """区域选择器 - 用于选择OCR识别区域"""

    信号:
        - region_changed                        # 区域更改信号

    属性:
        - image: np.ndarray                     # 当前图像
        - region: Dict                          # 当前区域
        - selecting: bool                      # 是否正在选择

    方法:
        - init_ui()                             # 初始化UI
        - set_image(image)                      # 设置图像
        - set_region(region)                   # 设置区域
        - get_region() -> Dict                  # 获取区域
        - mousePressEvent(event)                # 鼠标按下事件
        - mouseMoveEvent(event)                # 鼠标移动事件
        - mouseReleaseEvent(event)              # 鼠标释放事件
        - paintEvent(event)                    # 绘制事件
```

## 5. 配置管理

### 5.1 配置文件 (config.py)

#### 5.1.1 配置项
```python
# 项目根目录
BASE_DIR: Path

# 数据文件路径
TASK_WEAPON_FILE: str
MONSTER_WEAKNESS_FILE: str

# 游戏窗口配置
GAME_WINDOW_TITLE: str
GAME_WINDOW_CLASS: str

# OCR识别区域配置
OCR_REGION: Dict

# OCR引擎配置
OCR_ENGINE: str
OCR_LANG: str
PADDLEOCR_USE_GPU: bool

# 窗口配置
WINDOW_CONFIG: Dict

# 监控配置
MONITOR_CONFIG: Dict

# UI配置
UI_CONFIG: Dict

# 调试配置
DEBUG: bool
DEBUG_SAVE_SCREENSHOT: bool
DEBUG_SCREENSHOT_DIR: str
```

### 5.2 数据文件

#### 5.2.1 任务武器数据 (task_weapon.json)
```json
{
  "任务名称": {
    "targets": ["怪物名称"],
    "weapons": [
      {
        "weapon": "武器名称",
        "element": "属性",
      }
    ]
  }
}
```

#### 5.2.2 怪物弱点数据 (monster_weakness.json)
```json
{
  "怪物名称": {
    "weakness": {
      ""
    },
    "recommended_weapon": {
      "weapon": "武器名称",
      "element": "属性"
    }
  }
}
```

## 6. 数据流设计

### 6.1 主流程数据流
```
游戏窗口
  ↓
ScreenshotCapture.capture_ocr_region()
  ↓
OCREngine.recognize_text()
  ↓
DataMatcher.get_recommendation()
  ↓
MainWindowController.on_workflow_result()
  ↓
ChatWindow.show_weapon_recommendation()
```

### 6.2 错误处理数据流
```
Workflow.execute()
  ↓
发生错误
  ↓
on_error_callback()
  ↓
MainWindowController.on_workflow_error()
  ↓
ChatWindow.add_assistant_message()
```

## 7. 性能优化

### 7.1 截图优化
- 支持多种截图方法，自动选择最优方案
- 只截取OCR识别区域，减少图像处理量
- 使用mss库进行高效截图

### 7.2 OCR优化
- 使用RapidOCR作为默认OCR引擎，速度快且准确
- 支持GPU加速（需安装CUDA版本的PaddlePaddle）
- 可调整OCR识别间隔，平衡性能和实时性

### 7.3 匹配优化
- 使用模糊匹配算法，提高匹配准确率
- 缓存识别历史，避免重复处理
- 限制历史记录大小，控制内存使用

### 7.4 UI优化
- 使用定时器控制监控频率
- 异步处理耗时操作，避免界面卡顿
- 优化图像显示，使用缩放和缓存

## 8. 扩展性设计

### 8.1 OCR引擎扩展
- 支持多种OCR引擎
- 易于添加新的OCR引擎
- 可通过配置文件切换引擎

### 8.2 数据源扩展
- 支持JSON格式数据文件
- 易于添加新的数据源
- 支持在线数据更新

### 8.3 UI扩展
- 模块化UI组件设计
- 易于添加新的设置选项
- 支持自定义主题

### 8.4 功能扩展
- 工作流模块化设计
- 易于添加新的处理步骤
- 支持自定义回调函数

## 9. 安全性考虑

### 9.1 数据安全
- 本地存储数据，不上传到服务器
- 敏感信息加密存储
- 定期清理临时文件

### 9.2 运行安全
- 异常处理机制
- 资源释放机制
- 防止内存泄漏

## 10. 部署说明

### 10.1 环境要求
- Python 3.8+
- Windows 操作系统
- 《怪物猎人崛起》游戏

### 10.2 依赖安装
```bash
pip install -r requirements.txt
```

### 10.3 运行方式
```bash
python main.py
```

### 10.4 打包发布
可使用PyInstaller等工具将程序打包为可执行文件，方便分发。

## 11. 维护与更新

### 11.1 日志管理
- 分级日志记录
- 日志文件轮转
- 调试信息开关

### 11.2 版本控制
- 使用Git进行版本控制
- 遵循语义化版本号
- 维护变更日志

### 11.3 问题反馈
- 提供问题反馈渠道
- 收集用户反馈
- 定期更新修复

## 12. 附录

### 12.1 术语表
- OCR：光学字符识别
- GUI：图形用户界面
- API：应用程序接口
- DC：设备上下文

### 12.2 参考资料
- PySide6官方文档
- RapidOCR文档
- OpenCV文档
- 怪物猎人崛起游戏资料

### 12.3 版本历史
- v1.0.0：初始版本
