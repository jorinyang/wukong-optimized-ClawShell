"""
Strategy Analyzer - ClawShell v0.1
===================================

策略分析器。
根据采集的状态数据，分析并决定是否需要切换策略。

核心逻辑：
1. 收集当前指标
2. 评估条件
3. 决定是否切换
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class StrategyAnalyzer:
    """
    策略分析器
    ==========
    
    分析状态数据，决定是否需要切换策略。
    
    使用示例：
        analyzer = StrategyAnalyzer()
        
        # 分析当前状态
        metrics = collector.collect_all()
        decision = analyzer.analyze(metrics)
        
        if decision.should_switch:
            switcher.switch_to(decision.target_strategy)
    """
    
    # 告警阈值
    THRESHOLDS = {
        # 系统资源
        "cpu_high": 80.0,           # CPU > 80%
        "memory_high": 85.0,        # 内存 > 85%
        "disk_high": 90.0,          # 磁盘 > 90%
        
        # API状态
        "api_error_rate_high": 0.3,   # API错误率 > 30%
        "api_error_rate_critical": 0.5,  # API错误率 > 50%
        
        # 业务状态
        "task_completion_low": 0.5,  # 任务完成率 < 50%
    }
    
    def __init__(self):
        self._last_analysis_time: Optional[datetime] = None
        self._last_metrics: Dict[str, float] = {}
        self._consecutive_failures: int = 0
        
        logger.info("StrategyAnalyzer initialized")
    
    def analyze(self, metrics: Dict[str, float]) -> "AnalysisResult":
        """
        分析指标并返回决策
        
        Args:
            metrics: 指标字典
        
        Returns:
            分析结果
        """
        self._last_metrics = metrics
        self._last_analysis_time = datetime.now()
        
        # 按优先级检查条件
        issues = []
        target_strategy = "default"
        
        # 1. 检查严重问题
        for issue, strategy in self._check_critical_issues(metrics):
            issues.append(issue)
            target_strategy = strategy
            self._consecutive_failures += 1
        
        # 2. 检查一般问题
        if target_strategy == "default":
            for issue, strategy in self._check_warning_issues(metrics):
                issues.append(issue)
                target_strategy = strategy
        
        # 3. 检查是否需要恢复
        if not issues and self._consecutive_failures > 0:
            self._consecutive_failures = 0
            if self._should_recover():
                return AnalysisResult(
                    should_switch=True,
                    target_strategy="default",
                    reason="recovered",
                    issues=[],
                    confidence=0.9,
                )
        
        # 4. 重置失败计数（如果没问题）
        if not issues:
            self._consecutive_failures = 0
        
        # 生成决策
        should_switch = target_strategy != "default"
        confidence = self._calculate_confidence(issues, metrics)
        
        return AnalysisResult(
            should_switch=should_switch,
            target_strategy=target_strategy,
            reason="issues_detected" if issues else "normal",
            issues=issues,
            confidence=confidence,
        )
    
    def _check_critical_issues(self, metrics: Dict[str, float]) -> List[tuple]:
        """检查严重问题"""
        issues = []
        
        # API错误率严重
        api_error_rate = metrics.get("api.error_rate", 0)
        if api_error_rate > self.THRESHOLDS["api_error_rate_critical"]:
            msg = "API error rate critical: %.1f%%" % (api_error_rate * 100)
            issues.append(msg)
            msg_zh = "API错误率过高 (%.1f%%)" % (api_error_rate * 100)
            return [(msg_zh, "emergency")]
        
        # 系统资源严重不足
        cpu = metrics.get("system.cpu_percent", 0)
        memory = metrics.get("system.memory_percent", 0)
        
        if cpu > self.THRESHOLDS["cpu_high"] or memory > self.THRESHOLDS["memory_high"]:
            msg = "System resource critical: CPU %.1f%%, Memory %.1f%%" % (cpu, memory)
            issues.append(msg)
            msg_zh = "系统资源不足 (CPU %.1f%%, Memory %.1f%%)" % (cpu, memory)
            return [(msg_zh, "economy")]
        
        # 任务完成率严重低
        task_completion = metrics.get("business.task_completion_rate", 1.0)
        if task_completion < self.THRESHOLDS["task_completion_low"]:
            msg = "Task completion rate critical: %.1f%%" % (task_completion * 100)
            issues.append(msg)
            msg_zh = "任务完成率过低 (%.1f%%)" % (task_completion * 100)
            return [(msg_zh, "emergency")]
        
        return issues
    
    def _check_warning_issues(self, metrics: Dict[str, float]) -> List[tuple]:
        """检查一般警告问题"""
        issues = []
        
        # API错误率偏高
        api_error_rate = metrics.get("api.error_rate", 0)
        if api_error_rate > self.THRESHOLDS["api_error_rate_high"]:
            msg = "API error rate elevated: %.1f%%" % (api_error_rate * 100)
            issues.append(msg)
            msg_zh = "API错误率偏高 (%.1f%%)" % (api_error_rate * 100)
            return [(msg_zh, "emergency")]
        
        # 系统资源偏紧
        cpu = metrics.get("system.cpu_percent", 0)
        memory = metrics.get("system.memory_percent", 0)
        
        if cpu > self.THRESHOLDS["cpu_high"] * 0.8 or memory > self.THRESHOLDS["memory_high"] * 0.8:
            msg = "System resource warning: CPU %.1f%%, Memory %.1f%%" % (cpu, memory)
            issues.append(msg)
            msg_zh = "系统资源紧张 (CPU %.1f%%, Memory %.1f%%)" % (cpu, memory)
            return [(msg_zh, "economy")]
        
        return issues
    
    def _should_recover(self) -> bool:
        """判断是否应该恢复默认策略"""
        # 连续5次分析都没问题，认为已恢复
        return self._consecutive_failures == 0
    
    def _calculate_confidence(self, issues: List[str], metrics: Dict[str, float]) -> float:
        """计算决策置信度"""
        if not issues:
            return 1.0
        
        # 基于问题数量和严重程度计算置信度
        base_confidence = 0.7
        
        # 问题越多，置信度越高
        if len(issues) > 2:
            base_confidence += 0.1
        
        # API错误率高，置信度高
        api_error_rate = metrics.get("api.error_rate", 0)
        if api_error_rate > 0.5:
            base_confidence += 0.15
        
        return min(base_confidence, 0.99)
    
    def get_last_metrics(self) -> Dict[str, float]:
        """获取上次分析时的指标"""
        return self._last_metrics.copy()
    
    def get_thresholds(self) -> Dict[str, float]:
        """获取当前阈值配置"""
        return self.THRESHOLDS.copy()
    
    def set_threshold(self, name: str, value: float):
        """设置阈值"""
        if name in self.THRESHOLDS:
            self.THRESHOLDS[name] = value
            logger.info("Threshold updated: %s = %s", name, value)


@dataclass
class AnalysisResult:
    """
    分析结果
    =========
    """
    should_switch: bool       # 是否应该切换
    target_strategy: str      # 目标策略
    reason: str               # 原因
    issues: List[str]        # 发现的问题
    confidence: float         # 置信度 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_switch": self.should_switch,
            "target_strategy": self.target_strategy,
            "reason": self.reason,
            "issues": self.issues,
            "confidence": self.confidence,
        }
