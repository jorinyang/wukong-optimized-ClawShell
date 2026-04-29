"""
Utils Module - 工具函数
========================
通用工具函数
"""

import sys
from pathlib import Path

# 从clawshell复用utils
_clawshell_utils = Path("~/.openclaw/clawshell").expanduser()
if str(_clawshell_utils) not in sys.path:
    sys.path.insert(0, str(_clawshell_utils))

__all__ = []
