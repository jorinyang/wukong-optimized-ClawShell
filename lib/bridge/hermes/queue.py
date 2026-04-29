#!/usr/bin/env python3
# hermes_bridge/queue.py
"""
消息队列

支持优先级和批量的消息队列
"""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from heapq import heappush, heappop


@dataclass
class QueuedItem:
    """队列项"""
    priority: int  # 数值越小优先级越高
    timestamp: float
    data: Dict
    mode: str  # instant, fast, standard, batch
    
    def __lt__(self, other):
        # 用于heapq比较
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class MessageQueue:
    """
    优先级消息队列
    
    支持：
    1. 优先级排队
    2. 响应模式分组
    3. 批量出队
    4. 限流控制
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.max_size = self.config.get('max_size', 1000)
        self.batch_size = self.config.get('batch_size', 10)
        
        # 优先级队列 (heap)
        self._heap: List[QueuedItem] = []
        
        # 按响应模式分组
        self._by_mode: Dict[str, List[QueuedItem]] = defaultdict(list)
        
        # 统计
        self.stats = {
            'enqueued': 0,
            'dequeued': 0,
            'dropped': 0,
            'current_size': 0
        }
        
        self._lock = asyncio.Lock()
    
    def _default_config(self) -> Dict:
        return {
            'max_size': 1000,
            'batch_size': 10,
            'mode_priorities': {
                'instant': 0,
                'fast': 1,
                'standard': 2,
                'batch': 3
            }
        }
    
    def _get_priority(self, mode: str) -> int:
        """获取模式的优先级数值"""
        priorities = self.config.get('mode_priorities', {})
        return priorities.get(mode, 2)
    
    async def enqueue(self, item: Dict) -> bool:
        """
        入队
        
        参数:
            item: {
                'event': ClawshellEvent,
                'response_mode': ResponseMode,
                'classified_at': str
            }
        
        返回:
            bool: 是否入队成功
        """
        async with self._lock:
            # 检查队列满
            if len(self._heap) >= self.max_size:
                self.stats['dropped'] += 1
                return False
            
            mode = item.get('response_mode', 'standard').value if hasattr(item.get('response_mode'), 'value') else str(item.get('response_mode', 'standard'))
            
            queued_item = QueuedItem(
                priority=self._get_priority(mode),
                timestamp=datetime.now().timestamp(),
                data=item,
                mode=mode
            )
            
            heappush(self._heap, queued_item)
            self._by_mode[mode].append(queued_item)
            
            self.stats['enqueued'] += 1
            self.stats['current_size'] = len(self._heap)
            
            return True
    
    async def dequeue(self) -> Optional[Dict]:
        """
        单项出队 (最高优先级)
        
        返回:
            Dict: 队列项的data，或None
        """
        async with self._lock:
            if not self._heap:
                return None
            
            item = heappop(self._heap)
            mode = item.mode
            if item in self._by_mode[mode]:
                self._by_mode[mode].remove(item)
            
            self.stats['dequeued'] += 1
            self.stats['current_size'] = len(self._heap)
            
            return item.data
    
    async def dequeue_batch(self, mode: str = None, max_count: int = None) -> List[Dict]:
        """
        批量出队
        
        参数:
            mode: 按响应模式过滤 (可选)
            max_count: 最大数量 (可选)
        
        返回:
            List[Dict]: 队列项列表
        """
        if max_count is None:
            max_count = self.batch_size
        
        async with self._lock:
            result = []
            
            if mode:
                # 指定模式
                items = self._by_mode.get(mode, [])
                for _ in range(min(len(items), max_count)):
                    if items:
                        item = items.pop(0)
                        if item in self._heap:
                            self._heap.remove(item)
                            # 重新构建heap
                            self._rebuild_heap()
                        result.append(item.data)
            else:
                # 全部模式，按优先级
                for _ in range(min(len(self._heap), max_count)):
                    if self._heap:
                        item = heappop(self._heap)
                        if item in self._by_mode[item.mode]:
                            self._by_mode[item.mode].remove(item)
                        result.append(item.data)
            
            self.stats['dequeued'] += len(result)
            self.stats['current_size'] = len(self._heap)
            
            return result
    
    def _rebuild_heap(self):
        """重建堆"""
        import heapq
        self._heap = []
        for mode_items in self._by_mode.values():
            for item in mode_items:
                heappush(self._heap, item)
    
    async def peek(self, mode: str = None, count: int = 5) -> List[Dict]:
        """
        查看队列项 (不出队)
        
        参数:
            mode: 按响应模式过滤
            count: 查看数量
        
        返回:
            List[Dict]: 队列项列表
        """
        async with self._lock:
            if mode:
                items = self._by_mode.get(mode, [])[:count]
            else:
                # 按优先级排序查看
                sorted_items = sorted(self._heap, key=lambda x: (x.priority, x.timestamp))
                items = sorted_items[:count]
            
            return [item.data for item in items]
    
    async def size(self) -> int:
        """获取队列大小"""
        return len(self._heap)
    
    async def clear(self):
        """清空队列"""
        async with self._lock:
            self._heap.clear()
            self._by_mode.clear()
            self.stats['current_size'] = 0
    
    def get_stats(self) -> Dict:
        """获取队列统计"""
        return {
            **self.stats,
            'by_mode': {mode: len(items) for mode, items in self._by_mode.items()},
            'mode_priorities': self.config.get('mode_priorities', {})
        }


if __name__ == "__main__":
    # 测试代码
    print("=== MessageQueue 测试 ===\n")
    
    import asyncio
    
    queue = MessageQueue({
        'max_size': 100,
        'batch_size': 5
    })
    
    async def test_queue():
        # 入队测试
        print("=== 入队测试 ===")
        
        test_items = [
            {'event': 'task1', 'response_mode': 'standard'},
            {'event': 'task2', 'response_mode': 'fast'},
            {'event': 'task3', 'response_mode': 'instant'},
            {'event': 'task4', 'response_mode': 'batch'},
            {'event': 'task5', 'response_mode': 'standard'},
        ]
        
        for item in test_items:
            await queue.enqueue(item)
            print(f"入队: {item['event']} ({item['response_mode']})")
        
        print(f"\n队列大小: {await queue.size()}")
        print(f"统计: {queue.get_stats()}")
        
        # 查看
        print("\n=== 查看队列 (peek) ===")
        peeked = await queue.peek(count=3)
        for item in peeked:
            print(f"  - {item['event']} ({item['response_mode']})")
        
        # 出队测试
        print("\n=== 批量出队 ===")
        dequeued = await queue.dequeue_batch(max_count=3)
        for item in dequeued:
            print(f"出队: {item['event']} ({item['response_mode']})")
        
        print(f"\n剩余队列大小: {await queue.size()}")
        
        # 统计
        print("\n=== 最终统计 ===")
        print(json.dumps(queue.get_stats(), indent=2))
    
    asyncio.run(test_queue())
