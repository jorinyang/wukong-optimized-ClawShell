#!/usr/bin/env python3
"""
ClawShell 鲁棒控制器
版本: v0.2.0-A
理论依据: 钱学森《工程控制论》- 鲁棒性设计
功能: 参数不确定下仍保持性能的控制系统
"""

import time
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


# ============ 数据结构 ============

class PerturbationType(Enum):
    """扰动类型"""
    PARAMETER = "parameter"       # 参数扰动
    EXTERNAL = "external"        # 外部干扰
    STRUCTURAL = "structural"    # 结构扰动
    MEASUREMENT = "measurement"  # 测量噪声


@dataclass
class Perturbation:
    """扰动描述"""
    perturbation_type: PerturbationType
    magnitude: float
    affected_params: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class RobustnessMetrics:
    """鲁棒性指标"""
    stability_margin: float      # 稳定裕度
    performance_degradation: float  # 性能降级
    recovery_time: float         # 恢复时间
    robustness_score: float      # 鲁棒性评分 (0-100)


# ============ 鲁棒控制器 ============

class RobustController:
    """
    鲁棒控制器
    
    依据: 工程控制论的鲁棒性设计理论
    
    功能：
    - 摄动容忍度控制
    - 备份恢复机制
    - 稳定域控制
    - 性能保证
    
    使用示例:
        controller = RobustController(
            tolerance=0.3,        # 30%参数扰动容忍
            stability_margin=0.5  # 50%稳定裕度
        )
        
        # 设置控制目标
        controller.set_target(expected_value=70.0)
        
        # 执行鲁棒控制
        control_signal = controller.control(actual_value=85.0, perturbation=0.2)
        
        # 检查鲁棒性
        metrics = controller.evaluate_robustness()
    """

    def __init__(
        self,
        tolerance: float = 0.3,          # 容许的最大参数扰动比例
        stability_margin: float = 0.5,     # 稳定裕度
        backup_enabled: bool = True,         # 是否启用备份
        max_recovery_attempts: int = 3     # 最大恢复尝试次数
    ):
        self.tolerance = tolerance
        self.stability_margin = stability_margin
        self.backup_enabled = backup_enabled
        self.max_recovery_attempts = max_recovery_attempts
        
        # 控制目标
        self.expected_value: Optional[float] = None
        
        # 备份存储
        self.backup_params: Dict[str, float] = {}
        self.backup_count = 0
        
        # 恢复历史
        self.recovery_history: List[Dict] = []
        
        # 统计
        self.stats = {
            "total_controls": 0,
            "perturbations_detected": 0,
            "recoveries_attempted": 0,
            "recoveries_successful": 0,
            "backups_created": 0
        }

    def set_target(self, expected_value: float):
        """设置控制目标"""
        self.expected_value = expected_value

    def control(
        self,
        actual_value: float,
        perturbation: float = 0.0,
        controller_fn: Optional[Callable] = None
    ) -> float:
        """
        执行鲁棒控制
        
        Args:
            actual_value: 实际值
            perturbation: 检测到的扰动大小 (0-1)
            controller_fn: 控制函数，如果为None则使用简单的比例控制
        
        Returns:
            float: 控制信号
        """
        self.stats["total_controls"] += 1
        
        # 检测扰动
        if abs(perturbation) > 0:
            self.stats["perturbations_detected"] += 1
        
        # 扰动处理
        if perturbation > self.tolerance:
            # 超过容忍度，需要恢复
            if self.backup_enabled:
                success = self._attempt_recovery(perturbation)
                if success:
                    self.stats["recoveries_successful"] += 1
                else:
                    # 使用降级控制
                    return self._degraded_control(actual_value, perturbation)
        
        # 正常控制
        if controller_fn:
            return controller_fn(actual_value, self.expected_value)
        else:
            return self._default_control(actual_value, perturbation)

    def _default_control(self, actual: float, perturbation: float) -> float:
        """默认比例控制"""
        if self.expected_value is None:
            return 0.0
        
        # 偏差
        deviation = self.expected_value - actual
        
        # 考虑扰动的自适应增益
        adaptive_gain = 1.0 / (1.0 + perturbation)
        
        # 比例控制
        control = adaptive_gain * deviation
        
        return control

    def _degraded_control(self, actual: float, perturbation: float) -> float:
        """
        降级控制 - 当扰动超过容忍度时使用
        
        目标：保证系统稳定，而非最优性能
        """
        if self.expected_value is None:
            return 0.0
        
        # 计算偏差
        deviation = self.expected_value - actual
        
        # 保守增益（降低灵敏度）
        conservative_gain = 0.5
        
        # 限幅
        max_control = abs(deviation) * conservative_gain
        
        control = conservative_gain * deviation
        
        # 限制最大输出
        if abs(control) > max_control:
            control = max_control if control > 0 else -max_control
        
        return control

    def _attempt_recovery(self, perturbation: float) -> bool:
        """
        尝试恢复
        
        Returns:
            bool: 恢复是否成功
        """
        self.stats["recoveries_attempted"] += 1
        
        # 创建备份
        if self.backup_enabled and self.backup_count < self.max_recovery_attempts:
            self._create_backup()
        
        # 简单恢复策略：等待扰动自然衰减
        # 实际实现中，这里可能需要更复杂的恢复算法
        time.sleep(0.01)  # 短暂等待
        
        # 记录恢复尝试
        self.recovery_history.append({
            "perturbation": perturbation,
            "attempt": self.stats["recoveries_attempted"],
            "timestamp": time.time()
        })
        
        # 保持最近10条记录
        if len(self.recovery_history) > 10:
            self.recovery_history.pop(0)
        
        return True

    def _create_backup(self):
        """创建参数备份"""
        if self.expected_value is not None:
            self.backup_params["expected_value"] = self.expected_value
            self.backup_count += 1
            self.stats["backups_created"] += 1

    def recover_from_backup(self) -> bool:
        """
        从备份恢复
        
        Returns:
            bool: 恢复是否成功
        """
        if not self.backup_params:
            return False
        
        if "expected_value" in self.backup_params:
            self.expected_value = self.backup_params["expected_value"]
            return True
        
        return False

    def evaluate_robustness(
        self,
        test_perturbations: Optional[List[float]] = None
    ) -> RobustnessMetrics:
        """
        评估鲁棒性
        
        Args:
            test_perturbations: 测试用的扰动列表
        
        Returns:
            RobustnessMetrics: 鲁棒性指标
        """
        if test_perturbations is None:
            # 默认测试范围
            test_perturbations = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
        
        stable_count = 0
        total_tests = len(test_perturbations)
        
        for pert in test_perturbations:
            # 简单稳定性测试：扰动下系统是否发散
            if pert <= self.tolerance:
                stable_count += 1
            elif pert <= self.tolerance * 2:
                # 超过容忍度但有恢复机制
                if self.backup_enabled:
                    stable_count += 0.5
        
        # 计算稳定裕度
        stability_margin = stable_count / total_tests if total_tests > 0 else 0
        
        # 性能降级评估
        performance_degradation = 0.0
        if self.backup_enabled:
            performance_degradation = 0.1 * self.stats["perturbations_detected"]
        
        # 恢复时间评估
        recovery_time = 0.0
        if self.recovery_history:
            recovery_time = sum(
                r.get("duration", 0) 
                for r in self.recovery_history
            ) / len(self.recovery_history)
        
        # 鲁棒性评分
        robustness_score = (
            stability_margin * 0.5 +
            (1 - performance_degradation) * 0.3 +
            (1 / (1 + recovery_time)) * 0.2
        ) * 100
        
        return RobustnessMetrics(
            stability_margin=stability_margin,
            performance_degradation=performance_degradation,
            recovery_time=recovery_time,
            robustness_score=robustness_score
        )

    def get_stability_region(self) -> tuple:
        """
        获取稳定域
        
        Returns:
            (min_value, max_value): 稳定域范围
        """
        if self.expected_value is None:
            return (0, 0)
        
        # 稳定域 = 期望值 ± (期望值 * 稳定裕度 * (1 - 容忍度))
        margin = self.expected_value * self.stability_margin * (1 - self.tolerance)
        
        return (
            self.expected_value - margin,
            self.expected_value + margin
        )

    def is_stable(self, value: float) -> bool:
        """
        检查给定值是否在稳定域内
        
        Args:
            value: 要检查的值
        
        Returns:
            bool: 是否稳定
        """
        min_val, max_val = self.get_stability_region()
        return min_val <= value <= max_val

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "backup_count": self.backup_count,
            "recovery_history_size": len(self.recovery_history),
            "stability_region": self.get_stability_region()
        }


# ============ 便捷函数 ============

def create_robust_controller(
    tolerance: float = 0.3,
    stability_margin: float = 0.5
) -> RobustController:
    """创建鲁棒控制器"""
    return RobustController(
        tolerance=tolerance,
        stability_margin=stability_margin
    )
