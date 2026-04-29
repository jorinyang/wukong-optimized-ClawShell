#!/usr/bin/env python3
"""
ClawShell 事件优先级队列
版本: v0.2.3-A
功能: 高/中/低优先级分级处理、超时处理
"""

import os
import json
import time
import heapq
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from threading import Lock
from pathlib import Path

# ============ 配置 ============

PQ_STATE_PATH = Path("~/.openclaw/.pq_state.json").expanduser()


# ============ 数据结构 ============

class Priority(Enum):
    """优先级"""
    CRITICAL = 0  # 最高优先级
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BULK = 4  # 最低优先级，批量处理


@dataclass
class PrioritizedEvent:
    """优先级事件"""
    priority: Priority
    event_id: str
    event_type: str
    data: Dict
    created_at: float = field(default_factory=time.time)
    scheduled_at: Optional[float] = None  # 计划执行时间
    deadline: Optional[float] = None  # 最后期限
    retries: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        # 堆比较：首先按优先级，然后按时间
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at
    
    def to_dict(self) -> Dict:
        return {
            "priority": self.priority.name,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "created_at": self.created_at,
            "scheduled_at": self.scheduled_at,
            "deadline": self.deadline,
            "retries": self.retries,
            "max_retries": self.max_retries
        }


@dataclass
class TimeoutConfig:
    """超时配置"""
    default_timeout: float = 30.0  # 默认超时（秒）
    max_timeout: float = 300.0  # 最大超时
    check_interval: float = 1.0  # 检查间隔（秒）
    on_timeout: str = "retry"  # retry, dead_letter, ignore


# ============ 优先级队列 ============

class PriorityQueue:
    """优先级队列"""
    
    def __init__(self):
        self._heap: List[PrioritizedEvent] = []
        self._lock = Lock()
        self._event_map: Dict[str, PrioritizedEvent] = {}  # 快速查找
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if PQ_STATE_PATH.exists():
            try:
                with open(PQ_STATE_PATH) as f:
                    state = json.load(f)
                    for event_data in state.get("events", []):
                        event = PrioritizedEvent(
                            priority=Priority[event_data["priority"]],
                            event_id=event_data["event_id"],
                            event_type=event_data["event_type"],
                            data=event_data["data"],
                            created_at=event_data.get("created_at", time.time()),
                            scheduled_at=event_data.get("scheduled_at"),
                            deadline=event_data.get("deadline"),
                            retries=event_data.get("retries", 0),
                            max_retries=event_data.get("max_retries", 3)
                        )
                        self._event_map[event.event_id] = event
                        heapq.heappush(self._heap, event)
            except:
                pass
    
    def _save_state(self):
        """保存状态"""
        with self._lock:
            state = {
                "last_update": time.time(),
                "events": [e.to_dict() for e in self._heap]
            }
            with open(PQ_STATE_PATH, 'w') as f:
                json.dump(state, f, indent=2)
    
    def enqueue(self, event: PrioritizedEvent) -> bool:
        """入队"""
        with self._lock:
            if event.event_id in self._event_map:
                return False
            
            self._event_map[event.event_id] = event
            heapq.heappush(self._heap, event)
            self._save_state()
            return True
    
    def dequeue(self) -> Optional[PrioritizedEvent]:
        """出队（获取最高优先级事件）"""
        with self._lock:
            while self._heap:
                event = heapq.heappop(self._heap)
                
                # 检查是否已计划到未来
                if event.scheduled_at and event.scheduled_at > time.time():
                    # 放回堆中
                    heapq.heappush(self._heap, event)
                    return None
                
                # 从映射中移除
                if event.event_id in self._event_map:
                    del self._event_map[event.event_id]
                    self._save_state()
                    return event
            
            return None
    
    def peek(self) -> Optional[PrioritizedEvent]:
        """查看最高优先级事件（不移除）"""
        with self._lock:
            if not self._heap:
                return None
            
            # 找到第一个未计划或已到期的
            for event in self._heap:
                if not event.scheduled_at or event.scheduled_at <= time.time():
                    return event
            
            return None
    
    def get(self, event_id: str) -> Optional[PrioritizedEvent]:
        """获取指定事件"""
        return self._event_map.get(event_id)
    
    def remove(self, event_id: str) -> bool:
        """移除指定事件"""
        with self._lock:
            if event_id not in self._event_map:
                return False
            
            del self._event_map[event_id]
            # 注意：不会从堆中物理删除，只是不再被引用
            self._save_state()
            return True
    
    def requeue(self, event: PrioritizedEvent, delay: float = 0) -> bool:
        """重新入队（用于重试）"""
        event.retries += 1
        
        if delay > 0:
            event.scheduled_at = time.time() + delay
        
        return self.enqueue(event)
    
    def size(self) -> int:
        """队列大小"""
        return len(self._event_map)
    
    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self._event_map) == 0
    
    def get_by_priority(self, priority: Priority) -> List[PrioritizedEvent]:
        """获取指定优先级的所有事件"""
        with self._lock:
            return [e for e in self._event_map.values() if e.priority == priority]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            stats = {
                "total": len(self._event_map),
                "by_priority": {},
                "scheduled": 0,
                "with_deadline": 0
            }
            
            for p in Priority:
                stats["by_priority"][p.name] = len([
                    e for e in self._event_map.values() if e.priority == p
                ])
            
            stats["scheduled"] = len([
                e for e in self._event_map.values() if e.scheduled_at
            ])
            
            stats["with_deadline"] = len([
                e for e in self._event_map.values() if e.deadline
            ])
            
            return stats


