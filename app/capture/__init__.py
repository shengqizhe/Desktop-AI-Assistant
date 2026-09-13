# -*- coding: utf-8 -*-
"""采集侧模块。

首期只提供协议与固定槽位环形缓存的结构，不启动真实采集（迭代计划 I2）。
"""

from app.capture.protocol import (
    CODECS,
    CaptureCommand,
    CaptureStatus,
    FrameChunk,
    ScreenEvent,
)
from app.capture.ring_buffer import RingBufferSlot, SlotRingBuffer

__all__ = [
    "CODECS",
    "CaptureCommand",
    "CaptureStatus",
    "FrameChunk",
    "ScreenEvent",
    "RingBufferSlot",
    "SlotRingBuffer",
]
