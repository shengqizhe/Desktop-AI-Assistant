# -*- coding: utf-8 -*-
"""固定槽位环形缓存（方案 5.2 / 迭代计划 I2）。

不逐帧创建和删除文件：槽位被新帧直接覆盖，超过时长覆盖最旧帧。
本模块只管理元数据与写入顺序，实际落盘策略由后续 Worker 使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.capture.protocol import FrameChunk


@dataclass
class RingBufferSlot:
    """单个固定槽位。``payload`` 被新帧覆盖，不产生新文件。"""

    index: int
    frame: FrameChunk | None = None
    hash_key: str = ""

    @property
    def occupied(self) -> bool:
        return self.frame is not None

    @property
    def size_bytes(self) -> int:
        return len(self.frame.payload) if self.frame else 0

    def write(self, frame: FrameChunk, hash_key: str) -> bool:
        """写入槽位。返回 True 表示内容有变化（需要实际编码落盘）。"""
        changed = hash_key != self.hash_key
        self.frame = frame
        self.hash_key = hash_key
        return changed

    def clear(self) -> None:
        self.frame = None
        self.hash_key = ""


@dataclass
class SlotRingBuffer:
    """固定的槽位环。写满后从最旧槽位开始覆盖。"""

    capacity: int = 40
    max_bytes: int = 128 * 1024 * 1024
    slots: list[RingBufferSlot] = field(default_factory=list)
    _cursor: int = 0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("槽位数量必须为正数")
        if not self.slots:
            self.slots = [RingBufferSlot(index=i) for i in range(self.capacity)]

    @property
    def occupied_count(self) -> int:
        return sum(1 for slot in self.slots if slot.occupied)

    @property
    def total_bytes(self) -> int:
        return sum(slot.size_bytes for slot in self.slots)

    @property
    def overflowed(self) -> bool:
        return self.total_bytes > self.max_bytes

    def write(self, frame: FrameChunk, hash_key: str) -> RingBufferSlot:
        """写入下一个槽位；环满后覆盖最旧的一个。"""
        slot = self.slots[self._cursor % self.capacity]
        slot.write(frame, hash_key)
        self._cursor += 1
        if self.overflowed:
            self.evict_oldest()
        return slot

    def evict_oldest(self) -> bool:
        """磁盘超上限时清理最旧的非当前槽位。返回是否有槽位被清空。"""
        oldest = min(
            (s for s in self.slots if s.occupied),
            key=lambda s: (s.frame.timestamp if s.frame else ""),
            default=None,
        )
        if oldest is None:
            return False
        oldest.clear()
        return True

    def clear(self) -> None:
        """用户清空缓存：清空后不可从历史恢复。"""
        for slot in self.slots:
            slot.clear()
        self._cursor = 0

    def frames(self) -> list[FrameChunk]:
        """按时间顺序返回已占用的帧。"""
        return [
            slot.frame
            for slot in sorted(
                (s for s in self.slots if s.occupied),
                key=lambda s: (s.frame.timestamp if s.frame else ""),
            )
        ]


__all__ = ["RingBufferSlot", "SlotRingBuffer"]
