"""
Layer 2 - 自适应层 (ClawShell v1.0 Wrapper)
============================================
来源: ~/.openclaw/adaptor/ + ~/.openclaw/eventbus/
功能: 自修复、发现、条件引擎、策略选择、状态收集、分析响应、紧急响应、ML引擎、市场发现

导入示例:
    from clawshell.lib.layer2 import SelfHealing, Discovery, ControlLoop
"""

import sys
from pathlib import Path

_src_dirs = [
    Path("~/.openclaw/adaptor").expanduser(),
    Path("~/.openclaw/eventbus").expanduser(),
]
for _d in _src_dirs:
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

try:
    from self_healing import SelfHealingEngine as SelfHealing
    from discovery import DiscoveryEngine as Discovery
    from condition_engine import ConditionEngine
    from adaptive_controller import AdaptiveController
    from adaptive_tuner import AdaptiveParameterTuner as AdaptiveTuner
    from state_collector import StateCollector
    from analyzer import Analyzer
    from responder import Responder
    from emergency import Emergency
    from ml_engine import MLEngine
    from market_discovery import MarketDiscovery
    from control_loop import FeedbackControlLoop as ControlLoop
    
    __all__ = [
        "SelfHealing", "Discovery", "ConditionEngine", "AdaptiveController",
        "AdaptiveTuner", "StateCollector", "Analyzer", "Responder",
        "Emergency", "MLEngine", "MarketDiscovery", "ControlLoop"
    ]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
