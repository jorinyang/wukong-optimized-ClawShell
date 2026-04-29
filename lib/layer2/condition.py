#!/usr/bin/env python3
"""
ClawShell 条件触发引擎 (Condition Trigger Engine)
版本: v0.2.1-B
功能: 基于条件的自动触发，填补"事后响应"到"事前预防"的空白
依赖: EventBus, StrategySwitcher
"""

import json
import logging
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Lock
import operator

from lib.core.eventbus.schema import Event, EventType

logger = logging.getLogger(__name__)


# ============ 条件类型定义 ============

class ConditionType(Enum):
    """条件类型"""
    THRESHOLD = "threshold"           # 阈值比较 (value > threshold)
    CHANGE = "change"                 # 变化检测 (|delta| > threshold)
    TIME_WINDOW = "time_window"       # 时间窗口 (within time range)
    COMPOSITE = "composite"          # 组合条件 (AND/OR expressions)
    NEGATION = "negation"            # 逆向条件 (从坏变好)


class ComparisonOp(Enum):
    """比较运算符"""
    GT = ">"    # 大于
    LT = "<"    # 小于
    GE = ">="   # 大于等于
    LE = "<="   # 小于等于
    EQ = "=="   # 等于
    NE = "!="   # 不等于


# ============ 数据结构 ============

@dataclass
class Condition:
    """条件定义"""
    type: str                          # ConditionType.value
    target_metric: str                 # 监控指标名
    comparison: str = ">"              # 比较运算符
    threshold: float = 0.0             # 阈值
    time_window: Optional[int] = None # 时间窗口（秒）
    consecutive: bool = True           # 是否需要连续满足
    expression: str = ""               # 组合表达式 (用于COMPOSITE)
    target_metrics: List[str] = field(default_factory=list)  # 多指标

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Condition":
        return cls(**data)


@dataclass
class ConditionTrigger:
    """条件触发器"""
    id: str
    name: str
    condition: Condition
    action_type: str                   # 触发动作类型
    action_config: Dict = field(default_factory=dict)  # 动作配置
    cooldown: int = 60                # 冷却时间（秒）
    last_triggered: Optional[float] = None
    triggered_count: int = 0          # 触发次数
    enabled: bool = True
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "condition": self.condition.to_dict(),
            "action_type": self.action_type,
            "action_config": self.action_config,
            "cooldown": self.cooldown,
            "last_triggered": self.last_triggered,
            "triggered_count": self.triggered_count,
            "enabled": self.enabled,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConditionTrigger":
        data["condition"] = Condition.from_dict(data["condition"])
        return cls(**data)


# ============ 内置触发动作 ============

class TriggerActions:
    """内置触发动作"""

    @staticmethod
    def send_alert(trigger: ConditionTrigger, context: Dict):
        """发送告警"""
        logger.warning(f"🚨 ALERT: {trigger.name} triggered!")
        logger.warning(f"   Metric: {trigger.condition.target_metric}")
        logger.warning(f"   Value: {context.get('current_value')}")
        logger.warning(f"   Threshold: {trigger.condition.threshold}")

    @staticmethod
    def switch_strategy(trigger: ConditionTrigger, context: Dict):
        """切换策略"""
        strategy = trigger.action_config.get("strategy", "emergency")
        logger.info(f"🔄 Switching to strategy: {strategy}")

    @staticmethod
    def scale_up(trigger: ConditionTrigger, context: Dict):
        """扩容"""
        logger.info(f"📈 Scaling up: {trigger.name}")

    @staticmethod
    def scale_down(trigger: ConditionTrigger, context: Dict):
        """缩容"""
        logger.info(f"📉 Scaling down: {trigger.name}")

    @staticmethod
    def switch_to_backup(trigger: ConditionTrigger, context: Dict):
        """切换到备用"""
        logger.warning(f"🔀 Switching to backup: {trigger.name}")

    @staticmethod
    def restore_normal(trigger: ConditionTrigger, context: Dict):
        """恢复正常"""
        logger.info(f"✅ Restoring normal: {trigger.name}")

    @staticmethod
    def log_event(trigger: ConditionTrigger, context: Dict):
        """记录事件"""
        logger.info(f"📝 Event logged: {trigger.name}")


