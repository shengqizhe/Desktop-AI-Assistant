# -*- coding: utf-8 -*-
"""Core 层公开接口。

UI 层只依赖这里导出的协议、状态机与配置，不导入 agent/capture 的内部实现。
"""

from app.core.app_state import AppState, AppStateMachine
from app.core.config import (
    AppConfig,
    CaptureConfig,
    HotkeyConfig,
    ProviderConfig,
    UIConfig,
    get_app_data_dir,
    get_config_path,
    load_config,
    save_config,
)
from app.core.events import (
    ArrowPlaced,
    CaptionAdded,
    CaptionDismissed,
    CaptureStateChanged,
    Event,
    ProviderFailed,
    StateChanged,
    VerificationCompleted,
)
from app.core.logging_setup import get_logger, init_logging, redact
from app.core.protocol import (
    MAX_AI_OBJECTS,
    MAX_TEXT_LENGTH,
    MAX_USER_ARROWS,
    PROTOCOL_VERSION,
    Annotation,
    CompletionCheck,
    ContextReady,
    GuideInstruction,
    PrivacyPolicy,
    Target,
    UserQuestion,
    UserStepFeedback,
    VerificationResult,
    VisualGuide,
    validate_unit,
)
from app.core.session import Message, Session
from app.core.tutorial_state import StepState, TutorialStateMachine, TutorialStep

__all__ = [
    "AppState",
    "AppStateMachine",
    "AppConfig",
    "CaptureConfig",
    "HotkeyConfig",
    "ProviderConfig",
    "UIConfig",
    "get_app_data_dir",
    "get_config_path",
    "load_config",
    "save_config",
    "Event",
    "StateChanged",
    "CaptionAdded",
    "CaptionDismissed",
    "ArrowPlaced",
    "CaptureStateChanged",
    "ProviderFailed",
    "VerificationCompleted",
    "get_logger",
    "init_logging",
    "redact",
    "PROTOCOL_VERSION",
    "MAX_TEXT_LENGTH",
    "MAX_USER_ARROWS",
    "MAX_AI_OBJECTS",
    "validate_unit",
    "Annotation",
    "ContextReady",
    "GuideInstruction",
    "PrivacyPolicy",
    "Target",
    "UserQuestion",
    "UserStepFeedback",
    "VerificationResult",
    "VisualGuide",
    "CompletionCheck",
    "Message",
    "Session",
    "StepState",
    "TutorialStateMachine",
    "TutorialStep",
]
