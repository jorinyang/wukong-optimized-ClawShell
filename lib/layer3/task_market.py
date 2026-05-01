#!/usr/bin/env python3
"""
ClawShell TaskMarket - 任务市场匹配引擎
版本: v0.2.1-B
功能: 实现任务自动匹配最佳执行节点，形成"发布→匹配→执行→评价"闭环
依赖: NodeRegistry, TrustManager, SwarmDiscovery
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Lock

from lib.layer4.swarm import NodeRegistry, Node, NodeType, NodeStatus

logger = logging.getLogger(__name__)


# ============ 任务状态定义 ============

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 待发布
    PUBLISHED = "published"       # 已发布
    MATCHED = "matched"          # 已匹配
    EXECUTING = "executing"     # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"      # 已取消
    TIMEOUT = "timeout"          # 超时


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


# ============ 数据结构 ============

@dataclass
class Task:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    required_capabilities: List[str] = field(default_factory=list)  # 所需能力
    min_trust_score: float = 0.0         # 最低信任分
    priority: int = TaskPriority.NORMAL.value
    timeout: int = 3600                   # 超时时间（秒）
    retry_count: int = 0                  # 已重试次数
    max_retries: int = 3                 # 最大重试次数
    payload: Dict[str, Any] = field(default_factory=dict)  # 任务负载
    tags: List[str] = field(default_factory=list)
    status: str = TaskStatus.PENDING.value
    assigned_node: Optional[str] = None   # 分配的节点ID
    created_at: float = field(default_factory=time.time)
    published_at: Optional[float] = None
    matched_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "min_trust_score": self.min_trust_score,
            "priority": self.priority,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "payload": self.payload,
            "tags": self.tags,
            "status": self.status,
            "assigned_node": self.assigned_node,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "matched_at": self.matched_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        return cls(**data)


@dataclass
class TaskEvaluation:
    """任务评价"""
    task_id: str
    node_id: str
    score: float                    # 0-100
    execution_time: float          # 执行时间（秒）
    success: bool
    quality_score: float           # 质量评分 0-100
    feedback: str = ""
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)


# ============ 任务匹配器 ============

class TaskMatcher:
    """
    任务匹配器
    ==============

    匹配算法：
    - 需求匹配度 (40%): 节点能力是否满足任务需求
    - 能力强度 (30%): 节点对能力的熟练程度
    - 负载均衡 (20%): 节点当前负载
    - 信任分 (10%): 节点信任评分
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        trust_manager=None
    ):
        self.node_registry = node_registry
        self.trust_manager = trust_manager

    def match(self, task: Task) -> Optional[Node]:
        """
        匹配最佳节点
        返回: 最佳匹配节点 或 None
        """
        candidates = self._filter_candidates(task)
        if not candidates:
            return None

        # 评分排序
        scored = []
        for node in candidates:
            score = self._calculate_score(task, node)
            scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    def match_top_k(self, task: Task, k: int = 3) -> List[Node]:
        """
        匹配Top-K最佳节点
        """
        candidates = self._filter_candidates(task)
        if not candidates:
            return []

        scored = []
        for node in candidates:
            score = self._calculate_score(task, node)
            scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in scored[:k]]

    def _filter_candidates(self, task: Task) -> List[Node]:
        """过滤候选节点"""
        candidates = []
        for node in self.node_registry.get_active():
            # 检查节点状态
            if node.status == NodeStatus.OFFLINE:
                continue

            # 检查能力匹配
            if task.required_capabilities:
                if not all(cap in node.capabilities for cap in task.required_capabilities):
                    continue

            # 检查信任分
            if self.trust_manager:
                trust_score = self.trust_manager.get_trust_score(node.id)
                if trust_score < task.min_trust_score:
                    continue

            candidates.append(node)

        return candidates

    def _calculate_score(self, task: Task, node: Node) -> float:
        """
        计算匹配评分
        权重：需求匹配40% + 能力强度30% + 负载20% + 信任10%
        """
        # 需求匹配度 (40%)
        match_score = self._calc_match_score(task, node)

        # 能力强度 (30%)
        capability_score = self._calc_capability_score(task, node)

        # 负载均衡 (20%) - 负载越低分数越高
        load_score = self._calc_load_score(node)

        # 信任分 (10%)
        trust_score = self._calc_trust_score(node)

        return (
            match_score * 0.4 +
            capability_score * 0.3 +
            load_score * 0.2 +
            trust_score * 0.1
        )

    def _calc_match_score(self, task: Task, node: Node) -> float:
        """计算需求匹配度"""
        if not task.required_capabilities:
            return 100.0

        matched = sum(1 for cap in task.required_capabilities if cap in node.capabilities)
        return (matched / len(task.required_capabilities)) * 100

    def _calc_capability_score(self, task: Task, node: Node) -> float:
        """计算能力强度"""
        # 基于节点的metadata中的能力评分
        if not task.required_capabilities:
            return 100.0

        scores = []
        for cap in task.required_capabilities:
            cap_score = node.metadata.get("capabilities", {}).get(cap, {}).get("score", 50)
            scores.append(cap_score)

        return sum(scores) / len(scores) if scores else 50.0

    def _calc_load_score(self, node: Node) -> float:
        """计算负载评分"""
        max_load = node.metadata.get("max_load", 100)
        current_load = node.current_load if hasattr(node, "current_load") else 0

        if max_load <= 0:
            return 50.0

        load_ratio = current_load / max_load
        return (1.0 - load_ratio) * 100

    def _calc_trust_score(self, node: Node) -> float:
        """计算信任评分"""
        if self.trust_manager:
            return self.trust_manager.get_trust_score(node.id)
        return node.metadata.get("trust_score", 50.0)


