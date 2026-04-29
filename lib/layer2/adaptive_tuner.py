#!/usr/bin/env python3
"""
ClawShell 自适应参数调整器
版本: v0.2.0-A
理论依据: 钱学森《工程控制论》- 自适应控制
功能: 根据环境变化自动调整控制参数
"""

import time
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


# ============ 数据结构 ============

class TuningStatus(Enum):
    """调参状态"""
    IDLE = "idle"
    TUNING = "tuning"
    CONVERGED = "converged"
    FAILED = "failed"


@dataclass
class ParameterConfig:
    """参数配置"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    step_size: float = 0.1
    learning_rate: float = 0.1


@dataclass
class TuningResult:
    """调参结果"""
    parameter: str
    initial_value: float
    final_value: float
    iterations: int
    converged: bool
    improvement: float
    timestamp: float = field(default_factory=time.time)


# ============ 自适应参数调整器 ============

class AdaptiveParameterTuner:
    """
    自适应参数调整器
    
    依据: 工程控制论的自适应控制理论
    
    功能：
    - 根据偏差自动调整参数
    - 学习率自适应
    - 参数边界保护
    - 收敛判断
    
    使用示例:
        tuner = AdaptiveParameterTuner()
        
        # 添加可调参数
        tuner.add_parameter("kp", initial=1.0, min=0.1, max=10.0)
        tuner.add_parameter("ki", initial=0.1, min=0.01, max=1.0)
        
        # 执行调参
        result = tuner.tune(
            objective_fn=lambda params: -abs(evaluate(params)),  # 目标函数（负值，越小越好）
            target_value=0.0,
            max_iterations=100
        )
    """

    def __init__(
        self,
        convergence_threshold: float = 0.01,
        max_stagnant_iterations: int = 10
    ):
        self.convergence_threshold = convergence_threshold
        self.max_stagnant_iterations = max_stagnant_iterations
        
        # 参数存储
        self.parameters: Dict[str, ParameterConfig] = {}
        
        # 调参历史
        self.history: List[Dict] = []
        
        # 回调函数
        self.on_iteration: Optional[Callable] = None
        self.on_converged: Optional[Callable] = None
        self.on_failed: Optional[Callable] = None
        
        # 统计
        self.stats = {
            "total_tunings": 0,
            "converged_count": 0,
            "failed_count": 0
        }

    def add_parameter(
        self,
        name: str,
        initial: float,
        min_value: float,
        max_value: float,
        step_size: float = 0.1,
        learning_rate: float = 0.1
    ):
        """添加可调参数"""
        config = ParameterConfig(
            name=name,
            current_value=initial,
            min_value=min_value,
            max_value=max_value,
            step_size=step_size,
            learning_rate=learning_rate
        )
        self.parameters[name] = config

    def remove_parameter(self, name: str) -> bool:
        """移除参数"""
        if name in self.parameters:
            del self.parameters[name]
            return True
        return False

    def get_parameters(self) -> Dict[str, float]:
        """获取当前参数值"""
        return {name: config.current_value for name, config in self.parameters.items()}

    def tune(
        self,
        objective_fn: Callable[[Dict[str, float]], float],
        target_value: float = 0.0,
        max_iterations: int = 100,
        verbose: bool = False
    ) -> TuningResult:
        """
        执行调参
        
        Args:
            objective_fn: 目标函数，输入参数字典，返回评价值
            target_value: 目标值
            max_iterations: 最大迭代次数
            verbose: 是否打印详细信息
        
        Returns:
            TuningResult: 调参结果
        """
        if not self.parameters:
            raise ValueError("No parameters to tune")
        
        self.stats["total_tunings"] += 1
        
        # 记录初始状态
        initial_params = self.get_parameters()
        initial_score = objective_fn(initial_params)
        
        # 迭代调参
        best_params = initial_params.copy()
        best_score = initial_score
        stagnant_count = 0
        
        for iteration in range(max_iterations):
            # 计算当前评价值
            current_score = objective_fn(self.get_parameters())
            current_deviation = abs(current_score - target_value)
            
            # 检查是否收敛
            if current_deviation < self.convergence_threshold:
                if verbose:
                    print(f"Converged at iteration {iteration}")
                
                result = TuningResult(
                    parameter=str(list(self.parameters.keys())),
                    initial_value=initial_score,
                    final_value=current_score,
                    iterations=iteration + 1,
                    converged=True,
                    improvement=abs(initial_score - current_score)
                )
                self.stats["converged_count"] += 1
                self._record_history(result, iteration)
                return result
            
            # 检查是否停滞
            if current_score >= best_score:
                stagnant_count += 1
                if stagnant_count >= self.max_stagnant_iterations:
                    if verbose:
                        print(f"Stagnated at iteration {iteration}")
                    break
            else:
                best_score = current_score
                best_params = self.get_parameters().copy()
                stagnant_count = 0
            
            # 自适应调整参数
            self._adaptive_step(objective_fn, current_score, target_value)
            
            # 触发回调
            if self.on_iteration:
                self.on_iteration(iteration, self.get_parameters(), current_score)
            
            if verbose and iteration % 10 == 0:
                print(f"Iter {iteration}: score={current_score:.4f}, deviation={current_deviation:.4f}")
        
        # 未收敛
        final_score = objective_fn(self.get_parameters())
        result = TuningResult(
            parameter=str(list(self.parameters.keys())),
            initial_value=initial_score,
            final_value=final_score,
            iterations=max_iterations,
            converged=False,
            improvement=abs(initial_score - final_score)
        )
        self.stats["failed_count"] += 1
        self._record_history(result, max_iterations)
        
        if self.on_failed:
            self.on_failed(result)
        
        return result

    def _adaptive_step(
        self,
        objective_fn: Callable[[Dict[str, float]], float],
        current_score: float,
        target: float
    ):
        """自适应步进"""
        deviation = current_score - target
        
        for name, config in self.parameters.items():
            # 根据偏差方向和大小自适应调整步长
            if deviation > 0:
                # 需要减小
                step = -config.step_size * config.learning_rate
            else:
                # 需要增大
                step = config.step_size * config.learning_rate
            
            # 应用步进
            new_value = config.current_value + step
            
            # 边界保护
            new_value = max(config.min_value, min(config.max_value, new_value))
            
            # 更新参数
            old_value = config.current_value
            config.current_value = new_value
            
            # 如果没有改善，回退
            if abs(objective_fn(self.get_parameters()) - current_score) > abs(deviation):
                config.current_value = old_value

    def tune_batch(
        self,
        configs: List[Dict[str, Any]],
        objective_fn: Callable[[Dict[str, float]], float],
        target_value: float = 0.0
    ) -> List[TuningResult]:
        """
        批量调参
        
        Args:
            configs: 参数配置列表
            objective_fn: 目标函数
            target_value: 目标值
        
        Returns:
            List[TuningResult]: 调参结果列表
        """
        results = []
        
        for config in configs:
            # 重置参数
            self.parameters.clear()
            
            # 添加参数
            for param_name, param_config in config.items():
                self.add_parameter(param_name, **param_config)
            
            # 执行调参
            result = self.tune(objective_fn, target_value)
            results.append(result)
        
        return results

    def get_best_parameters(self) -> Dict[str, float]:
        """获取最优参数（从历史中）"""
        if not self.history:
            return self.get_parameters()
        
        best = min(self.history, key=lambda x: abs(x["final_score"]))
        return best["parameters"]

    def _record_history(self, result: TuningResult, iteration: int):
        """记录历史"""
        record = {
            "iteration": iteration,
            "parameters": self.get_parameters(),
            "initial_score": result.initial_value,
            "final_score": result.final_value,
            "converged": result.converged,
            "timestamp": result.timestamp
        }
        self.history.append(record)
        
        # 保持最近100条记录
        if len(self.history) > 100:
            self.history.pop(0)
        
        if result.converged and self.on_converged:
            self.on_converged(result)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "total_parameters": len(self.parameters),
            "history_size": len(self.history)
        }


# ============ 便捷函数 ============

def create_tuner(
    convergence_threshold: float = 0.01,
    max_stagnant: int = 10
) -> AdaptiveParameterTuner:
    """创建调参器"""
    return AdaptiveParameterTuner(
        convergence_threshold=convergence_threshold,
        max_stagnant_iterations=max_stagnant
    )
