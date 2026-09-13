# -*- coding: utf-8 -*-
"""AI Provider 与编排层。

AI 只允许返回视觉指导协议；本层不提供任何可被模型调用的本机函数，
也不执行鼠标、键盘、文件系统或系统命令（方案 5.5 / 8.3）。
"""

from app.agent.mock_provider import MockGuideProvider
from app.agent.orchestrator import GuideOrchestrator
from app.agent.parser import ParseError, parse_guide_payload
from app.agent.provider import (
    GuideRequest,
    GuideResponse,
    Provider,
    ProviderError,
    ProviderTimeout,
)
from app.agent.validator import ValidationError, validate_instructions

__all__ = [
    "MockGuideProvider",
    "GuideOrchestrator",
    "ParseError",
    "parse_guide_payload",
    "GuideRequest",
    "GuideResponse",
    "Provider",
    "ProviderError",
    "ProviderTimeout",
    "ValidationError",
    "validate_instructions",
]
