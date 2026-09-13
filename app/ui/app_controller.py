# -*- coding: utf-8 -*-
"""应用控制器：把窗口、托盘、快捷键、Provider 与状态机串起来。

这里是唯一知道"全部部件"的地方；UI 与 Core 之间只通过协议对象和信号交互。
"""

from __future__ import annotations

from PySide6.QtCore import QMetaObject, QObject, Signal

from app.agent.context_builder import ContextWindow
from app.agent.openai_provider import build_provider
from app.agent.orchestrator import GuideOrchestrator
from app.core.app_state import AppState, AppStateMachine
from app.core.config import AppConfig, save_config
from app.core.logging_setup import get_logger
from app.core.protocol import Annotation, GuideInstruction, UserQuestion
from app.core.session import Message, Session, new_id
from app.core.tutorial_state import StepState, TutorialStateMachine
from app.platform.windows import TrayController
from app.platform.windows.hotkeys import GlobalHotkeys, HotkeyError
from app.ui.window_manager import WindowManager

#: 与设计令牌一致的状态 -> 灵动岛上的可视状态
_ISLAND_STATES = {
    AppState.MONITORING: "monitoring",
    AppState.ARROW_PLACEMENT: "arrow_placement",
    AppState.ANALYZING: "analyzing",
    AppState.CONTEXT_LOCKING: "analyzing",
    AppState.GUIDING: "guiding",
    AppState.WAITING_FOR_USER: "waiting_for_user",
    AppState.VERIFYING: "guiding",
    AppState.CLARIFYING: "waiting_for_user",
    AppState.COMPLETED: "completed",
    AppState.PRIVACY_PAUSED: "privacy_paused",
    AppState.PAUSED: "privacy_paused",
    AppState.ERROR: "error",
    AppState.INITIALIZING: "idle",
    AppState.PRIVACY_SETUP: "idle",
}


