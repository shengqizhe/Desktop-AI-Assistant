# -*- coding: utf-8 -*-
"""GUI 集成测试（方案 9.2 集成测试 + I1/I3 验收）。

需要真实窗口系统，因此在无显示器环境下自动跳过。
运行：.venv\\Scripts\\python.exe -m pytest tests/integration -q
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _gui_available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        from PySide6.QtWidgets import QApplication  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("DISPLAY") or sys.platform == "win32")


pytestmark = [
    pytest.mark.gui,
    pytest.mark.skipif(not _gui_available(), reason="没有可用的 GUI 环境"),
]


@pytest.fixture(scope="module")
def app_and_controller():
    """构建一次完整的应用外壳，供本模块所有用例复用。"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from app.main import _configure_qt_plugin_path

    _configure_qt_plugin_path()

    from app.core.config import load_config
    from app.ui.app_controller import AppController
    from app.ui.window_manager import WindowManager

    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)

    config = load_config()
    config.provider.use_mock = True

    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: [warnings.append(w.toString()) for w in ws])

    manager = WindowManager(engine, config)
    windows = manager.load_all()
    controller = AppController(config, manager)
    controller.start()

    yield qapp, controller, manager, windows, warnings

    controller.shutdown()


class TestWindowLoading:
    def test_all_windows_load(self, app_and_controller):
        _, _, _, windows, _ = app_and_controller
        assert windows.failures == {}
        assert set(windows.loaded) == {"island", "dock", "captions", "overlay", "history"}

    def test_qml_has_no_warnings(self, app_and_controller):
        _, _, _, _, warnings = app_and_controller
        assert warnings == []

    def test_island_is_top_centered_on_active_display(self, app_and_controller):
        _, _, _, windows, _ = app_and_controller
        from app.platform.windows import active_display

        display = active_display()
        assert display is not None
        island = windows.island
        expected_center = display.geometry.x() + display.geometry.width() // 2
        assert abs((island.x() + island.width() // 2) - expected_center) <= 2

    def test_dock_sits_below_island(self, app_and_controller):
        _, _, _, windows, _ = app_and_controller
        assert windows.dock.y() > windows.island.y() + windows.island.height() - 1

    def test_overlay_covers_full_display(self, app_and_controller):
        _, _, _, windows, _ = app_and_controller
        from app.platform.windows import active_display

        display = active_display()
        assert display is not None
        overlay = windows.overlay
        assert overlay.width() == display.geometry.width()
        assert overlay.height() == display.geometry.height()


class TestClickThrough:
    def test_overlay_is_click_through_by_default(self, app_and_controller):
        _, _, manager, _, _ = app_and_controller
        assert manager.overlay_click_through() is True

    def test_arrow_mode_takes_mouse_then_releases(self, app_and_controller):
        _, controller, manager, windows, _ = app_and_controller
        controller._toggle_arrow_mode(True)
        try:
            assert manager.overlay_click_through() is False
            assert windows.overlay.property("arrowMode") is True
        finally:
            controller._toggle_arrow_mode(False)
        assert manager.overlay_click_through() is True
        assert windows.overlay.property("arrowMode") is False


class TestAskFlow:
    def test_mock_question_produces_captions(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.ask("这个脚本为什么挂不上去？")
        captions = controller._captions
        kinds = [c["kind"] for c in captions]
        assert "question" in kinds
        # Mock 置信度低，必须进入澄清而不是假装已定位
        assert controller.state.state.value == "clarifying"
        assert windows.overlay.property("targetBox") is None

    def test_low_confidence_does_not_animate_pointer(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.ask("再问一次")
        assert windows.overlay.property("virtualCursor") is None

    def test_caption_count_is_capped(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        for i in range(10):
            controller.ask(f"问题 {i}")
        assert len(controller._captions) <= 6

    def test_empty_question_is_ignored(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        before = len(controller._captions)
        controller.ask("   ")
        assert len(controller._captions) == before


class TestCaptionIndependence:
    def test_dismissing_one_caption_keeps_others_and_tutorial(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.ask("测试字幕独立关闭")
        before = len(controller._captions)
        assert before >= 2

        target_id = controller._captions[0]["id"]
        tutorial_before = controller.tutorial.current
        controller.dismiss_caption(target_id)

        assert len(controller._captions) == before - 1
        # 关字幕不结束教程
        assert controller.tutorial.current is not None
        assert controller.tutorial.current.step_id == (
            tutorial_before.step_id if tutorial_before else None
        )

    def test_message_remains_in_session_after_dismiss(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        controller.ask("关掉后仍在历史里")
        target = controller._captions[0]
        controller.dismiss_caption(target["id"])
        # 只改变 visible，不删除会话内容
        assert any(m.id == target["id"] for m in controller.session.messages)


class TestArrowAnnotation:
    def test_placed_arrow_appears_in_overlay(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        controller.clear_annotations()
        controller._on_arrow_drawn(0.2, 0.3, 0.5, 0.4)
        payload = controller._annotations_payload
        assert len(payload) == 1
        assert payload[0]["owner"] == "user"
        assert payload[0]["color"] == "user-mark"

    def test_clear_only_removes_user_annotations(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        controller._on_arrow_drawn(0.1, 0.1, 0.2, 0.2)
        controller.clear_annotations()
        assert controller._annotations_payload == []
        # 清空不影响会话
        assert controller.session is not None

    def test_arrow_count_is_capped(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        controller.clear_annotations()
        for i in range(30):
            controller._on_arrow_drawn(0.1, 0.1, min(0.1 + i * 0.01, 0.9), 0.5)
        assert len(controller._annotations_payload) <= 20


class TestPauseAndTutorialPersistence:
    def test_pause_does_not_destroy_captions_or_tutorial(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.ask("暂停前的问题")
        captions_before = len(controller._captions)
        step_before = controller.tutorial.current.step_id if controller.tutorial.current else None

        controller.toggle_capture()
        try:
            assert controller.state.state.value == "privacy_paused"
            assert len(controller._captions) == captions_before
            assert (
                controller.tutorial.current.step_id if controller.tutorial.current else None
            ) == step_before
        finally:
            controller.toggle_capture()

    def test_pause_updates_island_label(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.toggle_capture()
        try:
            assert windows.island.property("cacheText") == "已暂停"
        finally:
            controller.toggle_capture()


class TestHistoryWindow:
    def test_history_opens_and_stays_open(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.ask("历史窗口测试")
        controller.show_history()
        assert windows.history.isVisible()
        assert len(windows.history.property("sessions") or []) >= 1

    def test_history_close_does_not_stop_tutorial(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.show_history()
        step = controller.tutorial.current.step_id if controller.tutorial.current else None
        controller._on_history_closed()
        assert (controller.tutorial.current.step_id if controller.tutorial.current else None) == step


class TestTrayAndHotkeys:
    def test_tray_is_available_on_windows(self, app_and_controller):
        _, controller, _, _, _ = app_and_controller
        assert controller.tray.available is True

    def test_hotkey_parsing_matches_plan(self):
        from app.platform.windows.hotkeys import parse_hotkey

        modifiers, vk = parse_hotkey("Ctrl+Alt+Space")
        assert modifiers != 0
        assert vk == 0x20

    @pytest.mark.parametrize("spec", ["Ctrl+", "Space", "", "Ctrl+Foo"])
    def test_invalid_hotkeys_are_rejected(self, spec):
        from app.platform.windows.hotkeys import HotkeyError, parse_hotkey

        with pytest.raises(HotkeyError):
            parse_hotkey(spec)
