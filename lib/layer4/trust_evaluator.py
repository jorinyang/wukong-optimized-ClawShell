#!/usr/bin/env python3
"""
ClawShell Swarm Trust Evaluator
信任动态评估模块
版本: v0.2.0-A
功能: 信任分动态计算、信任衰减机制、信任恢复策略
"""

import time
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from swarm.node_registry import NodeRegistry, NodeStatus


# ============ 数据结构 ============

class TrustLevel(Enum):
    """信任级别"""
    BLOCKED = "blocked"     # 拒绝
    VERY_LOW = "very_low"  # 很低
    LOW = "low"            # 低
    MEDIUM = "medium"      # 中
    HIGH = "high"          # 高
    VERY_HIGH = "very_high"  # 很高


@dataclass
class TrustScore:
    """信任分"""
    node_id: str
    score: float                    # 0-100
    level: TrustLevel
    last_updated: float = field(default_factory=time.time)
    history: List[float] = field(default_factory=list)  # 历史分数
    decay_count: int = 0            # 衰减次数
    recovery_count: int = 0         # 恢复次数


# ============ 信任评估器 ============

class TrustEvaluator:
    """
    信任动态评估器
    
    功能：
    - 信任分动态计算
    - 信任衰减机制
    - 信任恢复策略
    
    使用示例：
        evaluator = TrustEvaluator(node_registry)
        
        # 获取节点信任分
        trust = evaluator.get_trust(node_id)
        
        # 更新信任分
        evaluator.update_trust(node_id, delta=10)
        
        # 获取所有低信任节点
        low_trust_nodes = evaluator.get_low_trust_nodes(threshold=30)
    """

    # 信任级别阈值
    LEVEL_THRESHOLDS = {
        TrustLevel.BLOCKED: 0,
        TrustLevel.VERY_LOW: 20,
        TrustLevel.LOW: 40,
        TrustLevel.MEDIUM: 60,
        TrustLevel.HIGH: 80,
        TrustLevel.VERY_HIGH: 95
    }

    # 衰减配置
    DECAY_RATE = 0.95          # 每次衰减保留95%
    DECAY_INTERVAL = 3600      # 衰减间隔（秒）
    RECOVERY_RATE = 5          # 每次恢复增加5分
    MIN_SCORE = 0              # 最低分数
    MAX_SCORE = 100            # 最高分数

    def __init__(
        self,
        node_registry: NodeRegistry,
        initial_score: float = 50.0,
        decay_enabled: bool = True
    ):
        self.node_registry = node_registry
        self.initial_score = initial_score
        self.decay_enabled = decay_enabled
        
        # 信任分缓存
        self._trust_cache: Dict[str, TrustScore] = {}
        
        # 回调函数
        self._callbacks: List[Callable] = []
        
        # 统计数据
        self._stats = {
            "total_evaluations": 0,
            "decay_triggered": 0,
            "recovery_triggered": 0,
            "blocked_nodes": 0
        }

    def get_trust(self, node_id: str) -> TrustScore:
        """获取节点信任分"""
        if node_id not in self._trust_cache:
            # 初始化信任分
            self._trust_cache[node_id] = TrustScore(
                node_id=node_id,
                score=self.initial_score,
                level=TrustLevel.MEDIUM
            )
        
        return self._trust_cache[node_id]

    def update_trust(self, node_id: str, delta: float, reason: str = ""):
        """
        更新信任分
        
        Args:
            node_id: 节点ID
            delta: 分数变化（正数增加，负数减少）
            reason: 更新原因
        """
        trust = self.get_trust(node_id)
        
        old_score = trust.score
        trust.score = max(self.MIN_SCORE, min(self.MAX_SCORE, trust.score + delta))
        trust.last_updated = time.time()
        
        # 记录历史
        trust.history.append(trust.score)
        if len(trust.history) > 100:
            trust.history.pop(0)
        
        # 更新级别
        trust.level = self._score_to_level(trust.score)
        
        # 触发回调
        if old_score != trust.score:
            for callback in self._callbacks:
                try:
                    callback(trust, old_score, delta, reason)
                except Exception as e:
                    print(f"❌ Trust callback error: {e}")
        
        self._stats["total_evaluations"] += 1

    def decay_trust(self, node_id: str):
        """信任衰减"""
        trust = self.get_trust(node_id)
        
        # 检查是否应该衰减
        if trust.last_updated < time.time() - self.DECAY_INTERVAL:
            old_score = trust.score
            trust.score *= self.DECAY_RATE
            trust.score = max(self.MIN_SCORE, trust.score)
            trust.decay_count += 1
            trust.last_updated = time.time()
            
            self._stats["decay_triggered"] += 1
            
            # 更新级别
            trust.level = self._score_to_level(trust.score)

    def recover_trust(self, node_id: str, success: bool):
        """
        信任恢复
        
        Args:
            node_id: 节点ID
            success: 操作是否成功
        """
        trust = self.get_trust(node_id)
        
        if success:
            # 成功恢复
            self.update_trust(node_id, self.RECOVERY_RATE, "successful_operation")
            trust.recovery_count += 1
            self._stats["recovery_triggered"] += 1
        else:
            # 失败衰减
            self.update_trust(node_id, -self.RECOVERY_RATE * 2, "failed_operation")

    def block_node(self, node_id: str, reason: str = ""):
        """屏蔽节点"""
        trust = self.get_trust(node_id)
        trust.score = self.MIN_SCORE
        trust.level = TrustLevel.BLOCKED
        self._stats["blocked_nodes"] += 1
        
        print(f"🚫 Node {node_id} blocked: {reason}")

    def get_low_trust_nodes(self, threshold: float = 40.0) -> List[str]:
        """获取低信任节点列表"""
        low_trust = []
        for node_id in self._trust_cache:
            trust = self._trust_cache[node_id]
            if trust.score < threshold:
                low_trust.append(node_id)
        return low_trust

    def get_trust_summary(self) -> Dict:
        """获取信任摘要"""
        if not self._trust_cache:
            return {"total_nodes": 0}
        
        scores = [t.score for t in self._trust_cache.values()]
        levels = {}
        for t in self._trust_cache.values():
            levels[t.level.value] = levels.get(t.level.value, 0) + 1
        
        return {
            "total_nodes": len(self._trust_cache),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "level_distribution": levels,
            **self._stats
        }

    def register_callback(self, callback: Callable):
        """注册信任变化回调"""
        self._callbacks.append(callback)

    def _score_to_level(self, score: float) -> TrustLevel:
        """分数转级别"""
        if score >= self.LEVEL_THRESHOLDS[TrustLevel.VERY_HIGH]:
            return TrustLevel.VERY_HIGH
        elif score >= self.LEVEL_THRESHOLDS[TrustLevel.HIGH]:
            return TrustLevel.HIGH
        elif score >= self.LEVEL_THRESHOLDS[TrustLevel.MEDIUM]:
            return TrustLevel.MEDIUM
        elif score >= self.LEVEL_THRESHOLDS[TrustLevel.LOW]:
            return TrustLevel.LOW
        elif score >= self.LEVEL_THRESHOLDS[TrustLevel.VERY_LOW]:
            return TrustLevel.VERY_LOW
        else:
            return TrustLevel.BLOCKED

    def _level_to_score(self, level: TrustLevel) -> float:
        """级别转分数"""
        return self.LEVEL_THRESHOLDS[level]


# ============ 便捷函数 ============

def create_evaluator(node_registry: NodeRegistry) -> TrustEvaluator:
    """创建评估器"""
    return TrustEvaluator(node_registry)
