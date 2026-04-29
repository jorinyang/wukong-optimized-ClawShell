"""
StateCollector - 状态收集器
Adaptor 模块组件
"""

import psutil
import time
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class StateCollector:
    """
    状态收集器
    
    负责收集系统状态和性能指标。
    
    Example:
        collector = StateCollector()
        
        # 收集指标
        metrics = collector.collect_metrics()
        
        # 获取系统状态
        status = collector.get_system_status()
    """
    
    def __init__(self):
        """初始化状态收集器"""
        self._metrics_history: List[Dict] = []
        self._max_history = 100
        logger.info("StateCollector initialized")
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        收集系统指标
        
        Returns:
            指标字典
        """
        metrics = {
            "timestamp": time.time(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
            },
            "business": {
                "task_completed": 0,
                "task_failed": 0,
                "event_queue_length": 0,
            }
        }
        
        # 保存到历史
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]
        
        return metrics
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            状态字典
        """
        metrics = self.collect_metrics()
        
        # 计算状态
        cpu_status = "normal" if metrics["system"]["cpu_percent"] < 80 else "warning"
        memory_status = "normal" if metrics["system"]["memory_percent"] < 80 else "warning"
        disk_status = "normal" if metrics["system"]["disk_percent"] < 90 else "warning"
        
        return {
            "cpu": {
                "percent": metrics["system"]["cpu_percent"],
                "status": cpu_status
            },
            "memory": {
                "percent": metrics["system"]["memory_percent"],
                "status": memory_status
            },
            "disk": {
                "percent": metrics["system"]["disk_percent"],
                "status": disk_status
            },
            "overall": "healthy" if all([
                cpu_status == "normal",
                memory_status == "normal",
                disk_status == "normal"
            ]) else "degraded"
        }
    
    def get_metrics_history(self, limit: int = 10) -> List[Dict]:
        """
        获取指标历史
        
        Args:
            limit: 返回数量限制
        
        Returns:
            指标历史列表
        """
        return self._metrics_history[-limit:]
    
    def check_threshold(self, metric: str, threshold: float) -> bool:
        """
        检查指标是否超过阈值
        
        Args:
            metric: 指标名称 (cpu/memory/disk)
            threshold: 阈值
        
        Returns:
            是否超过阈值
        """
        metrics = self.collect_metrics()
        
        if metric == "cpu":
            return metrics["system"]["cpu_percent"] > threshold
        elif metric == "memory":
            return metrics["system"]["memory_percent"] > threshold
        elif metric == "disk":
            return metrics["system"]["disk_percent"] > threshold
        
        return False
