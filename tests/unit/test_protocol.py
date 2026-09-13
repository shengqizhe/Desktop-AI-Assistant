# -*- coding: utf-8 -*-
"""协议校验测试（方案 9.1 单元测试）。"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.core.protocol import (
    MAX_ANNOTATIONS_PER_MESSAGE,
    Annotation,
    CompletionCheck,
    GuideInstruction,
    Target,
    UserQuestion,
    validate_unit,
)


class TestValidateUnit:
    def test_accepts_bounds(self):
        assert validate_unit(0.0, "x") == 0.0
        assert validate_unit(1.0, "x") == 1.0
        assert validate_unit(0.5, "x") == 0.5

    @pytest.mark.parametrize("value", [-0.01, 1.01, -100, 2])
    def test_rejects_out_of_range(self, value):
        with pytest.raises(ValueError):
            validate_unit(value, "x")

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite(self, value):
        with pytest.raises(ValueError):
            validate_unit(value, "x")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            validate_unit("0.5", "x")


class TestAnnotation:
    def test_valid_annotation(self):
        a = Annotation(id="a1", start=(0.1, 0.2), end=(0.3, 0.4))
        assert a.owner == "user"
        assert a.style == "arrow"

    def test_rejects_out_of_range_points(self):
        with pytest.raises(ValidationError):
            Annotation(id="a1", start=(0.1, 1.5), end=(0.3, 0.4))

    def test_rejects_unknown_owner(self):
        with pytest.raises(ValidationError):
            Annotation(id="a1", owner="robot", start=(0.1, 0.2), end=(0.3, 0.4))


class TestGuideInstruction:
    def test_valid_read_only(self):
        instruction = GuideInstruction(
            step_id="unity.console.open-error",
            text="请点击 Console 中最上方的红色错误。",
            target=Target(bounds=(0.62, 0.71, 0.18, 0.04), confidence=0.91),
            risk="read_only",
        )
        assert instruction.visual_guide.action == "arrow"
        assert instruction.target.confidence == 0.91

    @pytest.mark.parametrize("action", ["click", "double_click", "right_click", "drag",
                                        "type", "scroll", "arrow"])
    def test_accepts_allowed_visual_actions(self, action):
        instruction = GuideInstruction(
            step_id="s1", text="测试", visual_guide={"action": action}
        )
        assert instruction.visual_guide.action == action

    @pytest.mark.parametrize(
        "action", ["exec", "run", "shell", "delete_file", "poweroff", ""]
    )
    def test_rejects_unknown_visual_actions(self, action):
        with pytest.raises(ValidationError):
            GuideInstruction(step_id="s1", text="测试", visual_guide={"action": action})

    def test_rejects_out_of_range_bounds(self):
        with pytest.raises(ValidationError):
            GuideInstruction(
                step_id="s1", text="测试", target={"bounds": (0.5, 0.5, 2.0, 0.1)}
            )

    def test_rejects_empty_text(self):
        with pytest.raises(ValidationError):
            GuideInstruction(step_id="s1", text="   ")

    def test_rejects_overlong_text(self):
        with pytest.raises(ValidationError):
            GuideInstruction(step_id="s1", text="字" * 1001)

    def test_rejects_non_finite_confidence(self):
        with pytest.raises(ValidationError):
            GuideInstruction(
                step_id="s1", text="测试", target={"confidence": float("nan")}
            )

    def test_rejects_unknown_risk(self):
        with pytest.raises(ValidationError):
            GuideInstruction(step_id="s1", text="测试", risk="whatever")

    def test_rejects_extra_fields(self):
        """未知字段必须被拒，避免模型注入额外指令字段。"""
        with pytest.raises(ValidationError):
            GuideInstruction(
                step_id="s1", text="测试", execute_command="rm -rf /"
            )


class TestUserQuestion:
    def test_valid(self):
        q = UserQuestion(question="为什么这个脚本挂不上去？")
        assert q.privacy_policy.cloud_upload_allowed is False

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            UserQuestion(question="   ")

    def test_rejects_too_many_annotations(self):
        annotations = [
            Annotation(id=f"a{i}", start=(0.1, 0.1), end=(0.2, 0.2))
            for i in range(MAX_ANNOTATIONS_PER_MESSAGE + 1)
        ]
        with pytest.raises(ValidationError):
            UserQuestion(question="测试", annotations=annotations)

    def test_default_upload_not_allowed(self):
        """默认不上传：隐私默认值必须是 False（方案 17.1）。"""
        assert UserQuestion(question="测试").privacy_policy.cloud_upload_allowed is False


class TestCompletionCheck:
    def test_defaults_to_manual(self):
        assert CompletionCheck().type == "manual"

    def test_rejects_bad_threshold(self):
        with pytest.raises(ValidationError):
            CompletionCheck(confidence_threshold=1.5)


def test_no_nan_leaks_into_protocol():
    """确保没有任何路径能让 NaN 进入渲染层。"""
    with pytest.raises(ValidationError):
        Target(bounds=(math.nan, 0.1, 0.2, 0.2))
