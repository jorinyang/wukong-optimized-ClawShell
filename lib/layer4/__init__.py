"""
Layer 4 - 集群层 (ClawShell v1.0)
====================================

功能: 集群发现、信任评估、信任撤销、生态位匹配、失败检测

使用示例:
    from lib.layer4 import SwarmDiscovery, TrustManager
"""

import sys
from pathlib import Path

# 检查是否有源目录可用
_source_paths = [
    Path(__file__).parent.parent.parent / "swarm",  # ../../../swarm
    Path.home() / ".openclaw" / "swarm",
]

for _sp in _source_paths:
    if _sp.exists() and str(_sp) not in sys.path:
        sys.path.insert(0, str(_sp))
        break

try:
    from swarm_discovery import SwarmDiscovery
    from trust_manager import TrustManager, TrustEvaluator
    from trust_revocator import TrustRevocator
    from ecology import EcologyMatcher as Ecology
    from failure_detector import FailureDetector
    from metrics_collector import MetricsCollector
    
    __all__ = [
        "SwarmDiscovery", "TrustManager", "TrustEvaluator",
        "TrustRevocator", "Ecology", "FailureDetector",
        "MetricsCollector",
    ]
except ImportError as e:
    # 如果源目录不可用，提供空实现
    class _FallbackMixin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"Layer4 module unavailable: {e}")
    
    SwarmDiscovery = _FallbackMixin
    TrustManager = _FallbackMixin
    TrustEvaluator = _FallbackMixin
    TrustRevocator = _FallbackMixin
    Ecology = _FallbackMixin
    FailureDetector = _FallbackMixin
    MetricsCollector = _FallbackMixin
    
    __all__ = [
        "SwarmDiscovery", "TrustManager", "TrustEvaluator",
        "TrustRevocator", "Ecology", "FailureDetector",
        "MetricsCollector",
    ]
