# -*- coding: utf-8 -*-
"""python -m pytest 的共享配置。"""

from __future__ import annotations

import sys
from pathlib import Path

# 让 tests 能直接 import app.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
