"""
Layer 3 - 自组织层 (ClawShell v1.0)
====================================

功能: DAG编排、任务市场、任务注册、任务协调、调度、N8N客户端、上下文管理

使用示例:
    from lib.layer3 import TaskMarket, DAG
"""

import sys
from pathlib import Path

# 检查是否有源目录可用
_source_paths = [
    Path(__file__).parent.parent.parent / "organizer",  # ../../../organizer
    Path.home() / ".openclaw" / "organizer",
]

for _sp in _source_paths:
    if _sp.exists() and str(_sp) not in sys.path:
        sys.path.insert(0, str(_sp))
        break

try:
    from dag import TaskDAG as DAG
    from market import TaskMarket
    from registry import TaskRegistry
    from coordinator import Coordinator
    from task_scheduler import TaskScheduler
    from ecology import Ecology
    
    __all__ = [
        "DAG", "TaskMarket", "TaskRegistry", "Coordinator",
        "TaskScheduler", "Ecology",
    ]
except ImportError as e:
    # 如果源目录不可用，提供空实现
    class _FallbackMixin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"Layer3 module unavailable: {e}")
    
    DAG = _FallbackMixin
    TaskMarket = _FallbackMixin
    TaskRegistry = _FallbackMixin
    Coordinator = _FallbackMixin
    TaskScheduler = _FallbackMixin
    Ecology = _FallbackMixin
    
    __all__ = [
        "DAG", "TaskMarket", "TaskRegistry", "Coordinator",
        "TaskScheduler", "Ecology",
    ]
