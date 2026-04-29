"""
Layer 1 - 自感知层
==================
来源: ~/.openclaw/clawshell/self_healing/
功能: 健康检查、系统监控、磁盘监控、进程监控、Agent监控、网关监控、服务监控
"""

import sys
from pathlib import Path

# Link to clawshell self_healing module
_clawshell_self_healing = Path("~/.openclaw/clawshell/self_healing").expanduser()
if str(_clawshell_self_healing) not in sys.path:
    sys.path.insert(0, str(_clawshell_self_healing))

try:
    from health_monitor import HealthMonitor, HealthReport, HealthStatus, SystemIssue
    from repair_engine import RepairEngine, RepairResult, RepairAction, RepairStatus
    from scan_scheduler import ScanScheduler, ScanConfig, ScanResult
    
    __all__ = ["HealthMonitor", "HealthReport", "HealthStatus", "SystemIssue",
               "RepairEngine", "RepairResult", "RepairAction", "RepairStatus",
               "ScanScheduler", "ScanConfig", "ScanResult"]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
