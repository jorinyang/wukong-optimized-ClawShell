"""
Strategy - 策略库 (ClawShell v1.0)
====================================

功能: 策略注册、评估、切换

使用示例:
    from lib.core.strategy import StrategyRegistry, StrategyEvaluator
"""

from .registry import StrategyRegistry
from .evaluator import StrategyEvaluator
from .switcher import StrategySwitcher

__all__ = [
    "StrategyRegistry", "StrategyEvaluator", "StrategySwitcher"
]
