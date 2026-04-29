#!/usr/bin/env python3
"""
ClawShell Organizer Task Scheduler
任务调度器模块
功能: 基于DAG的任务调度，支持优先级和依赖管理
"""

import time
import threading
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


@dataclass
class ScheduledTask:
    """调度任务"""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ScheduleStats:
    """调度统计"""
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0


class TaskScheduler:
    """
    任务调度器
    
    功能：
    - DAG调度
    - 依赖管理
    - 优先级调度
    - 重试机制
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        
        self._tasks: Dict[str, ScheduledTask] = {}
        self._ready_queue: List[str] = []  # 就绪任务队列
        self._running: Set[str] = set()
        self._lock = threading.Lock()
        
        self._stats = ScheduleStats()
        
        # 启动调度线程
        self._running_scheduler = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def add_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[Set[str]] = None,
        max_retries: int = 3
    ) -> bool:
        """添加任务"""
        with self._lock:
            if task_id in self._tasks:
                return False
            
            task = ScheduledTask(
                id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs or {},
                priority=priority,
                dependencies=dependencies or set(),
                max_retries=max_retries
            )
            
            self._tasks[task_id] = task
            self._update_ready_queue()
            self._stats.total_tasks += 1
            self._stats.pending_tasks += 1
            
            return True

    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """添加任务依赖"""
        with self._lock:
            if task_id not in self._tasks or depends_on not in self._tasks:
                return False
            
            self._tasks[task_id].dependencies.add(depends_on)
            self._tasks[depends_on].dependents.add(task_id)
            
            self._update_ready_queue()
            return True

    def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            if len(self._running) >= self.max_concurrent:
                return False
            
            task = self._tasks[task_id]
            
            if task.status not in [TaskStatus.READY, TaskStatus.PENDING]:
                return False
            
            # 检查依赖是否满足
            for dep_id in task.dependencies:
                dep_task = self._tasks.get(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    return False
            
            # 启动执行
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self._running.add(task_id)
            self._stats.pending_tasks -= 1
            self._stats.running_tasks += 1
            
            return True

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """完成任务"""
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result
            
            self._running.discard(task_id)
            self._stats.running_tasks -= 1
            self._stats.completed_tasks += 1
            
            # 更新依赖此任务的任务
            self._update_dependents(task_id)
            self._update_ready_queue()

    def fail_task(self, task_id: str, error: str) -> None:
        """任务失败"""
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task.retry_count += 1
            task.error = error
            
            if task.retry_count >= task.max_retries:
                task.status = TaskStatus.FAILED
                self._running.discard(task_id)
                self._stats.running_tasks -= 1
                self._stats.failed_tasks += 1
                
                # 标记依赖任务为blocked
                for dep_id in task.dependents:
                    if dep_id in self._tasks:
                        self._tasks[dep_id].status = TaskStatus.BLOCKED
            else:
                task.status = TaskStatus.READY
                self._running.discard(task_id)
                self._stats.running_tasks -= 1
                self._stats.pending_tasks += 1
            
            self._update_ready_queue()

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> List[ScheduledTask]:
        """获取就绪任务"""
        with self._lock:
            return [self._tasks[tid] for tid in self._ready_queue]

    def get_running_tasks(self) -> List[ScheduledTask]:
        """获取运行中任务"""
        with self._lock:
            return [self._tasks[tid] for tid in self._running if tid in self._tasks]

    def _update_ready_queue(self) -> None:
        """更新就绪队列"""
        self._ready_queue.clear()
        
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.PENDING:
                # 检查依赖
                deps_satisfied = all(
                    self._tasks.get(dep_id) and 
                    self._tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                
                if deps_satisfied:
                    task.status = TaskStatus.READY
                    self._ready_queue.append(task_id)
        
        # 按优先级排序
        self._ready_queue.sort(
            key=lambda tid: self._tasks[tid].priority.value,
            reverse=True
        )

    def _update_dependents(self, completed_task_id: str) -> None:
        """更新依赖任务"""
        for dep_id in self._tasks[completed_task_id].dependents:
            dep_task = self._tasks.get(dep_id)
            if dep_task and dep_task.status == TaskStatus.BLOCKED:
                # 检查其他依赖是否也完成
                all_deps_done = all(
                    self._tasks.get(d) and 
                    self._tasks[d].status == TaskStatus.COMPLETED
                    for d in dep_task.dependencies
                )
                if all_deps_done:
                    dep_task.status = TaskStatus.READY

    def _scheduler_loop(self) -> None:
        """调度循环"""
        while self._running_scheduler:
            with self._lock:
                # 尝试启动就绪任务
                while self._ready_queue and len(self._running) < self.max_concurrent:
                    task_id = self._ready_queue.pop(0)
                    if self.execute_task(task_id):
                        # 在新线程中执行
                        thread = threading.Thread(
                            target=self._execute_task_async,
                            args=(task_id,),
                            daemon=True
                        )
                        thread.start()
            
            time.sleep(0.1)

    def _execute_task_async(self, task_id: str) -> None:
        """异步执行任务"""
        task = self._tasks.get(task_id)
        if task is None:
            return
        
        try:
            result = task.func(*task.args, **task.kwargs)
            self.complete_task(task_id, result)
        except Exception as e:
            self.fail_task(task_id, str(e))

    def stop(self) -> None:
        """停止调度器"""
        self._running_scheduler = False
        if self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)

    def get_stats(self) -> ScheduleStats:
        """获取统计"""
        return self._stats

    def visualize_dag(self) -> Dict:
        """可视化DAG"""
        with self._lock:
            nodes = []
            edges = []
            
            for task_id, task in self._tasks.items():
                nodes.append({
                    "id": task_id,
                    "label": task.name,
                    "status": task.status.value,
                    "priority": task.priority.value,
                })
                
                for dep_id in task.dependencies:
                    edges.append({
                        "from": dep_id,
                        "to": task_id
                    })
            
            return {"nodes": nodes, "edges": edges}
