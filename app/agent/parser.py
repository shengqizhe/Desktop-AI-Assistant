# -*- coding: utf-8 -*-
"""解析层：把模型返回的 JSON / Markdown-JSON 转成 dict（方案 5.5 Parser）。

V4.1 的 ``_parse_openai_compatible_text`` 用正则抠字符串，没有 schema；
这里只负责"取出可解析的 JSON"，字段合法性交给 validator。
"""

from __future__ import annotations

import json
import re
from typing import Any


class ParseError(ValueError):
    """无法从返回文本中取得合法 JSON。"""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_noise(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("\ufeff"):
        cleaned = cleaned[1:]
    return cleaned


def _candidates(text: str) -> list[str]:
    """按可信度排列候选 JSON 片段。"""
    cleaned = _strip_noise(text)
    out: list[str] = []

    for match in _FENCE_RE.finditer(cleaned):
        body = match.group(1).strip()
        if body:
            out.append(body)

    if cleaned:
        out.append(cleaned)

    # 退一步：截取第一个 { 到最后一个 }
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last > first:
        snippet = cleaned[first : last + 1]
        if snippet not in out:
            out.append(snippet)

    return out


def parse_json(text: str) -> dict[str, Any]:
    """取出一个 JSON 对象；失败抛 :class:`ParseError`。"""
    for candidate in _candidates(text):
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # 允许模型直接返回指令数组
            return {"steps": data}
    raise ParseError("模型返回中未找到合法 JSON 对象")


#: 兼容字段别名，减少因模型措辞不同导致的失败
_ALIASES: dict[str, str] = {
    "guide": "steps",
    "instructions": "steps",
    "plan": "steps",
    "text": "text",
    "content": "text",
    "message": "text",
    "step_id": "step_id",
    "id": "step_id",
    "action": "action",
    "confidence": "confidence",
    "completion": "completion_check",
    "risk": "risk",
}


def _normalize_step(raw: dict[str, Any]) -> dict[str, Any]:
    """把单步指令归一化成 GuideInstruction 的字段名。"""
    step: dict[str, Any] = {}
    for key, value in raw.items():
        target_key = _ALIASES.get(str(key).strip().lower(), str(key).strip())
        step[target_key] = value

    # visual_guide：允许 action/show_* 平铺在顶层
    visual = step.get("visual_guide")
    if not isinstance(visual, dict):
        visual = {}
        for name in ("action", "show_highlight", "show_arrow", "mouse_animation"):
            if name in step:
                visual[name] = step.pop(name)
        step["visual_guide"] = visual

    # target：允许直接给 bounds
    target = step.get("target")
    if not isinstance(target, dict):
        target = {}
        if "bounds" in step:
            target["bounds"] = step.pop("bounds")
        step["target"] = target

    return step


def parse_guide_payload(text: str) -> list[dict[str, Any]]:
    """解析出待校验的步骤字典列表。

    返回空列表表示模型明确表示"无法定位"，调用方应进入澄清流程。
    """
    data = parse_json(text)

    # 顶层别名：模型常把 steps 写成 instructions/guide/plan
    for alias in ("instructions", "guide", "plan"):
        if alias in data and "steps" not in data:
            data = {**data, "steps": data[alias]}
            break

    steps_raw = data.get("steps")
    if steps_raw is None:
        # 单步返回：整个对象就是一步
        if "text" in data and ("step_id" in data or "action" in data):
            steps_raw = [data]
        else:
            return []

    if isinstance(steps_raw, dict):
        steps_raw = [steps_raw]
    if not isinstance(steps_raw, list):
        raise ParseError("steps 字段必须是数组")

    steps: list[dict[str, Any]] = []
    for index, raw in enumerate(steps_raw):
        if not isinstance(raw, dict):
            continue
        step = _normalize_step(raw)
        step.setdefault("step_id", f"step-{index + 1}")
        steps.append(step)
    return steps


__all__ = ["ParseError", "parse_json", "parse_guide_payload"]
