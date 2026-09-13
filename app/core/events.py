# -*- coding: utf-8 -*-
"""版本化事件（UI 与 Core 之间）。

事件与命令都不携带屏幕原始像素，只携带元数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.app_state import AppState
from app.core.session import _now


@dataclass(frozen=True)
class Event:
    """所有事件的基类，带协议版本以便未来迁移。"""

    protocol_version: str = "1.0"
    timestamp: str = field(default_factory=_now)

    @property
    def name(self) -> str:
        return type(self).__name__


@dataclass(frozen=True)
class StateChanged(Event):
    previous: AppState = AppState.INITIALIZING
    current: AppState = AppState.INITIALIZING


@dataclass(frozen=True)
class CaptionAdded(Event):
    message_id: str = ""
    text: str = ""


@dataclass(frozen=True)
class CaptionDismissed(Event):
    message_id: str = ""


@dataclass(frozen=True)
class ArrowPlaced(Event):
    annotation_id: str = ""


@dataclass(frozen=True)
class CaptureStateChanged(Event):
    running: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ProviderFailed(Event):
    stage: str = ""
    reason: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationCompleted(Event):
    step_id: str = ""
    result: str = "uncertain"


__all__ = [
    "Event",
    "StateChanged",
    "CaptionAdded",
    "CaptionDismissed",
    "ArrowPlaced",
    "CaptureStateChanged",
    "ProviderFailed",
    "VerificationCompleted",
]
