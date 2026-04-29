"""
Node Coordinator - ClawShell v0.1
===============================

节点协调器。
负责节点的注册、心跳、任务协调和状态管理。

功能：
- 节点注册/注销
- 心跳检测
- 故障转移
- 负载均衡
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class NodeInfo:
    """
    节点信息
    =========
    """
    def __init__(
        self,
        node_id: str,
        node_type: str,  # openclaw, hermes, n8n, skill, mcp
        name: str,
        capabilities: List[str],
        endpoint: str = None,
        metadata: Dict = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.capabilities = capabilities
        self.endpoint = endpoint
        self.metadata = metadata or {}
        
        self.status = "offline"  # online, offline, busy, error
        self.last_heartbeat = None
        self.current_tasks = []
        self.max_tasks = 5
        
        self注册时间 = datetime.now().isoformat()
    
    def is_alive(self, timeout: int = 60) -> bool:
        """检查节点是否存活"""
        if not self.last_heartbeat:
            return False
        
        last = datetime.fromisoformat(self.last_heartbeat)
        elapsed = (datetime.now() - last).total_seconds()
        return elapsed < timeout
    
    def can_accept_task(self) -> bool:
        """检查是否能接受新任务"""
        return self.status in ["online", "busy"] and len(self.current_tasks) < self.max_tasks


class NodeCoordinator:
    """
    节点协调器
    ==========
    
    负责管理所有执行节点的生命周期。
    
    使用示例：
        coordinator = NodeCoordinator()
        
        # 注册节点
        coordinator.register_node(NodeInfo(
            node_id="agent-1",
            node_type="skill",
            name="分析Agent",
            capabilities=["analysis", "research"]
        ))
        
        # 启动心跳检测
        coordinator.start_heartbeat_check(interval=30)
        
        # 分发任务
        result = coordinator.dispatch_task(
            task={"name": "分析报告"},
            target_nodes=["agent-1"]
        )
    """
    
    def __init__(
        self,
        heartbeat_timeout: int = 60,
        check_interval: int = 30,
    ):
        self.heartbeat_timeout = heartbeat_timeout
        self.check_interval = check_interval
        
        # 节点注册表
        self._nodes: Dict[str, NodeInfo] = {}
        
        # 任务分配表
        self._task_assignments: Dict[str, str] = {}  # task_id -> node_id
        
        # 锁
        self._lock = Lock()
        
        # 心跳检测线程
        self._heartbeat_thread: Thread = None
        self._running = False
        
        # 任务处理器
        self._task_handlers: Dict[str, Callable] = {}
        
        logger.info("NodeCoordinator initialized")
    
    def register_node(self, node: NodeInfo) -> bool:
        """
        注册节点
        
        Args:
            node: 节点信息
        
        Returns:
            是否注册成功
        """
        with self._lock:
            self._nodes[node.node_id] = node
            node.status = "online"
            node.last_heartbeat = datetime.now().isoformat()
        
        logger.info(f"Registered node: {node.node_id} - {node.name}")
        
        # 发布事件
        self._publish_event("node.registered", node)
        
        return True
    
    def unregister_node(self, node_id: str) -> bool:
        """
        注销节点
        
        Args:
            node_id: 节点ID
        
        Returns:
            是否注销成功
        """
        with self._lock:
            if node_id not in self._nodes:
                return False
            
            node = self._nodes[node_id]
            node.status = "offline"
            
            # 重新分配该节点的任务
            self._reassign_tasks(node_id)
            
            del self._nodes[node_id]
        
        logger.info(f"Unregistered node: {node_id}")
        self._publish_event("node.unregistered", {"node_id": node_id})
        
        return True
    
    def heartbeat(self, node_id: str, current_load: int = None) -> bool:
        """
        节点心跳
        
        Args:
            node_id: 节点ID
            current_load: 当前负载
        
        Returns:
            是否成功
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                logger.warning(f"Heartbeat from unknown node: {node_id}")
                return False
            
            node.last_heartbeat = datetime.now().isoformat()
            node.status = "online"
            
            if current_load is not None:
                node.current_tasks = current_load if isinstance(current_load, list) else []
        
        return True
    
    def start_heartbeat_check(self, interval: int = None):
        """
        启动心跳检测
        
        Args:
            interval: 检测间隔（秒）
        """
        interval = interval or self.check_interval
        self._running = True
        
        def heartbeat_checker():
            while self._running:
                try:
                    self._check_node_health()
                except Exception as e:
                    logger.error(f"Heartbeat check error: {e}")
                time.sleep(interval)
        
        self._heartbeat_thread = Thread(target=heartbeat_checker, daemon=True)
        self._heartbeat_thread.start()
        
        logger.info(f"Started heartbeat check (interval={interval}s)")
    
    def stop_heartbeat_check(self):
        """停止心跳检测"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        logger.info("Stopped heartbeat check")
    
    def _check_node_health(self):
        """检查节点健康状态"""
        now = datetime.now()
        
        with self._lock:
            for node_id, node in list(self._nodes.items()):
                if not node.last_heartbeat:
                    continue
                
                last = datetime.fromisoformat(node.last_heartbeat)
                elapsed = (now - last).total_seconds()
                
                if elapsed > self.heartbeat_timeout:
                    if node.status != "offline":
                        logger.warning(f"Node {node_id} heartbeat timeout (offline)")
                        node.status = "offline"
                        self._reassign_tasks(node_id)
                        self._publish_event("node.offline", {"node_id": node_id})
    
    def _reassign_tasks(self, node_id: str):
        """重新分配节点的任务"""
        tasks_to_reassign = []
        
        for task_id, assigned_node in self._task_assignments.items():
            if assigned_node == node_id:
                tasks_to_reassign.append(task_id)
        
        for task_id in tasks_to_reassign:
            del self._task_assignments[task_id]
            logger.info(f"Task {task_id} needs reassignment (node {node_id} offline)")
            self._publish_event("task.reassign_needed", {"task_id": task_id})
    
    def dispatch_task(
        self,
        task: Dict,
        target_nodes: List[str] = None,
        required_capabilities: List[str] = None,
    ) -> Dict:
        """
        分发任务
        
        Args:
            task: 任务信息
            target_nodes: 目标节点列表（可选）
            required_capabilities: 所需能力（可选）
        
        Returns:
            分配结果
        """
        task_id = task.get("id", str(time.time()))
        
        with self._lock:
            # 如果指定了目标节点，直接分配
            if target_nodes:
                for node_id in target_nodes:
                    node = self._nodes.get(node_id)
                    if node and node.can_accept_task():
                        self._assign_task_to_node(task_id, node)
                        return {"status": "assigned", "node_id": node_id}
            
            # 否则根据能力匹配
            if required_capabilities:
                best_node = self._find_best_node(required_capabilities)
                if best_node:
                    self._assign_task_to_node(task_id, best_node)
                    return {"status": "assigned", "node_id": best_node.node_id}
            
            # 找不到合适的节点
            return {"status": "pending", "reason": "no_available_node"}
    
    def _find_best_node(self, capabilities: List[str]) -> Optional[NodeInfo]:
        """找到最佳匹配节点"""
        best_node = None
        best_score = 0
        
        for node in self._nodes.values():
            if not node.can_accept_task():
                continue
            
            # 计算能力匹配分数
            score = sum(1 for cap in capabilities if cap in node.capabilities)
            score = score / len(capabilities) if capabilities else 0
            
            if score > best_score:
                best_score = score
                best_node = node
        
        return best_node
    
    def _assign_task_to_node(self, task_id: str, node: NodeInfo):
        """分配任务到节点"""
        self._task_assignments[task_id] = node.node_id
        node.current_tasks.append(task_id)
        
        logger.info(f"Assigned task {task_id} to node {node.node_id}")
        self._publish_event("task.assigned", {
            "task_id": task_id,
            "node_id": node.node_id,
        })
    
    def complete_task(self, task_id: str, node_id: str, result: Dict = None):
        """完成任务"""
        with self._lock:
            node = self._nodes.get(node_id)
            if node and task_id in node.current_tasks:
                node.current_tasks.remove(task_id)
            
            if task_id in self._task_assignments:
                del self._task_assignments[task_id]
        
        self._publish_event("task.completed", {
            "task_id": task_id,
            "node_id": node_id,
            "result": result,
        })
    
    def fail_task(self, task_id: str, node_id: str, error: str):
        """标记任务失败"""
        with self._lock:
            node = self._nodes.get(node_id)
            if node and task_id in node.current_tasks:
                node.current_tasks.remove(task_id)
            
            if task_id in self._task_assignments:
                del self._task_assignments[task_id]
        
        self._publish_event("task.failed", {
            "task_id": task_id,
            "node_id": node_id,
            "error": error,
        })
    
    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """获取节点信息"""
        return self._nodes.get(node_id)
    
    def list_nodes(
        self,
        status: str = None,
        node_type: str = None,
    ) -> List[NodeInfo]:
        """列出节点"""
        nodes = list(self._nodes.values())
        
        if status:
            nodes = [n for n in nodes if n.status == status]
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        
        return nodes
    
    def get_coordinator_stats(self) -> Dict:
        """获取协调器统计"""
        with self._lock:
            nodes = list(self._nodes.values())
            
            return {
                "total_nodes": len(nodes),
                "online_nodes": len([n for n in nodes if n.status == "online"]),
                "offline_nodes": len([n for n in nodes if n.status == "offline"]),
                "busy_nodes": len([n for n in nodes if n.status == "busy"]),
                "total_tasks": len(self._task_assignments),
                "nodes_by_type": self._group_by(nodes, "node_type"),
            }
    
    def _group_by(self, items: List, key: str) -> Dict:
        """按key分组"""
        result = {}
        for item in items:
            group = getattr(item, key, "unknown")
            result[group] = result.get(group, 0) + 1
        return result
    
    def _publish_event(self, event_type: str, data: Dict):
        """发布事件"""
        try:
            from eventbus import Publisher
            pub = Publisher(source="node_coordinator")
            pub.publish(
                event_type=None,
                payload={
                    "event_name": event_type,
                    **data,
                },
                tags=["coordinator", event_type],
            )
        except Exception as e:
            logger.debug(f"Failed to publish event: {e}")
