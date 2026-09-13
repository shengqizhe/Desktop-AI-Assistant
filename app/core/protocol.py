# -*- coding: utf-8 -*-
"""版本化数据协议（方案第 6 节、17.4 节）。

所有消息都带 ``protocol_version`` 与 ``session_id``。本模块只做数据校验：
``GuideInstruction.visual_guide.action`` 只描述覆盖层的视觉演示，绝不映射到
真实鼠标、键盘、文件系统或系统命令。
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROTOCOL_VERSION = "1.0"

VISUAL_ACTIONS: frozenset[str] = frozenset(
    {"click", "double_click", "right_click", "drag", "type", "scroll", "arrow"}
)
RISK_LEVELS: frozenset[str] = frozenset({"read_only", "confirm", "high"})
ANNOTATION_OWNERS: frozenset[str] = frozenset({"user", "ai"})
ANNOTATION_STYLES: frozenset[str] = frozenset({"arrow", "highlight", "rectangle"})

MAX_TEXT_LENGTH = 1000
MAX_USER_ARROWS = 20
MAX_AI_OBJECTS = 10
MAX_ANNOTATIONS_PER_MESSAGE = MAX_USER_ARROWS + MAX_AI_OBJECTS


def validate_unit(value: float, name: str) -> float:
    """归一化坐标必须是 0..1 的有限数值，否则拒绝。

    越界或非有限坐标不允许进入渲染层（方案 9.4 安全测试）。
    刻意不接受数字字符串：协议里坐标必须是 JSON number，字符串视为协议违规。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是数值（非字符串/布尔），收到 {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} 必须是有限数值，收到 {number}")
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} 必须在 0..1 之间，收到 {number}")
    return number


class _Message(BaseModel):
    """所有协议消息的公共信封。"""

    model_config = ConfigDict(extra="forbid")

    protocol_version: str = Field(default=PROTOCOL_VERSION, max_length=16)
    session_id: str = Field(default="local-session", min_length=1, max_length=128)


class ActiveWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process: str = Field(default="", max_length=260)
    title: str = Field(default="", max_length=512)


