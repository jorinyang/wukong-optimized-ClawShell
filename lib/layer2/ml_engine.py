#!/usr/bin/env python3
"""
ClawShell AI/ML 引擎 (ML Engine)
版本: v0.2.1-B
功能: 异常检测、趋势预测、根因分析
"""

import os
import json
import time
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path

# ============ 配置 ============

ML_STATE_PATH = Path("~/.real/.ml_state.json").expanduser()
ML_CONFIG_PATH = Path("~/.real/.ml_config.json").expanduser()

DEFAULT_WINDOW_SIZE = 30  # 统计窗口大小
DEFAULT_ANOMALY_THRESHOLD = 3.0  # 异常阈值（标准差倍数）
DEFAULT_TREND_WINDOW = 7  # 趋势分析窗口（天）


# ============ 数据结构 ============

@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }


@dataclass
class Anomaly:
    """异常描述"""
    metric_name: str
    timestamp: float
    value: float
    expected_value: float
    deviation: float  # 偏离程度（标准差倍数）
    severity: str  # low, medium, high, critical
    description: str
    possible_causes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "metric_name": self.metric_name,
            "timestamp": self.timestamp,
            "value": self.value,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
            "severity": self.severity,
            "description": self.description,
            "possible_causes": self.possible_causes
        }


@dataclass
class Trend:
    """趋势描述"""
    metric_name: str
    direction: str  # increasing, decreasing, stable, volatile
    slope: float  # 斜率
    confidence: float  # 置信度 0-1
    forecast: List[float]  # 预测值
    summary: str
    
    def to_dict(self) -> Dict:
        return {
            "metric_name": self.metric_name,
            "direction": self.direction,
            "slope": self.slope,
            "confidence": self.confidence,
            "forecast": self.forecast,
            "summary": self.summary
        }


@dataclass
class RootCause:
    """根因分析结果"""
    primary_cause: str
    secondary_causes: List[str]
    evidence: List[Dict]  # 支持证据
    confidence: float
    recommendation: str
    
    def to_dict(self) -> Dict:
        return {
            "primary_cause": self.primary_cause,
            "secondary_causes": self.secondary_causes,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "recommendation": self.recommendation
        }


# ============ 统计工具 ============

