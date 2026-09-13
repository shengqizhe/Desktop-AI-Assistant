# -*- coding: utf-8 -*-
"""教程步骤状态机（方案 10.2）。"""

from __future__ import annotations

from enum import Enum

from app.core.protocol import CompletionCheck, GuideInstruction, VerificationResult


class StepState(str, Enum):
    PLANNED = "planned"
    PRESENTING = "presenting"
    WAITING_FOR_USER = "waiting_for_user"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    NEEDS_HELP = "needs_help"
    BLOCKED_BY_RISK = "blocked_by_risk"
    SKIPPED = "skipped"


_ALLOWED: dict[StepState, frozenset[StepState]] = {
    StepState.PLANNED: frozenset({StepState.PRESENTING, StepState.SKIPPED, StepState.BLOCKED_BY_RISK}),
    StepState.PRESENTING: frozenset({StepState.WAITING_FOR_USER, StepState.BLOCKED_BY_RISK}),
    StepState.WAITING_FOR_USER: frozenset(
        {StepState.VERIFYING, StepState.NEEDS_HELP, StepState.BLOCKED_BY_RISK}
    ),
    StepState.VERIFYING: frozenset(
        {
            StepState.SUCCEEDED,
            StepState.NEEDS_HELP,
            StepState.BLOCKED_BY_RISK,
            StepState.SKIPPED,
        }
    ),
    StepState.NEEDS_HELP: frozenset({StepState.PRESENTING, StepState.SKIPPED}),
    StepState.SUCCEEDED: frozenset(),
    StepState.BLOCKED_BY_RISK: frozenset({StepState.PRESENTING, StepState.SKIPPED}),
    StepState.SKIPPED: frozenset(),
}


class TutorialStep:
    """单个教程步骤，携带协议对象与状态。"""

    def __init__(self, instruction: GuideInstruction) -> None:
        self.instruction = instruction
        self.state = StepState.PLANNED
        self.feedback: str | None = None
        self.verification: VerificationResult | None = None

    @property
    def step_id(self) -> str:
        return self.instruction.step_id

    @property
    def requires_confirmation(self) -> bool:
        """高风险步骤不能被普通“完成”按钮跳过（方案 7 阶段 5 验收）。"""
        return self.instruction.risk in {"confirm", "high"}

    @property
    def completion_check(self) -> CompletionCheck:
        return self.instruction.completion_check

    def transition(self, target: StepState) -> StepState:
        if target is self.state:
            return self.state
        if target not in _ALLOWED.get(self.state, frozenset()):
            raise ValueError(f"非法步骤迁移：{self.state.value} -> {target.value}")
        self.state = target
        return self.state


class TutorialStateMachine:
    """多步骤教程：维护步骤列表、当前步与推进规则。

    教程状态独立于字幕可见性与历史窗口开合（方案 10.5 状态约束）。
    """

    def __init__(self, session_id: str = "local-session") -> None:
        self.session_id = session_id
        self._steps: list[TutorialStep] = []
        self._index = -1

    @property
    def steps(self) -> tuple[TutorialStep, ...]:
        return tuple(self._steps)

    @property
    def current(self) -> TutorialStep | None:
        if 0 <= self._index < len(self._steps):
            return self._steps[self._index]
        return None

    @property
    def is_finished(self) -> bool:
        if not self._steps:
            return False
        return all(
            step.state in {StepState.SUCCEEDED, StepState.SKIPPED} for step in self._steps
        )

    @property
    def position(self) -> tuple[int, int]:
        """返回 (当前步序号, 总步数)，用于字幕显示“当前步骤 1/4”。"""
        total = len(self._steps)
        if total == 0 or self._index < 0:
            return (0, total)
        return (self._index + 1, total)

    def load(self, instructions: list[GuideInstruction]) -> TutorialStep | None:
        if not instructions:
            raise ValueError("教程至少需要一个步骤")
        self._steps = [TutorialStep(item) for item in instructions]
        self._index = 0
        self._steps[0].transition(StepState.PRESENTING)
        return self.current

    def animation_finished(self) -> TutorialStep | None:
        step = self.current
        if step is not None and step.state is StepState.PRESENTING:
            step.transition(StepState.WAITING_FOR_USER)
        return self.current

    def report(self, feedback: str) -> TutorialStep | None:
        """用户显式反馈：done / not_done / help。"""
        step = self.current
        if step is None:
            return None
        step.feedback = feedback
        if step.state is StepState.WAITING_FOR_USER:
            if feedback == "help":
                step.transition(StepState.NEEDS_HELP)
            else:
                step.transition(StepState.VERIFYING)
        return self.current

    def resolve(self, succeeded: bool) -> TutorialStep | None:
        """验证结论：进入下一步或留在当前步等待纠正。"""
        step = self.current
        if step is None:
            return None
        if step.state is not StepState.VERIFYING:
            return self.current
        step.transition(StepState.SUCCEEDED if succeeded else StepState.NEEDS_HELP)
        if succeeded:
            return self.advance()
        return self.current

    def advance(self) -> TutorialStep | None:
        if self._index + 1 >= len(self._steps):
            return self.current
        self._index += 1
        step = self.current
        if step is not None and step.state is StepState.PLANNED:
            step.transition(StepState.PRESENTING)
        return self.current

    def skip_current(self) -> TutorialStep | None:
        step = self.current
        if step is not None and step.state not in {StepState.SUCCEEDED, StepState.SKIPPED}:
            step.transition(StepState.BLOCKED_BY_RISK)
            step.transition(StepState.SKIPPED)
        return self.advance()

    def reset(self) -> None:
        self._steps = []
        self._index = -1


__all__ = ["StepState", "TutorialStep", "TutorialStateMachine"]
