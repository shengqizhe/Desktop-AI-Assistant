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


    def test_overlay_is_visible_so_guides_can_appear(self, app_and_controller):
        """覆盖层必须常驻可见：箭头与目标框画在它上面。

        隐藏窗口无法显示任何指导内容，这是容易被忽略的真实缺陷。
        """
        _, _, _, windows, _ = app_and_controller
        assert windows.overlay.isVisible(), "覆盖层未显示，指导内容不可能可见"


class TestOverlayActuallyRenders:
    """像素级验证：确认标注真的画出来了，而不只是数据写进去了。

    这里防的是一类真实回归——QML 里 Item 未给尺寸会让 Canvas 被撑成 0x0，
    数据正确但屏幕上什么都看不到，纯数据断言无法发现。

    注意：Canvas 需要一帧才会重绘，所以断言前必须 pump 事件循环，
    否则 grabWindow 抓到的是重绘前的画面。
    """

    @staticmethod
    def _pump(milliseconds: int = 60) -> None:
        from PySide6.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    @classmethod
    def _wait_for_pixels(cls, window, predicate, timeout_ms: int = 2000) -> int:
        """轮询等待画面出现目标像素。

        Canvas 首帧重绘有约 200ms 延迟，用固定 sleep 会产生随机失败；
        这里改为有上限的轮询：若始终不出现，仍然会失败。
        """
        waited = 0
        hits = 0
        while waited < timeout_ms:
            cls._pump(100)
            waited += 100
            hits = cls._count_pixels(window.grabWindow(), predicate)
            if hits > 0:
                break
        return hits

    @staticmethod
    def _count_pixels(image, predicate) -> int:
        hits = 0
        for y in range(0, image.height(), 2):
            for x in range(0, image.width(), 2):
                color = image.pixelColor(x, y)
                if color.alpha() > 40 and predicate(color):
                    hits += 1
        return hits

    @staticmethod
    def _is_user_mark(color) -> bool:
        return color.red() > 180 and 120 < color.green() < 200 and color.blue() < 150

    @staticmethod
    def _is_moonlight(color) -> bool:
        return (
            100 < color.red() < 170
            and 140 < color.green() < 190
            and 180 < color.blue() < 230
        )

    def test_user_arrow_renders_pixels(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.clear_annotations()
        self._pump()
        controller._on_arrow_drawn(0.10, 0.50, 0.40, 0.50)

        hits = self._wait_for_pixels(windows.overlay, self._is_user_mark)
        assert hits > 50, f"用户箭头未渲染到屏幕（暖橙像素 {hits}）"

    def test_target_box_renders_pixels(self, app_and_controller):
        from app.core.protocol import GuideInstruction

        _, controller, _, windows, _ = app_and_controller
        controller._apply_visual_guide(
            GuideInstruction(
                step_id="render-check",
                text="点击这里",
                target={"bounds": (0.30, 0.30, 0.20, 0.10), "confidence": 0.92},
                visual_guide={"action": "click", "mouse_animation": "single_click"},
            )
        )

        hits = self._wait_for_pixels(windows.overlay, self._is_moonlight)
        assert hits > 50, f"目标框/虚拟鼠标未渲染（月光蓝像素 {hits}）"

    def test_cleared_arrow_disappears_from_screen(self, app_and_controller):
        _, controller, _, windows, _ = app_and_controller
        controller.clear_annotations()
        self._pump()
        controller._on_arrow_drawn(0.10, 0.50, 0.40, 0.50)
        assert self._wait_for_pixels(windows.overlay, self._is_user_mark) > 50

        controller.clear_annotations()
        # 清空后必须归零：这里允许重绘延迟，但不允许残留
        after = self._wait_for_absence(windows.overlay, self._is_user_mark)
        assert after == 0, f"清空后画面上仍有箭头（{after} 像素）"

    @classmethod
    def _wait_for_absence(cls, window, predicate, timeout_ms: int = 2000) -> int:
        """等待目标像素消失，返回最终计数。"""
        waited = 0
        hits = cls._count_pixels(window.grabWindow(), predicate)
        while waited < timeout_ms and hits > 0:
            cls._pump(100)
            waited += 100
            hits = cls._count_pixels(window.grabWindow(), predicate)
        return hits
