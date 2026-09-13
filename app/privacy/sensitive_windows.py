# -*- coding: utf-8 -*-
"""隐私策略：黑名单、敏感窗口与上传守卫（方案 5.3 / 12 节）。

首期只实现判定逻辑，不做实际遮罩；判定结果决定帧是否进入缓存与上下文包。
"""

from __future__ import annotations

import re

#: 默认黑名单：密码管理器、系统安全界面、远程桌面客户端
DEFAULT_PROCESS_BLACKLIST: tuple[str, ...] = (
    "keepass.exe",
    "1password.exe",
    "bitwarden.exe",
    "lastpass.exe",
    "logonui.exe",
    "consent.exe",
    "credentialuibroker.exe",
    "mstsc.exe",
)

#: 窗口标题中的敏感关键词（不区分大小写）
SENSITIVE_TITLE_PATTERNS: tuple[str, ...] = (
    r"密码",
    r"password",
    r"passwd",
    r"凭据",
    r"credential",
    r"私钥",
    r"private\s*key",
    r"银行卡",
    r"身份证",
    r"付款",
    r"payment",
    r"验证码",
    r"otp",
    r"token",
)

_TITLE_RE = re.compile("|".join(SENSITIVE_TITLE_PATTERNS), re.IGNORECASE)


def is_blacklisted_process(process: str, extra: list[str] | None = None) -> bool:
    name = str(process or "").strip().lower()
    if not name:
        return False
    candidates = list(DEFAULT_PROCESS_BLACKLIST) + [e.lower() for e in (extra or [])]
    return name in candidates


def is_sensitive_title(title: str, extra: list[str] | None = None) -> bool:
    text = str(title or "")
    if not text:
        return False
    if _TITLE_RE.search(text):
        return True
    for pattern in extra or []:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def should_pause_capture(
    process: str,
    title: str,
    *,
    process_blacklist: list[str] | None = None,
    title_patterns: list[str] | None = None,
) -> tuple[bool, str]:
    """返回 (是否暂停, 原因)。原因用于界面展示，不含敏感原文。"""
    if is_blacklisted_process(process, process_blacklist):
        return True, "当前应用在采集黑名单中"
    if is_sensitive_title(title, title_patterns):
        return True, "当前窗口标题包含敏感信息"
    return False, ""


__all__ = [
    "DEFAULT_PROCESS_BLACKLIST",
    "SENSITIVE_TITLE_PATTERNS",
    "is_blacklisted_process",
    "is_sensitive_title",
    "should_pause_capture",
]
