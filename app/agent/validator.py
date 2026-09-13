# -*- coding: utf-8 -*-
"""校验层：只放行协议内的字段、动作、风险与坐标（方案 5.5 Validator）。

这是安全边界：非法 JSON、未知动作、越界坐标都必须在这里被拒绝，
不能进入渲染层（方案 9.4 安全测试）。
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.core.protocol import (
    MAX_AI_OBJECTS,
    VISUAL_ACTIONS,
    GuideInstruction,
)


class ValidationError(ValueError):
    """模型返回通过了解析但未通过协议校验。"""


def validate_instruction(raw: dict[str, Any]) -> GuideInstruction:
    """校验单步指令。"""
    action = ""
    visual = raw.get("visual_guide")
    if isinstance(visual, dict):
        action = str(visual.get("action", ""))
    if action and action not in VISUAL_ACTIONS:
        raise ValidationError(f"未知视觉动作：{action}")

    try:
        instruction = GuideInstruction.model_validate(raw)
    except PydanticValidationError as exc:
        raise ValidationError(f"指导字段不合法：{exc.errors()[0].get('msg', '')}") from exc

    # 越界或非有限坐标已在模型层被拒；这里再兜一层风险等级
    if instruction.risk not in {"read_only", "confirm", "high"}:
        raise ValidationError(f"未知风险等级：{instruction.risk}")
    return instruction


def validate_instructions(raws: list[dict[str, Any]]) -> list[GuideInstruction]:
    """校验多步。单步失败不静默丢弃，而是整体报错，避免播放半套教程。"""
    if not raws:
        raise ValidationError("模型未返回任何可执行步骤")
    if len(raws) > MAX_AI_OBJECTS * 3:
        raise ValidationError(f"步骤数量异常：{len(raws)}")
    return [validate_instruction(raw) for raw in raws]


def clamp_confidence(value: Any, default: float = 0.0) -> float:
    """低置信度澄清逻辑使用；非数值一律按 0 处理，不猜测。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return min(max(number, 0.0), 1.0)


__all__ = ["ValidationError", "validate_instruction", "validate_instructions", "clamp_confidence"]
