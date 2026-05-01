"""
Strategy Switcher - ClawShell v0.1
=================================

策略切换器。
根据条件自动切换策略。
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .schema import Strategy, StrategyType, SwitchCondition, StrategyConfig

logger = logging.getLogger(__name__)


class StrategySwitcher:
    """
    策略切换器
    ==========
    
    负责：
    - 加载和管理策略
    - 评估切换条件
    - 执行策略切换
    
    使用示例：
        switcher = StrategySwitcher()
        
        # 获取当前策略
        strategy = switcher.get_current_strategy()
        
        # 手动切换
        switcher.switch_to("emergency")
        
        # 自动评估
        switcher.evaluate_and_switch(metrics={"api_error_rate": 0.5})
    """
    
    def __init__(
        self,
        strategies_path: str = "~/.real/strategies",
        config_path: str = "~/.real/strategies/config.yaml",
    ):
        self.strategies_path = Path(strategies_path).expanduser()
        self.config_path = Path(config_path).expanduser()
        
        # 确保目录存在
        self.strategies_path.mkdir(parents=True, exist_ok=True)
        
        # 策略缓存
        self._strategies: Dict[str, Strategy] = {}
        self._conditions: List[SwitchCondition] = []
        
        # 当前策略
        self._current_strategy: Optional[Strategy] = None
        self._current_strategy_name: str = "default"
        
        # 切换回调
        self._on_switch_callbacks: List[Callable[[str, str], None]] = []
        
        # 加载配置
        self._load_config()
        
        # 加载策略
        self._load_strategies()
        
        logger.info(f"StrategySwitcher initialized, current: {self._current_strategy_name}")
    
    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                config = StrategyConfig.from_dict(data)
                self._current_strategy_name = config.current_strategy
                
                # 加载条件
                self._conditions = []
                for c in config.conditions:
                    if isinstance(c, dict):
                        self._conditions.append(SwitchCondition.from_dict(c))
                    elif isinstance(c, SwitchCondition):
                        self._conditions.append(c)
                
                logger.info(f"Loaded config: current={self._current_strategy_name}, conditions={len(self._conditions)}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
    
    def _load_strategies(self):
        """加载所有策略"""
        # 加载预置策略
        self._load_builtin_strategies()
        
        # 加载自定义策略
        custom_dir = self.strategies_path / "custom"
        if custom_dir.exists():
            for yaml_file in custom_dir.glob("*.yaml"):
                self._load_strategy_file(yaml_file)
        
        # 设置当前策略
        if self._current_strategy_name in self._strategies:
            self._current_strategy = self._strategies[self._current_strategy_name]
        elif "default" in self._strategies:
            self._current_strategy = self._strategies["default"]
            self._current_strategy_name = "default"
    
    def _load_builtin_strategies(self):
        """加载预置策略"""
        # Default策略
        self._strategies["default"] = Strategy(
            name="default",
            type=StrategyType.DEFAULT,
            description="默认策略，正常情况下使用",
        )
        
        # Emergency策略
        self._strategies["emergency"] = Strategy(
            name="emergency",
            type=StrategyType.EMERGENCY,
            description="应急策略，API错误率较高时使用",
        )
        
        # Economy策略
        self._strategies["economy"] = Strategy(
            name="economy",
            type=StrategyType.ECONOMY,
            description="节约策略，资源不足时使用",
        )
        
        # Aggressive策略
        self._strategies["aggressive"] = Strategy(
            name="aggressive",
            type=StrategyType.AGGRESSIVE,
            description="激进策略，全力运行时使用",
        )
    
    def _load_strategy_file(self, path: Path):
        """从文件加载策略"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            strategy = Strategy.from_dict(data)
            self._strategies[strategy.name] = strategy
            logger.debug(f"Loaded strategy: {strategy.name}")
        except Exception as e:
            logger.error(f"Failed to load strategy from {path}: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            config = StrategyConfig(
                current_strategy=self._current_strategy_name,
                strategies=list(self._strategies.values()),
                conditions=self._conditions,
            )
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
            
            logger.debug(f"Saved config: current={self._current_strategy_name}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get_current_strategy(self) -> Strategy:
        """获取当前策略"""
        if self._current_strategy is None:
            self._current_strategy = self._strategies.get("default")
        return self._current_strategy
    
    def get_strategy(self, name: str) -> Optional[Strategy]:
        """获取指定策略"""
        return self._strategies.get(name)
    
    def switch_to(self, strategy_name: str, reason: str = None) -> bool:
        """
        切换到指定策略
        
        Args:
            strategy_name: 策略名称
            reason: 切换原因
        
        Returns:
            是否切换成功
        """
        if strategy_name not in self._strategies:
            logger.warning(f"Strategy not found: {strategy_name}")
            return False
        
        old_strategy = self._current_strategy_name
        
        self._current_strategy = self._strategies[strategy_name]
        self._current_strategy_name = strategy_name
        
        # 保存配置
        self._save_config()
        
        # 记录切换历史
        self._record_switch(old_strategy, strategy_name, reason)
        
        # 触发回调
        for callback in self._on_switch_callbacks:
            try:
                callback(old_strategy, strategy_name)
            except Exception as e:
                logger.error(f"Switch callback error: {e}")
        
        logger.info(f"Switched strategy: {old_strategy} -> {strategy_name}")
        if reason:
            logger.info(f"  Reason: {reason}")
        
        return True
    
    def _record_switch(self, from_strategy: str, to_strategy: str, reason: str = None):
        """记录切换历史"""
        history_entry = {
            "from": from_strategy,
            "to": to_strategy,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 追加到配置
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
            except:
                data = {}
        else:
            data = {}
        
        if "switch_history" not in data:
            data["switch_history"] = []
        
        data["switch_history"].append(history_entry)
        
        # 保留最近50条
        data["switch_history"] = data["switch_history"][-50:]
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def evaluate_and_switch(self, metrics: Dict[str, float]) -> Optional[str]:
        """
        评估条件并切换策略
        
        Args:
            metrics: 当前指标
        
        Returns:
            切换后的策略名称，如果没有切换则返回None
        """
        # 按优先级排序条件
        sorted_conditions = sorted(
            [c for c in self._conditions if c.enabled],
            key=lambda c: c.priority,
            reverse=True,
        )
        
        for condition in sorted_conditions:
            if condition.evaluate(metrics):
                target = condition.target_strategy
                if target != self._current_strategy_name:
                    self.switch_to(target, reason=f"Condition triggered: {condition.name}")
                    return target
        
        return None
    
    def add_condition(self, condition: SwitchCondition):
        """添加切换条件"""
        self._conditions.append(condition)
        self._save_config()
        logger.info(f"Added condition: {condition.name}")
    
    def remove_condition(self, condition_name: str):
        """移除切换条件"""
        self._conditions = [c for c in self._conditions if c.name != condition_name]
        self._save_config()
        logger.info(f"Removed condition: {condition_name}")
    
    def on_switch(self, callback: Callable[[str, str], None]):
        """注册切换回调"""
        self._on_switch_callbacks.append(callback)
    
    def get_switch_history(self, limit: int = 10) -> List[Dict]:
        """获取切换历史"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                history = data.get("switch_history", [])
                return history[-limit:]
            except:
                pass
        return []


# 全局单例
_switcher: Optional[StrategySwitcher] = None


def get_switcher() -> StrategySwitcher:
    """获取全局策略切换器实例"""
    global _switcher
    if _switcher is None:
        _switcher = StrategySwitcher()
    return _switcher
