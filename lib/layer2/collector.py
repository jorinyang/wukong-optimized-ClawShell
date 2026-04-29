"""
State Collector - ClawShell v0.1
=================================

状态采集器。
采集系统状态，为策略切换提供依据。

采集维度：
- API状态（错误率、响应时间）
- 资源状态（内存、CPU、磁盘）
- 任务状态（队列长度、处理速度）
- 业务状态（用户活动、项目进度）
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import psutil

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    """指标样本"""
    name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)


class StateCollector:
    """
    状态采集器
    ==========
    
    采集系统状态指标，供Analyzer和Responder使用。
    
    使用示例：
        collector = StateCollector()
        
        # 采集所有指标
        metrics = collector.collect_all()
        
        # 采集特定维度
        api_metrics = collector.collect_api_status()
        system_metrics = collector.collect_system_status()
    """
    
    def __init__(self):
        self._samples: List[MetricSample] = []
        self._api_error_counts: Dict[str, int] = {}
        self._api_request_counts: Dict[str, int] = {}
        
        logger.info("StateCollector initialized")
    
    def collect_all(self) -> Dict[str, float]:
        """
        采集所有指标
        
        Returns:
            指标字典
        """
        metrics = {}
        
        # 系统状态
        system_metrics = self.collect_system_status()
        metrics.update(system_metrics)
        
        # API状态
        api_metrics = self.collect_api_status()
        metrics.update(api_metrics)
        
        # 业务状态
        business_metrics = self.collect_business_status()
        metrics.update(business_metrics)
        
        return metrics
    
    def collect_system_status(self) -> Dict[str, float]:
        """
        采集系统状态
        
        Returns:
            系统指标字典
        """
        try:
            # CPU使用率（interval=None返回自上次调用的平均值，首次调用需要interval）
            cpu_percent = psutil.cpu_percent(interval=None)
            if cpu_percent == 0:  # 首次调用，强制采集
                cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            metrics = {
                "system.cpu_percent": min(cpu_percent, 100.0),  # 确保不超过100
                "system.memory_percent": memory_percent,
                "system.disk_percent": disk_percent,
            }
            
            logger.debug(f"System metrics: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect system status: {e}")
            return {
                "system.cpu_percent": 0,
                "system.memory_percent": 0,
                "system.disk_percent": 0,
            }
    
    def collect_api_status(self) -> Dict[str, float]:
        """
        采集API状态
        
        Returns:
            API指标字典
        """
        metrics = {}
        
        # 计算各API的错误率
        for api_name in self._api_error_counts.keys():
            errors = self._api_error_counts.get(api_name, 0)
            requests = self._api_request_counts.get(api_name, 1)
            error_rate = errors / requests if requests > 0 else 0
            metrics[f"api.{api_name}.error_rate"] = error_rate
            metrics[f"api.{api_name}.request_count"] = requests
            metrics[f"api.{api_name}.error_count"] = errors
        
        # 全局错误率
        total_errors = sum(self._api_error_counts.values())
        total_requests = sum(self._api_request_counts.values())
        if total_requests > 0:
            metrics["api.error_rate"] = total_errors / total_requests
        else:
            metrics["api.error_rate"] = 0
        
        logger.debug(f"API metrics: {metrics}")
        return metrics
    
    def collect_business_status(self) -> Dict[str, float]:
        """
        采集业务状态
        
        Returns:
            业务指标字典
        """
        # 事件队列长度
        try:
            from eventbus import EventBus
            bus = EventBus()
            history = bus.get_history(limit=1000)
            
            # 计算任务完成率
            completed = len([e for e in history if "task.completed" in str(e.type)])
            failed = len([e for e in history if "task.failed" in str(e.type)])
            total = completed + failed
            
            task_completion_rate = completed / total if total > 0 else 1.0
            
            return {
                "business.event_queue_length": len(history),
                "business.task_completion_rate": task_completion_rate,
                "business.task_completed": completed,
                "business.task_failed": failed,
            }
        except Exception as e:
            logger.debug(f"Could not collect business status: {e}")
            return {
                "business.event_queue_length": 0,
                "business.task_completion_rate": 1.0,
            }
    
    def record_api_call(self, api_name: str, success: bool):
        """
        记录API调用
        
        Args:
            api_name: API名称
            success: 是否成功
        """
        if api_name not in self._api_request_counts:
            self._api_request_counts[api_name] = 0
            self._api_error_counts[api_name] = 0
        
        self._api_request_counts[api_name] += 1
        if not success:
            self._api_error_counts[api_name] += 1
    
    def record_error(self, error_type: str):
        """
        记录错误
        
        Args:
            error_type: 错误类型
        """
        self._samples.append(MetricSample(
            name=f"error.{error_type}",
            value=1,
            tags=["error", error_type],
        ))
    
    def get_sample(self, metric_name: str, last: int = 10) -> List[MetricSample]:
        """
        获取指标样本
        
        Args:
            metric_name: 指标名称
            last: 获取最近N个
        
        Returns:
            样本列表
        """
        samples = [s for s in self._samples if s.name == metric_name]
        return samples[-last:]
    
    def clear_samples(self):
        """清空样本"""
        self._samples.clear()
        self._api_error_counts.clear()
        self._api_request_counts.clear()


# 全局单例
_collector: Optional[StateCollector] = None


def get_collector() -> StateCollector:
    """获取全局状态采集器实例"""
    global _collector
    if _collector is None:
        _collector = StateCollector()
    return _collector
