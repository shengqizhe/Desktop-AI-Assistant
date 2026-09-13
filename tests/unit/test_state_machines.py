# -*- coding: utf-8 -*-
"""状态机测试（方案 17.10：每个状态的进入、退出、取消和恢复都要有测试）。"""

from __future__ import annotations

import pytest

from app.core.app_state import AppState, AppStateMachine
from app.core.protocol import GuideInstruction
from app.core.tutorial_state import StepState, TutorialStateMachine


class TestAppStateMachine:
    def test_starts_initializing(self):
        assert AppStateMachine().state is AppState.INITIALIZING

    def test_normal_boot_flow(self):
        sm = AppStateMachine()
        sm.transition(AppState.PRIVACY_SETUP)
        sm.transition(AppState.MONITORING)
        assert sm.state is AppState.MONITORING

    def test_rejects_illegal_transition(self):
        sm = AppStateMachine()
        with pytest.raises(ValueError):
            sm.transition(AppState.GUIDING)

    def test_full_guidance_flow(self):
        sm = AppStateMachine()
        for state in (
            AppState.PRIVACY_SETUP,
            AppState.MONITORING,
            AppState.CONTEXT_LOCKING,
            AppState.ANALYZING,
            AppState.GUIDING,
            AppState.WAITING_FOR_USER,
            AppState.VERIFYING,
            AppState.COMPLETED,
        ):
            sm.transition(state)
        assert sm.state is AppState.COMPLETED

    @pytest.mark.parametrize(
        "state",
        [
            AppState.MONITORING,
            AppState.ARROW_PLACEMENT,
            AppState.ANALYZING,
            AppState.GUIDING,
            AppState.WAITING_FOR_USER,
            AppState.CLARIFYING,
            AppState.COMPLETED,
        ],
    )
    def test_pause_reachable_from_active_states(self, state):
        """暂停是全局覆盖，任何活跃状态都应能进入暂停。"""
        sm = AppStateMachine()
        _force_state(sm, state)
        sm.transition(AppState.PRIVACY_PAUSED)
        assert sm.state is AppState.PRIVACY_PAUSED
        assert sm.paused_from is state

    def test_resume_returns_to_monitoring(self):
        sm = AppStateMachine()
        _force_state(sm, AppState.WAITING_FOR_USER)
        sm.transition(AppState.PRIVACY_PAUSED)
        sm.transition(AppState.MONITORING)
        assert sm.state is AppState.MONITORING
        assert sm.paused_from is None

    def test_paused_state_is_recognised(self):
        sm = AppStateMachine()
        _force_state(sm, AppState.MONITORING)
        sm.transition(AppState.PRIVACY_PAUSED)
        assert sm.is_paused()

    def test_self_transition_is_noop(self):
        sm = AppStateMachine()
        assert sm.transition(AppState.INITIALIZING) is AppState.INITIALIZING
        assert len(sm.history) == 1

    def test_history_records_path(self):
        sm = AppStateMachine()
        sm.transition(AppState.PRIVACY_SETUP)
        sm.transition(AppState.MONITORING)
        assert sm.history == (
            AppState.INITIALIZING,
            AppState.PRIVACY_SETUP,
            AppState.MONITORING,
        )


def _force_state(sm: AppStateMachine, target: AppState) -> None:
    """测试辅助：绕过业务顺序直接把状态机置于目标状态。"""
    sm._state = target  # noqa: SLF001 - 测试需要构造前置条件


class TestTutorialStateMachine:
    def _instructions(self, count: int = 3) -> list[GuideInstruction]:
        return [
            GuideInstruction(step_id=f"step-{i}", text=f"第 {i} 步")
            for i in range(1, count + 1)
        ]

    def test_load_presents_first_step(self):
        sm = TutorialStateMachine()
        step = sm.load(self._instructions())
        assert step is not None
        assert step.state is StepState.PRESENTING
        assert sm.position == (1, 3)

    def test_rejects_empty_plan(self):
        with pytest.raises(ValueError):
            TutorialStateMachine().load([])

    def test_animation_finished_moves_to_waiting(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        step = sm.animation_finished()
        assert step is not None and step.state is StepState.WAITING_FOR_USER

    def test_success_advances_to_next_step(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        sm.animation_finished()
        sm.report("done")
        assert sm.current is not None and sm.current.state is StepState.VERIFYING
        sm.resolve(True)
        assert sm.current is not None
        assert sm.current.step_id == "step-2"
        assert sm.position == (2, 3)

    def test_failure_keeps_current_step_for_correction(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        sm.animation_finished()
        sm.report("not_done")
        sm.resolve(False)
        assert sm.current is not None
        assert sm.current.step_id == "step-1"
        assert sm.current.state is StepState.NEEDS_HELP

    def test_help_moves_to_needs_help(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        sm.animation_finished()
        sm.report("help")
        assert sm.current is not None and sm.current.state is StepState.NEEDS_HELP

    def test_completes_after_last_step(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions(2))
        for _ in range(2):
            sm.animation_finished()
            sm.report("done")
            sm.resolve(True)
        assert sm.is_finished

    def test_high_risk_step_requires_confirmation(self):
        sm = TutorialStateMachine()
        sm.load(
            [
                GuideInstruction(step_id="s1", text="删除该文件", risk="confirm"),
            ]
        )
        assert sm.current is not None
        assert sm.current.requires_confirmation is True

    def test_skip_marks_step_skipped(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions(2))
        sm.skip_current()
        assert sm.steps[0].state is StepState.SKIPPED
        assert sm.current is not None and sm.current.step_id == "step-2"

    def test_reset_clears_steps(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        sm.reset()
        assert sm.current is None
        assert sm.steps == ()
        assert sm.position == (0, 0)

    def test_illegal_step_transition_rejected(self):
        sm = TutorialStateMachine()
        sm.load(self._instructions())
        with pytest.raises(ValueError):
            sm.steps[0].transition(StepState.SUCCEEDED)
