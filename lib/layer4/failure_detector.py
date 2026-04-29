#!/usr/bin/env python3
"""
ClawShell Swarm Failure Detector
故障检测模块
版本: v0.2.0-A
功能: 连续失败检测、超时检测、异常模式识别
"""

import time
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


# ============ 数据结构 ============

class FailureType(Enum):
    """故障类型"""
    TIMEOUT = "timeout"           # 超时
    ERROR = "error"              # 错误
    OFFLINE = "offline"          # 离线
    DEGRADED = "degraded"        # 降级
    MEMORY = "memory"            # 内存问题
    CPU = "cpu"                  # CPU问题


@dataclass
class FailureRecord:
    """故障记录"""
    node_id: str
    failure_type: FailureType
    timestamp: float
    message: str
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class FailurePattern:
    """故障模式"""
    node_id: str
    pattern_type: str            # continuous_failure, intermittent, spike
    count: int                   # 失败次数
    first_seen: float
    last_seen: float
    interval_avg: float          # 平均间隔


# ============ 故障检测器 ============

class FailureDetector:
    """
    故障检测器
    
    功能：
    - 连续失败检测
    - 超时检测
    - 异常模式识别
    - 故障统计
    
    使用示例：
        detector = FailureDetector()
        
        # 记录失败
        detector.record_failure(node_id, FailureType.TIMEOUT, "Request timeout")
        
        # 检查是否异常
        is_anomalous = detector.is_anomalous(node_id)
        
        # 获取故障记录
        records = detector.get_failures(node_id)
    """

    def __init__(
        self,
        continuous_failure_threshold: int = 3,
        timeout_threshold: float = 30.0,
        anomaly_score_threshold: float = 70.0
    ):
        self.continuous_failure_threshold = continuous_failure_threshold
        self.timeout_threshold = timeout_threshold
        self.anomaly_score_threshold = anomaly_score_threshold
        
        # 失败记录
        self._failure_records: Dict[str, List[FailureRecord]] = {}
        
        # 连续失败计数
        self._consecutive_failures: Dict[str, int] = {}
        
        # 上次成功时间
        self._last_success: Dict[str, float] = {}
        
        # 故障模式
        self._patterns: Dict[str, FailurePattern] = {}
        
        # 回调函数
        self._callbacks: List[Callable] = []
        
        # 统计数据
        self._stats = {
            "total_failures": 0,
            "timeout_failures": 0,
            "error_failures": 0,
            "offline_failures": 0,
            "anomaly_detected": 0
        }

    def record_failure(
        self,
        node_id: str,
        failure_type: FailureType,
        message: str = ""
    ):
        """记录失败"""
        # 创建失败记录
        record = FailureRecord(
            node_id=node_id,
            failure_type=failure_type,
            timestamp=time.time(),
            message=message
        )
        
        # 添加到记录列表
        if node_id not in self._failure_records:
            self._failure_records[node_id] = []
        self._failure_records[node_id].append(record)
        
        # 保持最近100条记录
        if len(self._failure_records[node_id]) > 100:
            self._failure_records[node_id].pop(0)
        
        # 更新连续失败计数
        self._consecutive_failures[node_id] = self._consecutive_failures.get(node_id, 0) + 1
        
        # 更新统计
        self._stats["total_failures"] += 1
        if failure_type == FailureType.TIMEOUT:
            self._stats["timeout_failures"] += 1
        elif failure_type == FailureType.ERROR:
            self._stats["error_failures"] += 1
        elif failure_type == FailureType.OFFLINE:
            self._stats["offline_failures"] += 1
        
        # 检测异常
        if self._detect_anomaly(node_id):
            self._stats["anomaly_detected"] += 1
            self._emit_anomaly_alert(node_id)
        
        # 识别模式
        self._recognize_pattern(node_id)

    def record_success(self, node_id: str):
        """记录成功"""
        self._last_success[node_id] = time.time()
        self._consecutive_failures[node_id] = 0

    def is_anomalous(self, node_id: str) -> bool:
        """检查是否异常"""
        consecutive = self._consecutive_failures.get(node_id, 0)
        return consecutive >= self.continuous_failure_threshold

    def get_failure_rate(self, node_id: str, window_seconds: float = 3600) -> float:
        """获取失败率"""
        if node_id not in self._failure_records:
            return 0.0
        
        current_time = time.time()
        recent_failures = [
            r for r in self._failure_records[node_id]
            if current_time - r.timestamp <= window_seconds
        ]
        
        # 估算总操作数（失败 + 成功）
        total_ops = len(recent_failures) + len([
            t for t, s in self._last_success.items()
            if node_id in t and current_time - s <= window_seconds
        ])
        
        if total_ops == 0:
            return 0.0
        
        return len(recent_failures) / total_ops * 100

    def get_failures(
        self,
        node_id: str,
        limit: int = 10,
        unresolved_only: bool = False
    ) -> List[FailureRecord]:
        """获取失败记录"""
        if node_id not in self._failure_records:
            return []
        
        records = self._failure_records[node_id]
        if unresolved_only:
            records = [r for r in records if not r.resolved]
        
        return records[-limit:]

    def resolve_failure(self, node_id: str, index: int = -1):
        """标记失败为已解决"""
        if node_id in self._failure_records and self._failure_records[node_id]:
            record = self._failure_records[node_id][index]
            record.resolved = True
            record.resolved_at = time.time()

    def get_pattern(self, node_id: str) -> Optional[FailurePattern]:
        """获取故障模式"""
        return self._patterns.get(node_id)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "nodes_with_failures": len(self._failure_records),
            "anomalous_nodes": sum(1 for c in self._consecutive_failures.values() if c >= self.continuous_failure_threshold)
        }

    def register_callback(self, callback: Callable):
        """注册回调"""
        self._callbacks.append(callback)

    def _detect_anomaly(self, node_id: str) -> bool:
        """检测异常"""
        consecutive = self._consecutive_failures.get(node_id, 0)
        return consecutive >= self.continuous_failure_threshold

    def _recognize_pattern(self, node_id: str):
        """识别故障模式"""
        if node_id not in self._failure_records or len(self._failure_records[node_id]) < 3:
            return
        
        records = self._failure_records[node_id][-10:]
        timestamps = [r.timestamp for r in records]
        
        # 计算间隔
        intervals = []
        for i in range(1, len(timestamps)):
            intervals.append(timestamps[i] - timestamps[i-1])
        
        if not intervals:
            return
        
        interval_avg = sum(intervals) / len(intervals)
        
        # 判断模式类型
        if all(i < 60 for i in intervals):  # 间隔都小于1分钟
            pattern_type = "continuous_failure"
        elif max(intervals) > 300:  # 有超过5分钟的间隔
            pattern_type = "intermittent"
        else:
            pattern_type = "spike"
        
        self._patterns[node_id] = FailurePattern(
            node_id=node_id,
            pattern_type=pattern_type,
            count=len(records),
            first_seen=timestamps[0],
            last_seen=timestamps[-1],
            interval_avg=interval_avg
        )

    def _emit_anomaly_alert(self, node_id: str):
        """发送异常告警"""
        for callback in self._callbacks:
            try:
                callback(node_id, self._consecutive_failures.get(node_id, 0))
            except Exception as e:
                print(f"❌ Anomaly callback error: {e}")


# ============ 便捷函数 ============

def create_detector(
    continuous_failure_threshold: int = 3,
    timeout_threshold: float = 30.0
) -> FailureDetector:
    """创建检测器"""
    return FailureDetector(
        continuous_failure_threshold=continuous_failure_threshold,
        timeout_threshold=timeout_threshold
    )