class Statistics:
    """统计工具"""
    
    @staticmethod
    def mean(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    @staticmethod
    def std(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = Statistics.mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def percentile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]
    
    @staticmethod
    def linear_regression(values: List[float]) -> Tuple[float, float]:
        """线性回归，返回 (slope, intercept)"""
        n = len(values)
        if n < 2:
            return 0.0, Statistics.mean(values)
        
        x = list(range(n))
        x_mean = Statistics.mean(x)
        y_mean = Statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, y_mean
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        return slope, intercept
    
    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """皮尔逊相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        x_mean = Statistics.mean(x)
        y_mean = Statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        x_std = Statistics.std(x)
        y_std = Statistics.std(y)
        
        if x_std == 0 or y_std == 0:
            return 0.0
        
        return numerator / (n * x_std * y_std)


# ============ 异常检测器 ============

class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE, threshold: float = DEFAULT_ANOMALY_THRESHOLD):
        self.window_size = window_size
        self.threshold = threshold
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
    
    def add_metric(self, metric: Metric):
        """添加指标"""
        self.history[metric.name].append(metric.value)
    
    def add_metrics(self, metrics: List[Metric]):
        """批量添加指标"""
        for metric in metrics:
            self.add_metric(metric)
    
    def detect(self, metric_name: str, value: float, timestamp: float) -> Optional[Anomaly]:
        """检测单个异常"""
        history = self.history.get(metric_name, deque())
        
        if len(history) < 5:  # 需要至少5个历史数据点
            # 初始化历史
            self.history[metric_name].append(value)
            return None
        
        # 计算统计量
        values = list(history)
        mean = Statistics.mean(values)
        std = Statistics.std(values)
        
        if std == 0:
            return None
        
        # 计算偏离程度
        deviation = abs(value - mean) / std
        
        if deviation >= self.threshold:
            # 确定严重程度
            if deviation >= 4.0:
                severity = "critical"
            elif deviation >= 3.5:
                severity = "high"
            elif deviation >= 3.0:
                severity = "medium"
            else:
                severity = "low"
            
            # 生成描述
            direction = "above" if value > mean else "below"
            description = f"{metric_name} is {deviation:.1f}σ {direction} expected (value={value:.2f}, expected={mean:.2f}±{std:.2f})"
            
            # 可能的根因
            possible_causes = self._infer_causes(metric_name, value, mean, deviation)
            
            return Anomaly(
                metric_name=metric_name,
                timestamp=timestamp,
                value=value,
                expected_value=mean,
                deviation=deviation,
                severity=severity,
                description=description,
                possible_causes=possible_causes
            )
        
        # 正常，更新历史
        self.history[metric_name].append(value)
        return None
    
    def _infer_causes(self, metric_name: str, value: float, expected: float, deviation: float) -> List[str]:
        """推断可能的根因"""
        causes = []
        
        # 基于指标名称推断
        metric_lower = metric_name.lower()
        
        if "cpu" in metric_lower or "usage" in metric_lower:
            if value > expected:
                causes.extend([
                    "进程CPU占用过高",
                    "系统负载增加",
                    "可能存在死循环或密集计算"
                ])
        
        elif "memory" in metric_lower or "mem" in metric_lower:
            if value > expected:
                causes.extend([
                    "内存泄漏",
                    "缓存未释放",
                    "数据量突然增长"
                ])
        
        elif "latency" in metric_lower or "delay" in metric_lower:
            if value > expected:
                causes.extend([
                    "网络延迟增加",
                    "服务响应变慢",
                    "数据库查询阻塞"
                ])
        
        elif "error" in metric_lower or "fail" in metric_lower:
            if value > expected:
                causes.extend([
                    "依赖服务不可用",
                    "配置变更导致",
                    "资源耗尽"
                ])
        
        elif "count" in metric_lower or "request" in metric_lower:
            if value > expected:
                causes.extend([
                    "流量突增",
                    "遭遇攻击或爬虫",
                    "业务活动导致"
                ])
            else:
                causes.extend([
                    "服务降级",
                    "网络连接问题",
                    "客户端异常"
                ])
        
        return causes[:3]  # 最多3个
    
    def detect_all(self) -> List[Anomaly]:
        """检测所有历史指标中的异常"""
        anomalies = []
        for metric_name, history in self.history.items():
            values = list(history)
            if values:
                latest = values[-1]
                anomaly = self.detect(metric_name, latest, time.time())
                if anomaly:
                    anomalies.append(anomaly)
        return anomalies


# ============ 趋势预测器 ============

class TrendPredictor:
    """趋势预测器"""
    
    def __init__(self, forecast_steps: int = 5):
        self.forecast_steps = forecast_steps
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def add_metric(self, metric: Metric):
        """添加指标"""
        self.history[metric.name].append((metric.timestamp, metric.value))
    
    def add_metrics(self, metrics: List[Metric]):
        """批量添加指标"""
        for metric in metrics:
            self.add_metric(metric)
    
    def predict(self, metric_name: str) -> Optional[Trend]:
        """预测趋势"""
        if metric_name not in self.history:
            return None
        
        history = list(self.history[metric_name])
        if len(history) < 7:  # 需要至少7个数据点
            return None
        
        # 按时间排序
        history.sort(key=lambda x: x[0])
        
        values = [h[1] for h in history]
        timestamps = [h[0] for h in history]
        
        # 线性回归
        slope, intercept = Statistics.linear_regression(values)
        
        # 计算置信度
        mean = Statistics.mean(values)
        std = Statistics.std(values)
        
        if std == 0:
            confidence = 0.5
        else:
            # 基于残差计算置信度
            predicted = [intercept + slope * i for i in range(len(values))]
            residuals = [abs(values[i] - predicted[i]) for i in range(len(values))]
            avg_residual = Statistics.mean(residuals)
            confidence = max(0.0, min(1.0, 1.0 - avg_residual / (mean if mean != 0 else 1)))
        
        # 确定方向
        if abs(slope) < std * 0.1:
            direction = "stable"
            summary = f"{metric_name} 保持稳定"
        elif slope > 0:
            # 检测波动性
            if Statistics.std(values[-5:]) > Statistics.std(values[:5]) * 1.5:
                direction = "volatile"
                summary = f"{metric_name} 呈上升趋势但波动较大"
            else:
                direction = "increasing"
                pct_change = (slope * len(values)) / mean * 100 if mean != 0 else 0
                summary = f"{metric_name} 呈上升趋势 (预计变化 {pct_change:.1f}%)"
        else:
            if Statistics.std(values[-5:]) > Statistics.std(values[:5]) * 1.5:
                direction = "volatile"
                summary = f"{metric_name} 呈下降趋势但波动较大"
            else:
                direction = "decreasing"
                pct_change = (slope * len(values)) / mean * 100 if mean != 0 else 0
                summary = f"{metric_name} 呈下降趋势 (预计变化 {pct_change:.1f}%)"
        
        # 预测未来值
        forecast = []
        last_idx = len(values) - 1
        for i in range(1, self.forecast_steps + 1):
            forecast.append(intercept + slope * (last_idx + i))
        
        return Trend(
            metric_name=metric_name,
            direction=direction,
            slope=slope,
            confidence=confidence,
            forecast=forecast,
            summary=summary
        )
    
    def predict_all(self) -> List[Trend]:
        """预测所有指标的趋势"""
        trends = []
        for metric_name in self.history:
            trend = self.predict(metric_name)
            if trend:
                trends.append(trend)
        return trends


# ============ 根因分析器 ============

class RootCauseAnalyzer:
    """根因分析器"""
    
    def __init__(self):
        # 常见错误模式
        self.error_patterns = {
            "timeout": {
                "keywords": ["timeout", "timed out", "deadline"],
                "likely_causes": [
                    "网络延迟",
                    "服务响应慢",
                    "资源不足",
                    "死锁"
                ],
                "recommendation": "检查网络状况和服务负载，考虑增加超时时间或启用熔断"
            },
            "connection_refused": {
                "keywords": ["connection refused", "ECONNREFUSED", "无法连接"],
                "likely_causes": [
                    "服务未启动",
                    "端口错误",
                    "防火墙阻止",
                    "服务已下线"
                ],
                "recommendation": "确认目标服务运行状态，检查端口配置和网络策略"
            },
            "memory_error": {
                "keywords": ["out of memory", "OOM", "memory leak", "内存不足"],
                "likely_causes": [
                    "内存泄漏",
                    "数据量超出预期",
                    "缓存未清理",
                    "进程内存限制"
                ],
                "recommendation": "检查内存使用趋势，查找内存泄漏，必要时重启服务或扩容"
            },
            "disk_full": {
                "keywords": ["no space left", "disk full", "ENOSPC", "磁盘空间不足"],
                "likely_causes": [
                    "日志文件过大",
                    "临时文件未清理",
                    "数据文件快速增长",
                    "磁盘老化"
                ],
                "recommendation": "清理磁盘空间，配置日志轮转，设置磁盘空间告警"
            },
            "auth_error": {
                "keywords": ["unauthorized", "permission denied", "认证失败", "token"],
                "likely_causes": [
                    "Token过期",
                    "权限不足",
                    "密钥配置错误",
                    "账户被禁用"
                ],
                "recommendation": "刷新认证信息，检查权限配置，确认账户状态"
            }
        }
    
    def analyze(self, error_chain: List[Dict]) -> RootCause:
        """分析错误链，返回根因"""
        if not error_chain:
            return RootCause(
                primary_cause="未知",
                secondary_causes=[],
                evidence=[],
                confidence=0.0,
                recommendation="收集更多错误信息进行分析"
            )
        
        # 收集所有错误信息
        all_errors = []
        for error in error_chain:
            error_msg = str(error.get("message", "")).lower()
            error_type = error.get("type", "")
            timestamp = error.get("timestamp", time.time())
            
            all_errors.append({
                "message": error_msg,
                "type": error_type,
                "timestamp": timestamp
            })
        
        # 匹配错误模式
        matched_patterns = []
        for error in all_errors:
            msg = error["message"]
            for pattern_name, pattern_info in self.error_patterns.items():
                for keyword in pattern_info["keywords"]:
                    if keyword.lower() in msg:
                        matched_patterns.append({
                            "pattern": pattern_name,
                            "error": error,
                            "causes": pattern_info["likely_causes"],
                            "recommendation": pattern_info["recommendation"]
                        })
                        break
        
        # 确定主要根因
        if matched_patterns:
            # 选择最早匹配的错误模式
            primary = matched_patterns[0]
            
            # 收集所有不同根因
            all_causes = []
            for p in matched_patterns:
                all_causes.extend(p["causes"])
            
            # 去重
            seen = set()
            unique_causes = []
            for cause in all_causes:
                if cause not in seen:
                    seen.add(cause)
                    unique_causes.append(cause)
            
            return RootCause(
                primary_cause=primary["causes"][0] if primary["causes"] else "未知",
                secondary_causes=unique_causes[1:4] if len(unique_causes) > 1 else [],
                evidence=all_errors[:5],  # 最多5条证据
                confidence=0.8,
                recommendation=primary["recommendation"]
            )
        
        # 无法匹配特定模式，返回通用分析
        latest_error = all_errors[0]
        
        return RootCause(
            primary_cause="系统异常",
            secondary_causes=[
                "配置问题",
                "资源不足",
                "外部依赖故障"
            ],
            evidence=all_errors[:3],
            confidence=0.5,
            recommendation="查看详细错误信息，检查系统日志以确定具体原因"
        )


# ============ ML引擎主类 ============

class MLEngine:
    """AI/ML引擎"""
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.trend_predictor = TrendPredictor()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if ML_STATE_PATH.exists():
            try:
                with open(ML_STATE_PATH) as f:
                    state = json.load(f)
                    # 可以恢复历史数据
            except:
                pass
    
    def _save_state(self):
        """保存状态"""
        state = {
            "last_update": time.time()
        }
        with open(ML_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> Optional[Anomaly]:
        """记录单个指标，返回异常（如有）"""
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        
        self.anomaly_detector.add_metric(metric)
        self.trend_predictor.add_metric(metric)
        
        return self.anomaly_detector.detect(name, value, metric.timestamp)
    
    def record_metrics(self, metrics: List[Metric]):
        """批量记录指标"""
        self.anomaly_detector.add_metrics(metrics)
        self.trend_predictor.add_metrics(metrics)
    
    def detect_anomalies(self) -> List[Anomaly]:
        """检测所有异常"""
        return self.anomaly_detector.detect_all()
    
    def predict_trends(self) -> List[Trend]:
        """预测所有趋势"""
        return self.trend_predictor.predict_all()
    
    def analyze_root_cause(self, error_chain: List[Dict]) -> RootCause:
        """分析根因"""
        return self.root_cause_analyzer.analyze(error_chain)
    
    def get_report(self) -> Dict:
        """获取ML分析报告"""
        anomalies = self.detect_anomalies()
        trends = self.predict_trends()
        
        return {
            "timestamp": time.time(),
            "anomalies": {
                "count": len(anomalies),
                "critical": len([a for a in anomalies if a.severity == "critical"]),
                "high": len([a for a in anomalies if a.severity == "high"]),
                "details": [a.to_dict() for a in anomalies[:10]]
            },
            "trends": {
                "count": len(trends),
                "increasing": len([t for t in trends if t.direction == "increasing"]),
                "decreasing": len([t for t in trends if t.direction == "decreasing"]),
                "stable": len([t for t in trends if t.direction == "stable"]),
                "details": [t.to_dict() for t in trends[:10]]
            }
        }


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell AI/ML引擎")
    parser.add_argument("--record", nargs=2, metavar=("NAME", "VALUE"), help="记录指标")
    parser.add_argument("--detect", action="store_true", help="检测异常")
    parser.add_argument("--predict", action="store_true", help="预测趋势")
    parser.add_argument("--analyze", type=str, help="分析根因 (JSON文件路径)")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()
    
    engine = MLEngine()
    
    if args.record:
        name, value = args.record
        anomaly = engine.record_metric(name, float(value))
        
        if anomaly:
            print(f"⚠️  异常检测: {anomaly.description}")
            print(f"   可能原因: {', '.join(anomaly.possible_causes)}")
        else:
            print(f"✅ 指标正常: {name}={value}")
    
    elif args.detect:
        anomalies = engine.detect_anomalies()
        
        if not anomalies:
            print("✅ 未检测到异常")
        else:
            print(f"⚠️  检测到 {len(anomalies)} 个异常:")
            for a in anomalies:
                print(f"  [{a.severity.upper()}] {a.description}")
    
    elif args.predict:
        trends = engine.predict_trends()
        
        if not trends:
            print("暂无足够数据预测趋势")
        else:
            print(f"📈 趋势预测 ({len(trends)} 个指标):")
            for t in trends:
                icon = "📈" if t.direction == "increasing" else "📉" if t.direction == "decreasing" else "➡️"
                print(f"  {icon} {t.summary}")
                print(f"      置信度: {t.confidence:.0%}")
    
    elif args.analyze:
        try:
            with open(args.analyze) as f:
                error_chain = json.load(f)
            
            result = engine.analyze_root_cause(error_chain)
            
            print(f"🔍 根因分析结果:")
            print(f"  主要原因: {result.primary_cause}")
            if result.secondary_causes:
                print(f"  次要原因: {', '.join(result.secondary_causes)}")
            print(f"  置信度: {result.confidence:.0%}")
            print(f"  建议: {result.recommendation}")
        except Exception as e:
            print(f"分析失败: {e}")
    
    elif args.report:
        report = engine.get_report()
        
        if args.format == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("=" * 60)
            print("ClawShell AI/ML 分析报告")
            print("=" * 60)
            print(f"时间: {datetime.fromtimestamp(report['timestamp'])}")
            print()
            
            print("异常检测:")
            print(f"  总数: {report['anomalies']['count']}")
            if report['anomalies']['count'] > 0:
                print(f"  严重: {report['anomalies']['critical']}")
                print(f"  高: {report['anomalies']['high']}")
            
            print()
            print("趋势预测:")
            print(f"  总数: {report['trends']['count']}")
            print(f"  上升: {report['trends']['increasing']}")
            print(f"  下降: {report['trends']['decreasing']}")
            print(f"  稳定: {report['trends']['stable']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
