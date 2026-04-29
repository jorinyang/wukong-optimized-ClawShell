#!/usr/bin/env python3
"""
ClawShell Adaptive Controller
自适应控制器 - Phase 3
版本: v1.0.0
功能: 实时监控+动态调节(神经反馈机制)
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

@dataclass
class MetricSnapshot:
    """指标快照"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    response_time: float
    error_rate: float
    throughput: float

@dataclass
class FeedbackSignal:
    """反馈信号"""
    metric: str
    current: float
    target: float
    deviation: float
    adjustment: float
    applied: bool = False

class AdaptiveController:
    """
    自适应控制器(神经反馈机制)
    
    功能：
    - 实时性能监控
    - 偏差检测
    - 自动调节
    - 反馈闭环
    """
    
    def __init__(
        self,
        target_response_time: float = 1.0,
        target_error_rate: float = 0.01,
        target_cpu: float = 70.0
    ):
        # 目标值
        self.target_response_time = target_response_time
        self.target_error_rate = target_error_rate
        self.target_cpu = target_cpu
        
        # 当前状态
        self.current_metrics: Dict[str, float] = {}
        self.history: deque = deque(maxlen=100)
        
        # 调节器
        self.adjustments: List[FeedbackSignal] = []
        
        # 回调函数
        self.callbacks: Dict[str, Callable] = {}
        
        # 控制线程
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def set_callback(self, metric: str, callback: Callable[[float], None]):
        """设置调节回调"""
        self.callbacks[metric] = callback
    
    def record_metric(self, metric: str, value: float):
        """记录指标"""
        self.current_metrics[metric] = value
        
        # 记录历史
        snapshot = MetricSnapshot(
            timestamp=time.time(),
            cpu_percent=self.current_metrics.get("cpu", 0),
            memory_percent=self.current_metrics.get("memory", 0),
            response_time=self.current_metrics.get("response_time", 0),
            error_rate=self.current_metrics.get("error_rate", 0),
            throughput=self.current_metrics.get("throughput", 0)
        )
        self.history.append(snapshot)
        
        # 检查偏差
        self._check_deviation(metric, value)
    
    def _check_deviation(self, metric: str, value: float):
        """检查偏差并调节"""
        target = self._get_target(metric)
        if target is None:
            return
        
        deviation = value - target
        deviation_percent = abs(deviation) / target if target > 0 else 0
        
        # 如果偏差超过10%，触发调节
        if deviation_percent > 0.1:
            adjustment = self._calculate_adjustment(metric, value, target, deviation)
            
            signal = FeedbackSignal(
                metric=metric,
                current=value,
                target=target,
                deviation=deviation,
                adjustment=adjustment
            )
            
            self.adjustments.append(signal)
            
            # 应用调节
            self._apply_adjustment(signal)
    
    def _get_target(self, metric: str) -> Optional[float]:
        """获取目标值"""
        targets = {
            "response_time": self.target_response_time,
            "error_rate": self.target_error_rate,
            "cpu": self.target_cpu
        }
        return targets.get(metric)
    
    def _calculate_adjustment(
        self,
        metric: str,
        current: float,
        target: float,
        deviation: float
    ) -> float:
        """计算调节量"""
        # PID控制器的简化版本
        Kp = 0.5  # 比例系数
        
        # 根据指标类型调整
        if metric == "response_time":
            # 响应时间过高，降低负载
            return -deviation * Kp
        elif metric == "error_rate":
            # 错误率过高，启用备用方案
            return -deviation * Kp * 2
        elif metric == "cpu":
            # CPU过高，限流
            return -deviation * Kp * 0.5
        
        return -deviation * Kp
    
    def _apply_adjustment(self, signal: FeedbackSignal):
        """应用调节"""
        if signal.metric in self.callbacks:
            try:
                self.callbacks[signal.metric](signal.adjustment)
                signal.applied = True
            except Exception as e:
                print(f"Failed to apply adjustment: {e}")
    
    def start_monitoring(self, interval: float = 5.0):
        """开始监控"""
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self._monitoring:
            # 检查历史数据
            if len(self.history) >= 10:
                recent = list(self.history)[-10:]
                
                # 计算平均指标
                avg_response = sum(s.response_time for s in recent) / 10
                avg_error = sum(s.error_rate for s in recent) / 10
                
                # 记录
                self.record_metric("response_time", avg_response)
                self.record_metric("error_rate", avg_error)
            
            time.sleep(interval)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "monitoring": self._monitoring,
            "current_metrics": self.current_metrics,
            "total_adjustments": len(self.adjustments),
            "applied_adjustments": sum(1 for a in self.adjustments if a.applied),
            "targets": {
                "response_time": self.target_response_time,
                "error_rate": self.target_error_rate,
                "cpu": self.target_cpu
            }
        }

if __name__ == "__main__":
    controller = AdaptiveController()
    
    print("=== 自适应控制器测试 ===")
    
    # 模拟指标记录
    controller.record_metric("response_time", 1.2)
    controller.record_metric("response_time", 0.9)
    controller.record_metric("error_rate", 0.02)
    
    # 设置回调
    def on_high_cpu(adjustment):
        print(f"CPU调节: {adjustment}")
    
    controller.set_callback("cpu", on_high_cpu)
    
    # 测试调节
    controller.record_metric("cpu", 85.0)
    
    print(f"\n状态: {controller.get_status()}")
    print(f"\n调节历史:")
    for adj in controller.adjustments:
        print(f"  {adj.metric}: {adj.current} -> {adj.target} (调整: {adj.adjustment:.2f})")
