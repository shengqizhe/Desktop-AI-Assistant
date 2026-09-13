# -*- coding: utf-8 -*-
"""桌面 AI 操作教练入口。

启动顺序（方案 4.2.4 / 17.2.1）：
1. 设置进程 DPI 感知（必须在 QApplication 之前）；
2. 初始化配置与日志；
3. 安装 Win32 全局快捷键事件过滤器；
4. 加载 QML 窗口，定位到活动显示器顶部；
5. 显示托盘并进入 Monitoring。

首期只做视觉指导：不点击、不输入、不删除、不执行命令、不移动真实鼠标。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_qt_plugin_path() -> None:
    """中文安装路径下 PySide6 可能找不到平台插件，显式指向真实路径。"""
    plugins = Path(sys.executable).resolve().parent.parent / "Lib" / "site-packages" / "PySide6" / "plugins"
    if plugins.is_dir():
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugins))
        platforms = plugins / "platforms"
        if platforms.is_dir():
            os.environ["PATH"] = str(platforms) + os.pathsep + os.environ.get("PATH", "")
    # QML 模块路径（PySide6 6.11 位于 PySide6/qml）
    qml_dir = Path(sys.executable).resolve().parent.parent / "Lib" / "site-packages" / "PySide6" / "qml"
    if qml_dir.is_dir():
        os.environ.setdefault("QML2_IMPORT_PATH", str(qml_dir))


_configure_qt_plugin_path()

from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402

from app.core.config import load_config, save_config  # noqa: E402
from app.core.logging_setup import get_logger, init_logging  # noqa: E402
from app.platform.windows import enable_dpi_awareness  # noqa: E402
from app.ui.app_controller import AppController  # noqa: E402
from app.ui.window_manager import WindowManager  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    # DPI 感知必须在创建 QApplication 之前设置，否则多屏坐标会错
    enable_dpi_awareness()

    config = load_config()
    try:
        save_config(config)
    except OSError:
        pass
    logger = init_logging()
    logger.info("启动 Desktop AI Coach")

    # 用 QApplication 而非 QGuiApplication：QSystemTrayIcon 与 QMenu 来自
    # QtWidgets，在纯 QGuiApplication 下会直接崩溃。QApplication 是
    # QGuiApplication 的子类，Qt Quick/QML 窗口不受影响。
    app = QApplication(argv)
    app.setApplicationName("Desktop AI Coach")
    app.setQuitOnLastWindowClosed(False)

    engine = QQmlApplicationEngine()
    engine.warnings.connect(
        lambda warnings: [logger.warning("QML: %s", w.toString()) for w in warnings]
    )

    manager = WindowManager(engine, config)
    windows = manager.load_all()
    if not windows.loaded:
        logger.error("没有任何窗口加载成功，退出")
        print("QML 窗口加载失败，请检查 app/ui/qml 目录与 PySide6 安装。", file=sys.stderr)
        return 1

    controller = AppController(config, manager)

    # 全局快捷键需要事件过滤器
    app.installNativeEventFilter(controller.hotkeys)

    controller.start()

    if controller.hotkey_failures:
        for spec, reason in controller.hotkey_failures.items():
            print(f"[警告] 快捷键 {spec} 不可用：{reason}", file=sys.stderr)

    # 首帧渲染后定位，避免尺寸未就绪导致位置偏移
    QTimer.singleShot(0, manager.layout)

    def _on_quit() -> None:
        controller.shutdown()
        app.quit()

    controller.tray.quitRequested.connect(_on_quit)
    app.aboutToQuit.connect(controller.shutdown)

    code = app.exec()
    logger.info("退出 Desktop AI Coach，代码 %s", code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
