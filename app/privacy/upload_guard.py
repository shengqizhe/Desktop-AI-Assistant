# -*- coding: utf-8 -*-
"""上传守卫：决定上下文包能否离开本机（方案 12.1 / 12.2）。

默认不上传。只有用户显式允许，且缓存未被隐私暂停、且存在至少一帧时，
才允许上传脱敏后的关键帧。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.context_builder import ContextPackage


@dataclass(frozen=True)
class UploadDecision:
    allowed: bool
    reason: str = ""


def decide_upload(
    package: ContextPackage,
    *,
    user_allowed: bool,
    capture_paused: bool,
    privacy_paused: bool,
) -> UploadDecision:
    """所有上传前必须经过这里，便于集中审计。"""
    if not user_allowed:
        return UploadDecision(False, "用户未开启云端分析")
    if privacy_paused:
        return UploadDecision(False, "隐私暂停中，不上传任何内容")
    if capture_paused:
        return UploadDecision(False, "采集已暂停，无可上传上下文")
    if package.frame_count <= 0:
        return UploadDecision(False, "当前时间窗口没有可用关键帧")
    if package.redacted_count > package.frame_count:
        return UploadDecision(False, "脱敏计数异常，拒绝上传")
    return UploadDecision(True, "已按策略允许上传脱敏关键帧")


__all__ = ["UploadDecision", "decide_upload"]
