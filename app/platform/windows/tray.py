# -*- coding: utf-8 -*-
"""系统托盘（方案 17.2.2）。

V4.1 有托盘实现可参考交互，但菜单语义不同：这里是
展开灵动岛 / 暂停采集 / 历史 / 设置 / 退出。
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.ui import theme


def build_tray_pixmap(size: int = 64) -> QPixmap:
    """程序内绘制托盘图标，避免依赖已删除的 public/ 素材。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(theme.INK_800))
    painter.setPen(QColor(theme.MOONLIGHT))
    painter.drawRoundedRect(4, 16, size - 8, size - 32, 12, 12)
    painter.setBrush(QColor(theme.CHAMPAGNE))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(int(size * 0.30), int(size * 0.45), int(size * 0.12), int(size * 0.12))
    painter.end()
    return pixmap


class TrayController(QObject):
    """托盘交互。所有动作都通过信号交给上层，不在托盘里直接改业务状态。"""

    toggleIslandRequested = Signal()
    toggleCaptureRequested = Signal()
    historyRequested = Signal()
    settingsRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon = QSystemTrayIcon(QIcon(build_tray_pixmap()), self)
        self._icon.setToolTip("桌面 AI 操作教练")
        self._menu = QMenu()
        self._capture_action: QAction | None = None
        self._build_menu()
        self._icon.setContextMenu(self._menu)
        self._icon.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        toggle = QAction("展开灵动岛", self._menu)
        toggle.triggered.connect(self.toggleIslandRequested.emit)
        self._menu.addAction(toggle)

        self._capture_action = QAction("暂停采集", self._menu)
        self._capture_action.triggered.connect(self.toggleCaptureRequested.emit)
        self._menu.addAction(self._capture_action)

        self._menu.addSeparator()

        history = QAction("查看历史", self._menu)
        history.triggered.connect(self.historyRequested.emit)
        self._menu.addAction(history)

        settings = QAction("设置", self._menu)
        settings.triggered.connect(self.settingsRequested.emit)
        self._menu.addAction(settings)

        self._menu.addSeparator()

        quit_action = QAction("退出", self._menu)
        quit_action.triggered.connect(self.quitRequested.emit)
        self._menu.addAction(quit_action)

    def set_capture_paused(self, paused: bool) -> None:
        if self._capture_action is not None:
            self._capture_action.setText("恢复采集" if paused else "暂停采集")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # 托盘左键展开灵动岛
        if reason == QSystemTrayIcon.Trigger:
            self.toggleIslandRequested.emit()

    def show(self) -> None:
        self._icon.show()

    def hide(self) -> None:
        self._icon.hide()

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()


__all__ = ["build_tray_pixmap", "TrayController"]
