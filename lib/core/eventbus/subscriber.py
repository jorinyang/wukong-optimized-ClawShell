"""
Event Subscriber - ClawShell v0.1
=================================

事件订阅者封装。
提供便捷的事件订阅接口，支持过滤器和批处理。
"""

from typing import Callable, Dict, Any, List, Optional
from functools import wraps
from datetime import datetime, timedelta

from .schema import Event, EventType, EventFilter
from .core import EventBus


class Subscriber:
    """
    事件订阅器
    ==========
    
    提供便捷的事件订阅接口，支持过滤器和自动清理。
    
    使用示例：
        sub = Subscriber()
        
        # 订阅任务完成事件
        @sub.on(EventType.TASK_COMPLETED)
        def handle_task_completed(event):
            print(f"Task {event.payload['task_id']} completed")
        
        # 带过滤器
        @sub.on(EventType.ERROR_OCCURRED, tags=["critical"])
        def handle_critical_error(event):
            print(f"Critical error: {event.payload['message']}")
        
        # 启动
        sub.start()
    """
    
    def __init__(self, eventbus: EventBus = None):
        """
        初始化订阅器
        
        Args:
            eventbus: 事件总线实例，默认使用全局实例
        """
        self.eventbus = eventbus
        self._handlers: Dict[str, List[tuple]] = {}  # event_type -> [(handler, filter), ...]
        self._started = False
    
    @property
    def bus(self) -> EventBus:
        """获取事件总线"""
        if self.eventbus is None:
            from .core import get_eventbus
            self.eventbus = get_eventbus()
        return self.eventbus
    
    def on(
        self,
        event_type: EventType,
        tags: List[str] = None,
        sources: List[str] = None,
        async_mode: bool = False,
    ):
        """
        装饰器：订阅事件
        
        Args:
            event_type: 事件类型
            tags: 过滤标签
            sources: 过滤来源
            async_mode: 是否异步处理
        
        Returns:
            装饰器函数
        """
        def decorator(handler: Callable[[Event], None]) -> Callable[[Event], None]:
            self.subscribe(
                event_type=event_type,
                handler=handler,
                tags=tags,
                sources=sources,
                async_mode=async_mode,
            )
            return handler
        return decorator
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
        tags: List[str] = None,
        sources: List[str] = None,
        async_mode: bool = False,
    ) -> None:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 处理函数
            tags: 过滤标签
            sources: 过滤来源
            async_mode: 是否异步处理
        """
        # 创建过滤器
        filter_info = {
            "tags": tags or [],
            "sources": sources or [],
        }
        
        # 包装处理函数，加入过滤逻辑
        def wrapped_handler(event: Event):
            # 检查标签过滤
            if filter_info["tags"]:
                if not any(tag in event.tags for tag in filter_info["tags"]):
                    return
            
            # 检查来源过滤
            if filter_info["sources"]:
                if event.source not in filter_info["sources"]:
                    return
            
            handler(event)
        
        # 注册到事件总线
        if async_mode:
            self.bus.subscribe_async(event_type, wrapped_handler)
        else:
            self.bus.subscribe(event_type, wrapped_handler)
        
        # 记录处理器
        event_type_value = event_type.value
        if event_type_value not in self._handlers:
            self._handlers[event_type_value] = []
        self._handlers[event_type_value].append((handler, filter_info))
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None] = None,
    ) -> None:
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            handler: 处理函数，不传则取消该类型所有订阅
        """
        if handler is None:
            # 取消所有该类型的订阅
            if event_type.value in self._handlers:
                for h, _ in self._handlers[event_type.value]:
                    self.bus.unsubscribe(event_type, h)
                self._handlers[event_type.value].clear()
        else:
            # 取消特定的处理器
            if event_type.value in self._handlers:
                to_remove = []
                for i, (h, filter_info) in enumerate(self._handlers[event_type.value]):
                    if h == handler:
                        self.bus.unsubscribe(event_type, h)
                        to_remove.append(i)
                
                for i in reversed(to_remove):
                    self._handlers[event_type.value].pop(i)
    
    def start(self) -> None:
        """启动订阅器"""
        self._started = True
    
    def stop(self) -> None:
        """停止订阅器"""
        self._started = False
        # 取消所有订阅
        for event_type_value, handlers in self._handlers.items():
            try:
                event_type = EventType(event_type_value)
                for handler, _ in handlers:
                    self.bus.unsubscribe(event_type, handler)
            except ValueError:
                pass
        self._handlers.clear()
    
    def get_subscriptions(self) -> Dict[str, List[Dict]]:
        """
        获取当前订阅列表
        
        Returns:
            订阅信息
        """
        result = {}
        for event_type_value, handlers in self._handlers.items():
            result[event_type_value] = [
                {
                    "handler": h.__name__,
                    "filter": f,
                }
                for h, f in handlers
            ]
        return result


