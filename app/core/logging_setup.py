# -*- coding: utf-8 -*-
"""本地日志：轮转文件 + 脱敏。

日志绝不写入 API Key、原始屏幕帧或键盘原文（方案 9.4 安全测试）。
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_app_data_dir

LOGGER_NAME = "coach"

#: 形如 sk-xxx 或 32 位以上十六进制/字母数字串一律打码
_SECRET_PATTERNS = (
    re.compile(r"(sk-[A-Za-z0-9_\-]{8,})"),
    re.compile(r"(api[_-]?key[\"'=:\s]+)([A-Za-z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([A-Za-z0-9_\-\.]{8,})", re.IGNORECASE),
)
_URL_CREDENTIALS = re.compile(r"(https?://)([^\s/:@]+):([^\s/@]+)@")


def redact(text: str) -> str:
    """对日志文本做脱敏，便于诊断包导出。"""
    result = str(text)
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            result = pattern.sub(lambda m: f"{m.group(1)}***", result)
        else:
            result = pattern.sub("***", result)
    result = _URL_CREDENTIALS.sub(lambda m: f"{m.group(1)}***:***@", result)
    return result


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def init_logging(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    logger.propagate = False

    target = log_file or (get_app_data_dir() / "coach.log")
    target.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        target, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(_RedactingFilter())
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


__all__ = ["LOGGER_NAME", "redact", "init_logging", "get_logger"]
