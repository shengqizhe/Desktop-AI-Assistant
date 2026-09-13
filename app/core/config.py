# -*- coding: utf-8 -*-
"""本地配置读写。

配置固定写在仓库根目录 ``data/config.json``（打包后位于 exe 同级目录），
支持缓存时长、采集范围、快捷键与 Provider 配置。日志与配置都不含 API Key
明文以外的敏感屏幕内容；API Key 单独存放，不写进日志。
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CONFIG_VERSION = 1

#: 采集范围（方案 7.2）：当前显示器 / 当前窗口 / 指定显示器 / 应用白名单
CAPTURE_SCOPES = ("current_display", "current_window", "display", "app_allowlist")


def get_app_data_dir() -> Path:
    """返回持久化数据目录。

    打包后使用 exe 同级目录，实现绿色便携模式；开发时使用仓库根目录。
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[2]
    target = base / "data"
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_config_path() -> Path:
    return get_app_data_dir() / "config.json"


@dataclass
class CaptureConfig:
    """本地屏幕缓存配置（方案 7.2 / 迭代计划 I2）。"""

    enabled: bool = True
    scope: str = "current_display"
    duration_seconds: int = 60
    sample_interval_ms: int = 1500
    max_cache_bytes: int = 128 * 1024 * 1024
    jpeg_max_edge: int = 1280
    jpeg_quality: int = 55

    def validate(self) -> None:
        if self.scope not in CAPTURE_SCOPES:
            raise ValueError(f"不支持的采集范围：{self.scope}")
        if self.duration_seconds not in {60, 180, 300, 600}:
            raise ValueError("缓存时长只能是 60/180/300/600 秒")
        if not 200 <= self.sample_interval_ms <= 10_000:
            raise ValueError("采样间隔必须在 200..10000 毫秒")
        if self.max_cache_bytes <= 0:
            raise ValueError("缓存上限必须为正数")
        if not 320 <= self.jpeg_max_edge <= 3840:
            raise ValueError("JPEG 最长边必须在 320..3840")
        if not 1 <= self.jpeg_quality <= 95:
            raise ValueError("JPEG 质量必须在 1..95")


@dataclass
class HotkeyConfig:
    """全局快捷键（方案 17.2.2）。"""

    toggle_island: str = "Ctrl+Alt+Space"
    focus_prompt: str = "Ctrl+Alt+Q"
    arrow_mode: str = "Ctrl+Alt+A"
    toggle_capture: str = "Ctrl+Alt+P"


@dataclass
class ProviderConfig:
    """OpenAI-compatible Provider（迭代计划第 3 节）。"""

    base_url: str = "https://opencode.ai/zen/v1"
    chat_completions: str = "https://opencode.ai/zen/v1/chat/completions"
    models: str = "https://opencode.ai/zen/v1/models"
    api_key: str = "public"
    model: str = "deepseek-v4-flash-free"
    timeout_seconds: int = 120
    use_mock: bool = True

    def endpoint(self) -> str:
        """允许只配置 base_url，其余按端点拼接。"""
        if self.chat_completions:
            return self.chat_completions
        return self.base_url.rstrip("/") + "/chat/completions"

    def redacted(self) -> dict[str, Any]:
        """用于日志与诊断包导出的脱敏视图。"""
        data = asdict(self)
        data["api_key"] = "***" if self.api_key else ""
        return data


@dataclass
class UIConfig:
    """灵动岛位置按显示器设备 ID 保存，不使用单一绝对坐标。"""

    display_positions: dict[str, list[int]] = field(default_factory=dict)
    island_collapsed: bool = True
    low_performance_mode: bool = False
    reduce_motion: bool = False


@dataclass
class AppConfig:
    version: int = CONFIG_VERSION
    privacy_setup_done: bool = False
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    def validate(self) -> None:
        self.capture.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _merge_dataclass(cls: Any, payload: Any) -> Any:
    """按已知字段合并，忽略未知键，兼容旧版本配置。"""
    if not isinstance(payload, dict):
        return cls()
    known = {f for f in cls.__dataclass_fields__}
    return cls(**{k: v for k, v in payload.items() if k in known})


def load_config(path: Path | None = None) -> AppConfig:
    target = path or get_config_path()
    if not target.exists():
        config = AppConfig()
        config.validate()
        return config
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = AppConfig()
        config.validate()
        return config

    config = AppConfig(
        version=int(raw.get("version", CONFIG_VERSION)),
        privacy_setup_done=bool(raw.get("privacy_setup_done", False)),
        capture=_merge_dataclass(CaptureConfig, raw.get("capture")),
        hotkeys=_merge_dataclass(HotkeyConfig, raw.get("hotkeys")),
        provider=_merge_dataclass(ProviderConfig, raw.get("provider")),
        ui=_merge_dataclass(UIConfig, raw.get("ui")),
    )
    config.validate()
    return config


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    config.validate()
    target = path or get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, target)
    return target


__all__ = [
    "CONFIG_VERSION",
    "CAPTURE_SCOPES",
    "get_app_data_dir",
    "get_config_path",
    "CaptureConfig",
    "HotkeyConfig",
    "ProviderConfig",
    "UIConfig",
    "AppConfig",
    "load_config",
    "save_config",
]
