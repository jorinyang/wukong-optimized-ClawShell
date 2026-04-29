#!/usr/bin/env python3
"""
ClawShell EventBus Event Metrics
事件指标收集模块
功能: 收集、统计、分析事件流指标
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import json


@dataclass
class EventMetric:
    """事件指标"""
    event_type: str
    count: int = 0
    total_size: int = 0
    avg_size: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    avg_latency: float = 0.0
    error_count: int = 0
    last_occurrence: float = 0
    first_occurrence: float = 0


@dataclass
class MetricsSnapshot:
    """指标快照"""
    timestamp: float
    total_events: int
    total_errors: int
    throughput: float  # 事件/秒
    avg_latency: float
    metrics: Dict[str, EventMetric]


class EventMetrics:
    """
    事件指标收集器
    
    功能：
    - 事件计数
    - 延迟统计
    - 吞吐量监控
    - 错误率追踪
    - 指标快照
    """

    def __init__(self, window_size: int = 60):
        self.window_size = window_size  # 时间窗口(秒)
        
        self._metrics: Dict[str, EventMetric] = {}
        self._event_history: List[Dict] = []  # 滑动窗口
        self._lock = threading.Lock()
        
        self._stats = {
            "total_events": 0,
            "total_errors": 0,
            "snapshots_taken": 0,
        }

    def record_event(self, event_type: str, size: int = 0, 
                    latency: float = 0.0, is_error: bool = False) -> None:
        """记录事件"""
        with self._lock:
            current_time = time.time()
            
            # 更新指标
            if event_type not in self._metrics:
                self._metrics[event_type] = EventMetric(
                    event_type=event_type,
                    first_occurrence=current_time
                )
            
            metric = self._metrics[event_type]
            metric.count += 1
            metric.total_size += size
            metric.avg_size = metric.total_size / metric.count
            metric.last_occurrence = current_time
            
            if latency > 0:
                metric.min_latency = min(metric.min_latency, latency)
                metric.max_latency = max(metric.max_latency, latency)
                # 简化平均计算
                if metric.avg_latency == 0:
                    metric.avg_latency = latency
                else:
                    metric.avg_latency = (metric.avg_latency + latency) / 2
            
            if is_error:
                metric.error_count += 1
                self._stats["total_errors"] += 1
            
            # 添加到历史
            self._event_history.append({
                "timestamp": current_time,
                "event_type": event_type,
                "is_error": is_error,
                "latency": latency,
                "size": size,
            })
            
            self._stats["total_events"] += 1
            
            # 清理滑动窗口
            self._cleanup_history(current_time)

    def _cleanup_history(self, current_time: float) -> None:
        """清理过期历史"""
        cutoff = current_time - self.window_size
        self._event_history = [
            e for e in self._event_history 
            if e["timestamp"] >= cutoff
        ]

    def get_metric(self, event_type: str) -> Optional[EventMetric]:
        """获取特定事件类型指标"""
        return self._metrics.get(event_type)

    def get_all_metrics(self) -> Dict[str, EventMetric]:
        """获取所有指标"""
        return dict(self._metrics)

    def get_snapshot(self) -> MetricsSnapshot:
        """获取当前快照"""
        with self._lock:
            current_time = time.time()
            
            # 计算吞吐量
            history_start = current_time - self.window_size
            recent_events = [e for e in self._event_history if e["timestamp"] >= history_start]
            throughput = len(recent_events) / self.window_size if self.window_size > 0 else 0
            
            # 计算总体延迟
            latencies = [e["latency"] for e in recent_events if e["latency"] > 0]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            return MetricsSnapshot(
                timestamp=current_time,
                total_events=self._stats["total_events"],
                total_errors=self._stats["total_errors"],
                throughput=throughput,
                avg_latency=avg_latency,
                metrics=dict(self._metrics)
            )

    def get_top_events(self, limit: int = 10, by: str = "count") -> List[EventMetric]:
        """获取Top N事件"""
        metrics = list(self._metrics.values())
        
        if by == "count":
            return sorted(metrics, key=lambda x: x.count, reverse=True)[:limit]
        elif by == "error":
            return sorted(metrics, key=lambda x: x.error_count, reverse=True)[:limit]
        elif by == "latency":
            return sorted(metrics, key=lambda x: x.avg_latency, reverse=True)[:limit]
        
        return metrics[:limit]

    def get_error_rate(self, event_type: Optional[str] = None) -> float:
        """获取错误率"""
        with self._lock:
            if event_type:
                metric = self._metrics.get(event_type)
                if metric and metric.count > 0:
                    return metric.error_count / metric.count
                return 0.0
            
            total = sum(m.count for m in self._metrics.values())
            errors = sum(m.error_count for m in self._metrics.values())
            
            return errors / total if total > 0 else 0.0

    def get_throughput_history(self, points: int = 60) -> List[Dict]:
        """获取吞吐量历史"""
        with self._lock:
            if not self._event_history:
                return []
            
            # 计算每个时间点的吞吐量
            current_time = time.time()
            interval = self.window_size / points
            
            history = []
            for i in range(points):
                start = current_time - self.window_size + (i * interval)
                end = start + interval
                count = sum(1 for e in self._event_history 
                          if start <= e["timestamp"] < end)
                history.append({
                    "timestamp": end,
                    "count": count,
                    "throughput": count / interval if interval > 0 else 0
                })
            
            return history

    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict]:
        """检测异常"""
        with self._lock:
            anomalies = []
            
            for event_type, metric in self._metrics.items():
                if metric.count == 0:
                    continue
                
                # 计算基于历史的异常
                history_start = time.time() - self.window_size
                recent = [e for e in self._event_history 
                         if e["event_type"] == event_type and e["timestamp"] >= history_start]
                
                if len(recent) < 5:
                    continue
                
                recent_latencies = [e["latency"] for e in recent if e["latency"] > 0]
                if not recent_latencies:
                    continue
                
                mean = sum(recent_latencies) / len(recent_latencies)
                variance = sum((x - mean) ** 2 for x in recent_latencies) / len(recent_latencies)
                std = variance ** 0.5
                
                # 检查当前延迟是否异常
                if metric.avg_latency > mean + (threshold * std):
                    anomalies.append({
                        "event_type": event_type,
                        "type": "high_latency",
                        "current": metric.avg_latency,
                        "expected": mean,
                        "deviation": (metric.avg_latency - mean) / std if std > 0 else 0,
                    })
                
                # 检查错误率
                recent_errors = sum(1 for e in recent if e["is_error"])
                recent_error_rate = recent_errors / len(recent)
                if recent_error_rate > 0.1:  # 超过10%
                    anomalies.append({
                        "event_type": event_type,
                        "type": "high_error_rate",
                        "current": recent_error_rate,
                        "threshold": 0.1,
                    })
            
            return anomalies

    def export_metrics(self) -> str:
        """导出指标为JSON"""
        snapshot = self.get_snapshot()
        data = {
            "timestamp": snapshot.timestamp,
            "total_events": snapshot.total_events,
            "total_errors": snapshot.total_errors,
            "throughput": snapshot.throughput,
            "avg_latency": snapshot.avg_latency,
            "metrics": {
                event_type: {
                    "count": m.count,
                    "avg_size": m.avg_size,
                    "min_latency": m.min_latency,
                    "max_latency": m.max_latency,
                    "avg_latency": m.avg_latency,
                    "error_count": m.error_count,
                    "error_rate": m.error_count / m.count if m.count > 0 else 0,
                }
                for event_type, m in snapshot.metrics.items()
            }
        }
        return json.dumps(data, indent=2)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                **self._stats,
                "tracked_event_types": len(self._metrics),
                "history_size": len(self._event_history),
            }
