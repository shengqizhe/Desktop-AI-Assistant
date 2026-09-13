# -*- coding: utf-8 -*-
"""编排层：意图 → 上下文 → Provider → 解析 → 校验（方案 5.5 Orchestrator）。

本层不渲染、不执行。产出的 GuideInstruction 一定已通过协议校验。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agent.context_builder import ContextPackage, ContextWindow, build_context
from app.agent.parser import ParseError, parse_guide_payload
from app.agent.prompts import build_system_prompt
from app.agent.provider import GuideRequest, Provider, ProviderError
from app.agent.retry import RetryingProvider
from app.agent.validator import ValidationError, clamp_confidence, validate_instructions
from app.core.logging_setup import get_logger
from app.core.protocol import GuideInstruction, UserQuestion

#: 低于此置信度不播放指向性动画，转为澄清（方案 9.4 / 阶段 4 验收）
CONFIDENCE_FLOOR = 0.6


@dataclass
class GuideOutcome:
    """一次编排的结果。``needs_clarification`` 为 True 时不播放指向动画。"""

    instructions: list[GuideInstruction] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_text: str = ""
    error: str = ""
    attempts: int = 0
    context: ContextPackage | None = None

    @property
    def ok(self) -> bool:
        return bool(self.instructions) and not self.error

    @property
    def best_confidence(self) -> float:
        if not self.instructions:
            return 0.0
        return clamp_confidence(self.instructions[0].target.confidence)


class GuideOrchestrator:
    """把一次提问变成已校验的指导步骤。"""

    def __init__(
        self,
        provider: Provider,
        *,
        retry: bool = True,
        confidence_floor: float = CONFIDENCE_FLOOR,
    ) -> None:
        self._provider = RetryingProvider(provider) if retry else provider
        self._confidence_floor = confidence_floor
        self._logger = get_logger()

    def ask(
        self,
        question: UserQuestion,
        window: ContextWindow | None = None,
        *,
        context: ContextPackage | None = None,
    ) -> GuideOutcome:
        package = context or build_context(
            question, window or ContextWindow()
        )
        request = GuideRequest(
            question=question,
            context=package.to_payload(),
            system_prompt=build_system_prompt(),
        )

        try:
            response = self._provider.complete(request)
        except ProviderError as exc:
            # 网络/超时失败：保留本地缓存与箭头，回到可重试状态
            self._logger.warning("Provider 失败：%s", exc)
            return GuideOutcome(error=str(exc), context=package)
        except Exception as exc:  # 兜底，避免异常穿透到 UI 线程
            self._logger.warning("Provider 异常：%s", exc)
            return GuideOutcome(error=f"模型调用异常：{exc}", context=package)

        try:
            raws = parse_guide_payload(response.raw_text)
        except ParseError as exc:
            self._logger.warning("解析失败：%s", exc)
            return GuideOutcome(error=f"模型返回无法解析：{exc}", context=package)

        if not raws:
            # 模型没有给出步骤：这是澄清信号，不是错误
            return GuideOutcome(
                needs_clarification=True,
                clarification_text="我需要你先圈选或指出关心的区域，才能给出准确指导。",
                context=package,
            )

        try:
            instructions = validate_instructions(raws)
        except ValidationError as exc:
            self._logger.warning("校验失败：%s", exc)
            return GuideOutcome(error=f"模型返回不符合协议：{exc}", context=package)

        first_confidence = clamp_confidence(instructions[0].target.confidence)
        if first_confidence < self._confidence_floor:
            # 低置信度不播放误导性点击动画
            return GuideOutcome(
                instructions=instructions,
                needs_clarification=True,
                clarification_text="我无法可靠定位该控件。请圈选目标，或告诉我按钮上的文字。",
                attempts=getattr(self._provider, "last_attempts", 1),
                context=package,
            )

        return GuideOutcome(
            instructions=instructions,
            attempts=getattr(self._provider, "last_attempts", 1),
            context=package,
        )

    def cancel(self) -> None:
        self._provider.cancel()


__all__ = ["CONFIDENCE_FLOOR", "GuideOutcome", "GuideOrchestrator"]
