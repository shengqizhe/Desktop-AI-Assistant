# -*- coding: utf-8 -*-
"""UI 层：PySide6 + Qt Quick/QML。

窗口分层互相独立：灵动岛、输入坞、字幕轨、历史窗口、覆盖层分别维护状态，
关闭其中任何一个都不结束教程（方案 4.4 / 10.5）。
"""

from app.ui.theme import state_visual

__all__ = ["state_visual"]
