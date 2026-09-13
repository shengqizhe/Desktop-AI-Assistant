# -*- coding: utf-8 -*-
"""窗口装配：把 6 个独立窗口按方案 4.2 / 17.2.3 定位。

窗口职责分离，控制器只做布局与坐标换算，不持有业务状态。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QUrl, Signal
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from app.core.config import AppConfig, save_config
from app.core.logging_setup import get_logger
from app.platform.windows import clickthrough, displays
from app.ui import theme

QML_DIR = Path(__file__).resolve().parent / "qml"

#: QML 文件 -> 窗口角色
QML_FILES = {
    "island": "Island.qml",
    "dock": "InputDock.qml",
    "captions": "CaptionRail.qml",
    "overlay": "AnnotationLayer.qml",
    "history": "HistoryWindow.qml",
}


@dataclass
class WindowSet:
    """已加载的窗口集合。"""

    island: QQuickWindow | None = None
    dock: QQuickWindow | None = None
    captions: QQuickWindow | None = None
    overlay: QQuickWindow | None = None
    history: QQuickWindow | None = None
    failures: dict[str, str] = field(default_factory=dict)

    def get(self, role: str) -> QQuickWindow | None:
        return getattr(self, role, None)

    @property
    def loaded(self) -> list[str]:
        return [role for role in QML_FILES if self.get(role) is not None]


class WindowManager(QObject):
    """加载 QML 并管理窗口布局、层级与穿透。"""

    layoutChanged = Signal()

    def __init__(self, engine: QQmlApplicationEngine, config: AppConfig) -> None:
        super().__init__()
        self._engine = engine
        self._config = config
        self._logger = get_logger()
        self.windows = WindowSet()
        self._display = displays.active_display()

    # ---- 加载 ----

    def load_all(self) -> WindowSet:
        for role, filename in QML_FILES.items():
            path = QML_DIR / filename
            if not path.exists():
                self.windows.failures[role] = f"缺少 QML：{filename}"
                continue
            before = len(self._engine.rootObjects())
            self._engine.load(QUrl.fromLocalFile(str(path)))
            roots = self._engine.rootObjects()
            if len(roots) <= before:
                self.windows.failures[role] = f"加载失败：{filename}"
                continue
            window = roots[-1]
            if not isinstance(window, QQuickWindow):
                self.windows.failures[role] = f"根对象不是窗口：{filename}"
                continue
            setattr(self.windows, role, window)

        self._apply_platform_styles()
        self.layout()
        if self.windows.failures:
            self._logger.warning("部分窗口加载失败：%s", self.windows.failures)
        return self.windows

    # ---- 平台样式与穿透 ----

    def _apply_platform_styles(self) -> None:
        overlay = self.windows.overlay
        if overlay is not None:
            clickthrough.make_overlay(overlay)
            # 覆盖层默认整窗穿透；进入箭头模式或播放动画时才临时打开命中
            clickthrough.set_click_through(overlay, True)

        if not clickthrough.is_supported():
            self._logger.warning("当前平台不支持 Win32 命中测试，穿透将不可用")

    def set_overlay_interactive(self, interactive: bool) -> None:
        """箭头放置/编辑期间临时接管鼠标（方案 4.5 覆盖层命中规则）。"""
        overlay = self.windows.overlay
        if overlay is None:
            return
        clickthrough.set_click_through(overlay, not interactive)

    def overlay_click_through(self) -> bool:
        overlay = self.windows.overlay
        if overlay is None:
            return True
        return clickthrough.is_click_through(overlay)

    # ---- 布局 ----

    def refresh_displays(self) -> displays.DisplayInfo | None:
        self._display = displays.active_display()
        return self._display

    def layout(self) -> None:
        """按当前活动显示器重新摆放所有窗口。"""
        display = self._display or self.refresh_displays()
        if display is None:
            return

        island = self.windows.island
        dock = self.windows.dock
        captions = self.windows.captions

        if island is not None:
            width = int(island.property("width") or theme.ISLAND_COLLAPSED_WIDTH)
            height = int(island.property("height") or theme.ISLAND_COLLAPSED_HEIGHT)
            saved = self._config.ui.display_positions.get(display.device_id)
            rect = displays.restore_position(
                saved, display, width, height, theme.ISLAND_TOP_MARGIN
            )
            island.setGeometry(rect)

        if dock is not None and island is not None:
            dock_rect = QRect(
                island.x() + (island.width() - dock.width()) // 2,
                island.y() + island.height() + 6,
                dock.width(),
                dock.height(),
            )
            dock.setGeometry(displays.clamp_to_display(dock_rect, display))

        if captions is not None and island is not None:
            # 字幕轨位于灵动岛右侧（方案 4.4.2）
            caption_rect = QRect(
                island.x() + island.width() - 60,
                island.y() + island.height() + 56,
                captions.width(),
                captions.height(),
            )
            captions.setGeometry(displays.clamp_to_display(caption_rect, display))

        overlay = self.windows.overlay
        if overlay is not None:
            overlay.setGeometry(display.geometry)

        history = self.windows.history
        if history is not None:
            area = display.geometry
            history_rect = QRect(
                area.x() + (area.width() - history.width()) // 2,
                area.y() + (area.height() - history.height()) // 2,
                history.width(),
                history.height(),
            )
            history.setGeometry(history_rect)

        self.layoutChanged.emit()

    def remember_island_position(self) -> None:
        """位置按显示器设备 ID 保存，不使用单一绝对坐标。"""
        island = self.windows.island
        display = self._display
        if island is None or display is None:
            return
        self._config.ui.display_positions[display.device_id] = [island.x(), island.y()]
        try:
            save_config(self._config)
        except OSError as exc:
            self._logger.warning("保存窗口位置失败：%s", exc)


__all__ = ["QML_DIR", "QML_FILES", "WindowSet", "WindowManager"]
