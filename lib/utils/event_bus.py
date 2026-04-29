"""
Event Bus - 简单事件总线
========================

提供轻量级的事件发布/订阅功能。
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import threading


@dataclass
class Event:
    """事件对象"""
    event_type: str
    payload: Dict[str, Any]
    source: str = "unknown"
    timestamp: Optional[str] = None
    event_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.event_id is None:
            self.event_id = f"{self.event_type}_{int(time.time() * 1000)}"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(**data)


class EventBus:
    """
    简单事件总线
    
    提供事件发布/订阅功能，支持内存和文件持久化。
    """
    
    def __init__(self, persistence_path: Optional[Path] = None):
        """
        初始化事件总线
        
        Args:
            persistence_path: 事件持久化目录
        """
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._persistence_path = persistence_path
        
        if persistence_path:
            persistence_path.mkdir(parents=True, exist_ok=True)
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        with self._lock:
            self._subscribers[event_type].append(handler)
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]):
        """取消订阅"""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(handler)
    
    def publish(self, event: Event):
        """
        发布事件
        
        Args:
            event: Event对象
        """
        # 持久化
        if self._persistence_path:
            self._persist_event(event)
        
        # 通知订阅者
        with self._lock:
            handlers = self._subscribers.get(event.event_type, [])
            handlers.extend(self._subscribers.get('*', []))  # 通配符订阅
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error: {e}")
    
    def _persist_event(self, event: Event):
        """持久化事件到文件"""
        try:
            date = datetime.now().strftime('%Y-%m-%d')
            event_file = self._persistence_path / f"{date}.jsonl"
            
            with open(event_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[EventBus] Persistence error: {e}")
    
    def get_subscribers(self, event_type: str) -> List[Callable]:
        """获取事件类型的订阅者"""
        with self._lock:
            return self._subscribers.get(event_type, []).copy()


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus(persistence_path: Optional[Path] = None) -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus(persistence_path)
    return _global_event_bus


def subscribe(event_type: str, handler: Callable[[Event], None]):
    """订阅事件（全局）"""
    get_event_bus().subscribe(event_type, handler)


def unsubscribe(event_type: str, handler: Callable[[Event], None]):
    """取消订阅（全局）"""
    get_event_bus().unsubscribe(event_type, handler)


def publish(event: Event):
    """发布事件（全局）"""
    get_event_bus().publish(event)
