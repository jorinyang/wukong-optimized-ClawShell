#!/usr/bin/env python3
"""
ClawShell 信任管理器 (Trust Manager)
版本: v0.2.5-B
功能: 已知节点认证、陌生节点评估、信任评分
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# ============ 配置 ============

TRUST_CONFIG_PATH = Path("~/.openclaw/.trust_config.json").expanduser()
TRUST_STATE_PATH = Path("~/.openclaw/.trust_state.json").expanduser()


# ============ 数据结构 ============

class TrustLevel(Enum):
    """信任级别"""
    UNKNOWN = "unknown"
    BLOCKED = "blocked"    # 拒绝
    LOW = "low"           # 初步信任
    MEDIUM = "medium"     # 中等信任
    HIGH = "high"         # 高度信任
    FULL = "full"        # 完全信任


@dataclass
class TrustScore:
    """信任评分"""
    node_id: str
    score: float = 0.0  # 0-100
    level: TrustLevel = TrustLevel.UNKNOWN
    interactions: int = 0
    successes: int = 0
    failures: int = 0
    last_interaction: float = 0
    history: List[Dict] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.interactions == 0:
            return 0.0
        return self.successes / self.interactions
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "score": self.score,
            "level": self.level.value,
            "interactions": self.interactions,
            "successes": self.successes,
            "failures": self.failures,
            "last_interaction": self.last_interaction,
            "history": self.history[-50:]  # 最近50条
        }


# ============ 信任评估器 ============

class TrustManager:
    """信任管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if TRUST_CONFIG_PATH.exists():
            try:
                with open(TRUST_CONFIG_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "initial_trust": 50.0,  # 初始信任分
            "success_bonus": 5.0,   # 成功加分
            "failure_penalty": 10.0, # 失败扣分
            "time_decay": 0.95,      # 时间衰减因子
            "min_score": 0.0,        # 最低分
            "max_score": 100.0,      # 最高分
            "thresholds": {
                "low": 30,
                "medium": 60,
                "high": 80,
                "full": 95
            },
            "known_nodes": {  # 预信任节点
                "openclaw": 100.0,
                "hermes": 100.0,
                "n8n": 80.0,
                "memos": 70.0,
                "obsidian": 70.0
            }
        }
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if TRUST_STATE_PATH.exists():
            try:
                with open(TRUST_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {"trust_scores": {}}
    
    def _save_state(self):
        """保存状态"""
        with open(TRUST_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _calculate_level(self, score: float) -> TrustLevel:
        """计算信任级别"""
        thresholds = self.config["thresholds"]
        
        if score >= thresholds["full"]:
            return TrustLevel.FULL
        elif score >= thresholds["high"]:
            return TrustLevel.HIGH
        elif score >= thresholds["medium"]:
            return TrustLevel.MEDIUM
        elif score >= thresholds["low"]:
            return TrustLevel.LOW
        else:
            return TrustLevel.BLOCKED
    
    # ---- 信任查询 ----
    
    def get_trust(self, node_id: str) -> TrustScore:
        """获取节点信任评分"""
        if node_id in self.state["trust_scores"]:
            data = self.state["trust_scores"][node_id]
            return TrustScore(
                node_id=node_id,
                score=data["score"],
                level=TrustLevel(data.get("level", "unknown")),
                interactions=data.get("interactions", 0),
                successes=data.get("successes", 0),
                failures=data.get("failures", 0),
                last_interaction=data.get("last_interaction", 0),
                history=data.get("history", [])
            )
        
        # 检查是否是已知节点
        for known_prefix, score in self.config["known_nodes"].items():
            if node_id.startswith(known_prefix):
                return TrustScore(
                    node_id=node_id,
                    score=score,
                    level=TrustLevel.HIGH,
                    interactions=1,
                    successes=1
                )
        
        # 新节点返回初始信任分
        return TrustScore(
            node_id=node_id,
            score=self.config["initial_trust"],
            level=TrustLevel.MEDIUM
        )
    
    def evaluate(self, node_id: str) -> Dict:
        """
        评估节点信任
        
        Returns:
            包含信任信息的字典
        """
        trust = self.get_trust(node_id)
        
        return {
            "node_id": node_id,
            "score": trust.score,
            "level": trust.level.value,
            "can_trust": trust.level not in [TrustLevel.UNKNOWN, TrustLevel.BLOCKED],
            "recommendation": self._get_recommendation(trust)
        }
    
    def _get_recommendation(self, trust: TrustScore) -> str:
        """获取信任建议"""
        if trust.level == TrustLevel.BLOCKED:
            return "拒绝交互"
        elif trust.level == TrustLevel.LOW:
            return "谨慎交互，限制权限"
        elif trust.level == TrustLevel.MEDIUM:
            return "允许基本交互"
        elif trust.level == TrustLevel.HIGH:
            return "允许大多数操作"
        elif trust.level == TrustLevel.FULL:
            return "完全信任，允许所有操作"
        else:
            return "需要先建立信任"
    
    # ---- 信任更新 ----
    
    def record_success(self, node_id: str, details: Optional[Dict] = None):
        """记录成功交互"""
        self._update_trust(node_id, success=True, details=details)
    
    def record_failure(self, node_id: str, details: Optional[Dict] = None):
        """记录失败交互"""
        self._update_trust(node_id, success=False, details=details)
    
    def _update_trust(self, node_id: str, success: bool, details: Optional[Dict] = None):
        """更新信任评分"""
        trust = self.get_trust(node_id)
        
        # 更新时间
        trust.last_interaction = time.time()
        trust.interactions += 1
        
        if success:
            trust.successes += 1
            trust.score = min(
                self.config["max_score"],
                trust.score + self.config["success_bonus"]
            )
        else:
            trust.failures += 1
            trust.score = max(
                self.config["min_score"],
                trust.score - self.config["failure_penalty"]
            )
        
        # 重新计算级别
        trust.level = self._calculate_level(trust.score)
        
        # 添加历史记录
        trust.history.append({
            "timestamp": time.time(),
            "success": success,
            "details": details or {}
        })
        
        # 保存
        self.state["trust_scores"][node_id] = trust.to_dict()
        self._save_state()
    
    # ---- 信任决策 ----
    
    def can_interact(self, node_id: str, required_level: TrustLevel = TrustLevel.MEDIUM) -> bool:
        """判断是否可以交互"""
        trust = self.get_trust(node_id)
        
        level_order = [
            TrustLevel.UNKNOWN,
            TrustLevel.BLOCKED,
            TrustLevel.LOW,
            TrustLevel.MEDIUM,
            TrustLevel.HIGH,
            TrustLevel.FULL
        ]
        
        return level_order.index(trust.level) >= level_order.index(required_level)
    
    def get_interaction_limits(self, node_id: str) -> Dict:
        """获取交互限制"""
        trust = self.get_trust(node_id)
        
        limits = {
            TrustLevel.BLOCKED: {"read": False, "write": False, "execute": False},
            TrustLevel.LOW: {"read": True, "write": False, "execute": False},
            TrustLevel.MEDIUM: {"read": True, "write": True, "execute": False},
            TrustLevel.HIGH: {"read": True, "write": True, "execute": True},
            TrustLevel.FULL: {"read": True, "write": True, "execute": True},
        }
        
        return limits.get(trust.level, limits[TrustLevel.LOW])
    
    # ---- 信任列表 ----
    
    def get_all_trusted(self) -> List[str]:
        """获取所有可信节点ID"""
        trusted = []
        for node_id in self.state.get("trust_scores", {}):
            if self.can_interact(node_id, TrustLevel.LOW):
                trusted.append(node_id)
        return trusted
    
    def get_trust_leaderboard(self, limit: int = 10) -> List[Dict]:
        """获取信任排行榜"""
        scores = []
        for node_id, data in self.state.get("trust_scores", {}).items():
            scores.append({
                "node_id": node_id,
                "score": data["score"],
                "level": data["level"],
                "interactions": data.get("interactions", 0)
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:limit]


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 信任管理器")
    subparsers = parser.add_subparsers(dest="command")
    
    # 评估
    eval_parser = subparsers.add_parser("eval", help="评估节点")
    eval_parser.add_argument("node_id")
    
    # 记录
    record_parser = subparsers.add_parser("record", help="记录交互")
    record_parser.add_argument("node_id")
    record_parser.add_argument("--success", action="store_true")
    record_parser.add_argument("--failure", action="store_true")
    
    # 排行榜
    subparsers.add_parser("top", help="信任排行榜")
    
    # 检查
    check_parser = subparsers.add_parser("check", help="检查信任")
    check_parser.add_argument("node_id")
    check_parser.add_argument("--level", default="medium")
    
    args = parser.parse_args()
    
    manager = TrustManager()
    
    if args.command == "eval":
        result = manager.evaluate(args.node_id)
        print("=" * 60)
        print(f"节点: {result['node_id']}")
        print(f"信任分: {result['score']:.1f}")
        print(f"信任级: {result['level']}")
        print(f"可信任: {'是' if result['can_trust'] else '否'}")
        print(f"建议: {result['recommendation']}")
    
    elif args.command == "record":
        if args.success:
            manager.record_success(args.node_id)
            print(f"✅ 已记录成功: {args.node_id}")
        elif args.failure:
            manager.record_failure(args.node_id)
            print(f"❌ 已记录失败: {args.node_id}")
    
    elif args.command == "top":
        leaderboard = manager.get_trust_leaderboard()
        print("信任排行榜:")
        for i, item in enumerate(leaderboard, 1):
            print(f"  {i}. {item['node_id']} - {item['score']:.1f} ({item['level']})")
    
    elif args.command == "check":
        required = TrustLevel(args.level)
        can = manager.can_interact(args.node_id, required)
        limits = manager.get_interaction_limits(args.node_id)
        print(f"节点 {args.node_id}:")
        print(f"  可交互: {'是' if can else '否'}")
        print(f"  限制: 读={limits['read']}, 写={limits['write']}, 执行={limits['execute']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
