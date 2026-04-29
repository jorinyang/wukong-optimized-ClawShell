#!/usr/bin/env python3
"""
ClawShell Enhanced Task Scheduler
增强版任务调度器 - Phase 2
版本: v1.0.0
功能: 并发扩容(4→8)、记忆延长、快照优化
"""

import time
import threading
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """任务"""
    id: str
    name: str
    state: TaskState = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

class EnhancedScheduler:
    """
    增强版任务调度器
    
    改进：
    - 并发槽位: 4 → 8
    - 记忆保留: 30min → 60min
    - 快照间隔: 10s → 5s
    """
    
    def __init__(
        self,
        max_concurrent: int = 8,  # 扩容: 4 → 8
        memory_retention: int = 3600,  # 延长: 1800 → 3600秒
        snapshot_interval: int = 5  # 优化: 10 → 5秒
    ):
        self.max_concurrent = max_concurrent
        self.memory_retention = memory_retention
        self.snapshot_interval = snapshot_interval
        
        self._tasks: Dict[str, Task] = {}
        self._running: Set[str] = set()
        self._completed: List[str] = []
        self._lock = threading.RLock()
        
        self._last_snapshot = time.time()
        self._snapshot_count = 0
        
    def submit(self, task_id: str, task_name: str) -> bool:
        """提交任务"""
        with self._lock:
            if task_id in self._tasks:
                return False
            
            task = Task(id=task_id, name=task_name)
            self._tasks[task_id] = task
            return True
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        return len(self._running) < self.max_concurrent
    
    def start(self, task_id: str) -> bool:
        """开始任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            if not self.can_execute():
                return False
            
            task = self._tasks[task_id]
            task.state = TaskState.RUNNING
            task.started_at = time.time()
            self._running.add(task_id)
            
            # 快照
            self._maybe_snapshot()
            
            return True
    
    def complete(self, task_id: str, result: Any = None):
        """完成任务"""
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.state = TaskState.COMPLETED
            task.completed_at = time.time()
            task.result = result
            
            if task_id in self._running:
                self._running.remove(task_id)
            
            self._completed.append(task_id)
            self._cleanup_old_tasks()
    
    def fail(self, task_id: str, error: str):
        """任务失败"""
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.state = TaskState.FAILED
            task.completed_at = time.time()
            task.error = error
            
            if task_id in self._running:
                self._running.remove(task_id)
            
            self._completed.append(task_id)
    
    def _maybe_snapshot(self):
        """快照"""
        now = time.time()
        if now - self._last_snapshot >= self.snapshot_interval:
            self._snapshot_count += 1
            self._last_snapshot = now
    
    def _cleanup_old_tasks(self):
        """清理旧任务"""
        now = time.time()
        to_remove = []
        
        for task_id, task in self._tasks.items():
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                if task.completed_at and (now - task.completed_at) > self.memory_retention:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self._tasks)
        completed = sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED)
        running = len(self._running)
        pending = total - completed - running
        
        return {
            "max_concurrent": self.max_concurrent,
            "memory_retention": self.memory_retention,
            "snapshot_interval": self.snapshot_interval,
            "total_tasks": total,
            "running": running,
            "pending": pending,
            "completed": completed,
            "snapshot_count": self._snapshot_count
        }

# 全局实例
_scheduler: Optional[EnhancedScheduler] = None

def get_scheduler() -> EnhancedScheduler:
    """获取调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = EnhancedScheduler()
    return _scheduler

if __name__ == "__main__":
    scheduler = EnhancedScheduler()
    
    print("=== 增强调度器测试 ===")
    print(f"并发槽位: {scheduler.max_concurrent}")
    print(f"记忆保留: {scheduler.memory_retention}s")
    print(f"快照间隔: {scheduler.snapshot_interval}s")
    
    # 测试任务
    scheduler.submit("task1", "测试任务1")
    scheduler.submit("task2", "测试任务2")
    
    print(f"\n提交后: {scheduler.get_stats()}")
    
    scheduler.start("task1")
    print(f"启动task1: {scheduler.get_stats()}")
    
    scheduler.complete("task1", "result1")
    print(f"完成task1: {scheduler.get_stats()}")