class EventHandler:
    """
    事件处理器基类
    ===============
    
    提供结构化的事件处理框架。
    
    使用示例：
        class MyHandler(EventHandler):
            def handle_task_completed(self, event):
                return {"status": "processed"}
            
            def handle_error_occurred(self, event):
                return {"action": "alert"}
        
        handler = MyHandler()
        handler.register()
    """
    
    # 子类重写此映射来定义处理方法
    HANDLERS = {
        EventType.TASK_COMPLETED: "handle_task_completed",
        EventType.TASK_FAILED: "handle_task_failed",
        EventType.ERROR_OCCURRED: "handle_error_occurred",
        EventType.ERROR_RECOVERED: "handle_error_recovered",
        EventType.INSIGHT_GENERATED: "handle_insight_generated",
        EventType.STRATEGY_SWITCHED: "handle_strategy_switched",
    }
    
    def __init__(self, async_mode: bool = False):
        self.async_mode = async_mode
        self.subscriber = Subscriber()
    
    def register(self) -> None:
        """注册所有处理器"""
        for event_type, method_name in self.HANDLERS.items():
            method = getattr(self, method_name, None)
            if method:
                self.subscriber.subscribe(
                    event_type=event_type,
                    handler=method,
                    async_mode=self.async_mode,
                )
        self.subscriber.start()
    
    def unregister(self) -> None:
        """取消注册所有处理器"""
        self.subscriber.stop()
    
    def handle_task_completed(self, event: Event) -> Any:
        """处理任务完成事件"""
        pass
    
    def handle_task_failed(self, event: Event) -> Any:
        """处理任务失败事件"""
        pass
    
    def handle_error_occurred(self, event: Event) -> Any:
        """处理错误发生事件"""
        pass
    
    def handle_error_recovered(self, event: Event) -> Any:
        """处理错误恢复事件"""
        pass
    
    def handle_insight_generated(self, event: Event) -> Any:
        """处理洞察生成事件"""
        pass
    
    def handle_strategy_switched(self, event: Event) -> Any:
        """处理策略切换事件"""
        pass


class BatchEventHandler(EventHandler):
    """
    批处理事件处理器
    =================
    
    累积事件后批量处理，减少处理开销。
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        batch_timeout: float = 5.0,
        async_mode: bool = False,
    ):
        super().__init__(async_mode=async_mode)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._event_buffer: Dict[EventType, List[Event]] = {}
        self._last_process_time = datetime.now()
    
    def handle_event(self, event: Event) -> None:
        """
        添加事件到缓冲区
        
        当缓冲区满或超时时，触发批量处理。
        """
        event_type = event.type if isinstance(event.type, EventType) else EventType.CUSTOM
        
        if event_type not in self._event_buffer:
            self._event_buffer[event_type] = []
        
        self._event_buffer[event_type].append(event)
        
        # 检查是否需要处理
        should_process = (
            len(self._event_buffer[event_type]) >= self.batch_size or
            (datetime.now() - self._last_process_time).total_seconds() >= self.batch_timeout
        )
        
        if should_process:
            self._process_batch(event_type)
    
    def _process_batch(self, event_type: EventType) -> None:
        """处理一批事件"""
        if event_type not in self._event_buffer or not self._event_buffer[event_type]:
            return
        
        events = self._event_buffer[event_type]
        self._event_buffer[event_type] = []
        self._last_process_time = datetime.now()
        
        # 调用子类的批量处理方法
        self.process_batch(event_type, events)
    
    def process_batch(self, event_type: EventType, events: List[Event]) -> None:
        """
        批量处理事件
        子类重写此方法实现具体的批处理逻辑
        """
        pass
    
    def flush(self) -> None:
        """强制处理所有缓冲区"""
        for event_type in list(self._event_buffer.keys()):
            self._process_batch(event_type)
