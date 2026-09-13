# -*- coding: utf-8 -*-
"""OpenAI-compatible Provider（httpx 实现）。

迁移说明：语义参考 V4.1 ``desktop_pet_fluent.py`` 第 258-732 行的
SSE 解析、vendor 猜测与错误文案，但实现全部重写：
V4.1 用 ``urllib`` 裸解析且无 schema，这里改用 httpx + pydantic，
并补齐超时、取消、大小上限与脱敏日志。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from app.agent.provider import (
    GuideRequest,
    GuideResponse,
    Provider,
    ProviderAuthError,
    ProviderNetworkError,
    ProviderProtocolError,
    ProviderTimeout,
)
from app.core.config import ProviderConfig
from app.core.logging_setup import get_logger, redact

#: 请求体上限，避免把超大上下文发给模型（方案 9.4 Provider 受限）
MAX_REQUEST_BYTES = 8 * 1024 * 1024
#: 响应体上限，防止异常返回撑爆内存
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

#: 常见网关的鉴权错误码
_AUTH_STATUS = {401, 403}


@dataclass
class OpenAICompatibleProvider(Provider):
    """OpenAI Chat Completions 兼容实现。"""

    config: ProviderConfig
    name = "openai-compatible"

    def __post_init__(self) -> None:
        self._cancelled = False
        self._logger = get_logger()

    # ---- 内部工具 ----

    @staticmethod
    def _guess_vendor(base_url: str, model: str) -> str:
        """参考 V4.1 ``_guess_chat_vendor``，仅用于日志与错误文案。"""
        blob = f"{base_url} {model}".lower()
        if "anthropic" in blob or "claude" in blob:
            return "anthropic"
        if "opencode" in blob:
            return "opencode"
        if "deepseek" in blob:
            return "deepseek"
        return "openai"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _payload(self, request: GuideRequest) -> dict[str, object]:
        return {
            "model": self.config.model,
            "messages": request.to_messages(),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

    # ---- Provider 接口 ----

    def complete(self, request: GuideRequest) -> GuideResponse:
        import httpx

        self._cancelled = False
        url = self.config.endpoint()
        payload = self._payload(request)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_REQUEST_BYTES:
            raise ProviderProtocolError(
                f"请求体过大（{len(body)} 字节），已拒绝发送"
            )

        started = time.monotonic()
        try:
            with httpx.Client(
                timeout=httpx.Timeout(float(self.config.timeout_seconds)),
                follow_redirects=False,
            ) as client:
                response = client.post(url, content=body, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(f"请求超时（{self.config.timeout_seconds}s）") from exc
        except httpx.HTTPError as exc:
            raise ProviderNetworkError(f"网络错误：{exc}") from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code in _AUTH_STATUS:
            raise ProviderAuthError(
                f"鉴权失败（HTTP {response.status_code}）：请检查 API Key"
            )
        if response.status_code >= 400:
            snippet = redact(response.text[:400])
            raise ProviderNetworkError(f"HTTP {response.status_code}：{snippet}")

        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ProviderProtocolError("响应体超过大小上限，已丢弃")

        text = self._extract_text(response.content, response.headers.get("content-type", ""))
        return GuideResponse(
            raw_text=text,
            model=self.config.model,
            latency_ms=latency_ms,
            finish_reason="stop",
        )

    @staticmethod
    def _extract_text(content: bytes, content_type: str) -> str:
        """兼容 JSON 与 SSE 两种返回。"""
        blob = content.decode("utf-8", errors="replace")

        if "text/event-stream" in content_type or blob.lstrip().startswith("data:"):
            return _extract_from_sse(blob)

        try:
            data = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise ProviderProtocolError("返回不是合法 JSON") from exc

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderProtocolError("返回缺少 choices 字段")
        message = choices[0].get("message") or {}
        text = message.get("content")
        if isinstance(text, list):
            # 部分网关返回分段内容
            text = "".join(
                part.get("text", "") for part in text if isinstance(part, dict)
            )
        if not isinstance(text, str) or not text.strip():
            raise ProviderProtocolError("返回内容为空")
        return text

    def cancel(self) -> None:
        self._cancelled = True

    def health(self) -> dict[str, object]:
        # 不在这里发网络请求，避免健康检查触发真实调用
        return {
            "name": self.name,
            "ready": bool(self.config.model and self.config.endpoint()),
            "vendor": self._guess_vendor(self.config.base_url, self.config.model),
            # 脱敏：不返回 api_key
            "model": self.config.model,
        }


def _extract_from_sse(blob: str) -> str:
    """从 SSE 流中拼接增量文本。

    对应 V4.1 ``_iter_sse_events`` 的语义，但用显式状态机替代正则。
    """
    chunks: list[str] = []
    for raw_line in blob.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line[len("data:") :].strip()
        if not line or line == "[DONE]":
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        delta = choices[0].get("delta") or {}
        piece = delta.get("content")
        if isinstance(piece, str):
            chunks.append(piece)
    text = "".join(chunks)
    if not text.strip():
        raise ProviderProtocolError("SSE 流中未取到内容")
    return text


def build_provider(config: ProviderConfig) -> Provider:
    """按配置创建 Provider。

    ``use_mock`` 为 True 时返回 Mock。这里不包重试：重试由
    :class:`app.agent.orchestrator.GuideOrchestrator` 统一负责，避免重复退避。
    """
    if config.use_mock:
        from app.agent.mock_provider import MockGuideProvider

        return MockGuideProvider()
    return OpenAICompatibleProvider(config)


__all__ = [
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "OpenAICompatibleProvider",
    "build_provider",
]
