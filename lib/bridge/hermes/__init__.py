"""
Hermes Bridge - Hermes协同模块 (ClawShell v1.0)
================================================

功能: Hermes事件消费、洞察同步、场景集成、触发配置、优先级分类

使用示例:
    from lib.bridge.hermes import HermesBridge, ScenarioIntegrator
"""

try:
    from .bridge import HermesBridge
    from .scenario_integrator import ScenarioIntegrator
    from .trigger_config import TriggerConfig
    from .classifier import EventClassifier
    from .matcher import EventMatcher
    from .publisher import HermesPublisher
    from .queue import HermesQueue
    from .events import Event, Priority, ResponseMode
    from .priority_rules import PRIORITY_RULES
    
    __all__ = [
        "HermesBridge", "ScenarioIntegrator",
        "TriggerConfig", "EventClassifier", "EventMatcher",
        "HermesPublisher", "HermesQueue",
        "Event", "Priority", "ResponseMode", "PRIORITY_RULES"
    ]
except ImportError as e:
    class _FallbackMixin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"Hermes bridge unavailable: {e}")
    
    HermesBridge = ScenarioIntegrator = TriggerConfig = _FallbackMixin
    
    __all__ = ["HermesBridge", "ScenarioIntegrator"]
