# -*- coding: utf-8 -*-
"""会话与消息模型（方案 4.4.4）。

字幕可见性、教程状态和历史持久化彼此独立：关掉字幕不等于删除消息，
关闭历史窗口不等于结束教程。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


MESSAGE_ROLES = ("user", "ai", "system")
MESSAGE_KINDS = ("question", "analysis", "instruction", "progress", "warning", "complete")


@dataclass
class Message:
    """一条会话消息，可映射为字幕轨上的一条字幕。"""

    text: str
    role: str = "ai"
    kind: str = "instruction"
    id: str = field(default_factory=lambda: new_id("message"))
    session_id: str = "local-session"
    step_id: str | None = None
    visible: bool = True
    pinned: bool = False
    created_at: str = field(default_factory=_now)
    dismissed_at: str | None = None
    knowledge_refs: list[str] = field(default_factory=list)

    def dismiss(self) -> None:
        """只改变可见性，不删除会话内容。"""
        self.visible = False
        self.dismissed_at = _now()

    def show(self) -> None:
        self.visible = True
        self.dismissed_at = None


@dataclass
class Session:
    """一次指导会话。"""

    id: str = field(default_factory=lambda: new_id("session"))
    title: str = ""
    app_name: str = ""
    question: str = ""
    completed: bool = False
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def add(self, message: Message) -> Message:
        message.session_id = self.id
        self.messages.append(message)
        self.updated_at = _now()
        return message

    def add_text(self, text: str, role: str = "ai", kind: str = "instruction", **kw) -> Message:
        return self.add(Message(text=text, role=role, kind=kind, **kw))

    @property
    def visible_messages(self) -> list[Message]:
        return [m for m in self.messages if m.visible]

    def summary(self) -> str:
        if self.title:
            return self.title
        if self.question:
            return self.question[:24]
        return "未命名会话"


__all__ = [
    "MESSAGE_ROLES",
    "MESSAGE_KINDS",
    "Message",
    "Session",
    "new_id",
    "dismiss",
]
