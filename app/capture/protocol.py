# -*- coding: utf-8 -*-
"""Capture Worker 通信协议（方案 5.2 / 11.1.1 性能替换边界）。

首期用 Python 实现；后期替换为原生 Worker 时协议不变，因此
灵动岛、AI Agent 与知识库都不需要改动。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PROTOCOL_VERSION = "1.0"

CODECS = ("jpeg", "webp", "raw")


@dataclass(frozen=True)
class FrameChunk:
    """一个屏幕帧。payload 为编码后的字节，不在此处解释。"""

    timestamp: str
    screen_id: str
    width: int
    height: int
    codec: str = "jpeg"
    payload: bytes = b""
    protocol_version: str = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if self.codec not in CODECS:
            raise ValueError(f"不支持的编码：{self.codec}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("帧尺寸必须为正数")


@dataclass(frozen=True)
class ScreenEvent:
    """屏幕/窗口状态变化，用于让上层决定暂停或重新定位。"""

    kind: Literal[
        "window_changed",
        "privacy_detected",
        "display_changed",
        "lock_screen",
        "uac_prompt",
        "remote_desktop",
    ]
    detail: str = ""
    timestamp: str = ""
    protocol_version: str = PROTOCOL_VERSION


@dataclass(frozen=True)
class CaptureCommand:
    """客户端 -> Worker 的命令。"""

    action: Literal["start", "pause", "set_duration", "set_scope", "clear", "stop"]
    value: str = ""
    protocol_version: str = PROTOCOL_VERSION


@dataclass
class CaptureStatus:
    """Worker 上报的运行状态。"""

    running: bool = False
    paused_reason: str = ""
    duration_seconds: int = 60
    scope: str = "current_display"
    frame_count: int = 0
    cache_bytes: int = 0
    dropped_frames: int = 0
    last_error: str = ""


__all__ = [
    "PROTOCOL_VERSION",
    "CODECS",
    "FrameChunk",
    "ScreenEvent",
    "CaptureCommand",
    "CaptureStatus",
]
