# -*- coding: utf-8 -*-
"""上下文构建（方案 5.3 时间窗口策略 / 8.3 输入上下文包）。

只构建最小上下文：当前问题、活动窗口、用户箭头与锁定时间窗口的元数据。
默认不上传完整屏幕，也不包含键盘原文、剪贴板或密码内容。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.protocol import Annotation, PrivacyPolicy, UserQuestion

DEFAULT_LOOKBACK_SECONDS = 60


@dataclass
class ContextWindow:
    """锁定的时间窗口。用户不用等"未来一分钟"采集完成就能得到回答。"""

    start: str = ""
    end: str = ""
    lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS

    def contains(self, timestamp: str) -> bool:
        if not self.start or not self.end:
            return False
        return self.start <= timestamp <= self.end


@dataclass
class ContextPackage:
    """送往 Provider 的最小上下文包。"""

    window: ContextWindow = field(default_factory=ContextWindow)
    active_process: str = ""
    active_title: str = ""
    annotations: list[Annotation] = field(default_factory=list)
    ocr_summary: list[str] = field(default_factory=list)
    event_summary: list[str] = field(default_factory=list)
    frame_count: int = 0
    redacted_count: int = 0
    upload_allowed: bool = False

    def to_payload(self) -> dict[str, Any]:
        """供 Provider 序列化；此处是唯一向外发送的数据出口。"""
        return {
            "window": {
                "start": self.window.start,
                "end": self.window.end,
                "lookback_seconds": self.window.lookback_seconds,
            },
            "active_window": {
                "process": self.active_process,
                "title": self.active_title,
            },
            "annotations": [a.model_dump() for a in self.annotations],
            "ocr_summary": self.ocr_summary,
            "events": self.event_summary,
            "redaction": {
                "frame_count": self.frame_count,
                "redacted_count": self.redacted_count,
                "upload_allowed": self.upload_allowed,
            },
        }

    def describe(self) -> str:
        """给用户看的上下文摘要（上传前预览）。"""
        scope = "允许上传脱敏关键帧" if self.upload_allowed else "仅本地处理"
        return (
            f"{self.window.start} ~ {self.window.end}；"
            f"窗口 {self.active_title or '未识别'}；"
            f"箭头 {len(self.annotations)} 个；{scope}"
        )


def build_context(
    question: UserQuestion,
    window: ContextWindow,
    *,
    frame_count: int = 0,
    redacted_count: int = 0,
    ocr_summary: list[str] | None = None,
    event_summary: list[str] | None = None,
) -> ContextPackage:
    """从问题与时间窗口构建最小上下文包。"""
    policy: PrivacyPolicy = question.privacy_policy
    return ContextPackage(
        window=window,
        active_process=question.active_window.process,
        active_title=question.active_window.title,
        annotations=list(question.annotations),
        ocr_summary=list(ocr_summary or []),
        event_summary=list(event_summary or []),
        frame_count=frame_count,
        redacted_count=redacted_count,
        # 默认不上传；只有用户在隐私面板明确允许时才为 True
        upload_allowed=bool(policy.cloud_upload_allowed),
    )


__all__ = [
    "DEFAULT_LOOKBACK_SECONDS",
    "ContextWindow",
    "ContextPackage",
    "build_context",
]
