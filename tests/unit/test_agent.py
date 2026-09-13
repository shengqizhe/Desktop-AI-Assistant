# -*- coding: utf-8 -*-
"""Provider / 解析 / 校验 / 编排测试（方案 9.1、9.2）。"""

from __future__ import annotations

import json

import pytest

from app.agent.mock_provider import MockGuideProvider
from app.agent.openai_provider import _extract_from_sse, build_provider
from app.agent.orchestrator import GuideOrchestrator
from app.agent.parser import ParseError, parse_guide_payload, parse_json
from app.agent.provider import (
    GuideRequest,
    GuideResponse,
    Provider,
    ProviderNetworkError,
    ProviderProtocolError,
)
from app.agent.retry import RetryPolicy, RetryingProvider
from app.agent.validator import ValidationError, clamp_confidence, validate_instructions
from app.core.config import ProviderConfig
from app.core.protocol import UserQuestion


class _ScriptedProvider(Provider):
    """按脚本返回或抛错，用于测试编排与重试。"""

    name = "scripted"

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def complete(self, request: GuideRequest) -> GuideResponse:
        self.calls += 1
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def cancel(self) -> None:
        pass


HIT = json.dumps(
    {
        "steps": [
            {
                "step_id": "unity.console.open-error",
                "text": "请点击 Console 中最上方的红色错误。",
                "target": {"bounds": [0.62, 0.71, 0.18, 0.04], "confidence": 0.91},
                "visual_guide": {"action": "click", "mouse_animation": "single_click"},
                "completion_check": {"type": "screen_change_or_text",
                                     "expected": ["CS1002"]},
                "risk": "read_only",
            }
        ]
    },
    ensure_ascii=False,
)


class TestParser:
    def test_parses_plain_json(self):
        assert parse_json(HIT)["steps"][0]["step_id"] == "unity.console.open-error"

    def test_parses_markdown_fenced_json(self):
        text = f"以下是指导：\n```json\n{HIT}\n```\n希望有帮助。"
        assert parse_json(text)["steps"][0]["step_id"] == "unity.console.open-error"

    def test_parses_json_embedded_in_prose(self):
        text = f"好的，结果是 {HIT} 完成。"
        assert parse_guide_payload(text)

    def test_raises_on_garbage(self):
        with pytest.raises(ParseError):
            parse_json("这不是 JSON")

    def test_normalizes_aliases(self):
        raw = {"instructions": [{"id": "s1", "content": "点击这里", "action": "arrow"}]}
        steps = parse_guide_payload(json.dumps(raw, ensure_ascii=False))
        assert steps[0]["step_id"] == "s1"
        assert steps[0]["text"] == "点击这里"
        assert steps[0]["visual_guide"]["action"] == "arrow"

    def test_normalizes_bare_bounds(self):
        raw = {"steps": [{"step_id": "s1", "text": "点这里", "bounds": [0.1, 0.2, 0.3, 0.4]}]}
        steps = parse_guide_payload(json.dumps(raw, ensure_ascii=False))
        assert steps[0]["target"]["bounds"] == [0.1, 0.2, 0.3, 0.4]

    def test_generates_missing_step_ids(self):
        raw = {"steps": [{"text": "a"}, {"text": "b"}]}
        steps = parse_guide_payload(json.dumps(raw, ensure_ascii=False))
        assert [s["step_id"] for s in steps] == ["step-1", "step-2"]

    def test_empty_steps_means_clarification(self):
        assert parse_guide_payload('{"steps": []}') == []


class TestValidator:
    def test_accepts_valid_step(self):
        steps = parse_guide_payload(HIT)
        instructions = validate_instructions(steps)
        assert instructions[0].target.confidence == 0.91

    def test_rejects_unknown_action(self):
        steps = [{"step_id": "s1", "text": "执行命令", "visual_guide": {"action": "exec"}}]
        with pytest.raises(ValidationError):
            validate_instructions(steps)

    def test_rejects_out_of_range_bounds(self):
        steps = [{"step_id": "s1", "text": "点这里",
                  "target": {"bounds": [0.9, 0.9, 2.0, 0.1]}}]
        with pytest.raises(ValidationError):
            validate_instructions(steps)

    def test_rejects_empty_plan(self):
        with pytest.raises(ValidationError):
            validate_instructions([])

    def test_rejects_extra_unknown_field(self):
        steps = [{"step_id": "s1", "text": "测试", "execute": "rm -rf /"}]
        with pytest.raises(ValidationError):
            validate_instructions(steps)

    def test_clamp_confidence(self):
        assert clamp_confidence(0.5) == 0.5
        assert clamp_confidence(2.0) == 1.0
        assert clamp_confidence(-1) == 0.0
        assert clamp_confidence("abc") == 0.0
        assert clamp_confidence(float("nan")) == 0.0
        assert clamp_confidence(None, default=0.3) == 0.3


