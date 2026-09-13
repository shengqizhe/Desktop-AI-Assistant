# -*- coding: utf-8 -*-
"""Provider 抽象与错误分类（方案 5.5 职责分离）。

Provider 只负责 HTTP、流式响应、超时、取消、重试，不解析业务语义。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.protocol import UserQuestion


class ProviderError(RuntimeError):
    """Provider 可恢复错误基类。"""

    retryable = True


class ProviderTimeout(ProviderError):
    """超时。"""

    retryable = True


class ProviderNetworkError(ProviderError):
    """网络不可达。"""

    retryable = True


class ProviderProtocolError(ProviderError):
    """返回内容不符合协议。"""

    retryable = False


class ProviderAuthError(ProviderError):
    """鉴权失败。"""

    retryable = False


@dataclass
class GuideRequest:
    """一次指导请求：问题 + 最小上下文。"""

    question: UserQuestion
    context: dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    max_tokens: int = 2000
    temperature: float = 0.2

    def to_messages(self) -> list[dict[str, str]]:
        """构造 OpenAI-compatible 消息体。

        上下文只包含已脱敏的元数据摘要，不含原始屏幕像素、键盘原文或剪贴板。
        """
        import json

        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        payload = {
            "question": self.question.question,
            "active_window": self.question.active_window.model_dump(),
            "annotations": [a.model_dump() for a in self.question.annotations],
            "context": self.context,
        }
        messages.append(
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        )
        return messages


@dataclass
class GuideResponse:
    """Provider 的原始返回。解析与校验由 parser/validator 负责。"""

    raw_text: str
    model: str = ""
    latency_ms: int = 0
    finish_reason: str = ""


class Provider(ABC):
    """所有 Provider 的共同接口。"""

    name = "provider"

    @abstractmethod
    def complete(self, request: GuideRequest) -> GuideResponse:
        """执行一次补全。实现方必须处理超时并把错误转成 ProviderError 子类。"""

    @abstractmethod
    def cancel(self) -> None:
        """取消进行中的请求。"""

    def health(self) -> dict[str, Any]:
        return {"name": self.name, "ready": True}


__all__ = [
    "ProviderError",
    "ProviderTimeout",
    "ProviderNetworkError",
    "ProviderProtocolError",
    "ProviderAuthError",
    "GuideRequest",
    "GuideResponse",
    "Provider",
]
