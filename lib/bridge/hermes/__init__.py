"""
Hermes Bridge - Hermes协同模块 (ClawShell v1.0 Wrapper)
========================================================
来源: ~/.openclaw/workspace/shared/hermes_bridge/
功能: Hermes事件消费、洞察同步、场景集成、触发配置
"""

import sys
from pathlib import Path

_src = Path("~/.openclaw/workspace/shared/hermes_bridge").expanduser()
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from bridge import HermesBridge
    from bridge_v2 import HermesBridgeV2
    from scenario_integrator import ScenarioIntegrator
    from trigger_config import TriggerConfig
    from classifier import EventClassifier
    from matcher import EventMatcher
    from publisher import HermesPublisher
    from queue import HermesQueue
    
    __all__ = [
        "HermesBridge", "HermesBridgeV2", "ScenarioIntegrator",
        "TriggerConfig", "EventClassifier", "EventMatcher",
        "HermesPublisher", "HermesQueue"
    ]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
