"""
Event Publisher - ClawShell v0.1
================================

事件发布者封装。
提供便捷的事件发布接口。
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .schema import Event, EventType


class Publisher:
    """
    事件发布器
    ==========
    
    提供便捷的事件发布接口，支持快速创建和发送事件。
    
    使用示例：
        pub = Publisher(source="openclaw")
        
        # 发布任务完成事件
        pub.task_completed(task_id="123", result={"status": "ok"})
        
        # 发布错误事件
        pub.error_occurred(error_type="APIError", message="timeout")
    """
    
    def __init__(self, source: str = "system"):
        """
        初始化发布器
        
        Args:
            source: 事件来源标识
        """
        self.source = source
        self._trace_id_counter = 0
    
    def _next_trace_id(self) -> str:
        """生成追踪ID"""
        self._trace_id_counter += 1
        return f"{self.source}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._trace_id_counter}"
    
    def publish(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Event:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            payload: 事件数据
            trace_id: 追踪ID
            correlation_id: 关联ID
            tags: 标签列表
        
        Returns:
            创建的事件对象
        """
        from .core import get_eventbus
        
        event = Event(
            type=event_type,
            source=self.source,
            payload=payload,
            trace_id=trace_id or self._next_trace_id(),
            correlation_id=correlation_id,
            tags=tags or [],
        )
        
        get_eventbus().publish(event)
        return event
    
    # ========== 快捷方法 ==========
    
    def task_scheduled(
        self,
        task_id: str,
        task_type: str,
        schedule: str = None,
        **kwargs
    ) -> Event:
        """发布任务调度事件"""
        return self.publish(
            EventType.TASK_SCHEDULED,
            {
                "task_id": task_id,
                "task_type": task_type,
                "schedule": schedule,
                **kwargs
            },
        )
    
    def task_started(
        self,
        task_id: str,
        task_type: str = None,
        **kwargs
    ) -> Event:
        """发布任务开始事件"""
        return self.publish(
            EventType.TASK_STARTED,
            {
                "task_id": task_id,
                "task_type": task_type,
                **kwargs
            },
        )
    
    def task_completed(
        self,
        task_id: str,
        task_type: str = None,
        result: Dict = None,
        duration: float = None,
        **kwargs
    ) -> Event:
        """发布任务完成事件"""
        return self.publish(
            EventType.TASK_COMPLETED,
            {
                "task_id": task_id,
                "task_type": task_type,
                "result": result or {},
                "duration": duration,
                **kwargs
            },
        )
    
    def task_failed(
        self,
        task_id: str,
        task_type: str = None,
        error: str = None,
        **kwargs
    ) -> Event:
        """发布任务失败事件"""
        return self.publish(
            EventType.TASK_FAILED,
            {
                "task_id": task_id,
                "task_type": task_type,
                "error": error,
                **kwargs
            },
        )
    
    def error_occurred(
        self,
        error_type: str,
        message: str,
        severity: str = "medium",
        **kwargs
    ) -> Event:
        """发布错误事件"""
        return self.publish(
            EventType.ERROR_OCCURRED,
            {
                "error_type": error_type,
                "message": message,
                "severity": severity,
                **kwargs
            },
            tags=[error_type, severity],
        )
    
    def error_recovered(
        self,
        error_type: str,
        recovery_method: str = None,
        **kwargs
    ) -> Event:
        """发布错误恢复事件"""
        return self.publish(
            EventType.ERROR_RECOVERED,
            {
                "error_type": error_type,
                "recovery_method": recovery_method,
                **kwargs
            },
            tags=[error_type],
        )
    
    def error_critical(
        self,
        error_type: str,
        message: str,
        action_required: str = None,
        **kwargs
    ) -> Event:
        """发布严重错误事件"""
        return self.publish(
            EventType.ERROR_CRITICAL,
            {
                "error_type": error_type,
                "message": message,
                "action_required": action_required,
                **kwargs
            },
            tags=[error_type, "critical"],
        )
    
    def insight_generated(
        self,
        insight_type: str,
        content: str,
        source: str = None,
        confidence: float = None,
        **kwargs
    ) -> Event:
        """发布洞察生成事件"""
        return self.publish(
            EventType.INSIGHT_GENERATED,
            {
                "insight_type": insight_type,
                "content": content,
                "source": source,
                "confidence": confidence,
                **kwargs
            },
            tags=[insight_type],
        )
    
    def insight_consumed(
        self,
        insight_id: str,
        consumer: str = None,
        usage: str = None,
        **kwargs
    ) -> Event:
        """发布洞察消费事件"""
        return self.publish(
            EventType.INSIGHT_CONSUMED,
            {
                "insight_id": insight_id,
                "consumer": consumer,
                "usage": usage,
                **kwargs
            },
        )
    
    def strategy_switched(
        self,
        from_strategy: str,
        to_strategy: str,
        reason: str = None,
        **kwargs
    ) -> Event:
        """发布策略切换事件"""
        return self.publish(
            EventType.STRATEGY_SWITCHED,
            {
                "from_strategy": from_strategy,
                "to_strategy": to_strategy,
                "reason": reason,
                **kwargs
            },
            tags=[to_strategy],
        )
    
    def strategy_loaded(
        self,
        strategy_name: str,
        config: Dict = None,
        **kwargs
    ) -> Event:
        """发布策略加载事件"""
        return self.publish(
            EventType.STRATEGY_LOADED,
            {
                "strategy_name": strategy_name,
                "config": config or {},
                **kwargs
            },
        )
    
    def health_api_error(
        self,
        api_name: str,
        error_type: str,
        retry_count: int = None,
        **kwargs
    ) -> Event:
        """发布API错误健康事件"""
        return self.publish(
            EventType.HEALTH_API_ERROR,
            {
                "api_name": api_name,
                "error_type": error_type,
                "retry_count": retry_count,
                **kwargs
            },
            tags=["health", "api_error"],
        )
    
    def health_api_recovered(
        self,
        api_name: str,
        recovery_time: float = None,
        **kwargs
    ) -> Event:
        """发布API恢复健康事件"""
        return self.publish(
            EventType.HEALTH_API_RECOVERED,
            {
                "api_name": api_name,
                "recovery_time": recovery_time,
                **kwargs
            },
            tags=["health", "recovered"],
        )
    
    def health_balance_low(
        self,
        balance: float,
        threshold: float = None,
        **kwargs
    ) -> Event:
        """发布余额不足健康事件"""
        return self.publish(
            EventType.HEALTH_BALANCE_LOW,
            {
                "balance": balance,
                "threshold": threshold,
                **kwargs
            },
            tags=["health", "balance"],
        )
    
    def genome_loaded(
        self,
        genome_version: str,
        source: str = None,
        **kwargs
    ) -> Event:
        """发布基因组加载事件"""
        return self.publish(
            EventType.GENOME_LOADED,
            {
                "genome_version": genome_version,
                "source": source,
                **kwargs
            },
        )
    
    def genome_saved(
        self,
        genome_version: str,
        target: str = None,
        **kwargs
    ) -> Event:
        """发布基因组保存事件"""
        return self.publish(
            EventType.GENOME_SAVED,
            {
                "genome_version": genome_version,
                "target": target,
                **kwargs
            },
        )
    
    def genome_herited(
        self,
        from_version: str,
        to_version: str,
        heritage_type: str = "restart",
        **kwargs
    ) -> Event:
        """发布基因传承事件"""
        return self.publish(
            EventType.GENOME_HERITAGE,
            {
                "from_version": from_version,
                "to_version": to_version,
                "heritage_type": heritage_type,
                **kwargs
            },
        )
    
    def custom(
        self,
        event_name: str,
        payload: Dict,
        tags: list = None,
        **kwargs
    ) -> Event:
        """发布自定义事件"""
        return self.publish(
            EventType.CUSTOM,
            {
                "event_name": event_name,
                **payload,
                **kwargs
            },
            tags=tags or [event_name],
        )
