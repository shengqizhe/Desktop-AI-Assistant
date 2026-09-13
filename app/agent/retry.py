# -*- coding: utf-8 -*-
"""分级重试（方案 5.5 Retry）。

网络/超时可重试；协议与鉴权错误不重试，直接进入澄清或离线状态。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.agent.provider import GuideRequest, GuideResponse, Provider, ProviderError


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.6
    max_delay_seconds: float = 4.0

    def delay_for(self, attempt: int) -> float:
        """指数退避，上限封顶。attempt 从 1 开始。"""
        delay = self.base_delay_seconds * (2 ** max(attempt - 1, 0))
        return min(delay, self.max_delay_seconds)


class RetryingProvider:
    """包装任意 Provider，按错误类型决定是否重试。"""

    def __init__(
        self,
        provider: Provider,
        policy: RetryPolicy | None = None,
        sleep=time.sleep,
    ) -> None:
        self._provider = provider
        self._policy = policy or RetryPolicy()
        self._sleep = sleep
        self.last_attempts = 0

    @property
    def name(self) -> str:
        return self._provider.name

    def complete(self, request: GuideRequest) -> GuideResponse:
        last_error: ProviderError | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            self.last_attempts = attempt
            try:
                return self._provider.complete(request)
            except ProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self._policy.max_attempts:
                    raise
                self._sleep(self._policy.delay_for(attempt))
        # 理论上不可达
        raise last_error or ProviderError("重试耗尽")

    def cancel(self) -> None:
        self._provider.cancel()

    def health(self) -> dict[str, object]:
        return self._provider.health()


__all__ = ["RetryPolicy", "RetryingProvider"]
