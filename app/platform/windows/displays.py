# -*- coding: utf-8 -*-
"""多显示器与 DPI（方案 5.7 / 17.2.3）。

V4.1 只用过废弃的 ``QApplication.desktop()``，且无任何 DPI 感知，
本模块是新建实现。位置按显示器设备 ID 保存，不使用单一绝对坐标。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QScreen

if sys.platform == "win32":
    import ctypes

    _shcore = ctypes.windll.shcore
    _user32 = ctypes.windll.user32
else:  # pragma: no cover
    _shcore = None
    _user32 = None

# PER_MONITOR_AWARE_V2：多屏不同 DPI 下坐标才正确
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4) if sys.platform == "win32" else None


def enable_dpi_awareness() -> bool:
    """必须在创建 QApplication 之前调用。"""
    if sys.platform != "win32" or _shcore is None:
        return False
    try:
        if _user32.SetProcessDpiAwarenessContext(
            _DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        ):
            return True
    except Exception:
        pass
    try:
        _shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class DisplayInfo:
    """一个显示器的几何与缩放信息。"""

    name: str
    device_id: str
    geometry: QRect          # 虚拟桌面坐标（可能为负）
    scale: float             # devicePixelRatio
    is_primary: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "device_id": self.device_id,
            "x": self.geometry.x(),
            "y": self.geometry.y(),
            "width": self.geometry.width(),
            "height": self.geometry.height(),
            "scale": self.scale,
            "primary": self.is_primary,
        }


def display_device_id(screen: QScreen) -> str:
    """稳定标识。Qt6 提供 ``name``；若为空则退回几何摘要。

    不使用几何作为唯一键，是因为显示器重新排列后几何会变。
    """
    name = screen.name() or ""
    if name:
        return name
    geo = screen.geometry()
    return f"display-{geo.width()}x{geo.height()}"


def list_displays() -> list[DisplayInfo]:
    screens = QGuiApplication.screens()
    primary = QGuiApplication.primaryScreen()
    infos: list[DisplayInfo] = []
    for screen in screens:
        infos.append(
            DisplayInfo(
                name=screen.name() or "display",
                device_id=display_device_id(screen),
                geometry=screen.geometry(),
                scale=float(screen.devicePixelRatio()),
                is_primary=screen is primary,
            )
        )
    return infos


def active_display() -> DisplayInfo | None:
    """当前光标所在显示器；取不到时退回主屏。"""
    screen = QGuiApplication.screenAt(_cursor_pos())
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    return DisplayInfo(
        name=screen.name() or "display",
        device_id=display_device_id(screen),
        geometry=screen.geometry(),
        scale=float(screen.devicePixelRatio()),
        is_primary=screen is QGuiApplication.primaryScreen(),
    )


def _cursor_pos() -> QPoint:
    if sys.platform == "win32" and _user32 is not None:

        class _POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        point = _POINT()
        _user32.GetCursorPos(ctypes.byref(point))
        return QPoint(int(point.x), int(point.y))
    return QPoint(0, 0)


def clamp_to_display(rect: QRect, display: DisplayInfo) -> QRect:
    """把窗口夹回显示器可见区域，避免拖出屏幕后无法找回。"""
    area = display.geometry
    width = min(rect.width(), area.width())
    height = min(rect.height(), area.height())
    x = max(area.left(), min(rect.x(), area.right() - width + 1))
    y = max(area.top(), min(rect.y(), area.bottom() - height + 1))
    return QRect(x, y, width, height)


def top_center_on(display: DisplayInfo, width: int, height: int, margin: int = 14) -> QRect:
    """灵动岛默认锚定活动显示器顶部中央（方案 4.2）。"""
    area = display.geometry
    x = area.x() + (area.width() - width) // 2
    return QRect(x, area.y() + margin, width, height)


def restore_position(
    saved: list[int] | None, display: DisplayInfo, width: int, height: int, margin: int = 14
) -> QRect:
    """按显示器设备 ID 恢复位置；DPI 或分辨率变化时夹回可见区域。"""
    if not saved or len(saved) != 2:
        return top_center_on(display, width, height, margin)
    rect = QRect(int(saved[0]), int(saved[1]), width, height)
    return clamp_to_display(rect, display)


def to_normalized(x: int, y: int, display: DisplayInfo) -> tuple[float, float]:
    """屏幕像素 -> 该显示器内的 0..1 归一化坐标。"""
    area = display.geometry
    if area.width() <= 0 or area.height() <= 0:
        return (0.0, 0.0)
    nx = (x - area.x()) / area.width()
    ny = (y - area.y()) / area.height()
    return (min(max(nx, 0.0), 1.0), min(max(ny, 0.0), 1.0))


def to_pixels(nx: float, ny: float, display: DisplayInfo) -> tuple[int, int]:
    """归一化坐标 -> 屏幕像素。"""
    area = display.geometry
    px = int(area.x() + nx * area.width())
    py = int(area.y() + ny * area.height())
    return (px, py)


__all__ = [
    "enable_dpi_awareness",
    "DisplayInfo",
    "display_device_id",
    "list_displays",
    "active_display",
    "clamp_to_display",
    "top_center_on",
    "restore_position",
    "to_normalized",
    "to_pixels",
]
