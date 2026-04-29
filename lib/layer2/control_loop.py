#!/usr/bin/env python3
"""
ClawShell 自适应控制闭环
版本: v0.2.0-A
理论依据: 钱学森《工程控制论》
功能: 基于工程控制论的自进化控制闭环
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


# ============ 数据结构 ============

class ControlSignalType(Enum):
    """控制信号类型"""
    POSITIVE = "positive"     # 正向调节
    NEGATIVE = "negative"   # 负向调节
    STABLE = "stable"       # 稳定
    ADAPTIVE = "adaptive"   # 自适应


@dataclass
class ControlSignal:
    """控制信号"""
    signal_type: ControlSignalType
    magnitude: float              # 幅度
    target_component: str         # 目标组件
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemState:
    """系统状态"""
    component: str
    expected: float
    actual: float
    deviation: float
    status: str  # normal, warning, critical
    timestamp: float = field(default_factory=time.time)


@dataclass
class FeedbackData:
    """反馈数据"""
    expected: Any
    actual: Any
    deviation: Any
    control_signal: Optional[ControlSignal] = None


# ============ 比较器 ============

class Comparator:
    """
    比较器 - 计算期望与实际的偏差
    依据: 工程控制论的偏差检测机制
    """

    def __init__(self, tolerance: float = 0.0):
        self.tolerance = tolerance  # 容差
        self.history: List[SystemState] = []

    def compute(self, expected: float, actual: float) -> float:
        """计算偏差"""
        deviation = expected - actual
        
        # 考虑容差
        if abs(deviation) <= self.tolerance:
            return 0.0
        
        return deviation

    def compute_relative(self, expected: float, actual: float) -> float:
        """计算相对偏差"""
        if expected == 0:
            return 0.0
        return (expected - actual) / expected

    def record_state(self, state: SystemState):
        """记录系统状态"""
        self.history.append(state)
        
        # 保持最近100条记录
        if len(self.history) > 100:
            self.history.pop(0)

    def get_deviation_trend(self) -> str:
        """获取偏差趋势"""
        if len(self.history) < 3:
            return "unknown"
        
        recent = self.history[-3:]
        deviations = [s.deviation for s in recent]
        
        if all(d > 0 for d in deviations):
            return "increasing_positive"
        elif all(d < 0 for d in deviations):
            return "increasing_negative"
        elif all(abs(d) < self.tolerance for d in deviations):
            return "stable"
        else:
            return "fluctuating"


# ============ 调节器 ============

class Regulator:
    """
    调节器基类 - 依据偏差产生控制信号
    依据: 工程控制论的反馈调节机制
    """

    def __init__(self, name: str = "base"):
        self.name = name
        self.gain: float = 1.0  # 增益
        self.history: List[ControlSignal] = []

    def regulate(self, deviation: float, target: str) -> ControlSignal:
        """调节 - 子类实现"""
        raise NotImplementedError

    def record_signal(self, signal: ControlSignal):
        """记录控制信号"""
        self.history.append(signal)
        if len(self.history) > 100:
            self.history.pop(0)


class PIDRegulator(Regulator):
    """
    PID调节器 - 比例-积分-微分控制
    依据: 经典控制论的PID控制
    """

    def __init__(
        self,
        kp: float = 1.0,  # 比例系数
        ki: float = 0.0,  # 积分系数
        kd: float = 0.0,  # 微分系数
        name: str = "PID"
    ):
        super().__init__(name)
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.last_error = 0.0

    def regulate(self, deviation: float, target: str) -> ControlSignal:
        """PID调节"""
        # 比例项
        p = self.kp * deviation
        
        # 积分项
        self.integral += deviation
        i = self.ki * self.integral
        
        # 微分项
        derivative = deviation - self.last_error
        d = self.kd * derivative
        self.last_error = deviation
        
        # 综合输出
        output = p + i + d
        
        # 确定信号类型
        if abs(output) < 0.1:
            signal_type = ControlSignalType.STABLE
        elif output > 0:
            signal_type = ControlSignalType.POSITIVE
        else:
            signal_type = ControlSignalType.NEGATIVE
        
        signal = ControlSignal(
            signal_type=signal_type,
            magnitude=abs(output) * self.gain,
            target_component=target,
            reason=f"P={p:.2f}, I={i:.2f}, D={d:.2f}"
        )
        
        self.record_signal(signal)
        return signal


class AdaptiveRegulator(Regulator):
    """
    自适应调节器 - 根据环境自动调整
    依据: 现代控制论的自适应控制
    """

    def __init__(
        self,
        base_gain: float = 1.0,
        adaptation_rate: float = 0.1,
        name: str = "Adaptive"
    ):
        super().__init__(name)
        self.base_gain = base_gain
        self.adaptation_rate = adaptation_rate
        self.current_gain = base_gain

    def regulate(self, deviation: float, target: str) -> ControlSignal:
        """自适应调节"""
        # 根据偏差大小自适应调整增益
        if abs(deviation) > 10:
            # 大偏差：强控制
            self.current_gain = self.base_gain * 2
        elif abs(deviation) > 5:
            # 中偏差：正常控制
            self.current_gain = self.base_gain
        else:
            # 小偏差：精细控制
            self.current_gain = self.base_gain * 0.5
        
        # 根据历史调整增益
        if len(self.history) >= 5:
            recent_signals = self.history[-5:]
            avg_magnitude = sum(s.magnitude for s in recent_signals) / 5
            
            # 如果最近控制效果不佳（幅度过大），减小增益
            if avg_magnitude > 50:
                self.current_gain *= 0.9
            # 如果控制效果稳定，小幅增加增益以加快响应
            elif avg_magnitude < 10:
                self.current_gain *= 1.05
        
        output = deviation * self.current_gain
        
        signal_type = ControlSignalType.ADAPTIVE
        if abs(output) < 0.1:
            signal_type = ControlSignalType.STABLE
        elif output > 0:
            signal_type = ControlSignalType.POSITIVE
        else:
            signal_type = ControlSignalType.NEGATIVE
        
        signal = ControlSignal(
            signal_type=signal_type,
            magnitude=abs(output),
            target_component=target,
            reason=f"adaptive_gain={self.current_gain:.3f}"
        )
        
        self.record_signal(signal)
        return signal


# ============ 反馈控制闭环 ============

class FeedbackControlLoop:
    """
    反馈控制闭环
    依据: 工程控制论的信息反馈机制
    
    架构:
    期望目标 → 控制器 → 被控系统 → 传感器 → 比较器 → 调节器 → (循环)
    """

    def __init__(
        self,
        name: str = "MainLoop",
        use_adaptive: bool = True
    ):
        self.name = name
        self.comparator = Comparator(tolerance=0.01)
        
        if use_adaptive:
            self.regulator = AdaptiveRegulator()
        else:
            self.regulator = PIDRegulator()
        
        # 状态存储
        self.expected: Dict[str, float] = {}
        self.actual: Dict[str, float] = {}
        self.states: Dict[str, SystemState] = {}
        
        # 回调函数
        self.on_control_signal: Optional[Callable] = None
        
        # 统计
        self.stats = {
            "total_iterations": 0,
            "convergence_count": 0,
            "divergence_count": 0,
            "adaptive_changes": 0
        }

    def set_expected(self, component: str, value: float):
        """设置期望值"""
        self.expected[component] = value

    def update_actual(self, component: str, value: float):
        """更新实际值"""
        self.actual[component] = value

    def step(self) -> List[ControlSignal]:
        """
        执行一步闭环控制
        Returns: 产生的控制信号列表
        """
        self.stats["total_iterations"] += 1
        signals = []
        
        for component in self.expected:
            if component not in self.actual:
                continue
            
            expected = self.expected[component]
            actual = self.actual[component]
            
            # 1. 计算偏差
            deviation = self.comparator.compute(expected, actual)
            
            # 2. 记录系统状态
            status = "normal"
            if abs(deviation) > 5:
                status = "warning"
            if abs(deviation) > 10:
                status = "critical"
            
            state = SystemState(
                component=component,
                expected=expected,
                actual=actual,
                deviation=deviation,
                status=status
            )
            self.states[component] = state
            self.comparator.record_state(state)
            
            # 3. 产生控制信号
            if abs(deviation) > self.comparator.tolerance:
                signal = self.regulator.regulate(deviation, component)
                signals.append(signal)
                
                # 4. 触发回调
                if self.on_control_signal:
                    self.on_control_signal(signal)
                
                # 5. 检查收敛/发散
                if abs(deviation) < 0.1:
                    self.stats["convergence_count"] += 1
                elif abs(deviation) > 20:
                    self.stats["divergence_count"] += 1
        
        return signals

    def is_converged(self, component: str = None) -> bool:
        """检查是否收敛"""
        if component:
            if component not in self.states:
                return False
            return abs(self.states[component].deviation) < 0.1
        
        # 检查所有组件
        return all(
            abs(s.deviation) < 0.1 
            for s in self.states.values()
        )

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "name": self.name,
            "components": list(self.expected.keys()),
            "states": {
                c: {
                    "expected": s.expected,
                    "actual": s.actual,
                    "deviation": s.deviation,
                    "status": s.status
                }
                for c, s in self.states.items()
            },
            "stats": self.stats,
            "deviation_trend": self.comparator.get_deviation_trend()
        }


# ============ 自进化辅助类 ============

class EvolutionControlLoop(FeedbackControlLoop):
    """
    进化控制闭环 - 用于系统自进化
    融合Hermes的深度分析能力
    """

    def __init__(self, name: str = "EvolutionLoop"):
        super().__init__(name, use_adaptive=True)
        
        # 进化历史
        self.evolution_history: List[Dict] = []
        
        # 收敛阈值
        self.convergence_threshold = 0.05
        self.max_iterations = 100

    def evolve(
        self,
        component: str,
        initial_value: float,
        target_value: float,
        iterations: int = None
    ) -> Dict:
        """
        执行进化迭代
        
        Args:
            component: 组件名
            initial_value: 初始值
            target_value: 目标值
            iterations: 最大迭代次数
        
        Returns:
            进化结果
        """
        self.expected[component] = target_value
        self.actual[component] = initial_value
        
        max_iter = iterations or self.max_iterations
        evolution_log = []
        
        for i in range(max_iter):
            # 执行一步
            signals = self.step()
            
            # 记录
            if component in self.states:
                state = self.states[component]
                evolution_log.append({
                    "iteration": i,
                    "expected": state.expected,
                    "actual": state.actual,
                    "deviation": state.deviation,
                    "signals": [
                        {"type": s.signal_type.value, "magnitude": s.magnitude}
                        for s in signals
                    ]
                })
            
            # 检查收敛
            if self.is_converged(component):
                evolution_log.append({"converged": True, "iterations": i})
                break
        
        result = {
            "component": component,
            "initial": initial_value,
            "target": target_value,
            "final": self.actual.get(component, initial_value),
            "iterations": len(evolution_log),
            "converged": self.is_converged(component),
            "log": evolution_log
        }
        
        self.evolution_history.append(result)
        return result


# ============ 便捷函数 ============

def create_control_loop(name: str = "Main", adaptive: bool = True) -> FeedbackControlLoop:
    """创建控制闭环"""
    return FeedbackControlLoop(name=name, use_adaptive=adaptive)


def create_evolution_loop(name: str = "Evolution") -> EvolutionControlLoop:
    """创建进化闭环"""
    return EvolutionControlLoop(name=name)
