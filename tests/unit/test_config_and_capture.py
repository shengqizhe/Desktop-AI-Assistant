# -*- coding: utf-8 -*-
"""配置与采集缓存测试（方案 9.1）。"""

from __future__ import annotations

import json

import pytest

from app.capture.protocol import CaptureCommand, FrameChunk, ScreenEvent
from app.capture.ring_buffer import SlotRingBuffer
from app.core.config import (
    AppConfig,
    CaptureConfig,
    ProviderConfig,
    load_config,
    save_config,
)


class TestCaptureConfig:
    def test_defaults_match_plan(self):
        config = CaptureConfig()
        assert config.duration_seconds == 60
        assert config.sample_interval_ms == 1500
        assert config.max_cache_bytes == 128 * 1024 * 1024
        assert config.jpeg_max_edge == 1280
        assert config.jpeg_quality == 55
        assert config.scope == "current_display"

    @pytest.mark.parametrize("duration", [60, 180, 300, 600])
    def test_accepts_allowed_durations(self, duration):
        CaptureConfig(duration_seconds=duration).validate()

    def test_rejects_unsupported_duration(self):
        with pytest.raises(ValueError):
            CaptureConfig(duration_seconds=42).validate()

    def test_rejects_unknown_scope(self):
        with pytest.raises(ValueError):
            CaptureConfig(scope="everything").validate()

    def test_rejects_bad_jpeg_quality(self):
        with pytest.raises(ValueError):
            CaptureConfig(jpeg_quality=0).validate()

    def test_rejects_negative_cache_limit(self):
        with pytest.raises(ValueError):
            CaptureConfig(max_cache_bytes=-1).validate()


class TestConfigPersistence:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        config = AppConfig()
        config.ui.display_positions["DISPLAY1"] = [100, 20]
        config.privacy_setup_done = True
        save_config(config, path)

        loaded = load_config(path)
        assert loaded.privacy_setup_done is True
        assert loaded.ui.display_positions["DISPLAY1"] == [100, 20]

    def test_missing_file_returns_defaults(self, tmp_path):
        loaded = load_config(tmp_path / "nope.json")
        assert loaded.capture.duration_seconds == 60
        assert loaded.privacy_setup_done is False

    def test_corrupt_file_returns_defaults(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{ 这不是 JSON", encoding="utf-8")
        assert load_config(path).capture.duration_seconds == 60

    def test_unknown_keys_are_ignored(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(
            json.dumps({"capture": {"duration_seconds": 180, "future_key": 1}}),
            encoding="utf-8",
        )
        loaded = load_config(path)
        assert loaded.capture.duration_seconds == 180

    def test_atomic_write_leaves_no_tmp(self, tmp_path):
        path = tmp_path / "config.json"
        save_config(AppConfig(), path)
        assert path.exists()
        assert not (tmp_path / "config.json.tmp").exists()


class TestProviderConfig:
    def test_default_mock_is_on(self):
        assert ProviderConfig().use_mock is True

    def test_health_does_not_leak_key(self):
        config = ProviderConfig(api_key="sk-leak-me")
        payload = json.dumps(config.redacted())
        assert "sk-leak-me" not in payload


class TestFrameChunk:
    def test_valid_frame(self):
        frame = FrameChunk(timestamp="2026-09-13T10:00:00Z", screen_id="DISPLAY1",
                           width=1280, height=720)
        assert frame.codec == "jpeg"

    def test_rejects_bad_codec(self):
        with pytest.raises(ValueError):
            FrameChunk(timestamp="t", screen_id="D", width=10, height=10, codec="mp4")

    def test_rejects_non_positive_size(self):
        with pytest.raises(ValueError):
            FrameChunk(timestamp="t", screen_id="D", width=0, height=10)

    def test_event_and_command_defaults(self):
        assert ScreenEvent(kind="lock_screen").protocol_version == "1.0"
        assert CaptureCommand(action="pause").protocol_version == "1.0"


class TestSlotRingBuffer:
    def _frame(self, second: int) -> FrameChunk:
        return FrameChunk(
            timestamp=f"2026-09-13T10:00:{second:02d}Z",
            screen_id="DISPLAY1", width=1280, height=720,
            payload=b"x" * 10,
        )

    def test_writes_round_robin(self):
        ring = SlotRingBuffer(capacity=3)
        for i in range(3):
            ring.write(self._frame(i), hash_key=f"h{i}")
        assert ring.occupied_count == 3

    def test_overwrites_oldest_when_full(self):
        ring = SlotRingBuffer(capacity=2)
        ring.write(self._frame(1), hash_key="h1")
        ring.write(self._frame(2), hash_key="h2")
        ring.write(self._frame(3), hash_key="h3")
        # 容量固定，不会增长
        assert ring.occupied_count == 2
        timestamps = [f.timestamp for f in ring.frames()]
        assert "2026-09-13T10:00:01Z" not in timestamps

    def test_reports_content_change(self):
        ring = SlotRingBuffer(capacity=2)
        slot = ring.write(self._frame(1), hash_key="same")
        assert slot.write(self._frame(1), hash_key="same") is False
        assert slot.write(self._frame(2), hash_key="other") is True

    def test_clear_is_unrecoverable(self):
        ring = SlotRingBuffer(capacity=3)
        ring.write(self._frame(1), hash_key="h1")
        ring.clear()
        assert ring.occupied_count == 0
        assert ring.frames() == []
        assert ring.total_bytes == 0

    def test_evicts_when_over_limit(self):
        ring = SlotRingBuffer(capacity=4, max_bytes=15)
        ring.write(self._frame(1), hash_key="h1")
        ring.write(self._frame(2), hash_key="h2")
        # 每帧 10 字节，超过 15 字节上限后应清理最旧槽位
        assert ring.total_bytes <= 15

    def test_rejects_zero_capacity(self):
        with pytest.raises(ValueError):
            SlotRingBuffer(capacity=0)
