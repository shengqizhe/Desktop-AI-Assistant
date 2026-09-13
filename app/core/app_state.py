# -*- coding: utf-8 -*-
"""全局客户端状态机（方案 10.1）。"""

from __future__ import annotations

from enum import Enum


class AppState(str, Enum):
    INITIALIZING = "initializing"
    PRIVACY_SETUP = "privacy_setup"
    MONITORING = "monitoring"
    ARROW_PLACEMENT = "arrow_placement"
    CONTEXT_LOCKING = "context_locking"
    ANALYZING = "analyzing"
    GUIDING = "guiding"
    WAITING_FOR_USER = "waiting_for_user"
    VERIFYING = "verifying"
    CLARIFYING = "clarifying"
    COMPLETED = "completed"
    PRIVACY_PAUSED = "privacy_paused"
    PAUSED = "paused"
    ERROR = "error"


#: 需要暂停能力集中声明：暂停/隐私暂停是全局覆盖，任何状态都应能进入。
_PAUSABLE: frozenset[AppState] = frozenset(
    {
        AppState.MONITORING,
        AppState.ARROW_PLACEMENT,
        AppState.CONTEXT_LOCKING,
        AppState.ANALYZING,
        AppState.GUIDING,
        AppState.WAITING_FOR_USER,
        AppState.VERIFYING,
        AppState.CLARIFYING,
        AppState.COMPLETED,
    }
)

#: 显式迁移表。未列出的迁移会被拒绝，避免状态被静默跳过。
_EXPLICIT: dict[AppState, frozenset[AppState]] = {
    AppState.INITIALIZING: frozenset(
        {AppState.PRIVACY_SETUP, AppState.MONITORING, AppState.ERROR}
    ),
    AppState.PRIVACY_SETUP: frozenset(
        {AppState.MONITORING, AppState.ERROR, AppState.PRIVACY_PAUSED}
    ),
    AppState.MONITORING: frozenset(
        {
            AppState.ARROW_PLACEMENT,
            AppState.CONTEXT_LOCKING,
            AppState.ERROR,
            AppState.PAUSED,
        }
    ),
    AppState.ARROW_PLACEMENT: frozenset(
        {
            AppState.MONITORING,
            AppState.CONTEXT_LOCKING,
            AppState.CLARIFYING,
            AppState.WAITING_FOR_USER,
            AppState.ERROR,
        }
    ),
    AppState.CONTEXT_LOCKING: frozenset({AppState.ANALYZING, AppState.ERROR}),    AppState.ANALYZING: frozenset(
        {AppState.GUIDING, AppState.CLARIFYING, AppState.MONITORING, AppState.ERROR}
    ),
    AppState.GUIDING: frozenset(
        {AppState.WAITING_FOR_USER, AppState.COMPLETED, AppState.CLARIFYING, AppState.ERROR}
    ),
    AppState.WAITING_FOR_USER: frozenset(
        {
            AppState.VERIFYING,
            AppState.ANALYZING,
            AppState.CLARIFYING,
            AppState.ARROW_PLACEMENT,
            AppState.ERROR,
        }
    ),
    AppState.VERIFYING: frozenset(
        {
            AppState.GUIDING,
            AppState.CLARIFYING,
            AppState.COMPLETED,
            AppState.WAITING_FOR_USER,
            AppState.ERROR,
        }
    ),
    AppState.CLARIFYING: frozenset(
        {
            AppState.ANALYZING,
            AppState.WAITING_FOR_USER,
            AppState.ARROW_PLACEMENT,
            AppState.MONITORING,
            AppState.ERROR,
        }
    ),
    AppState.COMPLETED: frozenset({AppState.MONITORING, AppState.ERROR}),
    # 隐私暂停只能恢复到采集中，或进入错误态
    AppState.PRIVACY_PAUSED: frozenset({AppState.MONITORING, AppState.ERROR}),
    AppState.PAUSED: frozenset({AppState.MONITORING, AppState.ERROR}),
    AppState.ERROR: frozenset(
        {AppState.MONITORING, AppState.PRIVACY_SETUP, AppState.PAUSED}
    ),
}

#: 合并全局暂停覆盖
_ALLOWED: dict[AppState, frozenset[AppState]] = {
    state: (targets | ({AppState.PRIVACY_PAUSED} if state in _PAUSABLE else frozenset()))
    for state, targets in _EXPLICIT.items()
}

#: 从暂停恢复到采集前，需要记住的"原状态"。暂停是覆盖层，不破坏原有流程。
RESUME_TARGET: dict[AppState, AppState] = {
    AppState.PRIVACY_PAUSED: AppState.MONITORING,
    AppState.PAUSED: AppState.MONITORING,
}


class AppStateMachine:
    """只做状态迁移与校验，不持有 UI 引用。

    暂停/恢复对用户是全局操作：恢复后统一回到 Monitoring，
    由教程状态机独立保存当前步骤，避免暂停丢失教程进度。
    """

    def __init__(self, initial: AppState = AppState.INITIALIZING) -> None:
        self._state = initial
        self._history: list[AppState] = [initial]
        self._paused_from: AppState | None = None

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def history(self) -> tuple[AppState, ...]:
        return tuple(self._history)

    @property
    def paused_from(self) -> AppState | None:
        """被暂停打断前的状态，用于 UI 提示；不用于自动跳回。"""
        return self._paused_from

    def is_paused(self) -> bool:
        return self._state in {AppState.PRIVACY_PAUSED, AppState.PAUSED}

    def can_transition(self, target: AppState) -> bool:
        if target is self._state:
            return True
        return target in _ALLOWED.get(self._state, frozenset())

    def transition(self, target: AppState) -> AppState:
        if target is self._state:
            return self._state
        if not self.can_transition(target):
            raise ValueError(f"非法状态迁移：{self._state.value} -> {target.value}")
        if target in {AppState.PRIVACY_PAUSED, AppState.PAUSED}:
            self._paused_from = self._state
        elif self._state in {AppState.PRIVACY_PAUSED, AppState.PAUSED}:
            self._paused_from = None
        self._state = target
        self._history.append(target)
        return self._state


__all__ = ["AppState", "AppStateMachine", "RESUME_TARGET"]
