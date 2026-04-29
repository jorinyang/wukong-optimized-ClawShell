"""
Strategy Schema - ClawShell v0.1
==============================

策略格式定义。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import yaml


class StrategyType(Enum):
    """策略类型"""
    DEFAULT = "default"
    EMERGENCY = "emergency"
    ECONOMY = "economy"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class ConditionOperator(Enum):
    """条件操作符"""
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="
    EQ = "=="
    NE = "!="
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class APIConfig:
    """API配置"""
    retry_count: int = 3
    timeout: int = 30
    fallback_enabled: bool = True
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "fallback_enabled": self.fallback_enabled,
            "retry_delay": self.retry_delay,
            "exponential_backoff": self.exponential_backoff,
        }


@dataclass
class ErrorHandlingConfig:
    """错误处理配置"""
    auto_retry: bool = True
    alert_threshold: int = 3
    critical_threshold: int = 5
    recovery_wait: int = 60
    
    def to_dict(self) -> Dict:
        return {
            "auto_retry": self.auto_retry,
            "alert_threshold": self.alert_threshold,
            "critical_threshold": self.critical_threshold,
            "recovery_wait": self.recovery_wait,
        }


@dataclass
class PerformanceConfig:
    """性能配置"""
    concurrent_tasks: int = 10
    batch_size: int = 5
    max_queue_size: int = 100
    task_timeout: int = 300
    
    def to_dict(self) -> Dict:
        return {
            "concurrent_tasks": self.concurrent_tasks,
            "batch_size": self.batch_size,
            "max_queue_size": self.max_queue_size,
            "task_timeout": self.task_timeout,
        }


@dataclass
class Strategy:
    """
    策略配置
    =========
    """
    name: str
    type: StrategyType = StrategyType.DEFAULT
    description: str = ""
    
    # API配置
    api: APIConfig = field(default_factory=APIConfig)
    
    # 错误处理
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    
    # 性能配置
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # 元数据
    enabled: bool = True
    priority: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 自定义配置
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, StrategyType) else self.type,
            "description": self.description,
            "api": self.api.to_dict() if isinstance(self.api, APIConfig) else self.api,
            "error_handling": self.error_handling.to_dict() if isinstance(self.error_handling, ErrorHandlingConfig) else self.error_handling,
            "performance": self.performance.to_dict() if isinstance(self.performance, PerformanceConfig) else self.performance,
            "enabled": self.enabled,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
    
    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Strategy":
        return cls(
            name=data.get("name", "unknown"),
            type=StrategyType(data.get("type", "default")),
            description=data.get("description", ""),
            api=APIConfig(**data.get("api", {})),
            error_handling=ErrorHandlingConfig(**data.get("error_handling", {})),
            performance=PerformanceConfig(**data.get("performance", {})),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Strategy":
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


@dataclass
class SwitchCondition:
    """
    切换条件
    =========
    
    当条件满足时，自动切换到指定策略。
    """
    name: str
    condition: str  # e.g., "api_error_rate > 0.3"
    target_strategy: str  # e.g., "emergency"
    priority: int = 0
    enabled: bool = True
    description: str = ""
    
    def evaluate(self, metrics: Dict[str, float]) -> bool:
        """
        评估条件是否满足
        
        Args:
            metrics: 当前指标字典
        
        Returns:
            是否满足条件
        """
        try:
            # 解析条件 e.g., "api_error_rate > 0.3"
            parts = self.condition.split()
            if len(parts) != 3:
                return False
            
            metric_name = parts[0]
            operator = parts[1]
            threshold = float(parts[2])
            
            if metric_name not in metrics:
                return False
            
            current_value = metrics[metric_name]
            
            # 评估
            if operator == ">":
                return current_value > threshold
            elif operator == ">=":
                return current_value >= threshold
            elif operator == "<":
                return current_value < threshold
            elif operator == "<=":
                return current_value <= threshold
            elif operator == "==":
                return current_value == threshold
            elif operator == "!=":
                return current_value != threshold
            
            return False
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "condition": self.condition,
            "target_strategy": self.target_strategy,
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SwitchCondition":
        return cls(
            name=data.get("name", ""),
            condition=data.get("condition", ""),
            target_strategy=data.get("target_strategy", "default"),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )


@dataclass
class StrategyConfig:
    """
    策略配置文件
    =============
    """
    current_strategy: str = "default"
    strategies: List[Strategy] = field(default_factory=list)
    conditions: List[SwitchCondition] = field(default_factory=list)
    switch_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "current_strategy": self.current_strategy,
            "strategies": [s.to_dict() if isinstance(s, Strategy) else s for s in self.strategies],
            "conditions": [c.to_dict() if isinstance(c, SwitchCondition) else c for c in self.conditions],
            "switch_history": self.switch_history,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StrategyConfig":
        return cls(
            current_strategy=data.get("current_strategy", "default"),
            strategies=[Strategy.from_dict(s) if isinstance(s, dict) else s for s in data.get("strategies", [])],
            conditions=[SwitchCondition.from_dict(c) if isinstance(c, dict) else c for c in data.get("conditions", [])],
            switch_history=data.get("switch_history", []),
        )
