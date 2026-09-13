# Desktop AI Coach · 桌面 AI 操作教练

运行在 Windows 桌面顶部的操作指导工具。用户在使用 Unity、Office、浏览器、
ERP 或 Windows 设置等应用时直接提问，客户端基于最近的屏幕上下文给出
**视觉指导**：目标框、箭头、字幕和虚拟鼠标。

首期只做视觉指导，**不代替用户操作**。

## 安全边界

这是产品定义的一部分，不是临时限制：

- 不自动点击、不自动输入、不移动真实系统鼠标；
- 不删除文件、不执行命令、不启动或关闭其它应用；
- 不读取剪贴板、不采集音频、不保存键盘原文；
- 默认不上传任何屏幕内容，上传前需用户显式开启并经过脱敏检查；
- 模型只能返回视觉指导协议，拿不到任何可调用的本机函数。

`tests/unit/test_safety_guards.py` 会静态扫描 `app/` 目录，一旦有人把
执行型调用接回主线就会失败。

## 当前实现状态

本版本是**可运行的骨架**，对应方案 I0/I1 与 I3 的 Mock 通路。

已实现：

| 模块 | 内容 |
|---|---|
| 窗口分层 | 灵动岛、输入坞、字幕轨、覆盖层、历史窗口五个独立 QML 窗口 |
| 视觉风格 | 方案 4.1.1 设计令牌：冷调玻璃、月光蓝/香槟金/暖橙/低饱和红 |
| 覆盖层 | 全屏透明、默认点击穿透、箭头放置时临时接管鼠标 |
| 状态机 | 全局 14 状态 + 教程步骤 8 状态，非法迁移被拒 |
| 协议 | `UserQuestion` / `ContextReady` / `GuideInstruction` / `VerificationResult`（pydantic 强校验） |
| AI 通路 | Mock Provider → 解析 → 校验 → 编排；低置信度主动澄清 |
| Provider | OpenAI-compatible（httpx）：JSON + SSE、超时、取消、分级重试、大小上限 |
| 平台层 | Win32 点击穿透、多显示器 + DPI、`RegisterHotKey` 全局快捷键、系统托盘 |
| 隐私 | 进程黑名单、敏感标题识别、上传守卫（默认拒绝） |
| 采集 | 协议定义 + 固定槽位环形缓存（**未接入真实采集**） |
| 测试 | 158 个用例（含 GUI 集成测试与安全守卫） |

尚未实现（属方案 I2、I4–I7）：

- 真实屏幕采集 Worker（mss 采集、变化检测、落盘清理）；
- 真实模型请求（默认 `use_mock=True`，不联网）；
- 教程步骤的视觉验证与跨页面重新定位；
- 知识库导入、检索与证据引用；
- 设置页、首启向导、安装程序与代码签名。

## 环境要求

- Windows 10 22H2+ / Windows 11，x64；
- Python 3.12+（本仓库 `.venv` 为 3.12.10）；
- PySide6 6.6+、pydantic 2.5+、httpx、mss、Pillow。

## 安装

```powershell
cd "E:\Competition\博客\V4.1 功能拓展版"

# 若 .venv 不存在
python -m venv .venv

# 安装依赖（使用虚拟环境内的 Python，避免污染全局）
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 运行

```powershell
.\.venv\Scripts\python.exe -m app.main
```

或使用启动脚本：

```powershell
.\.venv\Scripts\python.exe start.py
```

### 操作方式

| 动作 | 入口 |
|---|---|
| 展开/收起灵动岛 | 双击灵动岛顶部抓手，或 `Ctrl+Alt+Space`，或托盘左键 |
| 聚焦提问输入 | `Ctrl+Alt+Q` |
| 放置箭头 | 点击灵动岛 `↗`，或 `Ctrl+Alt+A`；单击放置默认箭头，拖拽决定方向长度 |
| 取消放置 | `Esc` |
| 清空标注 | 点击灵动岛 `⟲` |
| 暂停/恢复采集 | `Ctrl+Alt+P`，或托盘右键菜单 |
| 历史窗口 | 点击灵动岛 `☰`；失焦不会自动关闭 |

## 测试

```powershell
# 全部用例（含 GUI 集成测试）
.\.venv\Scripts\python.exe -m pytest tests

# 只跑不依赖窗口的单元测试
.\.venv\Scripts\python.exe -m pytest tests/unit

# Python 编译检查
.\.venv\Scripts\python.exe -m compileall -q app start.py build.py
```

## 打包

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe build.py
```

产物：`dist/DesktopAICoach.exe`。QML 文件通过 `--add-data` 随包分发。

## 目录结构

```text
app/
  main.py                 入口：DPI → 配置 → 日志 → QML → 托盘
  core/                   协议、状态机、配置、日志、会话、事件
  ui/                     window_manager、app_controller、theme
    qml/                  Theme / Island / InputDock / CaptionRail
                          / AnnotationLayer / HistoryWindow
  agent/                  Provider、Prompt、解析、校验、重试、编排
  capture/                Worker 协议 + 固定槽位环形缓存
  privacy/                黑名单、敏感窗口、上传守卫
  platform/windows/       穿透、多显示器、快捷键、托盘
tests/
  unit/                   协议、状态机、agent、配置、安全守卫
  integration/            GUI 冒烟与交互集成
```

## 与 V4.1 的关系

本项目在 V4.1「皮皮桌面助手」的基础上重做，原项目保留为 git tag
`v4.1-pet-assistant`，可随时检出回退。

从 V4.1 迁移的内容（语义参考、实现全部重写）：

- OpenAI-compatible Provider 的 SSE 解析、vendor 猜测与错误处理思路；
- PyInstaller 打包流程的参数组织方式；
- 便携式数据目录（`sys._MEIPASS` + exe 同级 `data/`）思路；
- 系统托盘交互参考。

已从主线移除：桌面宠物与悬浮球、音乐模式、情感分析、语音/TTS/Vosk、
LangChain 包装、以及「模型 → Python 函数 → `launch_app`/`taskkill`」执行链路。

`app_launcher.py` 与 `knowledge/` 仍保留在工作区，作为旧执行能力的隔离参考，
**不被 `app/` 下任何模块引用**，并由安全守卫测试持续检查。
