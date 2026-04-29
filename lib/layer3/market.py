"""
Task Market - ClawShell v0.1
===========================

任务市场。
提供任务发布、匹配和分配功能。

功能：
- 任务发布
- 能力匹配
- 任务分配
- 结果汇总
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .registry import TaskRegistry, Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class NodeCapability:
    """
    节点能力
    =========
    """
    def __init__(
        self,
        node_id: str,
        name: str,
        capabilities: List[str],  # e.g., ["analysis", "coding", "writing"]
        categories: List[str],      # e.g., ["tech", "business"]
        max_concurrent: int = 1,
        current_load: int = 0,
        metadata: Dict = None,
    ):
        self.node_id = node_id
        self.name = name
        self.capabilities = capabilities
        self.categories = categories
        self.max_concurrent = max_concurrent
        self.current_load = current_load
        self.metadata = metadata or {}
        self.last_heartbeat = datetime.now().isoformat()
    
    def is_available(self) -> bool:
        """检查节点是否可用"""
        return self.current_load < self.max_concurrent
    
    def can_handle_task(self, task: Task) -> bool:
        """检查节点是否能处理任务"""
        if not self.is_available():
            return False
        
        # 检查能力匹配
        if task.category in self.categories:
            return True
        
        # 检查标签匹配
        if any(tag in self.capabilities for tag in task.tags):
            return True
        
        return False


class TaskMarket:
    """
    任务市场
    =========
    
    负责任务的发布、匹配和分配。
    
    使用示例：
        market = TaskMarket()
        
        # 注册执行节点
        market.register_node(NodeCapability(
            node_id="agent-1",
            name="分析Agent",
            capabilities=["analysis", "research"],
            categories=["analysis"]
        ))
        
        # 发布任务
        task = market.publish_task(
            name="分析报告",
            category="analysis",
            required_capabilities=["analysis"]
        )
        
        # 匹配任务
        matched = market.match_task(task.id)
    """
    
    def __init__(self, registry: TaskRegistry = None):
        self.registry = registry or TaskRegistry()
        
        # 执行节点注册
        self._nodes: Dict[str, NodeCapability] = {}
        
        # 任务-节点映射
        self._task_assignments: Dict[str, str] = {}  # task_id -> node_id
        
        logger.info("TaskMarket initialized")
    
    def register_node(self, node: NodeCapability) -> bool:
        """
        注册执行节点
        
        Args:
            node: 节点能力
        
        Returns:
            是否注册成功
        """
        self._nodes[node.node_id] = node
        logger.info(f"Registered node: {node.node_id} - {node.name}")
        return True
    
    def unregister_node(self, node_id: str) -> bool:
        """注销节点"""
        if node_id in self._nodes:
            del self._nodes[node_id]
            logger.info(f"Unregistered node: {node_id}")
            return True
        return False
    
    def get_node(self, node_id: str) -> Optional[NodeCapability]:
        """获取节点"""
        return self._nodes.get(node_id)
    
    def list_nodes(self, available_only: bool = False) -> List[NodeCapability]:
        """列出节点"""
        nodes = list(self._nodes.values())
        if available_only:
            nodes = [n for n in nodes if n.is_available()]
        return nodes
    
    def publish_task(
        self,
        name: str,
        description: str = "",
        category: str = "general",
        tags: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        required_capabilities: List[str] = None,
        metadata: Dict = None,
    ) -> Task:
        """
        发布任务到市场
        
        Args:
            name: 任务名称
            description: 任务描述
            category: 任务分类
            tags: 任务标签
            priority: 优先级
            required_capabilities: 所需能力
            metadata: 元数据
        
        Returns:
            创建的任务
        """
        # 通过注册器创建任务
        task = self.registry.register(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            priority=priority,
            metadata={
                **(metadata or {}),
                "required_capabilities": required_capabilities or [],
                "market_published": True,
            }
        )
        
        logger.info(f"Published task to market: {task.id} - {task.name}")
        return task
    
    def match_task(self, task_id: str) -> Optional[str]:
        """
        为任务匹配最佳执行节点
        
        Args:
            task_id: 任务ID
        
        Returns:
            匹配的节点ID，如果没有可用节点则返回None
        """
        task = self.registry.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return None
        
        # 获取所有可用节点
        available_nodes = self.list_nodes(available_only=True)
        if not available_nodes:
            logger.warning("No available nodes")
            return None
        
        # 评分并排序
        scored_nodes = []
        for node in available_nodes:
            score = self._calculate_match_score(node, task)
            scored_nodes.append((node, score))
        
        # 按分数排序
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_nodes:
            return None
        
        best_node = scored_nodes[0][0]
        
        # 分配任务
        return self._assign_task(task_id, best_node.node_id)
    
    def _calculate_match_score(self, node: NodeCapability, task: Task) -> float:
        """
        计算节点与任务的匹配分数
        
        Args:
            node: 节点
            task: 任务
        
        Returns:
            匹配分数 0-1
        """
        score = 0.0
        
        # 检查分类匹配
        if task.category in node.categories:
            score += 0.4
        
        # 检查能力匹配
        required = task.metadata.get("required_capabilities", [])
        if required:
            matched = sum(1 for cap in required if cap in node.capabilities)
            score += 0.4 * (matched / len(required))
        else:
            # 无特定能力要求，检查标签匹配
            tag_match = sum(1 for tag in task.tags if tag in node.capabilities)
            score += 0.2 * tag_match
        
        # 负载因素（负载越低分数越高）
        load_factor = 1.0 - (node.current_load / node.max_concurrent)
        score += 0.2 * load_factor
        
        return min(score, 1.0)
    
    def _assign_task(self, task_id: str, node_id: str) -> Optional[str]:
        """
        分配任务到节点
        
        Args:
            task_id: 任务ID
            node_id: 节点ID
        
        Returns:
            节点ID
        """
        node = self._nodes.get(node_id)
        if not node:
            return None
        
        # 更新任务状态
        self.registry.update_status(task_id, TaskStatus.RUNNING)
        self.registry.assign(task_id, node_id)
        
        # 更新节点负载
        node.current_load += 1
        
        # 记录分配
        self._task_assignments[task_id] = node_id
        
        logger.info(f"Assigned task {task_id} to node {node_id}")
        
        return node_id
    
    def complete_task(self, task_id: str, result: Dict = None) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            result: 执行结果
        
        Returns:
            是否成功
        """
        task = self.registry.get(task_id)
        if not task:
            return False
        
        # 获取节点
        node_id = self._task_assignments.get(task_id)
        if node_id:
            node = self._nodes.get(node_id)
            if node:
                node.current_load = max(0, node.current_load - 1)
        
        # 更新任务状态
        self.registry.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result or {}
        )
        
        # 清理分配记录
        if task_id in self._task_assignments:
            del self._task_assignments[task_id]
        
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        
        Returns:
            是否成功
        """
        # 类似complete_task但状态为FAILED
        node_id = self._task_assignments.get(task_id)
        if node_id:
            node = self._nodes.get(node_id)
            if node:
                node.current_load = max(0, node.current_load - 1)
        
        self.registry.update_status(task_id, TaskStatus.FAILED, error=error)
        
        if task_id in self._task_assignments:
            del self._task_assignments[task_id]
        
        return True
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        return self.registry.list_tasks(status=TaskStatus.PENDING)
    
    def get_running_tasks(self) -> List[Task]:
        """获取运行中任务"""
        return self.registry.list_tasks(status=TaskStatus.RUNNING)
    
    def get_market_stats(self) -> Dict:
        """获取市场统计"""
        return {
            "total_nodes": len(self._nodes),
            "available_nodes": len([n for n in self._nodes.values() if n.is_available()]),
            "total_tasks": len(self._task_assignments),
            "pending_tasks": len(self.get_pending_tasks()),
            "running_tasks": len(self.get_running_tasks()),
            "registry_stats": self.registry.get_stats(),
        }
