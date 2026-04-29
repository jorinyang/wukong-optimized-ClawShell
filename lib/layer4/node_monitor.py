#!/usr/bin/env python3
"""
ClawShell Swarm Node Monitor
节点健康监控模块
版本: v0.2.0-A
功能: 节点状态采集、心跳检测、离线告警
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from swarm.node_registry import NodeRegistry, NodeStatus


# ============ 数据结构 ============

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"        # 未知


@dataclass
class HealthMetrics:
    """健康指标"""
    node_id: str
    status: HealthStatus
    last_heartbeat: float
    response_time_ms: float
    error_count: int
    success_count: int
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime_seconds: int = 0


@dataclass
class HealthAlert:
    """健康告警"""
    node_id: str
    alert_type: str  # offline, degraded, unhealthy
    message: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


# ============ 节点监控器 ============

class NodeMonitor:
    """
    节点健康监控器
    
    功能：
    - 节点状态采集
    - 心跳检测
    - 离线告警
    - 健康评估
    
    使用示例：
        monitor = NodeMonitor(node_registry)
        monitor.start()
        
        # 获取节点健康状态
        health = monitor.get_health(node_id)
        
        # 注册告警回调
        monitor.register_alert_callback(lambda alert: print(f"Alert: {alert.message}"))
        
        monitor.stop()
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        heartbeat_interval: float = 30.0,
        offline_threshold: float = 120.0,
        degraded_threshold: float = 60.0
    ):
        self.node_registry = node_registry
        self.heartbeat_interval = heartbeat_interval
        self.offline_threshold = offline_threshold
        self.degraded_threshold = degraded_threshold
        
        # 健康状态缓存
        self._health_cache: Dict[str, HealthMetrics] = {}
        
        # 告警回调
        self._alert_callbacks: List[Callable] = []
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 统计数据
        self._stats = {
            "total_checks": 0,
            "healthy_count": 0,
            "degraded_count": 0,
            "unhealthy_count": 0,
            "offline_detected": 0
        }

    def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"✅ NodeMonitor started (interval={self.heartbeat_interval}s)")

    def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("✅ NodeMonitor stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_all_nodes()
            except Exception as e:
                print(f"❌ Monitor error: {e}")
            time.sleep(self.heartbeat_interval)

    def _check_all_nodes(self):
        """检查所有节点"""
        current_time = time.time()
        
        for node_id, node in self.node_registry.nodes.items():
            try:
                # 计算响应时间（模拟）
                response_time = self._measure_response_time(node)
                
                # 更新健康指标
                health = HealthMetrics(
                    node_id=node_id,
                    status=self._evaluate_status(node, current_time),
                    last_heartbeat=node.last_seen,
                    response_time_ms=response_time,
                    error_count=getattr(node, 'error_count', 0),
                    success_count=getattr(node, 'success_count', 0)
                )
                
                self._health_cache[node_id] = health
                
                # 检查是否离线
                if current_time - node.last_seen > self.offline_threshold:
                    if node.status != NodeStatus.OFFLINE:
                        self._emit_alert(HealthAlert(
                            node_id=node_id,
                            alert_type="offline",
                            message=f"Node {node.name} is offline"
                        ))
                
                self._stats["total_checks"] += 1
                
            except Exception as e:
                print(f"❌ Error checking node {node_id}: {e}")

    def _measure_response_time(self, node) -> float:
        """测量响应时间"""
        # 实际实现需要根据节点类型调用对应接口
        # 这里简化处理
        return 10.0 + (hash(node.id) % 100)

    def _evaluate_status(self, node, current_time: float) -> HealthStatus:
        """评估健康状态"""
        time_since_seen = current_time - node.last_seen
        
        if time_since_seen > self.offline_threshold:
            return HealthStatus.UNKNOWN
        elif time_since_seen > self.degraded_threshold:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _emit_alert(self, alert: HealthAlert):
        """发送告警"""
        self._stats["offline_detected"] += 1
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"❌ Alert callback error: {e}")

    def register_alert_callback(self, callback: Callable):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def get_health(self, node_id: str) -> Optional[HealthMetrics]:
        """获取节点健康状态"""
        return self._health_cache.get(node_id)

    def get_all_health(self) -> Dict[str, HealthMetrics]:
        """获取所有节点健康状态"""
        return self._health_cache.copy()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "cached_nodes": len(self._health_cache),
            "callbacks_registered": len(self._alert_callbacks)
        }


# ============ 便捷函数 ============

def create_monitor(node_registry: NodeRegistry) -> NodeMonitor:
    """创建监控器"""
    return NodeMonitor(node_registry)
