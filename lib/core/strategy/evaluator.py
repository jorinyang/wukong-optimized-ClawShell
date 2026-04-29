#!/usr/bin/env python3
"""
ClawShell 策略评估器
版本: v0.2.4-A
功能: 策略效果评估、多策略并发管理
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from pathlib import Path

# ============ 配置 ============

EVAL_STATE_PATH = Path("~/.openclaw/.strategy_eval_state.json").expanduser()
EVAL_CONFIG_PATH = Path("~/.openclaw/.strategy_eval_config.json").expanduser()


# ============ 数据结构 ============

@dataclass
class MetricRecord:
    """指标记录"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class StrategyMetrics:
    """策略指标"""
    strategy_id: str
    switch_count: int = 0  # 切换次数
    success_count: int = 0
    failure_count: int = 0
    avg_response_time: float = 0.0
    total_requests: int = 0
    history: List[Dict] = field(default_factory=list)  # 最近的历史记录
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "switch_count": self.switch_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_response_time": self.avg_response_time,
            "total_requests": self.total_requests,
            "success_rate": self.success_rate,
            "history": self.history[-20:]  # 最近20条
        }


@dataclass
class EvaluationResult:
    """评估结果"""
    strategy_id: str
    score: float  # 综合评分 0-100
    components: Dict[str, float]  # 各维度评分
    recommendation: str  # 建议
    should_switch: bool  # 是否建议切换
    confidence: float  # 置信度
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "score": self.score,
            "components": self.components,
            "recommendation": self.recommendation,
            "should_switch": self.should_switch,
            "confidence": self.confidence
        }


# ============ 策略评估器 ============