# 动作注册表
ACTION_REGISTRY: Dict[str, Callable] = {
    "send_alert": TriggerActions.send_alert,
    "switch_strategy": TriggerActions.switch_strategy,
    "scale_up": TriggerActions.scale_up,
    "scale_down": TriggerActions.scale_down,
    "switch_to_backup": TriggerActions.switch_to_backup,
    "restore_normal": TriggerActions.restore_normal,
    "log_event": TriggerActions.log_event,
}


# ============ 比较运算符映射 ============

OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


# ============ 条件触发引擎 ============

class ConditionEngine:
    """
    条件触发引擎
    ==============

    功能：
    - 阈值触发：value > threshold
    - 变化触发：|delta| > threshold
    - 时间窗口：within time range
    - 组合条件：AND/OR 表达式
    - 逆向条件：从坏变好

    使用示例：
        engine = ConditionEngine(eventbus)

        # 添加触发器
        trigger = ConditionTrigger(
            id="balance_low",
            name="余额不足预警",
            condition=Condition(
                type="threshold",
                target_metric="api_balance",
                comparison="<",
                threshold=100
            ),
            action_type="send_alert",
            cooldown=3600
        )
        engine.add_trigger(trigger)

        # 更新指标
        engine.update_metric("api_balance", 50)

        # 启动引擎
        engine.start()
    """

    def __init__(
        self,
        eventbus=None,
        persistence_path: str = "~/.openclaw/eventbus/conditions",
        check_interval: float = 5.0,
    ):
        self.eventbus = eventbus
        self.persistence_path = Path(persistence_path).expanduser()
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        self.check_interval = check_interval

        # 触发器存储
        self.triggers: Dict[str, ConditionTrigger] = {}
        self.triggers_lock = Lock()

        # 指标缓存
        self.metrics_cache: Dict[str, Dict[str, Any]] = {}

        # 运行状态
        self.running = False
        self._check_thread = None

        # 统计
        self.stats = {
            "total_triggers": 0,
            "total_executions": 0,
            "cooldown_bypasses": 0,
        }

        # 加载内置触发器
        self._load_builtin_triggers()

        logger.info("ConditionEngine initialized")
        logger.info(f"Persistence path: {self.persistence_path}")

    def _load_builtin_triggers(self):
        """加载内置触发器"""
        builtin_triggers = [
            {
                "id": "balance_low",
                "name": "余额不足预警",
                "condition": {
                    "type": "threshold",
                    "target_metric": "api_balance",
                    "comparison": "<",
                    "threshold": 100,
                },
                "action_type": "send_alert",
                "cooldown": 3600,
                "tags": ["builtin", "finance"]
            },
            {
                "id": "cpu_high",
                "name": "CPU过高告警",
                "condition": {
                    "type": "threshold",
                    "target_metric": "system_cpu",
                    "comparison": ">",
                    "threshold": 80,
                },
                "action_type": "scale_up",
                "cooldown": 300,
                "tags": ["builtin", "system"]
            },
            {
                "id": "memory_high",
                "name": "内存过高告警",
                "condition": {
                    "type": "threshold",
                    "target_metric": "system_memory",
                    "comparison": ">",
                    "threshold": 85,
                },
                "action_type": "switch_strategy",
                "action_config": {"strategy": "economy"},
                "cooldown": 600,
                "tags": ["builtin", "system"]
            },
            {
                "id": "strategy_switch_on_recovery",
                "name": "服务恢复自动恢复策略",
                "condition": {
                    "type": "negation",
                    "target_metric": "api_health",
                    "comparison": ">",
                    "threshold": 0.5,
                },
                "action_type": "restore_normal",
                "cooldown": 1800,
                "tags": ["builtin", "recovery"]
            },
        ]

        for t in builtin_triggers:
            trigger = ConditionTrigger(
                id=t["id"],
                name=t["name"],
                condition=Condition(**t["condition"]),
                action_type=t["action_type"],
                action_config=t.get("action_config", {}),
                cooldown=t.get("cooldown", 60),
                tags=t.get("tags", [])
            )
            self.add_trigger(trigger)

        logger.info(f"Loaded {len(builtin_triggers)} builtin triggers")

    def add_trigger(self, trigger: Union[ConditionTrigger, Dict]):
        """添加触发器"""
        if isinstance(trigger, Dict):
            trigger = ConditionTrigger.from_dict(trigger)

        with self.triggers_lock:
            self.triggers[trigger.id] = trigger
            self.stats["total_triggers"] = len(self.triggers)

        logger.info(f"Added trigger: {trigger.id} ({trigger.name})")

        # 保存到持久化
        self._save_trigger(trigger)

    def remove_trigger(self, trigger_id: str):
        """移除触发器"""
        with self.triggers_lock:
            if trigger_id in self.triggers:
                del self.triggers[trigger_id]
                self.stats["total_triggers"] = len(self.triggers)

        # 删除持久化文件
        trigger_file = self.persistence_path / f"{trigger_id}.json"
        if trigger_file.exists():
            trigger_file.unlink()

        logger.info(f"Removed trigger: {trigger_id}")

    def enable_trigger(self, trigger_id: str):
        """启用触发器"""
        with self.triggers_lock:
            if trigger_id in self.triggers:
                self.triggers[trigger_id].enabled = True
                logger.info(f"Enabled trigger: {trigger_id}")

    def disable_trigger(self, trigger_id: str):
        """禁用触发器"""
        with self.triggers_lock:
            if trigger_id in self.triggers:
                self.triggers[trigger_id].enabled = False
                logger.info(f"Disabled trigger: {trigger_id}")

    def update_metric(
        self,
        metric_name: str,
        value: Any,
        timestamp: Optional[float] = None
    ):
        """更新监控指标"""
        if timestamp is None:
            timestamp = time.time()

        old_value = self.metrics_cache.get(metric_name, {}).get("value")

        self.metrics_cache[metric_name] = {
            "value": value,
            "timestamp": timestamp,
            "old_value": old_value,
            "delta": abs(value - old_value) if old_value is not None else None
        }

        # 评估触发器
        self._evaluate_triggers(metric_name)

    def update_metrics_batch(self, metrics: Dict[str, Any]):
        """批量更新指标 - 先更新缓存，最后统一评估"""
        timestamp = time.time()

        # 第一步：更新所有指标缓存（不触发评估）
        for name, value in metrics.items():
            old_value = self.metrics_cache.get(name, {}).get("value")
            self.metrics_cache[name] = {
                "value": value,
                "timestamp": timestamp,
                "old_value": old_value,
                "delta": abs(value - old_value) if old_value is not None else None
            }

        # 第二步：评估所有触发器
        for metric_name in metrics.keys():
            self._evaluate_triggers(metric_name)

    def _evaluate_triggers(self, metric_name: str):
        """评估所有监控该指标的触发器"""
        with self.triggers_lock:
            triggers_to_evaluate = [
                t for t in self.triggers.values()
                if t.enabled and t.condition.target_metric == metric_name
            ]

        for trigger in triggers_to_evaluate:
            if self._check_cooldown(trigger):
                self.stats["cooldown_bypasses"] += 1
                continue

            if self._evaluate_condition(trigger.condition, metric_name):
                self._execute_action(trigger, metric_name)

    def _check_cooldown(self, trigger: ConditionTrigger) -> bool:
        """检查冷却时间"""
        if trigger.last_triggered is None:
            return False

        elapsed = time.time() - trigger.last_triggered
        return elapsed < trigger.cooldown

    def _evaluate_condition(self, condition: Condition, metric_name: str) -> bool:
        """评估条件"""
        metric = self.metrics_cache.get(metric_name, {})
        current = metric.get("value")
        old_value = metric.get("old_value")

        if current is None:
            return False

        cond_type = ConditionType(condition.type)

        if cond_type == ConditionType.THRESHOLD:
            return self._evaluate_threshold(condition, current)

        elif cond_type == ConditionType.CHANGE:
            delta = metric.get("delta")
            if delta is None:
                return False
            return self._evaluate_threshold(
                Condition(
                    type="threshold",
                    target_metric=condition.target_metric,
                    comparison=condition.comparison,
                    threshold=condition.threshold
                ),
                delta
            )

        elif cond_type == ConditionType.COMPOSITE:
            return self._evaluate_composite(condition)

        elif cond_type == ConditionType.NEGATION:
            return self._evaluate_negation(condition, old_value, current)

        elif cond_type == ConditionType.TIME_WINDOW:
            return self._evaluate_time_window(condition, metric.get("timestamp"))

        return False

    def _evaluate_threshold(self, condition: Condition, value: Any) -> bool:
        """评估阈值条件"""
        try:
            value = float(value)
            threshold = float(condition.threshold)
            op = OPS.get(condition.comparison, operator.gt)
            return op(value, threshold)
        except (TypeError, ValueError):
            return False

    def _evaluate_composite(self, condition: Condition) -> bool:
        """评估组合条件"""
        if not condition.expression:
            return False

        # 解析表达式，如 "error_rate > 5 AND error_count > 10"
        expression = condition.expression

        # 先替换指标名为实际值（保持原始大小写）
        for metric_name in condition.target_metrics:
            metric = self.metrics_cache.get(metric_name, {})
            value = metric.get("value", 0)
            expression = re.sub(
                rf'\b{metric_name}\b',
                str(float(value)),
                expression,
                flags=re.IGNORECASE  # 不区分大小写
            )

        # 替换AND/OR (保持Python运算符不变)
        expression = re.sub(r'\bAND\b', ' and ', expression, flags=re.IGNORECASE)
        expression = re.sub(r'\bOR\b', ' or ', expression, flags=re.IGNORECASE)

        try:
            # 安全评估 - 允许数字、字母(用于and/or)、运算符、空格
            safe_pattern = r'^[\d\.\s\+\-\*\/\(\)\>\<\=\&\|andor]+$'
            if re.match(safe_pattern, expression, re.IGNORECASE):
                return eval(expression)
            else:
                logger.warning(f"Expression contains unsafe characters: {expression}")
        except Exception as e:
            logger.error(f"Composite evaluation error: {e}")

        return False

    def _evaluate_negation(
        self,
        condition: Condition,
        old_value: Any,
        current: Any
    ) -> bool:
        """评估逆向条件（从坏变好）"""
        if old_value is None or current is None:
            return False

        try:
            old_val = float(old_value)
            curr_val = float(current)
            threshold = float(condition.threshold)

            # 从高于阈值变为低于或等于阈值
            return old_val > threshold and curr_val <= threshold
        except (TypeError, ValueError):
            return False

    def _evaluate_time_window(
        self,
        condition: Condition,
        timestamp: Optional[float]
    ) -> bool:
        """评估时间窗口条件"""
        if timestamp is None or condition.time_window is None:
            return False

        elapsed = time.time() - timestamp
        return elapsed <= condition.time_window

    def _execute_action(self, trigger: ConditionTrigger, metric_name: str):
        """执行触发动作"""
        metric = self.metrics_cache.get(metric_name, {})

        try:
            # 获取动作函数
            action_func = ACTION_REGISTRY.get(trigger.action_type)
            if action_func:
                context = {
                    "trigger_id": trigger.id,
                    "metric_name": metric_name,
                    "current_value": metric.get("value"),
                    "old_value": metric.get("old_value"),
                    "threshold": trigger.condition.threshold,
                    "timestamp": time.time()
                }
                action_func(trigger, context)

            # 更新触发器状态
            trigger.last_triggered = time.time()
            trigger.triggered_count += 1
            self.stats["total_executions"] += 1

            # 发布触发事件
            self._publish_triggered_event(trigger, metric_name, metric)

            # 持久化触发器
            self._save_trigger(trigger)

            logger.info(
                f"✅ Trigger executed: {trigger.name} "
                f"(count: {trigger.triggered_count})"
            )

        except Exception as e:
            logger.error(f"Action execution failed: {e}")

    def _publish_triggered_event(self, trigger: ConditionTrigger, metric_name: str, metric: Dict):
        """发布触发事件到EventBus"""
        if self.eventbus is None:
            return

        event = Event(
            type=EventType.CUSTOM,
            source="condition_engine",
            payload={
                "event_type": "condition.triggered",
                "trigger_id": trigger.id,
                "trigger_name": trigger.name,
                "metric_name": metric_name,
                "current_value": metric.get("value"),
                "old_value": metric.get("old_value"),
                "threshold": trigger.condition.threshold,
                "action_type": trigger.action_type,
                "tags": trigger.tags
            },
            tags=["condition", "triggered"] + trigger.tags
        )
        self.eventbus.publish(event)

    def _save_trigger(self, trigger: ConditionTrigger):
        """持久化触发器"""
        try:
            trigger_file = self.persistence_path / f"{trigger.id}.json"
            with open(trigger_file, "w") as f:
                json.dump(trigger.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trigger: {e}")

    def load_triggers(self):
        """从持久化加载触发器"""
        try:
            for trigger_file in self.persistence_path.glob("*.json"):
                with open(trigger_file) as f:
                    data = json.load(f)
                    trigger = ConditionTrigger.from_dict(data)
                    # 不覆盖已存在的触发器
                    if trigger.id not in self.triggers:
                        self.triggers[trigger.id] = trigger

            self.stats["total_triggers"] = len(self.triggers)
            logger.info(f"Loaded {len(self.triggers)} triggers from persistence")

        except Exception as e:
            logger.error(f"Failed to load triggers: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "active_triggers": len([
                t for t in self.triggers.values() if t.enabled
            ]),
            "metrics_count": len(self.metrics_cache),
            "triggers": [
                {
                    "id": t.id,
                    "name": t.name,
                    "enabled": t.enabled,
                    "triggered_count": t.triggered_count,
                    "last_triggered": t.last_triggered
                }
                for t in self.triggers.values()
            ]
        }

    def start(self):
        """启动引擎"""
        if self.running:
            logger.warning("ConditionEngine already running")
            return

        self.running = True
        self.load_triggers()
        logger.info("ConditionEngine started")

    def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("ConditionEngine stopped")

    def export_config(self) -> Dict:
        """导出配置"""
        return {
            "triggers": [t.to_dict() for t in self.triggers.values()],
            "stats": self.get_stats()
        }


