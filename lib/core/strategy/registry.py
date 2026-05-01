"""
Strategy Registry - ClawShell v0.1
=================================

策略注册器。
提供策略的注册、查询和管理功能。
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .schema import Strategy, StrategyType

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    策略注册器
    ==========
    
    管理所有策略的生命周期。
    
    使用示例：
        registry = StrategyRegistry()
        
        # 注册策略
        registry.register(my_strategy)
        
        # 查询策略
        strategy = registry.get("my_strategy")
        
        # 列出所有策略
        all_strategies = registry.list_strategies()
    """
    
    def __init__(self, base_path: str = "~/.real/strategies"):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 策略缓存
        self._strategies: Dict[str, Strategy] = {}
        
        # 加载所有策略
        self._load_all()
    
    def _load_all(self):
        """加载所有策略"""
        # 尝试从config.yaml加载
        config_file = self.base_path / "config.yaml"
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                strategies_data = data.get("strategies", [])
                for s_data in strategies_data:
                    if isinstance(s_data, dict):
                        strategy = Strategy.from_dict(s_data)
                        self._strategies[strategy.name] = strategy
            except Exception as e:
                logger.error(f"Failed to load strategies from config: {e}")
        
        # 补充加载builtin策略（如果config没有）
        builtin_names = ["default", "emergency", "economy", "aggressive"]
        for name in builtin_names:
            if name not in self._strategies:
                from .switcher import get_switcher
                switcher = get_switcher()
                strategy = switcher.get_strategy(name)
                if strategy:
                    self._strategies[name] = strategy
    
    def _load_strategy(self, path: Path):
        """加载单个策略"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            strategy = Strategy.from_dict(data)
            self._strategies[strategy.name] = strategy
            logger.debug(f"Loaded strategy: {strategy.name}")
        except Exception as e:
            logger.error(f"Failed to load strategy from {path}: {e}")
    
    def register(self, strategy: Strategy) -> bool:
        """
        注册策略
        
        Args:
            strategy: Strategy对象
        
        Returns:
            是否注册成功
        """
        try:
            # 创建目录
            strategy_dir = self.base_path / strategy.name
            strategy_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存策略文件
            strategy_file = strategy_dir / "strategy.yaml"
            with open(strategy_file, 'w', encoding='utf-8') as f:
                f.write(strategy.to_yaml())
            
            # 更新缓存
            self._strategies[strategy.name] = strategy
            
            logger.info(f"Registered strategy: {strategy.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register strategy {strategy.name}: {e}")
            return False
    
    def unregister(self, strategy_name: str) -> bool:
        """
        注销策略
        
        Args:
            strategy_name: 策略名称
        
        Returns:
            是否注销成功
        """
        if strategy_name in ["default", "emergency", "economy", "aggressive"]:
            logger.warning(f"Cannot unregister built-in strategy: {strategy_name}")
            return False
        
        if strategy_name not in self._strategies:
            return False
        
        try:
            # 删除文件
            strategy_dir = self.base_path / strategy_name
            if strategy_dir.exists():
                for file in strategy_dir.iterdir():
                    file.unlink()
                strategy_dir.rmdir()
            
            # 更新缓存
            del self._strategies[strategy_name]
            
            logger.info(f"Unregistered strategy: {strategy_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister strategy {strategy_name}: {e}")
            return False
    
    def get(self, strategy_name: str) -> Optional[Strategy]:
        """获取策略"""
        return self._strategies.get(strategy_name)
    
    def list_strategies(self, strategy_type: StrategyType = None) -> List[Strategy]:
        """
        列出策略
        
        Args:
            strategy_type: 可选，按类型过滤
        
        Returns:
            策略列表
        """
        strategies = list(self._strategies.values())
        
        if strategy_type:
            strategies = [s for s in strategies if s.type == strategy_type]
        
        return sorted(strategies, key=lambda s: s.priority, reverse=True)
    
    def enable(self, strategy_name: str) -> bool:
        """启用策略"""
        strategy = self.get(strategy_name)
        if strategy:
            strategy.enabled = True
            self.register(strategy)
            return True
        return False
    
    def disable(self, strategy_name: str) -> bool:
        """禁用策略"""
        strategy = self.get(strategy_name)
        if strategy:
            strategy.enabled = False
            self.register(strategy)
            return True
        return False
