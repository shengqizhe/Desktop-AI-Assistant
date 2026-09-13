# -*- coding: utf-8 -*-
"""隐私与采集基础模块。

首期只提供判定逻辑与接口，不做实际屏幕采集（属迭代计划 I2）。
"""

from app.privacy.sensitive_windows import (
    DEFAULT_PROCESS_BLACKLIST,
    SENSITIVE_TITLE_PATTERNS,
    is_blacklisted_process,
    is_sensitive_title,
    should_pause_capture,
)
from app.privacy.upload_guard import UploadDecision, decide_upload

__all__ = [
    "DEFAULT_PROCESS_BLACKLIST",
    "SENSITIVE_TITLE_PATTERNS",
    "is_blacklisted_process",
    "is_sensitive_title",
    "should_pause_capture",
    "UploadDecision",
    "decide_upload",
]