# ============ 超时处理器 ============

class TimeoutHandler:
    """超时处理器"""
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._timers: Dict[str, float] = {}  # event_id -> timeout_time
        self._callbacks: Dict[str, Callable] = {}  # event_id -> callback
        self._dead_letter_queue: List[PrioritizedEvent] = []
        self._lock = Lock()
    
    def set_timeout(self, event_id: str, timeout: float, callback: Callable, 
                    deadline: Optional[float] = None):
        """
        设置超时
        
        Args:
            event_id: 事件ID
            timeout: 超时时间（秒）
            callback: 超时时回调函数
            deadline: 最后期限（可选）
        """
        with self._lock:
            # 限制最大超时
            timeout = min(timeout, self.config.max_timeout)
            
            self._timers[event_id] = time.time() + timeout
            self._callbacks[event_id] = callback
            
            if deadline:
                self._timers[f"{event_id}_deadline"] = deadline
    
    def cancel(self, event_id: str):
        """取消超时"""
        with self._lock:
            self._timers.pop(event_id, None)
            self._timers.pop(f"{event_id}_deadline", None)
            self._callbacks.pop(event_id, None)
    
    def check_timeouts(self) -> List[PrioritizedEvent]:
        """
        检查超时事件
        返回需要处理的事件列表
        """
        now = time.time()
        timed_out = []
        
        with self._lock:
            expired_events = [
                (eid, timeout_time) for eid, timeout_time in self._timers.items()
                if not eid.endswith("_deadline") and timeout_time <= now
            ]
            
            for event_id, _ in expired_events:
                # 调用回调
                callback = self._callbacks.pop(event_id, None)
                if callback:
                    try:
                        callback(event_id)
                    except Exception as e:
                        print(f"Timeout callback error: {e}")
                
                # 取消相关deadline timer
                self._timers.pop(f"{event_id}_deadline", None)
            
            # 检查deadline
            expired_deadlines = [
                (eid.replace("_deadline", ""), dt) 
                for eid, dt in self._timers.items() 
                if eid.endswith("_deadline") and dt <= now
            ]
            
            for event_id, _ in expired_deadlines:
                timed_out.append(event_id)
                self._timers.pop(event_id, None)
                self._callbacks.pop(event_id, None)
        
        return timed_out
    
    def add_to_dead_letter(self, event: PrioritizedEvent, reason: str):
        """添加到死信队列"""
        with self._lock:
            event.data["dead_letter_reason"] = reason
            self._dead_letter_queue.append(event)
    
    def get_dead_letter_queue(self) -> List[PrioritizedEvent]:
        """获取死信队列"""
        with self._lock:
            return list(self._dead_letter_queue)
    
    def clear_dead_letter(self):
        """清空死信队列"""
        with self._lock:
            self._dead_letter_queue.clear()


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 优先级队列")
    parser.add_argument("--enqueue", nargs=3, metavar=("PRIORITY", "TYPE", "DATA"), help="入队")
    parser.add_argument("--dequeue", action="store_true", help="出队")
    parser.add_argument("--peek", action="store_true", help="查看")
    parser.add_argument("--stats", action="store_true", help="统计")
    parser.add_argument("--size", action="store_true", help="大小")
    args = parser.parse_args()
    
    pq = PriorityQueue()
    
    if args.enqueue:
        priority_str, event_type, data = args.enqueue
        try:
            priority = Priority[priority_str.upper()]
        except KeyError:
            print(f"Invalid priority: {priority_str}")
            print(f"Valid priorities: {[p.name for p in Priority]}")
            return
        
        event = PrioritizedEvent(
            priority=priority,
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=event_type,
            data={"data": data}
        )
        
        pq.enqueue(event)
        print(f"✅ 事件已入队: [{priority.name}] {event_type}")
    
    elif args.dequeue:
        event = pq.dequeue()
        if event:
            print(f"出队: [{event.priority.name}] {event.event_type}")
            print(f"  ID: {event.event_id}")
            print(f"  数据: {event.data}")
        else:
            print("队列为空")
    
    elif args.peek:
        event = pq.peek()
        if event:
            print(f"队首: [{event.priority.name}] {event.event_type}")
            print(f"  ID: {event.event_id}")
        else:
            print("队列为空")
    
    elif args.stats:
        stats = pq.get_stats()
        print("=" * 60)
        print("优先级队列统计")
        print("=" * 60)
        print(f"总事件数: {stats['total']}")
        print(f"已计划: {stats['scheduled']}")
        print(f"有deadline: {stats['with_deadline']}")
        print()
        print("按优先级:")
        for p, count in stats["by_priority"].items():
            print(f"  {p}: {count}")
    
    elif args.size:
        print(f"队列大小: {pq.size()}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