# ============ 任务市场 ============

class TaskMarket:
    """
    任务市场
    =============

    功能：
    - 任务发布
    - 自动匹配
    - 执行跟踪
    - 评价结算

    事件：
    - task.published
    - task.matched
    - task.executed
    - task.evaluated
    - task.settled
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        trust_manager=None,
        persistence_path: str = "~/.real/.task_market"
    ):
        self.node_registry = node_registry
        self.trust_manager = trust_manager
        self.matcher = TaskMatcher(node_registry, trust_manager)
        self.persistence_path = Path(persistence_path).expanduser()
        self.persistence_path.mkdir(parents=True, exist_ok=True)

        # 任务存储
        self.tasks: Dict[str, Task] = {}
        self.tasks_lock = Lock()

        # 评价存储
        self.evaluations: Dict[str, TaskEvaluation] = {}

        # 事件回调
        self.event_callbacks: Dict[str, List[Callable]] = {}

        # 统计
        self.stats = {
            "total_tasks": 0,
            "matched_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }

        # 加载持久化任务
        self._load_tasks()

        logger.info("TaskMarket initialized")
        logger.info(f"Persistence path: {self.persistence_path}")

    def publish_task(self, task: Task) -> str:
        """
        发布任务
        返回: 任务ID
        """
        task.status = TaskStatus.PUBLISHED.value
        task.published_at = time.time()

        with self.tasks_lock:
            self.tasks[task.id] = task

        self.stats["total_tasks"] += 1

        # 发布事件
        self._emit_event("task.published", {
            "task_id": task.id,
            "task_name": task.name,
            "priority": task.priority,
            "required_capabilities": task.required_capabilities
        })

        # 自动匹配
        self._match_task(task.id)

        logger.info(f"Task published: {task.id} ({task.name})")
        return task.id

    def _match_task(self, task_id: str) -> Optional[str]:
        """匹配任务到节点"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

        # 使用匹配器匹配
        node = self.matcher.match(task)
        if not node:
            logger.warning(f"No suitable node found for task: {task_id}")
            return None

        # 分配任务
        task.assigned_node = node.id
        task.status = TaskStatus.MATCHED.value
        task.matched_at = time.time()

        with self.tasks_lock:
            self.tasks[task_id] = task

        self.stats["matched_tasks"] += 1

        # 发布事件
        self._emit_event("task.matched", {
            "task_id": task_id,
            "node_id": node.id,
            "node_name": node.name
        })

        logger.info(f"Task matched: {task_id} -> {node.id} ({node.name})")
        return node.id

    def assign_task(self, task_id: str, node_id: str) -> bool:
        """手动分配任务"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            node = self.node_registry.get_node(node_id)
            if not node:
                return False

        task.assigned_node = node_id
        task.status = TaskStatus.MATCHED.value
        task.matched_at = time.time()

        with self.tasks_lock:
            self.tasks[task_id] = task

        self.stats["matched_tasks"] += 1

        self._emit_event("task.matched", {
            "task_id": task_id,
            "node_id": node_id,
            "manually": True
        })

        return True

    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.MATCHED.value:
                return False

            task.status = TaskStatus.EXECUTING.value
            task.started_at = time.time()
            self.tasks[task_id] = task

        self._emit_event("task.executing", {"task_id": task_id})
        return True

    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> bool:
        """完成任务"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            task.completed_at = time.time()
            task.result = result

            if error:
                task.status = TaskStatus.FAILED.value
                task.error = error
                self.stats["failed_tasks"] += 1
            else:
                task.status = TaskStatus.COMPLETED.value
                self.stats["completed_tasks"] += 1

            self.tasks[task_id] = task

        # 发布事件
        self._emit_event("task.completed" if not error else "task.failed", {
            "task_id": task_id,
            "success": error is None,
            "execution_time": task.completed_at - task.started_at if task.started_at else 0
        })

        return True

    def evaluate_task(self, evaluation: TaskEvaluation) -> bool:
        """评价任务"""
        self.evaluations[evaluation.task_id] = evaluation

        # 更新信任分
        if self.trust_manager:
            delta = 10 if evaluation.success else -20
            self.trust_manager.adjust_trust(evaluation.node_id, delta)

        self._emit_event("task.evaluated", evaluation.to_dict())
        return True

    def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            if task.retry_count >= task.max_retries:
                logger.warning(f"Task {task_id} exceeded max retries")
                return False

            task.retry_count += 1
            task.status = TaskStatus.PUBLISHED.value
            task.assigned_node = None
            task.matched_at = None
            task.started_at = None
            task.result = None
            task.error = None

            self.tasks[task_id] = task

        # 重新匹配
        self._match_task(task_id)
        return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False

            if task.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
                return False

            task.status = TaskStatus.CANCELLED.value
            self.tasks[task_id] = task

        self._emit_event("task.cancelled", {"task_id": task_id})
        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """获取指定状态的任务"""
        return [
            t for t in self.tasks.values()
            if t.status == status.value
        ]

    def get_tasks_by_node(self, node_id: str) -> List[Task]:
        """获取指定节点的任务"""
        return [
            t for t in self.tasks.values()
            if t.assigned_node == node_id
        ]

    def get_pending_tasks(self) -> List[Task]:
        """获取待匹配任务"""
        return self.get_tasks_by_status(TaskStatus.PUBLISHED)

    def get_executing_tasks(self) -> List[Task]:
        """获取执行中任务"""
        return self.get_tasks_by_status(TaskStatus.EXECUTING)

    def register_event_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self.event_callbacks:
            self.event_callbacks[event] = []
        self.event_callbacks[event].append(callback)

    def _emit_event(self, event: str, data: Dict):
        """触发事件"""
        callbacks = self.event_callbacks.get(event, [])
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    def _load_tasks(self):
        """加载持久化任务"""
        try:
            tasks_file = self.persistence_path / "tasks.json"
            if tasks_file.exists():
                with open(tasks_file) as f:
                    data = json.load(f)
                    for t in data.values():
                        self.tasks[t["id"]] = Task.from_dict(t)
                logger.info(f"Loaded {len(self.tasks)} tasks from persistence")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    def save_tasks(self):
        """保存任务到持久化"""
        try:
            tasks_file = self.persistence_path / "tasks.json"
            with open(tasks_file, "w") as f:
                data = {t.id: t.to_dict() for t in self.tasks.values()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "pending_tasks": len(self.get_pending_tasks()),
            "executing_tasks": len(self.get_executing_tasks()),
            "total_nodes": len(self.node_registry.nodes)
        }


# ============ 便捷函数 ============

def create_task(
    name: str,
    description: str = "",
    required_capabilities: Optional[List[str]] = None,
    priority: int = TaskPriority.NORMAL.value,
    timeout: int = 3600,
    max_retries: int = 3,
    tags: Optional[List[str]] = None
) -> Task:
    """创建任务"""
    return Task(
        name=name,
        description=description,
        required_capabilities=required_capabilities or [],
        priority=priority,
        timeout=timeout,
        max_retries=max_retries,
        tags=tags or []
    )
