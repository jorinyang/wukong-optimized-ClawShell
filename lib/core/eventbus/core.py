"""
EventBus Core - ClawShell v0.1
==============================

事件总线核心实现。
提供事件的发布、订阅、路由和持久化功能。
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Type
from threading import Lock, Thread
from collections import defaultdict
import time

from .schema import Event, EventType, EventFilter

logger = logging.getLogger(__name__)


class EventBus:
    """
    统一事件总线
    =============
    
    功能：
    - 发布/订阅模式
    - 事件持久化
    - 事件过滤
    - 异步处理
    - 死信队列
    
    使用示例：
        bus = EventBus()
        
        # 同步订阅
        def handler(event):
            print(f"Received: {event.type.value}")
        
        bus.subscribe(EventType.TASK_COMPLETED, handler)
        
        # 异步订阅
        bus.subscribe_async(EventType.ERROR_OCCURRED, async_handler)
        
        # 发布事件
        event = Event(type=EventType.TASK_COMPLETED, source="test")
        bus.publish(event)
    """
    
    def __init__(
        self,
        persistence_path: str = "~/.openclaw/eventbus/events",
        max_history: int = 10000,
        enable_dead_letter: bool = True,
        dead_letter_path: str = "~/.openclaw/eventbus/dead_letter",
    ):
        self.persistence_path = Path(persistence_path).expanduser()
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        
        self.max_history = max_history
        self.enable_dead_letter = enable_dead_letter
        
        if enable_dead_letter:
            self.dead_letter_path = Path(dead_letter_path).expanduser()
            self.dead_letter_path.mkdir(parents=True, exist_ok=True)
        
        # 订阅者存储: event_type -> [handler1, handler2, ...]
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # 异步订阅者
        self._async_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # 历史事件
        self._event_history: List[Event] = []
        
        # 锁
        self._lock = Lock()
        
        # 运行状态
        self._running = False
        self._async_thread: Optional[Thread] = None
        self._async_queue: List[Event] = []
        
        logger.info("EventBus initialized")
        logger.info(f"Persistence path: {self.persistence_path}")
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """
        订阅事件（同步）
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        with self._lock:
            self._subscribers[event_type.value].append(handler)
        logger.debug(f"Subscribed to {event_type.value}")
    
    def subscribe_async(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """
        订阅事件（异步）
        
        Args:
            event_type: 事件类型
            handler: 异步事件处理函数
        """
        with self._lock:
            self._async_subscribers[event_type.value].append(handler)
        logger.debug(f"Subscribed async to {event_type.value}")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        with self._lock:
            if event_type.value in self._subscribers:
                try:
                    self._subscribers[event_type.value].remove(handler)
                except ValueError:
                    pass
            if event_type.value in self._async_subscribers:
                try:
                    self._async_subscribers[event_type.value].remove(handler)
                except ValueError:
                    pass
        logger.debug(f"Unsubscribed from {event_type.value}")
    
    def publish(self, event: Event) -> None:
        """
        发布事件
        
        Args:
            event: 事件对象
        """
        # 设置时间戳
        if not event.timestamp:
            event.timestamp = datetime.now().isoformat()
        
        # 生成ID
        if not event.id:
            import uuid
            event.id = str(uuid.uuid4())
        
        with self._lock:
            # 添加到历史
            self._event_history.append(event)
            
            # 限制历史长度
            if len(self._event_history) > self.max_history:
                self._event_history = self._event_history[-self.max_history:]
            
            # 持久化
            self._persist_event(event)
            
            # 触发同步订阅者
            event_type_value = event.type.value if isinstance(event.type, EventType) else str(event.type)
            if event_type_value in self._subscribers:
                for handler in self._subscribers[event_type_value]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Sync handler error for {event_type_value}: {e}")
                        self._handle_dead_letter(event, str(e))
            
            # 添加到异步队列
            if event_type_value in self._async_subscribers:
                self._async_queue.append(event)
        
        logger.info(f"Published event: {event_type_value} from {event.source}")
    
    def publish_batch(self, events: List[Event]) -> None:
        """
        批量发布事件
        
        Args:
            events: 事件列表
        """
        for event in events:
            self.publish(event)
    
    def start_async_processing(self) -> None:
        """启动异步处理线程"""
        if self._running:
            return
        
        self._running = True
        self._async_thread = Thread(target=self._async_worker, daemon=True)
        self._async_thread.start()
        logger.info("Async event processing started")
    
    def stop_async_processing(self) -> None:
        """停止异步处理线程"""
        self._running = False
        if self._async_thread:
            self._async_thread.join(timeout=5)
        logger.info("Async event processing stopped")
    
    def _async_worker(self) -> None:
        """异步处理工作线程"""
        while self._running:
            try:
                if self._async_queue:
                    with self._lock:
                        if self._async_queue:
                            event = self._async_queue.pop(0)
                        
                        event_type_value = event.type.value if isinstance(event.type, EventType) else str(event.type)
                        
                        if event_type_value in self._async_subscribers:
                            for handler in self._async_subscribers[event_type_value]:
                                try:
                                    handler(event)
                                except Exception as e:
                                    logger.error(f"Async handler error: {e}")
                                    self._handle_dead_letter(event, str(e))
                else:
                    time.sleep(0.1)  # 避免CPU空转
            except Exception as e:
                logger.error(f"Async worker error: {e}")
    
    def _persist_event(self, event: Event) -> None:
        """
        持久化事件到磁盘
        
        Args:
            event: 事件对象
        """
        try:
            # 按日期分目录存储
            date_str = event.timestamp[:10]
            date_dir = self.persistence_path / date_str
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # 文件名: {timestamp}_{event_id[:8]}.json
            filename = f"{event.timestamp[:19].replace(':', '-')}_{event.id[:8]}.json"
            filepath = date_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(event.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")
    
    def _handle_dead_letter(self, event: Event, error: str) -> None:
        """
        处理死信事件
        
        Args:
            event: 失败的事件
            error: 错误信息
        """
        if not self.enable_dead_letter:
            return
        
        try:
            dead_letter = {
                "event": event.to_dict(),
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
            
            filename = f"dl_{event.id[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            filepath = self.dead_letter_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dead_letter, f, ensure_ascii=False, indent=2)
            
            logger.warning(f"Dead letter stored: {filename}")
        except Exception as e:
            logger.error(f"Failed to store dead letter: {e}")
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 按事件类型过滤
            source: 按来源过滤
            limit: 返回数量限制
        
        Returns:
            事件列表
        """
        with self._lock:
            history = self._event_history[-limit:]
        
        # 过滤
        if event_type:
            history = [e for e in history if e.type == event_type]
        if source:
            history = [e for e in history if e.source == source]
        
        return history
    
    def query_events(self, filter: EventFilter) -> List[Event]:
        """
        查询事件
        
        Args:
            filter: 事件过滤器
        
        Returns:
            匹配的事件列表
        """
        with self._lock:
            return [e for e in self._event_history if filter.matches(e)]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取事件统计
        
        Returns:
            统计信息
        """
        with self._lock:
            type_counts = defaultdict(int)
            source_counts = defaultdict(int)
            
            for event in self._event_history:
                event_type_value = event.type.value if isinstance(event.type, EventType) else str(event.type)
                type_counts[event_type_value] += 1
                source_counts[event.source] += 1
            
            return {
                "total_events": len(self._event_history),
                "subscribers_count": {
                    "sync": sum(len(v) for v in self._subscribers.values()),
                    "async": sum(len(v) for v in self._async_subscribers.values()),
                },
                "event_types": dict(type_counts),
                "sources": dict(source_counts),
                "async_queue_size": len(self._async_queue),
            }
    
    def clear_history(self) -> None:
        """清空历史事件（谨慎使用）"""
        with self._lock:
            self._event_history.clear()
        logger.warning("Event history cleared")


# 全局单例
_global_eventbus: Optional[EventBus] = None


def get_eventbus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_eventbus
    if _global_eventbus is None:
        _global_eventbus = EventBus()
    return _global_eventbus


def publish(event: Event) -> None:
    """快捷发布函数"""
    get_eventbus().publish(event)


def subscribe(event_type: EventType, handler: Callable[[Event], None]) -> None:
    """快捷订阅函数"""
    get_eventbus().subscribe(event_type, handler)
