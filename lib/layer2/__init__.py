"""
Layer 2 - 自适应层 (ClawShell v1.0)
====================================

功能: 自修复、自发现、条件引擎、策略评估、状态收集、分析响应、应急处理、ML引擎

使用示例:
    from lib.layer2 import SelfHealing, Discovery
"""

# 尝试从symlink源加载，如果存在的话
import sys
from pathlib import Path

# 检查是否有源目录可用
_source_paths = [
    Path(__file__).parent.parent.parent / "adaptor",  # ../../../adaptor
    Path.home() / ".openclaw" / "adaptor",
]

for _sp in _source_paths:
    if _sp.exists() and str(_sp) not in sys.path:
        sys.path.insert(0, str(_sp))
        break

try:
    from self_healing import SelfHealingEngine as SelfHealing
    from discovery import DiscoveryEngine as Discovery
    from analyzer import Analyzer
    from responder import Responder
    from emergency import Emergency
    from state_collector import StateCollector
    from ml_engine import MLEngine
    from market_discovery import MarketDiscovery
    from condition_engine import ConditionEngine
    
    __all__ = [
        "SelfHealing", "Discovery", "Analyzer", "Responder",
        "Emergency", "StateCollector", "MLEngine",
        "MarketDiscovery", "ConditionEngine",
    ]
except ImportError as e:
    # 如果源目录不可用，提供空实现
    class _FallbackMixin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"Layer2 module unavailable: {e}")
    
    SelfHealing = _FallbackMixin
    Discovery = _FallbackMixin
    Analyzer = _FallbackMixin
    Responder = _FallbackMixin
    Emergency = _FallbackMixin
    StateCollector = _FallbackMixin
    MLEngine = _FallbackMixin
    MarketDiscovery = _FallbackMixin
    ConditionEngine = None
    
    __all__ = [
        "SelfHealing", "Discovery", "Analyzer", "Responder",
        "Emergency", "StateCollector", "MLEngine",
        "MarketDiscovery", "ConditionEngine",
    ]
