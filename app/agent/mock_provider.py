# -*- coding: utf-8 -*-
"""Mock Provider：不联网、不执行真实操作（迭代计划 I0）。

返回低置信度提示，明确要求用户圈选或指出目标，不假装已完成视觉定位。
"""

from __future__ import annotations

import json

from app.agent.provider import GuideRequest, GuideResponse, Provider


class MockGuideProvider(Provider):
    """确定性返回，便于离线测试 UI 与协议通路。"""

    name = "mock"

    def __init__(self, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms
        self._cancelled = False

    def complete(self, request: GuideRequest) -> GuideResponse:
        self._cancelled = False
        question = request.question.question.strip() or "请先描述你卡住的地方。"

        # 目标置信度低于阈值时，协议要求主动澄清而不是猜测坐标
        payload = {
            "steps": [
                {
                    "step_id": "mock.locate-target",
                    "text": f"我收到：{question}。请圈选或指出你想操作的区域，我先确认目标位置。",
                    "target": {"confidence": 0.35},
                    "visual_guide": {
                        "action": "arrow",
                        "show_highlight": False,
                        "show_arrow": True,
                        "mouse_animation": "none",
                    },
                    "completion_check": {"type": "manual", "confidence_threshold": 0.8},
                    "risk": "read_only",
                }
            ]
        }
        return GuideResponse(
            raw_text=json.dumps(payload, ensure_ascii=False),
            model="mock",
            latency_ms=self._latency_ms,
            finish_reason="stop",
        )

    def cancel(self) -> None:
        self._cancelled = True

    def health(self) -> dict[str, object]:
        return {"name": self.name, "ready": True, "offline": True}


__all__ = ["MockGuideProvider"]
