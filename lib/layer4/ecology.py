#!/usr/bin/env python3
"""
ClawShell 生态位匹配引擎
版本: v0.2.1-B
功能: 需求优先 + 能力适配 的自动生态位匹配
依赖: NodeRegistry, TaskMarket
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .node_registry import NodeRegistry, Node, NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class EcologicalNiche:
    """生态位"""
    node_id: str
    node_name: str
    capabilities: List[str]
    availability: float  # 0-1, 1表示完全空闲
    trust_score: float   # 0-100

    def score_for_task(self, task) -> float:
        """计算任务匹配分数"""
        # 能力匹配度
        if not task.required_capabilities:
            capability_score = 1.0
        else:
            matched = sum(1 for cap in task.required_capabilities if cap in self.capabilities)
            capability_score = matched / len(task.required_capabilities)

        # 综合分数 = 能力匹配 * 0.6 + 可用度 * 0.2 + 信任 * 0.2
        return (
            capability_score * 0.6 +
            self.availability * 0.2 +
            (self.trust_score / 100) * 0.2
        )


class EcologicalMatcher:
    """
    生态位匹配器
    ==============

    功能：
    - 能力过滤
    - 生态位排序
    - 多节点推荐

    使用示例：
        matcher = EcologicalMatcher(node_registry)

        # 匹配最佳节点
        best = matcher.match_niche(task)

        # 匹配Top-3
        candidates = matcher.match_top_k(task, k=3)
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        trust_manager=None
    ):
        self.node_registry = node_registry
        self.trust_manager = trust_manager

        logger.info("EcologicalMatcher initialized")

    def match_niche(self, task) -> Optional[Node]:
        """
        匹配最佳生态位节点

        Args:
            task: 任务对象 (有 required_capabilities 属性)

        Returns:
            最佳匹配节点 或 None
        """
        candidates = self.match_top_k(task, k=1)
        return candidates[0] if candidates else None

    def match_top_k(self, task, k: int = 3) -> List[Node]:
        """
        匹配Top-K生态位节点

        Args:
            task: 任务对象
            k: 返回节点数量

        Returns:
            节点列表 (按匹配度降序)
        """
        # 第一步：能力过滤
        capable_nodes = self._filter_capable(task)
        if not capable_nodes:
            logger.warning(f"No nodes have required capabilities: {task.required_capabilities}")
            return []

        # 第二步：计算生态位分数
        niches = []
        for node in capable_nodes:
            availability = self._calc_availability(node)
            trust_score = self._get_trust_score(node.id)

            niche = EcologicalNiche(
                node_id=node.id,
                node_name=node.name,
                capabilities=node.capabilities,
                availability=availability,
                trust_score=trust_score
            )

            task_score = niche.score_for_task(task)
            niches.append((node, task_score))

        # 第三步：排序并返回Top-K
        niches.sort(key=lambda x: x[1], reverse=True)

        return [node for node, score in niches[:k]]

    def _filter_capable(self, task) -> List[Node]:
        """过滤具有所需能力的节点"""
        if not task.required_capabilities:
            # 无能力要求，返回所有活跃节点
            return [n for n in self.node_registry.nodes.values()
                   if n.status != NodeStatus.OFFLINE]

        capable = []
        for node in self.node_registry.nodes.values():
            if node.status == NodeStatus.OFFLINE:
                continue

            # 检查能力匹配
            if all(cap in node.capabilities for cap in task.required_capabilities):
                capable.append(node)

        return capable

    def _calc_availability(self, node: Node) -> float:
        """计算节点可用度"""
        max_load = node.metadata.get("max_load", 100)
        current_load = node.metadata.get("current_load", 0)

        if max_load <= 0:
            return 0.5

        return max(0, 1.0 - (current_load / max_load))

    def _get_trust_score(self, node_id: str) -> float:
        """获取信任分"""
        if self.trust_manager and hasattr(self.trust_manager, 'get_trust_score'):
            return self.trust_manager.get_trust_score(node_id)

        if node_id in self.node_registry.nodes:
            return self.node_registry.nodes[node_id].metadata.get("trust_score", 50.0)

        return 50.0

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.node_registry.nodes)
        active = len([n for n in self.node_registry.nodes.values()
                     if n.status != NodeStatus.OFFLINE])

        return {
            "total_nodes": total,
            "active_nodes": active,
            "idle_nodes": active
        }
