#!/usr/bin/env python3
"""
ClawShell 信任动态撤销扩展
版本: v0.2.1-B
功能: 基于行为的信任分动态调整和自动撤销
依赖: TrustManager
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

# 配置
REVOKE_THRESHOLD = 20      # 撤销阈值
MIN_TRUST_SCORE = 10     # 最低信任分
DECAY_RATE = 0.95         # 每日衰减率


class TrustRevocator:
    """
    信任动态撤销器
    ===============

    功能：
    - 信任分动态调整
    - 信任衰减
    - 自动撤销

    使用示例：
        revocator = TrustRevocator(trust_manager, node_registry)

        # 调整信任分
        revocator.adjust_trust("node_123", +10)  # 成功 +10

        # 调整信任分
        revocator.adjust_trust("node_123", -20)  # 失败 -20

        # 启动衰减
        revocator.start_decay()
    """

    def __init__(
        self,
        trust_manager,
        node_registry,
        revoke_threshold: float = REVOKE_THRESHOLD,
        min_trust_score: float = MIN_TRUST_SCORE
    ):
        self.trust_manager = trust_manager
        self.node_registry = node_registry
        self.revoke_threshold = revoke_threshold
        self.min_trust_score = min_trust_score

        # 事件回调
        self.callbacks: Dict[str, list] = {}

        logger.info("TrustRevocator initialized")
        logger.info(f"Revoke threshold: {revoke_threshold}")

    def adjust_trust(self, node_id: str, delta: float, reason: str = "") -> bool:
        """
        调整信任分

        Args:
            node_id: 节点ID
            delta: 调整值 (+/-)
            reason: 调整原因

        Returns:
            bool: 是否触发撤销
        """
        # 获取当前分数
        current_score = self._get_score(node_id)

        # 计算新分数
        new_score = max(self.min_trust_score, current_score + delta)

        # 记录历史
        self._record_adjustment(node_id, delta, new_score, reason)

        # 检查是否需要撤销
        if new_score < self.revoke_threshold:
            self._revoke_node(node_id, new_score)
            return True

        return False

    def _get_score(self, node_id: str) -> float:
        """获取信任分"""
        if hasattr(self.trust_manager, 'get_trust_score'):
            return self.trust_manager.get_trust_score(node_id)
        return 50.0  # 默认分数

    def _set_score(self, node_id: str, score: float):
        """设置信任分"""
        if hasattr(self.trust_manager, 'set_trust_score'):
            self.trust_manager.set_trust_score(node_id, score)
        elif hasattr(self.trust_manager, 'trust_scores'):
            if node_id in self.trust_manager.trust_scores:
                self.trust_manager.trust_scores[node_id].score = score

    def _record_adjustment(self, node_id: str, delta: float, new_score: float, reason: str):
        """记录调整历史"""
        record = {
            "delta": delta,
            "new_score": new_score,
            "reason": reason,
            "timestamp": time.time()
        }

        if hasattr(self.trust_manager, 'record_interaction'):
            self.trust_manager.record_interaction(node_id, record)

        logger.info(f"Trust adjusted: {node_id} {delta:+} -> {new_score} ({reason})")

        # 触发回调
        self._emit_callback("trust_adjusted", {
            "node_id": node_id,
            "delta": delta,
            "new_score": new_score,
            "reason": reason
        })

    def _revoke_node(self, node_id: str, score: float):
        """撤销节点"""
        logger.warning(f"Node {node_id} trust score {score} below threshold, revoking")

        # 更新节点状态
        self.node_registry.update_status(node_id, NodeStatus.OFFLINE)

        # 触发回调
        self._emit_callback("node_revoked", {
            "node_id": node_id,
            "score": score,
            "threshold": self.revoke_threshold
        })

    def register_callback(self, event: str, callback):
        """注册事件回调"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)

    def _emit_callback(self, event: str, data: dict):
        """触发回调"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "revoke_threshold": self.revoke_threshold,
            "min_trust_score": self.min_trust_score
        }


# 导出到NodeStatus
from swarm.node_registry import NodeStatus