# ============ 便捷函数 ============

def create_threshold_trigger(
    trigger_id: str,
    name: str,
    metric: str,
    comparison: str,
    threshold: float,
    action: str = "log_event",
    cooldown: int = 60
) -> ConditionTrigger:
    """创建阈值触发器"""
    return ConditionTrigger(
        id=trigger_id,
        name=name,
        condition=Condition(
            type=ConditionType.THRESHOLD.value,
            target_metric=metric,
            comparison=comparison,
            threshold=threshold
        ),
        action_type=action,
        cooldown=cooldown
    )


def create_change_trigger(
    trigger_id: str,
    name: str,
    metric: str,
    comparison: str,
    threshold: float,
    action: str = "log_event",
    cooldown: int = 60
) -> ConditionTrigger:
    """创建变化触发器"""
    return ConditionTrigger(
        id=trigger_id,
        name=name,
        condition=Condition(
            type=ConditionType.CHANGE.value,
            target_metric=metric,
            comparison=comparison,
            threshold=threshold
        ),
        action_type=action,
        cooldown=cooldown
    )


def create_composite_trigger(
    trigger_id: str,
    name: str,
    expression: str,
    target_metrics: List[str],
    action: str = "log_event",
    cooldown: int = 60
) -> ConditionTrigger:
    """创建组合触发器"""
    return ConditionTrigger(
        id=trigger_id,
        name=name,
        condition=Condition(
            type=ConditionType.COMPOSITE.value,
            target_metric=target_metrics[0] if target_metrics else "",
            expression=expression,
            target_metrics=target_metrics
        ),
        action_type=action,
        cooldown=cooldown
    )