class StrategyEvaluator:
    """策略评估器"""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyMetrics] = {}
        self.current_strategy: Optional[str] = None
        self.config = self._load_config()
        self.state = self._load_state()
        self._response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if EVAL_CONFIG_PATH.exists():
            try:
                with open(EVAL_CONFIG_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "evaluation_window": 300,  # 评估窗口（秒）
            "min_samples": 10,  # 最少样本数
            "success_weight": 0.4,  # 成功率权重
            "response_time_weight": 0.3,  # 响应时间权重
            "stability_weight": 0.3,  # 稳定性权重
            "switch_threshold": 20,  # 切换阈值（分数差距）
            "cooldown": 60  # 切换冷却期（秒）
        }
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if EVAL_STATE_PATH.exists():
            try:
                with open(EVAL_STATE_PATH) as f:
                    state = json.load(f)
                    
                    for sid, metrics_data in state.get("strategies", {}).items():
                        metrics = StrategyMetrics(
                            strategy_id=sid,
                            switch_count=metrics_data.get("switch_count", 0),
                            success_count=metrics_data.get("success_count", 0),
                            failure_count=metrics_data.get("failure_count", 0),
                            avg_response_time=metrics_data.get("avg_response_time", 0.0),
                            total_requests=metrics_data.get("total_requests", 0),
                            history=metrics_data.get("history", [])
                        )
                        self.strategies[sid] = metrics
                    
                    return {
                        "current_strategy": state.get("current_strategy"),
                        "last_switch": state.get("last_switch", 0),
                        "last_evaluation": state.get("last_evaluation", 0)
                    }
            except:
                pass
        return {
            "current_strategy": None,
            "last_switch": 0,
            "last_evaluation": 0
        }
    
    def _save_state(self):
        """保存状态"""
        state = {
            "strategies": {
                sid: metrics.to_dict() for sid, metrics in self.strategies.items()
            },
            "current_strategy": self.current_strategy,
            "last_switch": self.state.get("last_switch", 0),
            "last_evaluation": self.state.get("last_evaluation", 0)
        }
        with open(EVAL_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    # ---- 指标记录 ----
    
    def record_success(self, strategy_id: str, response_time: Optional[float] = None):
        """记录成功"""
        self._ensure_strategy(strategy_id)
        metrics = self.strategies[strategy_id]
        
        metrics.success_count += 1
        metrics.total_requests += 1
        
        if response_time is not None:
            metrics.avg_response_time = (
                (metrics.avg_response_time * (metrics.total_requests - 1) + response_time)
                / metrics.total_requests
            )
            self._response_times[strategy_id].append(response_time)
        
        self._add_history(strategy_id, "success", {"response_time": response_time})
        self._save_state()
    
    def record_failure(self, strategy_id: str, error: Optional[str] = None):
        """记录失败"""
        self._ensure_strategy(strategy_id)
        metrics = self.strategies[strategy_id]
        
        metrics.failure_count += 1
        metrics.total_requests += 1
        
        self._add_history(strategy_id, "failure", {"error": error})
        self._save_state()
    
    def record_switch(self, from_strategy: str, to_strategy: str):
        """记录策略切换"""
        if from_strategy in self.strategies:
            self.strategies[from_strategy].switch_count += 1
        
        self._ensure_strategy(to_strategy)
        
        self.current_strategy = to_strategy
        self.state["last_switch"] = time.time()
        
        self._add_history(to_strategy, "switch_in", {"from": from_strategy})
        self._save_state()
    
    def _ensure_strategy(self, strategy_id: str):
        """确保策略存在"""
        if strategy_id not in self.strategies:
            self.strategies[strategy_id] = StrategyMetrics(strategy_id=strategy_id)
    
    def _add_history(self, strategy_id: str, event_type: str, data: Dict):
        """添加历史记录"""
        metrics = self.strategies[strategy_id]
        
        metrics.history.append({
            "type": event_type,
            "timestamp": time.time(),
            **data
        })
        
        # 只保留最近100条
        if len(metrics.history) > 100:
            metrics.history = metrics.history[-100:]
    
    # ---- 评估 ----
    
    def evaluate(self, strategy_id: str) -> EvaluationResult:
        """评估单个策略"""
        if strategy_id not in self.strategies:
            return EvaluationResult(
                strategy_id=strategy_id,
                score=0,
                components={},
                recommendation="策略无数据",
                should_switch=False,
                confidence=0
            )
        
        metrics = self.strategies[strategy_id]
        
        # 检查样本数
        if metrics.total_requests < self.config["min_samples"]:
            return EvaluationResult(
                strategy_id=strategy_id,
                score=50,  # 默认分数
                components={
                    "success_rate": 50,
                    "response_time": 50,
                    "stability": 50
                },
                recommendation="样本不足，继续观察",
                should_switch=False,
                confidence=0.1
            )
        
        # 计算各维度分数 (0-100)
        
        # 1. 成功率 (权重 40%)
        success_rate = metrics.success_rate * 100
        success_score = success_rate
        
        # 2. 响应时间 (权重 30%)
        # 越快越好，假设100ms以下为满分
        response_time_score = max(0, 100 - metrics.avg_response_time)
        response_time_score = min(100, response_time_score)
        
        # 3. 稳定性 (权重 30%)
        # 基于失败率计算
        failure_rate = metrics.failure_count / metrics.total_requests
        stability_score = (1 - failure_rate) * 100
        
        # 综合评分
        score = (
            success_score * self.config["success_weight"] +
            response_time_score * self.config["response_time_weight"] +
            stability_score * self.config["stability_weight"]
        )
        
        # 生成建议
        if score >= 80:
            recommendation = "策略表现优秀，保持当前策略"
            should_switch = False
        elif score >= 60:
            recommendation = "策略表现良好，可继续观察"
            should_switch = False
        elif score >= 40:
            recommendation = "策略表现一般，建议关注其他策略"
            should_switch = True
        else:
            recommendation = "策略表现较差，建议切换"
            should_switch = True
        
        # 计算置信度（基于样本数）
        confidence = min(1.0, metrics.total_requests / 100)
        
        return EvaluationResult(
            strategy_id=strategy_id,
            score=score,
            components={
                "success_rate": success_score,
                "response_time": response_time_score,
                "stability": stability_score
            },
            recommendation=recommendation,
            should_switch=should_switch,
            confidence=confidence
        )
    
    def evaluate_all(self) -> Dict[str, EvaluationResult]:
        """评估所有策略"""
        results = {}
        for strategy_id in self.strategies:
            results[strategy_id] = self.evaluate(strategy_id)
        
        self.state["last_evaluation"] = time.time()
        self._save_state()
        
        return results
    
    def get_best_strategy(self) -> Optional[str]:
        """获取最佳策略"""
        results = self.evaluate_all()
        
        if not results:
            return None
        
        best = max(results.items(), key=lambda x: x[1].score)
        return best[0] if best[1].score > 0 else None
    
    def should_switch_now(self) -> bool:
        """判断是否应该现在切换"""
        # 检查冷却期
        cooldown = self.config["cooldown"]
        if time.time() - self.state.get("last_switch", 0) < cooldown:
            return False
        
        # 评估当前策略
        if not self.current_strategy:
            return True
        
        current_result = self.evaluate(self.current_strategy)
        
        # 获取最佳策略
        best_strategy = self.get_best_strategy()
        if not best_strategy or best_strategy == self.current_strategy:
            return False
        
        best_result = self.evaluate(best_strategy)
        
        # 检查分数差距是否超过阈值
        threshold = self.config["switch_threshold"]
        if best_result.score - current_result.score >= threshold:
            return True
        
        return False
    
    def get_recommendation(self) -> Dict:
        """获取策略建议"""
        current_result = self.evaluate(self.current_strategy) if self.current_strategy else None
        best_strategy = self.get_best_strategy()
        best_result = self.evaluate(best_strategy) if best_strategy else None
        
        return {
            "current_strategy": self.current_strategy,
            "current_score": current_result.score if current_result else None,
            "best_strategy": best_strategy,
            "best_score": best_result.score if best_result else None,
            "should_switch": self.should_switch_now(),
            "all_scores": {
                sid: result.score for sid, result in self.evaluate_all().items()
            }
        }


# ============ 多策略管理器 ============

class MultiStrategyManager:
    """多策略并发管理器"""
    
    def __init__(self):
        self.active_strategies: Dict[str, bool] = {}  # strategy_id -> enabled
        self.strategy_configs: Dict[str, Dict] = {}  # 策略特定配置
        self.evaluator = StrategyEvaluator()
    
    def enable_strategy(self, strategy_id: str, config: Optional[Dict] = None):
        """启用策略"""
        self.active_strategies[strategy_id] = True
        if config:
            self.strategy_configs[strategy_id] = config
    
    def disable_strategy(self, strategy_id: str):
        """禁用策略"""
        self.active_strategies[strategy_id] = False
    
    def get_enabled_strategies(self) -> List[str]:
        """获取已启用的策略"""
        return [sid for sid, enabled in self.active_strategies.items() if enabled]
    
    def get_strategy_config(self, strategy_id: str) -> Optional[Dict]:
        """获取策略配置"""
        return self.strategy_configs.get(strategy_id)


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 策略评估器")
    subparsers = parser.add_subparsers(dest="command")
    
    # 记录
    record_parser = subparsers.add_parser("record", help="记录结果")
    record_parser.add_argument("--strategy", required=True)
    record_parser.add_argument("--success", action="store_true")
    record_parser.add_argument("--failure", action="store_true")
    record_parser.add_argument("--time", type=float, help="响应时间(ms)")
    
    # 评估
    eval_parser = subparsers.add_parser("evaluate", help="评估策略")
    eval_parser.add_argument("--strategy", help="指定策略")
    eval_parser.add_argument("--all", action="store_true")
    
    # 建议
    subparsers.add_parser("recommend", help="获取建议")
    
    # 状态
    subparsers.add_parser("status", help="状态")
    
    args = parser.parse_args()
    
    evaluator = StrategyEvaluator()
    
    if args.command == "record":
        if args.success:
            evaluator.record_success(args.strategy, args.time)
            print(f"✅ 记录成功: {args.strategy}")
        elif args.failure:
            evaluator.record_failure(args.strategy)
            print(f"❌ 记录失败: {args.strategy}")
    
    elif args.command == "evaluate":
        if args.all:
            results = evaluator.evaluate_all()
            print("=" * 60)
            print("策略评估结果")
            print("=" * 60)
            for sid, result in sorted(results.items(), key=lambda x: -x[1].score):
                current_mark = " ← 当前" if sid == evaluator.current_strategy else ""
                print(f"\n[{sid}]{current_mark}")
                print(f"  综合评分: {result.score:.1f}")
                print(f"  成功率: {result.components['success_rate']:.1f}%")
                print(f"  响应时间: {result.components['response_time']:.1f}")
                print(f"  稳定性: {result.components['stability']:.1f}")
                print(f"  建议: {result.recommendation}")
        elif args.strategy:
            result = evaluator.evaluate(args.strategy)
            print(f"策略: {result.strategy_id}")
            print(f"评分: {result.score:.1f}")
            print(f"建议: {result.recommendation}")
    
    elif args.command == "recommend":
        rec = evaluator.get_recommendation()
        print("=" * 60)
        print("策略建议")
        print("=" * 60)
        print(f"当前策略: {rec['current_strategy']} (评分: {rec['current_score']})")
        print(f"最佳策略: {rec['best_strategy']} (评分: {rec['best_score']})")
        print(f"建议切换: {'是' if rec['should_switch'] else '否'}")
        print()
        print("各策略评分:")
        for sid, score in sorted(rec['all_scores'].items(), key=lambda x: -x[1]):
            print(f"  {sid}: {score:.1f}")
    
    elif args.command == "status":
        print("=" * 60)
        print("策略评估器状态")
        print("=" * 60)
        print(f"当前策略: {evaluator.current_strategy}")
        print(f"策略数量: {len(evaluator.strategies)}")
        print(f"最后评估: {time.ctime(evaluator.state.get('last_evaluation', 0))}")
        print(f"最后切换: {time.ctime(evaluator.state.get('last_switch', 0))}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
