#!/usr/bin/env python3
"""
ClawShell EventBus Event Aggregator
事件聚合器模块
功能: 将多个相关事件聚合为单个聚合事件
"""

import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class AggregatedEvent:
    """聚合事件"""
    id: str
    original_event_ids: List[str]
    event_type: str
    count: int
    first_occurrence: float
    last_occurrence: float
    aggregated_data: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AggregationRule:
    """聚合规则"""
    id: str
    name: str
    event_types: List[str]  # 要聚合的事件类型
    time_window: float  # 时间窗口(秒)
    count_threshold: int  # 数量阈值
    aggregation_key: Optional[str]  # 聚合键(可选)
    callback: Optional[Callable] = None  # 聚合完成回调


class EventAggregator:
    """
    事件聚合器
    
    功能：
    - 时间窗口聚合
    - 数量阈值聚合
    - 键值聚合
    - 聚合回调
    """

    def __init__(self):
        self._rules: Dict[str, AggregationRule] = {}
        self._pending_events: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
        
        self._stats = {
            "total_events_received": 0,
            "total_aggregated": 0,
            "rules_created": 0,
        }

    def create_rule(
        self,
        name: str,
        event_types: List[str],
        time_window: float = 60.0,
        count_threshold: int = 10,
        aggregation_key: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> AggregationRule:
        """创建聚合规则"""
        rule = AggregationRule(
            id=f"rule_{len(self._rules)}",
            name=name,
            event_types=event_types,
            time_window=time_window,
            count_threshold=count_threshold,
            aggregation_key=aggregation_key,
            callback=callback
        )
        self._rules[rule.id] = rule
        self._stats["rules_created"] += 1
        return rule

    def receive_event(self, event: Dict) -> Optional[AggregatedEvent]:
        """接收事件并检查是否需要聚合"""
        with self._lock:
            self._stats["total_events_received"] += 1
            
            event_type = event.get("type", "unknown")
            
            # 查找匹配的规则
            for rule_id, rule in self._rules.items():
                if event_type in rule.event_types:
                    self._pending_events[rule_id].append(event)
            
            # 检查每个规则是否满足聚合条件
            aggregated = None
            for rule_id, rule in self._rules.items():
                pending = self._pending_events[rule_id]
                
                if self._should_aggregate(pending, rule):
                    aggregated = self._aggregate_events(rule_id, rule)
                    if aggregated:
                        self._stats["total_aggregated"] += 1
                        if rule.callback:
                            rule.callback(aggregated)
            
            return aggregated

    def _should_aggregate(self, pending: List[Dict], rule: AggregationRule) -> bool:
        """检查是否应该聚合"""
        if len(pending) == 0:
            return False
        
        # 数量阈值
        if len(pending) >= rule.count_threshold:
            return True
        
        # 时间窗口
        if len(pending) >= 2:
            first_time = pending[0].get("timestamp", time.time())
            last_time = pending[-1].get("timestamp", time.time())
            if last_time - first_time >= rule.time_window:
                return True
        
        return False

    def _aggregate_events(self, rule_id: str, rule: AggregationRule) -> Optional[AggregatedEvent]:
        """聚合事件"""
        pending = self._pending_events[rule_id]
        if not pending:
            return None
        
        # 获取聚合键
        if rule.aggregation_key:
            # 按键分组
            groups: Dict[str, List[Dict]] = defaultdict(list)
            for event in pending:
                key = event.get(rule.aggregation_key, "default")
                groups[key].append(event)
            
            # 返回第一个满足条件的组
            for key, events in groups.items():
                if len(events) >= rule.count_threshold:
                    aggregated = self._create_aggregated_event(rule, events)
                    self._pending_events[rule_id] = []
                    return aggregated
        else:
            # 聚合所有待处理事件
            aggregated = self._create_aggregated_event(rule, pending)
            self._pending_events[rule_id] = []
            return aggregated
        
        return None

    def _create_aggregated_event(self, rule: AggregationRule, events: List[Dict]) -> AggregatedEvent:
        """创建聚合事件"""
        timestamps = [e.get("timestamp", time.time()) for e in events]
        
        # 聚合数据
        aggregated_data = {}
        for event in events:
            for key, value in event.get("data", {}).items():
                if key not in aggregated_data:
                    aggregated_data[key] = []
                aggregated_data[key].append(value)
        
        return AggregatedEvent(
            id=f"agg_{int(time.time() * 1000)}",
            original_event_ids=[e.get("id", f"unknown_{i}") for i, e in enumerate(events)],
            event_type=rule.name,
            count=len(events),
            first_occurrence=min(timestamps),
            last_occurrence=max(timestamps),
            aggregated_data=aggregated_data,
            metadata={"rule_id": rule.id}
        )

    def flush_rule(self, rule_id: str) -> Optional[AggregatedEvent]:
        """手动触发规则聚合"""
        with self._lock:
            if rule_id not in self._rules:
                return None
            
            rule = self._rules[rule_id]
            pending = self._pending_events[rule_id]
            
            if not pending:
                return None
            
            aggregated = self._create_aggregated_event(rule, pending)
            self._pending_events[rule_id] = []
            self._stats["total_aggregated"] += 1
            
            return aggregated

    def get_pending_count(self, rule_id: str) -> int:
        """获取待处理事件数"""
        return len(self._pending_events.get(rule_id, []))

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "active_rules": len(self._rules),
            "pending_events": sum(len(v) for v in self._pending_events.values()),
        }

    def clear(self) -> None:
        """清空所有待处理事件"""
        with self._lock:
            self._pending_events.clear()
