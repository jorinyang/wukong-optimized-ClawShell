#!/usr/bin/env python3
"""
ClawShell Swarm Weight Calculator
节点权重计算模块
版本: v0.2.0-A
功能: 节点能力权重、负载权重、响应时间权重
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


# ============ 数据结构 ============

@dataclass
class NodeWeights:
    """节点权重"""
    node_id: str
    capability_weight: float      # 能力权重
    load_weight: float          # 负载权重
    response_time_weight: float # 响应时间权重
    reliability_weight: float     # 可靠性权重
    total_weight: float = 0.0   # 总权重
    last_calculated: float = field(default_factory=time.time)


# ============ 权重计算器 ============

class WeightCalculator:
    """
    节点权重计算器
    
    功能：
    - 节点能力权重计算
    - 负载权重计算
    - 响应时间权重计算
    - 综合权重评估
    
    使用示例：
        calculator = WeightCalculator()
        
        # 计算节点权重
        weights = calculator.calculate_weights(node_id)
        
        # 获取最优节点
        best_node = calculator.get_best_node([node_id1, node_id2, node_id3])
    """

    def __init__(
        self,
        capability_weight: float = 0.3,
        load_weight: float = 0.25,
        response_time_weight: float = 0.25,
        reliability_weight: float = 0.2
    ):
        self.capability_weight = capability_weight
        self.load_weight = load_weight
        self.response_time_weight = response_time_weight
        self.reliability_weight = reliability_weight
        
        # 权重缓存
        self._weight_cache: Dict[str, NodeWeights] = {}
        
        # 统计数据
        self._stats = {
            "total_calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    def calculate_weights(
        self,
        node_id: str,
        capabilities: List[str] = None,
        current_load: float = 0.0,
        avg_response_time: float = 100.0,
        reliability_score: float = 90.0
    ) -> NodeWeights:
        """
        计算节点权重
        
        Args:
            node_id: 节点ID
            capabilities: 节点能力列表
            current_load: 当前负载 (0-100)
            avg_response_time: 平均响应时间 (ms)
            reliability_score: 可靠性评分 (0-100)
        
        Returns:
            NodeWeights: 节点权重
        """
        # 能力权重
        capability_score = self._calculate_capability_score(capabilities)
        
        # 负载权重（负载越低权重越高）
        load_score = 100 - current_load
        
        # 响应时间权重（时间越短权重越高）
        response_score = max(0, 100 - (avg_response_time / 10))
        
        # 可靠性权重
        reliability_score_final = reliability_score
        
        # 综合权重
        total = (
            capability_score * self.capability_weight +
            load_score * self.load_weight +
            response_score * self.response_time_weight +
            reliability_score_final * self.reliability_weight
        )
        
        weights = NodeWeights(
            node_id=node_id,
            capability_weight=capability_score,
            load_weight=load_score,
            response_time_weight=response_score,
            reliability_weight=reliability_score_final,
            total_weight=total
        )
        
        self._weight_cache[node_id] = weights
        self._stats["total_calculations"] += 1
        
        return weights

    def get_weights(self, node_id: str) -> Optional[NodeWeights]:
        """获取缓存的权重"""
        return self._weight_cache.get(node_id)

    def get_best_node(self, node_ids: List[str]) -> Optional[str]:
        """获取最优节点"""
        if not node_ids:
            return None
        
        best_node = None
        best_weight = -1
        
        for node_id in node_ids:
            weights = self._weight_cache.get(node_id)
            if weights and weights.total_weight > best_weight:
                best_weight = weights.total_weight
                best_node = node_id
        
        return best_node

    def get_ranked_nodes(self, node_ids: List[str]) -> List[str]:
        """获取排序后的节点列表"""
        node_weights = []
        for node_id in node_ids:
            weights = self._weight_cache.get(node_id)
            if weights:
                node_weights.append((node_id, weights.total_weight))
        
        # 按权重降序排序
        node_weights.sort(key=lambda x: x[1], reverse=True)
        
        return [n[0] for n in node_weights]

    def _calculate_capability_score(self, capabilities: List[str] = None) -> float:
        """计算能力得分"""
        if not capabilities:
            return 50.0
        
        # 基础分
        score = 50.0
        
        # 能力数量加成
        score += min(len(capabilities) * 5, 30)
        
        # 高级能力加成
        advanced = ["python", "analysis", "ml", "automation"]
        advanced_count = sum(1 for c in capabilities if c.lower() in advanced)
        score += advanced_count * 5
        
        return min(score, 100.0)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "cached_nodes": len(self._weight_cache)
        }


# ============ 便捷函数 ============

def create_calculator(
    capability_weight: float = 0.3,
    load_weight: float = 0.25,
    response_time_weight: float = 0.25,
    reliability_weight: float = 0.2
) -> WeightCalculator:
    """创建计算器"""
    return WeightCalculator(
        capability_weight=capability_weight,
        load_weight=load_weight,
        response_time_weight=response_time_weight,
        reliability_weight=reliability_weight
    )
