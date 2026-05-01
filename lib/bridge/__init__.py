"""
Bridge接口层 - lib/bridge/
==========================
包含: Hermes协同, 持久层, 外部工具

使用示例:
    from lib.bridge import hermes, persistence, external
"""

from . import hermes
from . import persistence
from . import external

__all__ = ["hermes", "persistence", "external"]