class Annotation(BaseModel):
    """用户箭头或 AI 引导对象（方案 17.2.4）。

    坐标使用相对屏幕的归一化坐标保存，渲染时再映射到物理像素。
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    owner: Literal["user", "ai"] = "user"
    screen_id: str = Field(default="DISPLAY1", max_length=128)
    start: tuple[float, float]
    end: tuple[float, float]
    style: Literal["arrow", "highlight", "rectangle"] = "arrow"
    color: str = Field(default="user-mark", max_length=32)
    z_index: int = Field(default=10, ge=0, le=1000)
    visible: bool = True
    created_at: str = Field(default="", max_length=64)

    @field_validator("start", "end")
    @classmethod
    def _check_points(cls, value: tuple[float, float]) -> tuple[float, float]:
        if len(value) != 2:
            raise ValueError("坐标点必须是二元组")
        return (
            validate_unit(value[0], "x"),
            validate_unit(value[1], "y"),
        )


class PrivacyPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud_upload_allowed: bool = False
    redacted_regions: list[tuple[float, float, float, float]] = Field(default_factory=list)

    @field_validator("redacted_regions")
    @classmethod
    def _check_regions(
        cls, value: list[tuple[float, float, float, float]]
    ) -> list[tuple[float, float, float, float]]:
        checked: list[tuple[float, float, float, float]] = []
        for region in value:
            if len(region) != 4:
                raise ValueError("脱敏区域必须是四元组 (x, y, w, h)")
            checked.append(
                tuple(validate_unit(v, "bounds") for v in region)  # type: ignore[arg-type]
            )
        return checked


class UserQuestion(_Message):
    """用户在输入坞提交的问题（方案 6.1）。"""

    question: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    active_window: ActiveWindow = Field(default_factory=ActiveWindow)
    annotations: list[Annotation] = Field(default_factory=list)
    privacy_policy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)

    @field_validator("question")
    @classmethod
    def _check_question(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("问题内容不能为空")
        return text

    @field_validator("annotations")
    @classmethod
    def _check_annotation_count(cls, value: list[Annotation]) -> list[Annotation]:
        if len(value) > MAX_ANNOTATIONS_PER_MESSAGE:
            raise ValueError(
                f"单次消息标注数量不得超过 {MAX_ANNOTATIONS_PER_MESSAGE}，收到 {len(value)}"
            )
        return value


class RedactionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_count: int = Field(default=0, ge=0)
    redacted_count: int = Field(default=0, ge=0)
    upload_allowed: bool = False


class ContextReady(_Message):
    """锁定时间窗口后构建的最小上下文包（方案 6.2）。"""

    window_start: str = Field(default="", max_length=64)
    window_end: str = Field(default="", max_length=64)
    keyframes: list[dict[str, Any]] = Field(default_factory=list)
    ocr: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    redaction_summary: RedactionSummary = Field(default_factory=RedactionSummary)


class Target(BaseModel):
    """AI 返回的帧内归一化目标（方案 5.7）。"""

    model_config = ConfigDict(extra="forbid")

    screen_id: str = Field(default="", max_length=128)
    frame_timestamp: str = Field(default="", max_length=64)
    bounds: tuple[float, float, float, float] | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("bounds")
    @classmethod
    def _check_bounds(
        cls, value: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if value is None:
            return None
        if len(value) != 4:
            raise ValueError("bounds 必须是四元组 (x, y, w, h)")
        return tuple(validate_unit(v, "bounds") for v in value)  # type: ignore[return-value]


class VisualGuide(BaseModel):
    """只控制视觉演示，不调用鼠标、键盘、文件系统或系统命令。"""

    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "click", "double_click", "right_click", "drag", "type", "scroll", "arrow"
    ] = "arrow"
    show_highlight: bool = True
    show_arrow: bool = True
    mouse_animation: Literal[
        "none", "move", "single_click", "double_click", "right_click", "drag", "scroll"
    ] = "none"


class CompletionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "manual", "screen_change", "screen_change_or_text", "text_appears"
    ] = "manual"
    expected: list[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class GuideInstruction(_Message):
    """AI 返回的单步视觉指导（方案 6.3）。"""

    step_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    target: Target = Field(default_factory=Target)
    visual_guide: VisualGuide = Field(default_factory=VisualGuide)
    completion_check: CompletionCheck = Field(default_factory=CompletionCheck)
    risk: Literal["read_only", "confirm", "high"] = "read_only"

    @field_validator("text")
    @classmethod
    def _check_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("指导文本不能为空")
        return text


class UserStepFeedback(_Message):
    """用户对当前步骤的显式反馈（方案 6.4）。"""

    step_id: str = Field(min_length=1, max_length=128)
    result: Literal["done", "not_done", "help"] = "done"
    note: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    timestamp: str = Field(default="", max_length=64)


class VerificationResult(_Message):
    """系统对步骤完成情况的验证结论（方案 6.4）。"""

    step_id: str = Field(min_length=1, max_length=128)
    result: Literal["succeeded", "failed", "uncertain", "blocked_by_risk", "skipped"] = (
        "uncertain"
    )
    evidence: dict[str, Any] = Field(default_factory=dict)
    next_step_id: str | None = Field(default=None, max_length=128)


__all__ = [
    "PROTOCOL_VERSION",
    "VISUAL_ACTIONS",
    "RISK_LEVELS",
    "ANNOTATION_OWNERS",
    "ANNOTATION_STYLES",
    "MAX_TEXT_LENGTH",
    "MAX_USER_ARROWS",
    "MAX_AI_OBJECTS",
    "validate_unit",
    "ActiveWindow",
    "Annotation",
    "PrivacyPolicy",
    "UserQuestion",
    "RedactionSummary",
    "ContextReady",
    "Target",
    "VisualGuide",
    "CompletionCheck",
    "GuideInstruction",
    "UserStepFeedback",
    "VerificationResult",
]
