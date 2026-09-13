# -*- coding: utf-8 -*-
"""Windows 平台适配层：多显示器、DPI、命中测试、全局快捷键、托盘。

其它层只依赖本包导出的接口，不直接调用 Win32。
"""

from app.platform.windows.clickthrough import (
    BASE_OVERLAY_EXSTYLE,
    Rect,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
    HitTestGate,
    hit_test_gate,
    is_click_through,
    is_supported,
    make_overlay,
    set_click_through,
    set_topmost,
)
from app.platform.windows.displays import (
    DisplayInfo,
    active_display,
    clamp_to_display,
    display_device_id,
    enable_dpi_awareness,
    list_displays,
    restore_position,
    to_normalized,
    to_pixels,
    top_center_on,
)
from app.platform.windows.hotkeys import GlobalHotkeys, HotkeyError, parse_hotkey
from app.platform.windows.tray import TrayController

__all__ = [
    "BASE_OVERLAY_EXSTYLE",
    "Rect",
    "WS_EX_LAYERED",
    "WS_EX_NOACTIVATE",
    "WS_EX_TOOLWINDOW",
    "WS_EX_TRANSPARENT",
    "HitTestGate",
    "hit_test_gate",
    "is_click_through",
    "is_supported",
    "make_overlay",
    "set_click_through",
    "set_topmost",
    "DisplayInfo",
    "active_display",
    "clamp_to_display",
    "display_device_id",
    "enable_dpi_awareness",
    "list_displays",
    "restore_position",
    "to_normalized",
    "to_pixels",
    "top_center_on",
    "GlobalHotkeys",
    "HotkeyError",
    "parse_hotkey",
    "TrayController",
]
