#!/usr/bin/env python3
"""
ClawShell Swarm Metrics Collector
指标收集模块
版本: v0.2.0-A
功能: 性能指标采集、可用性统计、协作质量评估
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


# ============ 数据结构 ============

@dataclass
class PerformanceMetrics:
    """性能指标"""
    node_id: str
    timestamp: float
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    uptime_seconds: int = 0


@dataclass
class AvailabilityMetrics:
    """可用性指标"""
    node_id: str
    timestamp: float
    uptime_percent: float = 0.0
    downtime_seconds: int = 0
    incidents_count: int = 0
    mttr_minutes: float = 0.0  # Mean Time To Recovery


@dataclass
class CollaborationMetrics:
    """协作指标"""
    node_id: str
    timestamp: float
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_duration_seconds: float = 0.0
    collaboration_score: float = 0.0  # 0-100


# ============ 指标收集器 ============

class MetricsCollector:
    """
    指标收集器
    
    功能：
    - 性能指标采集
    - 可用性统计
    - 协作质量评估
    - 历史数据管理
    
    使用示例：
        collector = MetricsCollector()
        
        # 记录请求
        collector.record_request(node_id, success=True, response_time=50)
        
        # 获取性能指标
        perf = collector.get_performance(node_id)
        
        # 获取可用性
        avail = collector.get_availability(node_id)
        
        # 获取协作指标
        collab = collector.get_collaboration(node_id)
    """

    def __init__(
        self,
        retention_hours: int = 24,
        aggregation_interval: int = 300  # 5分钟聚合
    ):
        self.retention_hours = retention_hours
        self.aggregation_interval = aggregation_interval
        
        # 性能数据
        self._performance_data: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        
        # 可用性数据
        self._availability_data: Dict[str, List[AvailabilityMetrics]] = defaultdict(list)
        
        # 协作数据
        self._collaboration_data: Dict[str, List[CollaborationMetrics]] = defaultdict(list)
        
        # 原始计数器
        self._request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total": 0, "success": 0, "failed": 0, "total_time": 0, "min_time": float("inf"), "max_time": 0
        })
        
        # 统计数据
        self._stats = {
            "total_records": 0,
            "nodes_tracked": 0,
            "oldest_record_age_hours": 0
        }

    def record_request(
        self,
        node_id: str,
        success: bool,
        response_time: float,
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0
    ):
        """记录请求"""
        counts = self._request_counts[node_id]
        counts["total"] += 1
        if success:
            counts["success"] += 1
        else:
            counts["failed"] += 1
        
        counts["total_time"] += response_time
        counts["min_time"] = min(counts["min_time"], response_time)
        counts["max_time"] = max(counts["max_time"], response_time)
        
        # 更新实时指标
        self._update_performance_metrics(node_id, cpu_usage, memory_usage)

    def record_task(
        self,
        node_id: str,
        completed: bool,
        duration_seconds: float
    ):
        """记录任务"""
        collab_data = self._collaboration_data[node_id]
        
        if not collab_data:
            collab_data.append(CollaborationMetrics(
                node_id=node_id,
                timestamp=time.time(),
                tasks_assigned=1,
                tasks_completed=1 if completed else 0,
                tasks_failed=0 if completed else 1,
                avg_task_duration_seconds=duration_seconds
            ))
        else:
            latest = collab_data[-1]
            latest.tasks_assigned += 1
            if completed:
                latest.tasks_completed += 1
            else:
                latest.tasks_failed += 1
            
            # 更新平均任务时长
            total_duration = latest.avg_task_duration_seconds * (latest.tasks_completed + latest.tasks_failed - 1)
            latest.avg_task_duration_seconds = (total_duration + duration_seconds) / (latest.tasks_completed + latest.tasks_failed)

    def get_performance(
        self,
        node_id: str,
        window_seconds: float = 3600
    ) -> Optional[PerformanceMetrics]:
        """获取性能指标"""
        if node_id not in self._performance_data:
            return None
        
        current_time = time.time()
        recent = [
            m for m in self._performance_data[node_id]
            if current_time - m.timestamp <= window_seconds
        ]
        
        if not recent:
            return None
        
        # 聚合最近的数据
        return self._aggregate_performance(recent)

    def get_availability(
        self,
        node_id: str,
        window_hours: float = 24
    ) -> Optional[AvailabilityMetrics]:
        """获取可用性指标"""
        if node_id not in self._availability_data:
            return None
        
        window_seconds = window_hours * 3600
        current_time = time.time()
        recent = [
            m for m in self._availability_data[node_id]
            if current_time - m.timestamp <= window_seconds
        ]
        
        if not recent:
            return None
        
        return self._aggregate_availability(recent)

    def get_collaboration(
        self,
        node_id: str,
        window_seconds: float = 86400  # 24小时
    ) -> Optional[CollaborationMetrics]:
        """获取协作指标"""
        if node_id not in self._collaboration_data:
            return None
        
        current_time = time.time()
        recent = [
            m for m in self._collaboration_data[node_id]
            if current_time - m.timestamp <= window_seconds
        ]
        
        if not recent:
            return None
        
        return self._aggregate_collaboration(recent)

    def get_all_metrics_summary(self, node_id: str) -> Dict:
        """获取所有指标摘要"""
        return {
            "performance": self.get_performance(node_id).__dict__ if self.get_performance(node_id) else None,
            "availability": self.get_availability(node_id).__dict__ if self.get_availability(node_id) else None,
            "collaboration": self.get_collaboration(node_id).__dict__ if self.get_collaboration(node_id) else None
        }

    def cleanup_old_data(self):
        """清理过期数据"""
        cutoff_time = time.time() - self.retention_hours * 3600
        
        for node_id in list(self._performance_data.keys()):
            self._performance_data[node_id] = [
                m for m in self._performance_data[node_id]
                if m.timestamp > cutoff_time
            ]
            if not self._performance_data[node_id]:
                del self._performance_data[node_id]
        
        # 统计
        self._stats["nodes_tracked"] = len(self._performance_data)
        
        if self._performance_data:
            oldest = min(
                m.timestamp for m in self._performance_data.values()
                for m in m
            )
            self._stats["oldest_record_age_hours"] = (time.time() - oldest) / 3600
        else:
            self._stats["oldest_record_age_hours"] = 0

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "nodes_tracked": len(self._performance_data),
            "performance_records": sum(len(v) for v in self._performance_data.values()),
            "collaboration_records": sum(len(v) for v in self._collaboration_data.values())
        }

    def _update_performance_metrics(
        self,
        node_id: str,
        cpu_usage: float,
        memory_usage: float
    ):
        """更新性能指标"""
        counts = self._request_counts[node_id]
        
        if counts["total"] == 0:
            return
        
        metrics = PerformanceMetrics(
            node_id=node_id,
            timestamp=time.time(),
            requests_total=counts["total"],
            requests_success=counts["success"],
            requests_failed=counts["failed"],
            avg_response_time_ms=counts["total_time"] / counts["total"],
            min_response_time_ms=counts["min_time"] if counts["min_time"] != float("inf") else 0,
            max_response_time_ms=counts["max_time"],
            cpu_usage_percent=cpu_usage,
            memory_usage_percent=memory_usage
        )
        
        self._performance_data[node_id].append(metrics)
        self._stats["total_records"] += 1
        
        # 保持最近1000条记录
        if len(self._performance_data[node_id]) > 1000:
            self._performance_data[node_id].pop(0)

    def _aggregate_performance(self, metrics: List[PerformanceMetrics]) -> PerformanceMetrics:
        """聚合性能指标"""
        return PerformanceMetrics(
            node_id=metrics[0].node_id,
            timestamp=time.time(),
            requests_total=sum(m.requests_total for m in metrics),
            requests_success=sum(m.requests_success for m in metrics),
            requests_failed=sum(m.requests_failed for m in metrics),
            avg_response_time_ms=sum(m.avg_response_time_ms for m in metrics) / len(metrics),
            min_response_time_ms=min(m.min_response_time_ms for m in metrics),
            max_response_time_ms=max(m.max_response_time_ms for m in metrics),
            cpu_usage_percent=sum(m.cpu_usage_percent for m in metrics) / len(metrics),
            memory_usage_percent=sum(m.memory_usage_percent for m in metrics) / len(metrics)
        )

    def _aggregate_availability(self, metrics: List[AvailabilityMetrics]) -> AvailabilityMetrics:
        """聚合可用性指标"""
        return AvailabilityMetrics(
            node_id=metrics[0].node_id,
            timestamp=time.time(),
            uptime_percent=sum(m.uptime_percent for m in metrics) / len(metrics),
            downtime_seconds=sum(m.downtime_seconds for m in metrics),
            incidents_count=sum(m.incidents_count for m in metrics),
            mttr_minutes=sum(m.mttr_minutes for m in metrics) / len(metrics) if metrics else 0
        )

    def _aggregate_collaboration(self, metrics: List[CollaborationMetrics]) -> CollaborationMetrics:
        """聚合协作指标"""
        total_tasks = sum(m.tasks_assigned for m in metrics)
        completed = sum(m.tasks_completed for m in metrics)
        failed = sum(m.tasks_failed for m in metrics)
        
        return CollaborationMetrics(
            node_id=metrics[0].node_id,
            timestamp=time.time(),
            tasks_assigned=total_tasks,
            tasks_completed=completed,
            tasks_failed=failed,
            avg_task_duration_seconds=sum(m.avg_task_duration_seconds for m in metrics) / len(metrics),
            collaboration_score=(completed / total_tasks * 100) if total_tasks > 0 else 0
        )


# ============ 便捷函数 ============

def create_collector(retention_hours: int = 24) -> MetricsCollector:
    """创建收集器"""
    return MetricsCollector(retention_hours=retention_hours)
