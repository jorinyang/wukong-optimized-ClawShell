"""
Layer 3 - 自组织层 (ClawShell v1.0 Wrapper)
============================================
来源: ~/.openclaw/organizer/ + ~/.openclaw/clawshell/
功能: DAG编排、任务市场、任务注册、任务协调、调度、N8N集成、上下文管理

导入示例:
    from lib.layer3 import DAG, TaskMarket, ContextManager
"""

import sys
from pathlib import Path

_clawshell_root = Path("~/.openclaw/clawshell_v1").expanduser()
_openclaw_root = Path("~/.openclaw").expanduser()

if str(_clawshell_root) not in sys.path:
    sys.path.insert(0, str(_clawshell_root))
if str(_openclaw_root) not in sys.path:
    sys.path.insert(0, str(_openclaw_root))

try:
    # Import from organizer package (requires .openclaw in path)
    from organizer.dag import TaskDAG as DAG
    from organizer.market import TaskMarket
    from organizer.registry import TaskRegistry as Registry
    from organizer.coordinator import Coordinator
    from organizer.task_scheduler import TaskScheduler
    from organizer.ecology import Ecology
    from organizer.load_balancer import LoadBalancer
    
    # From clawshell main directory
    try:
        from n8n_integration import N8NClient
        from context_manager import ContextManager
    except ImportError:
        N8NClient = None
        ContextManager = None
    
    __all__ = [
        "DAG", "TaskMarket", "Registry", "Coordinator",
        "TaskScheduler", "Ecology", "LoadBalancer",
        "N8NClient", "ContextManager"
    ]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