class AppController(QObject):
    """应用主控制器。"""

    captionAdded = Signal(str)
    stateChanged = Signal(str)

    def __init__(self, config: AppConfig, windows: WindowManager) -> None:
        super().__init__()
        self._config = config
        self._windows = windows
        self._logger = get_logger()

        self.state = AppStateMachine()
        self.tutorial = TutorialStateMachine()
        self.session = Session()
        self.orchestrator = GuideOrchestrator(build_provider(config.provider))

        self._pending_annotations: list[Annotation] = []
        #: 字幕以 Python 侧列表为唯一真值，避免从 QML var 属性读回 QJSValue
        self._captions: list[dict[str, object]] = []
        #: 覆盖层标注的 Python 侧镜像，同样避免读回 QJSValue
        self._annotations_payload: list[dict[str, object]] = []
        self._arrow_mode = False
        self._capture_paused = False
        self._history_session: Session | None = None

        self.tray = TrayController(self)
        self.hotkeys = GlobalHotkeys()
        self._hotkey_failures: dict[str, str] = {}

    # ---- 启动与退出 ----

    def start(self) -> None:
        self._wire_windows()
        self._wire_tray()
        self._register_hotkeys()
        self._show_desktop_layers()
        self._enter(AppState.MONITORING)
        self.tray.show()
        self._update_capture_labels()

    def _show_desktop_layers(self) -> None:
        """显示常驻层：覆盖层、灵动岛、输入坞。

        覆盖层必须显示——它承载箭头、目标框与虚拟鼠标，靠 Win32
        WS_EX_TRANSPARENT 保持点击穿透，而不是靠隐藏窗口。

        字幕轨只在有消息时出现（方案 4.4.2），历史窗口只在用户点击时出现。
        """
        overlay = self._windows.windows.overlay
        island = self._windows.windows.island
        dock = self._windows.windows.dock
        for window in (overlay, island, dock):
            if window is not None and not window.isVisible():
                window.show()
        self._windows.layout()

    def shutdown(self) -> None:
        """正常退出：先停快捷键与托盘，再保存窗口位置。"""
        try:
            self.hotkeys.unregister_all()
        except Exception:
            pass
        try:
            self.tray.hide()
        except Exception:
            pass
        self._windows.remember_island_position()

    @property
    def hotkey_failures(self) -> dict[str, str]:
        return dict(self._hotkey_failures)

    # ---- 装配 ----

    def _wire_windows(self) -> None:
        island = self._windows.windows.island
        if island is not None:
            island.arrowRequested.connect(lambda: self._toggle_arrow_mode(True))
            island.clearRequested.connect(self.clear_annotations)
            island.pauseToggled.connect(self.toggle_capture)
            island.historyRequested.connect(self.show_history)
            island.settingsRequested.connect(self._open_settings_placeholder)
            island.askRequested.connect(self.focus_prompt)

        dock = self._windows.windows.dock
        if dock is not None:
            dock.submitted.connect(self.ask)
            dock.cancelled.connect(self._cancel_input)

        captions = self._windows.windows.captions
        if captions is not None:
            captions.captionDismissed.connect(self.dismiss_caption)

        overlay = self._windows.windows.overlay
        if overlay is not None:
            overlay.arrowDrawn.connect(self._on_arrow_drawn)

        history = self._windows.windows.history
        if history is not None:
            history.sessionChosen.connect(self._on_history_session_chosen)
            history.messageRevealed.connect(self._on_message_revealed)
            history.closed.connect(self._on_history_closed)

    def _wire_tray(self) -> None:
        self.tray.toggleIslandRequested.connect(self.toggle_island)
        self.tray.toggleCaptureRequested.connect(self.toggle_capture)
        self.tray.historyRequested.connect(self.show_history)
        self.tray.settingsRequested.connect(self._open_settings_placeholder)
        # 退出由 main.py 连接，便于先走 Qt 退出流程

    def _register_hotkeys(self) -> None:
        mapping = {
            self._config.hotkeys.toggle_island: self.toggle_island,
            self._config.hotkeys.focus_prompt: self.focus_prompt,
            self._config.hotkeys.arrow_mode: lambda: self._toggle_arrow_mode(True),
            self._config.hotkeys.toggle_capture: self.toggle_capture,
        }
        self._hotkey_failures = self.hotkeys.register_many(mapping)
        if self._hotkey_failures:
            # 快捷键冲突不阻塞启动，只在界面上提示（方案 17.2.2）
            self._logger.warning("快捷键注册失败：%s", self._hotkey_failures)

    # ---- 状态 ----

    def _enter(self, target: AppState) -> None:
        if self.state.state is target:
            return
        try:
            previous = self.state.state
            self.state.transition(target)
        except ValueError as exc:
            self._logger.warning("状态迁移被拒：%s", exc)
            return
        island_state = _ISLAND_STATES.get(target, "idle")
        island = self._windows.windows.island
        if island is not None:
            island.setProperty("appState", island_state)
        self.stateChanged.emit(island_state)
        self._logger.info("状态 %s -> %s", previous.value, target.value)

    def _resume_after_arrow_mode(self) -> None:
        """退出箭头模式后回到被打断前的流程，而不是无条件回到 Monitoring。"""
        if self.state.is_paused():
            self._enter(AppState.MONITORING)
            return
        if self.tutorial.current is not None:
            self._enter(AppState.WAITING_FOR_USER)
        else:
            self._enter(AppState.MONITORING)

    # ---- 采集占位 ----

    def toggle_capture(self) -> None:
        """暂停/恢复本地采集。

        暂停是全局覆盖：进入 PrivacyPaused，但不清除教程状态与字幕，
        恢复后回到 Monitoring 并保留当前步骤（方案 7 阶段 5 验收）。
        """
        self._capture_paused = not self._capture_paused
        self.tray.set_capture_paused(self._capture_paused)
        self._update_capture_labels()
        if self._capture_paused:
            self._enter(AppState.PRIVACY_PAUSED)
        else:
            self._enter(AppState.MONITORING)

    def _update_capture_labels(self) -> None:
        island = self._windows.windows.island
        if island is None:
            return
        if self._capture_paused:
            island.setProperty("cacheText", "已暂停")
        else:
            seconds = self._config.capture.duration_seconds
            island.setProperty("cacheText", f"本地缓存 {seconds // 60:02d}:{seconds % 60:02d}")

    # ---- 灵动岛 ----

    def toggle_island(self) -> None:
        island = self._windows.windows.island
        if island is None:
            return
        if not island.isVisible():
            island.show()
            self._windows.layout()
            return
        expanded = bool(island.property("expanded"))
        island.setProperty("expanded", not expanded)
        # 展开后尺寸变化，重新贴到顶部中央并保持输入坞跟随
        self._windows.layout()
        self._windows.remember_island_position()

    def focus_prompt(self) -> None:
        island = self._windows.windows.island
        dock = self._windows.windows.dock
        if island is not None and not island.isVisible():
            island.show()
        if dock is not None:
            if not dock.isVisible():
                dock.show()
            self._windows.layout()
            QMetaObject.invokeMethod(dock, "focusInput")

    # ---- 箭头标注 ----

    def _toggle_arrow_mode(self, enabled: bool) -> None:
        """进入/退出箭头放置模式。

        箭头放置与采集暂停是两个独立维度：暂停期间仍可放箭头，
        状态保持 PrivacyPaused 不被改写（方案 10.4 异常状态互不覆盖）。
        """
        overlay = self._windows.windows.overlay
        if overlay is None:
            return
        self._arrow_mode = enabled
        overlay.setProperty("arrowMode", enabled)
        # 只有放置期间临时接管鼠标，放置一次后自动恢复穿透
        self._windows.set_overlay_interactive(enabled)

        if enabled:
            if not self.state.is_paused():
                self._enter(AppState.ARROW_PLACEMENT)
            return

        if self.state.is_paused():
            # 保持暂停，不因放箭头而静默恢复采集
            return
        self._resume_after_arrow_mode()

    def _on_arrow_drawn(self, x1: float, y1: float, x2: float, y2: float) -> None:
        if len(self._pending_annotations) >= 20:
            self._logger.warning("用户箭头已达上限，忽略新箭头")
            self._toggle_arrow_mode(False)
            return

        annotation = Annotation(
            id=new_id("annotation"),
            owner="user",
            start=(x1, y1),
            end=(x2, y2),
            style="arrow",
            color="user-mark",
        )
        self._pending_annotations.append(annotation)
        self._sync_annotations()
        # 放置一次后自动退出拦截（方案 4.5）
        self._toggle_arrow_mode(False)

    def clear_annotations(self) -> None:
        """清空只清除当前用户标注，不影响下层应用、会话与 AI 指导。"""
        self._pending_annotations.clear()
        self._sync_annotations()

    def undo_last_annotation(self) -> None:
        """一次撤销。"""
        if self._pending_annotations:
            self._pending_annotations.pop()
            self._sync_annotations()

    def _sync_annotations(self) -> None:
        overlay = self._windows.windows.overlay
        if overlay is None:
            return
        payload = [
            {
                "id": a.id,
                "owner": a.owner,
                "start": [a.start[0], a.start[1]],
                "end": [a.end[0], a.end[1]],
                "style": a.style,
                "color": a.color,
                "z_index": a.z_index,
                "visible": a.visible,
            }
            for a in self._pending_annotations
        ]
        self._annotations_payload = payload
        overlay.setProperty("annotations", payload)

    # ---- 提问与指导 ----

    def ask(self, text: str) -> None:
        question = text.strip()
        if not question:
            return

        user_message = self.session.add_text(question, role="user", kind="question")
        self.session.question = question
        self._push_caption(user_message)

        island = self._windows.windows.island
        dock = self._windows.windows.dock
        if island is not None:
            island.setProperty("expanded", True)
            self._windows.layout()
        if dock is not None:
            dock.setProperty("submitting", True)
            dock.setProperty("errorText", "")

        self._enter(AppState.CONTEXT_LOCKING)
        try:
            self._enter(AppState.ANALYZING)
            outcome = self.orchestrator.ask(
                UserQuestion(
                    question=question,
                    session_id=self.session.id,
                    annotations=list(self._pending_annotations),
                ),
                ContextWindow(start="", end=""),
            )
        finally:
            if dock is not None:
                dock.setProperty("submitting", False)

        if outcome.error:
            if dock is not None:
                dock.setProperty("errorText", "请求失败，可重试")
            self._push_caption(
                self.session.add_text(outcome.error, role="system", kind="warning")
            )
            self._enter(AppState.ERROR)
            return

        if outcome.needs_clarification and not outcome.instructions:
            self._push_caption(
                self.session.add_text(outcome.clarification_text, kind="analysis")
            )
            self._enter(AppState.CLARIFYING)
            return

        self._present(outcome.instructions, outcome.needs_clarification,
                      outcome.clarification_text)

    def _present(
        self,
        instructions: list[GuideInstruction],
        needs_clarification: bool,
        clarification_text: str,
    ) -> None:
        first = instructions[0]
        self.tutorial.load(instructions)

        self._push_caption(self.session.add_text(first.text, kind="instruction",
                                                 step_id=first.step_id))
        if needs_clarification and clarification_text:
            # 低置信度：显示澄清文字，但不播放指向性动画
            self._push_caption(
                self.session.add_text(clarification_text, kind="warning")
            )
            self._set_step_label("等待你指出目标")
            self._enter(AppState.CLARIFYING)
            return

        self._apply_visual_guide(first)
        self._set_step_label(self._step_label())
        self._enter(AppState.GUIDING)
        self.tutorial.animation_finished()
        self._enter(AppState.WAITING_FOR_USER)

    def _apply_visual_guide(self, instruction: GuideInstruction) -> None:
        overlay = self._windows.windows.overlay
        if overlay is None:
            return
        overlay.setProperty("guideAction", instruction.visual_guide.action)

        bounds = instruction.target.bounds
        if bounds is not None:
            overlay.setProperty(
                "targetBox",
                {
                    "x": bounds[0],
                    "y": bounds[1],
                    "w": bounds[2],
                    "h": bounds[3],
                    "confidence": instruction.target.confidence,
                },
            )
        else:
            overlay.setProperty("targetBox", None)

        if instruction.visual_guide.mouse_animation != "none" and bounds is not None:
            overlay.setProperty(
                "virtualCursor",
                {
                    "x": bounds[0] + bounds[2] / 2,
                    "y": bounds[1] + bounds[3] / 2,
                    "opacity": 1.0,
                    "ripple": instruction.visual_guide.action
                    in {"click", "double_click", "right_click"},
                    "action": instruction.visual_guide.action,
                },
            )

    def _set_step_label(self, text: str) -> None:
        island = self._windows.windows.island
        if island is not None:
            island.setProperty("stepText", text)

    def _step_label(self) -> str:
        current, total = self.tutorial.position
        if total <= 1:
            return ""
        return f"步骤 {current}/{total}"

    def confirm_step(self, succeeded: bool) -> None:
        """用户点击"我完成了"或验证结论回来时推进教程。"""
        step = self.tutorial.current
        if step is None:
            return
        if step.requires_confirmation:
            # 高风险动作不能被普通完成按钮跳过
            self._push_caption(
                self.session.add_text(
                    "这一步涉及不可逆操作，请自行确认后再继续。", kind="warning"
                )
            )
            return
        self.tutorial.report("done" if succeeded else "help")
        self._enter(AppState.VERIFYING)
        self.tutorial.resolve(succeeded)
        current = self.tutorial.current
        if current is None:
            return
        if current.state is StepState.NEEDS_HELP:
            self._push_caption(
                self.session.add_text("没有检测到这一步完成。要我再演示一次吗？",
                                      kind="warning")
            )
            self._enter(AppState.CLARIFYING)
            return
        self._push_caption(
            self.session.add_text(
                f"下一步：{current.instruction.text}", kind="instruction",
                step_id=current.step_id,
            )
        )
        self._apply_visual_guide(current.instruction)
        self._set_step_label(self._step_label())
        self._enter(AppState.GUIDING)
        self.tutorial.animation_finished()
        self._enter(AppState.WAITING_FOR_USER)

    def _cancel_input(self) -> None:
        self._enter(AppState.MONITORING)

    # ---- 字幕轨 ----

    def _push_caption(self, message: Message) -> None:
        captions = self._windows.windows.captions
        if captions is None:
            return
        visible = [c for c in self._captions if c.get("visible", True)]
        # 同时最多显示 6 条，更多消息保留在会话历史
        if len(visible) >= 6:
            visible = visible[-5:]
        visible.append(
            {"id": message.id, "kind": message.kind, "text": message.text,
             "visible": True}
        )
        self._captions = visible
        captions.setProperty("captions", visible)
        if not captions.isVisible():
            captions.show()
            self._windows.layout()
        self.captionAdded.emit(message.id)

    def dismiss_caption(self, message_id: str) -> None:
        """只关闭这一条，不影响教程状态与会话内容。"""
        for message in self.session.messages:
            if message.id == message_id:
                message.dismiss()
                break
        captions = self._windows.windows.captions
        self._captions = [c for c in self._captions if c["id"] != message_id]
        if captions is not None:
            captions.setProperty("captions", self._captions)
            if not self._captions:
                captions.hide()

    # ---- 历史窗口 ----

    def show_history(self) -> None:
        history = self._windows.windows.history
        if history is None:
            return
        history.setProperty("sessions", [self._session_summary(self.session)])
        history.setProperty("currentId", self.session.id)
        history.setProperty(
            "currentMessages",
            [
                {"role": m.role, "kind": m.kind, "text": m.text,
                 "createdAt": m.created_at}
                for m in self.session.messages
            ],
        )
        if not history.isVisible():
            history.show()
        history.raise_()

    def _session_summary(self, session: Session) -> dict[str, object]:
        return {
            "id": session.id,
            "app": session.app_name,
            "question": session.question or session.summary(),
            "updatedAt": session.updated_at[11:16] if len(session.updated_at) >= 16 else "",
            "completed": session.completed,
        }

    def _on_history_session_chosen(self, session_id: str) -> None:
        # 首期只有当前会话：保持窗口打开，不做自动关闭
        if session_id != self.session.id:
            self._logger.info("历史窗口请求了非当前会话：%s", session_id)

    def _on_message_revealed(self, text: str) -> None:
        """把历史消息重新投到字幕轨，不复制成新的历史消息。"""
        for message in self.session.messages:
            if message.text == text:
                message.show()
                self._push_caption(message)
                return
        self._push_caption(Message(text=text, role="ai", kind="instruction"))

    def _on_history_closed(self) -> None:
        # 关闭历史窗口不关闭字幕，也不暂停教程
        self._logger.info("历史窗口已关闭")

    def _open_settings_placeholder(self) -> None:
        # 设置页在后续迭代实现；此处只提示，不静默失败
        self._push_caption(
            self.session.add_text(
                "设置页将在后续迭代提供：缓存时长、隐私范围、模型与快捷键。",
                kind="analysis",
            )
        )

    # ---- 配置 ----

    def persist(self) -> None:
        try:
            save_config(self._config)
        except OSError as exc:
            self._logger.warning("保存配置失败：%s", exc)


__all__ = ["AppController"]
