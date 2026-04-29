"""
Layer 4 - 集群层 (ClawShell v1.0 Wrapper)
==========================================
来源: ~/.openclaw/swarm/ + ~/.openclaw/strategies/
功能: Swarm管理、信任评估、生态系统、协议、节点发现、信任撤销

导入示例:
    from lib.layer4 import SwarmDiscovery, TrustManager
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
    # Import from swarm package (requires .openclaw in path)
    from swarm.swarm_discovery import SwarmDiscovery
    from swarm.node_registry import NodeRegistry
    from swarm.trust_manager import TrustManager
    from swarm.trust_evaluator import TrustEvaluator
    from swarm.trust_revocator import TrustRevocator
    from swarm.ecology import SwarmEcology
    from swarm.metrics_collector import MetricsCollector
    from swarm.failure_detector import FailureDetector
    from swarm.node_monitor import NodeMonitor
    from swarm.weight_calculator import WeightCalculator
    
    __all__ = [
        "SwarmDiscovery", "NodeRegistry", "TrustManager", "TrustEvaluator",
        "TrustRevocator", "SwarmEcology", "MetricsCollector",
        "FailureDetector", "NodeMonitor", "WeightCalculator"
    ]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
