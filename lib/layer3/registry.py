"""
Task Registry - ClawShell v0.1
==============================

任务注册器。
负责注册、追踪和管理任务。

功能：
- 任务注册
- 任务状态跟踪
- 任务历史记录
"""

import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 待处理
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    TIMEOUT = "timeout"         # 超时


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """
    任务定义
    =========
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # 分类
    category: str = "general"      # general, analysis, execution, research
    tags: List[str] = field(default_factory=list)
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str = None
    completed_at: str = None
    
    # 执行信息
    assigned_to: str = None        # 执行者
    result: Dict = field(default_factory=dict)
    error: str = None
    
    # 依赖
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID列表
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "error": self.error,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = TaskStatus(status)
        
        priority = data.get("priority", 2)
        if isinstance(priority, int):
            priority = TaskPriority(priority)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            status=status,
            priority=priority,
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            assigned_to=data.get("assigned_to"),
            result=data.get("result", {}),
            error=data.get("error"),
            depends_on=data.get("depends_on", []),
            metadata=data.get("metadata", {}),
        )


class TaskRegistry:
    """
    任务注册器
    ===========
    
    负责任务的注册、追踪和管理。
    
    使用示例：
        registry = TaskRegistry()
        
        # 注册任务
        task = registry.register(
            name="分析报告",
            description="生成月度报告",
            category="analysis",
        )
        
        # 更新状态
        registry.update_status(task.id, TaskStatus.RUNNING)
        registry.update_status(task.id, TaskStatus.COMPLETED)
        
        # 查询任务
        task = registry.get(task.id)
        pending_tasks = registry.list_tasks(status=TaskStatus.PENDING)
    """
    
    def __init__(self, storage_path: str = "~/.real/organizer/registry"):
        import os
        from pathlib import Path
        
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._tasks: Dict[str, Task] = {}
        self._index_file = self.storage_path / "tasks_index.json"
        
        # 加载已有任务
        self._load_index()
        
        logger.info(f"TaskRegistry initialized at {self.storage_path}")
    
    def _load_index(self):
        """加载任务索引"""
        import json
        
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    data = json.load(f)
                
                for task_data in data.get("tasks", []):
                    task = Task.from_dict(task_data)
                    self._tasks[task.id] = task
                
                logger.info(f"Loaded {len(self._tasks)} tasks from index")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
    
    def _save_index(self):
        """保存任务索引"""
        import json
        
        try:
            data = {
                "tasks": [task.to_dict() for task in self._tasks.values()]
            }
            
            with open(self._index_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def register(
        self,
        name: str,
        description: str = "",
        category: str = "general",
        tags: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        depends_on: List[str] = None,
        metadata: Dict = None,
    ) -> Task:
        """
        注册新任务
        
        Args:
            name: 任务名称
            description: 任务描述
            category: 任务分类
            tags: 任务标签
            priority: 优先级
            depends_on: 依赖的任务ID
            metadata: 元数据
        
        Returns:
            创建的任务对象
        """
        task = Task(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            priority=priority,
            depends_on=depends_on or [],
            metadata=metadata or {},
        )
        
        self._tasks[task.id] = task
        self._save_index()
        
        logger.info(f"Registered task: {task.id} - {task.name}")
        
        # 发布事件
        self._publish_event("task.registered", task)
        
        return task
    
    def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        status: TaskStatus = None,
        category: str = None,
        assigned_to: str = None,
        tags: List[str] = None,
        limit: int = 100,
    ) -> List[Task]:
        """
        列出任务
        
        Args:
            status: 按状态过滤
            category: 按分类过滤
            assigned_to: 按执行者过滤
            tags: 按标签过滤
            limit: 返回数量限制
        
        Returns:
            任务列表
        """
        tasks = list(self._tasks.values())
        
        # 过滤
        if status:
            tasks = [t for t in tasks if t.status == status]
        if category:
            tasks = [t for t in tasks if t.category == category]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        
        # 按优先级和创建时间排序
        tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        
        return tasks[:limit]
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Dict = None,
        error: str = None,
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            result: 执行结果
            error: 错误信息
        
        Returns:
            是否更新成功
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False
        
        task.status = status
        
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now().isoformat()
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.now().isoformat()
        
        if result is not None:
            task.result = result
        
        if error:
            task.error = error
        
        self._save_index()
        
        # 发布事件
        self._publish_event(f"task.{status.value}", task)
        
        logger.info(f"Updated task {task_id} status to {status.value}")
        return True
    
    def assign(self, task_id: str, assigned_to: str) -> bool:
        """分配任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.assigned_to = assigned_to
        self._save_index()
        
        self._publish_event("task.assigned", task)
        
        return True
    
    def delete(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_index()
            logger.info(f"Deleted task: {task_id}")
            return True
        return False
    
    def get_stats(self) -> Dict:
        """获取任务统计"""
        stats = {
            "total": len(self._tasks),
            "by_status": {},
            "by_category": {},
        }
        
        for task in self._tasks.values():
            status_key = task.status.value if isinstance(task.status, TaskStatus) else task.status
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1
            
            stats["by_category"][task.category] = stats["by_category"].get(task.category, 0) + 1
        
        return stats
    
    def _publish_event(self, event_type: str, task: Task):
        """发布任务事件"""
        try:
            from eventbus import Publisher
            pub = Publisher(source="task_registry")
            pub.publish(
                event_type=None,
                payload={
                    "event_name": event_type,
                    "task_id": task.id,
                    "task_name": task.name,
                    "status": task.status.value if isinstance(task.status, TaskStatus) else task.status,
                },
                tags=["task", event_type],
            )
        except Exception as e:
            logger.debug(f"Failed to publish event: {e}")
