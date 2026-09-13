# -*- coding: utf-8 -*-
"""安全隔离守卫（方案 8.3 / 9.4）。

这些测试的作用是防止旧执行型链路被重新引入 Coach 主线：
一旦有人把 launch_app/taskkill/subprocess 接回指导路径，测试立即失败。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"

#: 绝不允许出现在 app/ 下的危险调用
FORBIDDEN_CALLS = (
    "launch_app",
    "close_app",
    "taskkill",
    "os.system",
    "os.popen",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "shutil.rmtree",
    "ctypes.windll.user32.SetCursorPos",
    "pyautogui.click",
)

#: app_launcher.py 是保留的旧执行模块，不参与 Coach 主线，单独豁免
EXEMPT_FILES = {"app_launcher.py"}

#: 允许出现 subprocess 的模块（仅打包/启动脚本，不在 app/ 内）
ALLOWED_PATTERNS = (
    # 生成文档字符串中提及的危险动作不算违规
    r"^\s*#",
    r"^\s*\"\"\"",
    r"^\s*\*",
)


def _iter_python_files() -> list[Path]:
    return [p for p in APP_DIR.rglob("*.py") if p.name not in EXEMPT_FILES]


def test_app_dir_exists():
    assert APP_DIR.is_dir(), f"未找到 app 目录：{APP_DIR}"


def test_no_forbidden_direct_calls():
    """app/ 下不得直接调用执行型 API。"""
    offenders: list[str] = []
    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for call in FORBIDDEN_CALLS:
                if call in line and not _is_within_string(source, line):
                    offenders.append(f"{path.relative_to(APP_DIR)}:{lineno} -> {call}")
    assert not offenders, "发现执行型调用进入 Coach 主线：\n" + "\n".join(offenders)


def _is_within_string(source: str, line: str) -> bool:
    """粗判该行是否只是文档/注释里的提及。"""
    return line.strip().startswith(('"""', "'''", "#", "*"))


def test_no_import_of_app_launcher():
    """app/ 下任何模块都不得导入被隔离的 app_launcher。"""
    offenders: list[str] = []
    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app_launcher" or alias.name.startswith("app_launcher."):
                        offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "app_launcher" or module.startswith("app_launcher."):
                    offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno}")
    assert not offenders, f"app_launcher 不得被导入：{offenders}"


def test_no_real_mouse_or_keyboard_control():
    """不得引入真实的鼠标/键盘控制库。"""
    forbidden_modules = {"pyautogui", "pynput", "keyboard", "wxautox", "win32api"}
    offenders: list[str] = []
    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_modules:
                        offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno} {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in forbidden_modules:
                    offenders.append(f"{path.relative_to(APP_DIR)}:{node.lineno} {node.module}")
    assert not offenders, f"发现真实输入控制库：{offenders}"


def test_prompts_do_not_grant_tool_calls():
    """系统提示词必须保持"无工具调用"约束。"""
    from app.agent.prompts import SYSTEM_PROMPT

    assert "不执行" in SYSTEM_PROMPT or "绝不能" in SYSTEM_PROMPT
    lowered = SYSTEM_PROMPT.lower()
    for dangerous in ("launch_app", "taskkill", "subprocess", "os.system"):
        assert dangerous not in lowered, f"提示词中不应出现 {dangerous}"


def test_visual_actions_stay_within_whitelist():
    """视觉动作白名单不允许包含执行类动作。"""
    from app.core.protocol import VISUAL_ACTIONS

    assert VISUAL_ACTIONS == {
        "click",
        "double_click",
        "right_click",
        "drag",
        "type",
        "scroll",
        "arrow",
    }
    for bad in ("exec", "run", "shell", "delete", "command", "launch"):
        assert bad not in VISUAL_ACTIONS


def test_default_config_blocks_cloud_upload():
    """默认配置必须禁止上传（方案 17.1 首期冻结）。"""
    from app.core.config import ProviderConfig, load_config

    assert ProviderConfig().use_mock is True
    from app.core.protocol import UserQuestion

    assert UserQuestion(question="测试").privacy_policy.cloud_upload_allowed is False


def test_redaction_masks_secrets():
    """日志脱敏不得泄漏 API Key。"""
    from app.core.logging_setup import redact

    text = "Authorization: Bearer sk-abcdef1234567890 failed"
    cleaned = redact(text)
    assert "sk-abcdef1234567890" not in cleaned
    assert "***" in cleaned

    url = "https://user:secret@example.com/v1/chat"
    assert "secret" not in redact(url)


def test_privacy_blocks_known_blacklist_processes():
    from app.privacy import should_pause_capture

    pause, reason = should_pause_capture("LogonUI.exe", "登录")
    assert pause is True and reason

    pause, _ = should_pause_capture("notepad.exe", "无标题 - 记事本")
    assert pause is False


def test_privacy_blocks_sensitive_titles():
    from app.privacy import should_pause_capture

    pause, reason = should_pause_capture("chrome.exe", "登录 - 请输入密码")
    assert pause is True and reason


def test_upload_guard_blocks_by_default():
    from app.agent.context_builder import ContextWindow, build_context
    from app.core.protocol import UserQuestion
    from app.privacy import decide_upload

    package = build_context(UserQuestion(question="测试"), ContextWindow())
    decision = decide_upload(package, user_allowed=False, capture_paused=False,
                             privacy_paused=False)
    assert decision.allowed is False

    decision = decide_upload(package, user_allowed=True, capture_paused=False,
                            privacy_paused=True)
    assert decision.allowed is False