class TestRetry:
    def test_retries_retryable_error(self):
        provider = _ScriptedProvider(
            [ProviderNetworkError("网络错误"), GuideResponse(raw_text=HIT)]
        )
        retrying = RetryingProvider(provider, RetryPolicy(max_attempts=3),
                                    sleep=lambda _: None)
        response = retrying.complete(GuideRequest(question=UserQuestion(question="测试")))
        assert response.raw_text == HIT
        assert provider.calls == 2

    def test_does_not_retry_protocol_error(self):
        provider = _ScriptedProvider([ProviderProtocolError("坏 JSON")])
        retrying = RetryingProvider(provider, RetryPolicy(max_attempts=3),
                                    sleep=lambda _: None)
        with pytest.raises(ProviderProtocolError):
            retrying.complete(GuideRequest(question=UserQuestion(question="测试")))
        assert provider.calls == 1

    def test_gives_up_after_max_attempts(self):
        provider = _ScriptedProvider([ProviderNetworkError("x")] * 3)
        retrying = RetryingProvider(provider, RetryPolicy(max_attempts=3),
                                    sleep=lambda _: None)
        with pytest.raises(ProviderNetworkError):
            retrying.complete(GuideRequest(question=UserQuestion(question="测试")))
        assert provider.calls == 3


class TestOrchestrator:
    def _ask(self, provider, question="这个脚本为什么挂不上去？"):
        return GuideOrchestrator(provider).ask(UserQuestion(question=question))

    def test_mock_yields_low_confidence_and_clarification(self):
        outcome = self._ask(MockGuideProvider())
        assert outcome.error == ""
        assert outcome.needs_clarification is True
        assert outcome.best_confidence < 0.6

    def test_high_confidence_produces_instructions(self):
        outcome = self._ask(_ScriptedProvider([GuideResponse(raw_text=HIT)]))
        assert outcome.ok is True
        assert outcome.needs_clarification is False
        assert outcome.instructions[0].step_id == "unity.console.open-error"

    def test_network_error_is_reported_not_raised(self):
        outcome = self._ask(
            _ScriptedProvider([ProviderNetworkError("离线")] * 3)
        )
        assert outcome.error
        assert outcome.instructions == []

    def test_invalid_json_does_not_crash(self):
        outcome = self._ask(_ScriptedProvider([GuideResponse(raw_text="不是 JSON")]))
        assert outcome.error
        assert "解析" in outcome.error

    def test_unknown_action_is_rejected_before_rendering(self):
        bad = json.dumps(
            {"steps": [{"step_id": "s1", "text": "执行", "visual_guide": {"action": "exec"}}]}
        )
        outcome = self._ask(_ScriptedProvider([GuideResponse(raw_text=bad)]))
        assert outcome.error
        assert outcome.instructions == []

    def test_low_confidence_does_not_claim_localisation(self):
        low = json.dumps(
            {
                "steps": [
                    {
                        "step_id": "s1",
                        "text": "可能是这里",
                        "target": {"bounds": [0.1, 0.1, 0.2, 0.2], "confidence": 0.2},
                    }
                ]
            }
        )
        outcome = self._ask(_ScriptedProvider([GuideResponse(raw_text=low)]))
        assert outcome.needs_clarification is True
        assert outcome.clarification_text

    def test_empty_steps_triggers_clarification_not_error(self):
        outcome = self._ask(_ScriptedProvider([GuideResponse(raw_text='{"steps": []}')]))
        assert outcome.error == ""
        assert outcome.needs_clarification is True


class TestOpenAIProvider:
    def test_sse_extraction(self):
        sse = (
            'data: {"choices":[{"delta":{"content":"你好"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"，世界"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        assert _extract_from_sse(sse) == "你好，世界"

    def test_sse_without_content_raises(self):
        with pytest.raises(ProviderProtocolError):
            _extract_from_sse("data: [DONE]\n\n")

    def test_build_provider_returns_mock_when_configured(self):
        config = ProviderConfig()
        assert config.use_mock is True
        assert build_provider(config).name == "mock"

    def test_build_provider_returns_real_when_configured(self):
        config = ProviderConfig(use_mock=False)
        assert build_provider(config).name == "openai-compatible"

    def test_redacted_config_hides_key(self):
        config = ProviderConfig(api_key="sk-secret-value")
        assert config.redacted()["api_key"] == "***"
        assert "sk-secret-value" not in json.dumps(config.redacted())

    def test_endpoint_derived_from_base_url(self):
        config = ProviderConfig(chat_completions="")
        assert config.endpoint() == "https://opencode.ai/zen/v1/chat/completions"
