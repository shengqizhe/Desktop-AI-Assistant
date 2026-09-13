# -*- coding: utf-8 -*-
"""Win32 窗口样式：点击穿透与命中测试（方案 4.5）。

V4.1 完全没有可复用实现，这里是新建能力。策略：

* 覆盖层默认 ``WS_EX_TRANSPARENT | WS_EX_LAYERED``，普通桌面区域点击穿透。
* 需要交互时（箭头放置/编辑、字幕 × 命中区），临时移除 ``WS_EX_TRANSPARENT``。
* 字幕轨用「窗口整体穿透 + 命中矩形放行」的方式，避免整窗吃掉点击。
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, Sequence

if sys.platform == "win32":
    _user32 = ctypes.windll.user32
else:  # pragma: no cover - 首期只支持 Windows
    _user32 = None

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

#: 覆盖层需要的扩展样式：不激活 + 工具窗口 + 分层
BASE_OVERLAY_EXSTYLE = WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE


def is_supported() -> bool:
    return _user32 is not None


@dataclass(frozen=True)
class Rect:
    """屏幕像素矩形，左上原点。"""

    x: int
    y: int
    width: int
    height: int

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


def _hwnd_of(widget: Any) -> int:
    """从 QWidget/QWindow 拿到真实 HWND。"""
    if hasattr(widget, "winId"):
        return int(widget.winId())
    raise TypeError(f"对象没有 winId()：{type(widget)!r}")


def get_exstyle(widget: Any) -> int:
    if not is_supported():
        return 0
    hwnd = _hwnd_of(widget)
    return int(_user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE))


def set_exstyle(widget: Any, exstyle: int) -> None:
    if not is_supported():
        return
    hwnd = _hwnd_of(widget)
    _user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, exstyle)


def _flag(widget: Any, mask: int, enabled: bool) -> int:
    style = get_exstyle(widget)
    style = (style | mask) if enabled else (style & ~mask)
    set_exstyle(widget, style)
    return style


def set_click_through(widget: Any, enabled: bool) -> int:
    """开启/关闭整窗点击穿透。

    开启后鼠标事件全部落到下层应用，窗口自身不再接收点击。
    """
    return _flag(widget, WS_EX_TRANSPARENT, enabled)


def is_click_through(widget: Any) -> bool:
    return bool(get_exstyle(widget) & WS_EX_TRANSPARENT)


def make_overlay(widget: Any) -> None:
    """把窗口配置成覆盖层基础样式：不抢焦点、不进任务栏、置顶。"""
    if not is_supported():
        return
    style = (get_exstyle(widget) | BASE_OVERLAY_EXSTYLE) & ~WS_EX_TRANSPARENT
    set_exstyle(widget, style)
    hwnd = _hwnd_of(widget)
    _user32.SetWindowPos(
        wintypes.HWND(hwnd),
        wintypes.HWND(HWND_TOPMOST),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )


def set_topmost(widget: Any) -> None:
    if not is_supported():
        return
    hwnd = _hwnd_of(widget)
    _user32.SetWindowPos(
        wintypes.HWND(hwnd),
        wintypes.HWND(HWND_TOPMOST),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
    )


class HitTestGate:
    """全局命中测试：只有登记的矩形才认为窗口"可点"。

    覆盖层需要「普通区域穿透 + 箭头/手柄可命中」。单独用
    ``WS_EX_TRANSPARENT`` 做不到区域级放行，因此这里维护一份实时命中矩形，
    由 :func:`point_is_interactive` 在需要时判定。
    """

    def __init__(self) -> None:
        self._rects: list[Rect] = []

    @property
    def rects(self) -> tuple[Rect, ...]:
        return tuple(self._rects)

    def clear(self) -> None:
        self._rects.clear()

    def add(self, rect: Rect) -> None:
        self._rects.append(rect)

    def add_many(self, rects: Sequence[Rect]) -> None:
        self._rects.extend(rects)

    def contains(self, px: int, py: int) -> bool:
        return any(rect.contains(px, py) for rect in self._rects)


_GATE = HitTestGate()


def hit_test_gate() -> HitTestGate:
    return _GATE


__all__ = [
    "WS_EX_LAYERED",
    "WS_EX_TRANSPARENT",
    "WS_EX_TOOLWINDOW",
    "WS_EX_NOACTIVATE",
    "BASE_OVERLAY_EXSTYLE",
    "Rect",
    "is_supported",
    "get_exstyle",
    "set_exstyle",
    "set_click_through",
    "is_click_through",
    "make_overlay",
    "set_topmost",
    "HitTestGate",
    "hit_test_gate",
]
