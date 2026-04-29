#!/usr/bin/env python3
"""
ClawShell Genome Quality Evaluator
知识质量评估模块
版本: v0.2.0
功能: 知识质量评分、完整性检查、一致性验证
"""

import time
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


class QualityDimension(Enum):
    """质量维度"""
    COMPLETENESS = "completeness"      # 完整性
    CONSISTENCY = "consistency"         # 一致性
    ACCURACY = "accuracy"              # 准确性
    FRESHNESS = "freshness"            # 时效性
    COHERENCE = "coherence"            # 连贯性
    USEFULNESS = "usefulness"          # 可用性


@dataclass
class QualityScore:
    """质量评分"""
    dimension: QualityDimension
    score: float  # 0-100
    weight: float = 1.0
    details: Dict = field(default_factory=dict)


@dataclass
class QualityReport:
    """质量报告"""
    entity_id: str
    overall_score: float
    dimension_scores: List[QualityScore]
    issues: List[str]
    suggestions: List[str]
    evaluated_at: float = field(default_factory=time.time)


@dataclass
class QualityMetrics:
    """质量指标"""
    total_entities: int = 0
    avg_completeness: float = 0.0
    avg_consistency: float = 0.0
    avg_accuracy: float = 0.0
    avg_freshness: float = 0.0
    avg_coherence: float = 0.0
    avg_usefulness: float = 0.0
    overall_avg: float = 0.0


class QualityEvaluator:
    """
    知识质量评估器
    
    功能：
    - 多维度质量评估
    - 完整性检查
    - 一致性验证
    - 质量报告生成
    """

    def __init__(
        self,
        weights: Optional[Dict[QualityDimension, float]] = None,
        freshness_threshold_days: float = 30.0
    ):
        # 质量维度权重
        self.weights = weights or {
            QualityDimension.COMPLETENESS: 1.5,
            QualityDimension.CONSISTENCY: 1.5,
            QualityDimension.ACCURACY: 2.0,
            QualityDimension.FRESHNESS: 1.0,
            QualityDimension.COHERENCE: 1.0,
            QualityDimension.USEFULNESS: 1.0,
        }
        
        self.freshness_threshold_days = freshness_threshold_days
        
        # 评估缓存
        self._cache: Dict[str, QualityReport] = {}
        
        # 统计
        self._stats = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "issues_found": 0,
        }

    def evaluate_entity(self, entity: Any, entity_id: str = "") -> QualityReport:
        """评估实体质量"""
        if not entity_id and hasattr(entity, "id"):
            entity_id = entity.id
        
        # 检查缓存
        if entity_id in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[entity_id]
        
        # 评估各维度
        dimension_scores = []
        issues = []
        suggestions = []
        
        # 1. 完整性评估
        completeness = self._evaluate_completeness(entity)
        dimension_scores.append(completeness)
        if completeness.score < 60:
            issues.append(f"完整性不足: {completeness.score:.1f}%")
            suggestions.append("补充缺失的必要字段")
        
        # 2. 一致性评估
        consistency = self._evaluate_consistency(entity)
        dimension_scores.append(consistency)
        if consistency.score < 60:
            issues.append(f"一致性不足: {consistency.score:.1f}%")
            suggestions.append("检查并修复矛盾的数据")
        
        # 3. 准确性评估
        accuracy = self._evaluate_accuracy(entity)
        dimension_scores.append(accuracy)
        if accuracy.score < 60:
            issues.append(f"准确性不足: {accuracy.score:.1f}%")
            suggestions.append("验证数据来源和计算逻辑")
        
        # 4. 时效性评估
        freshness = self._evaluate_freshness(entity)
        dimension_scores.append(freshness)
        if freshness.score < 60:
            issues.append(f"数据可能过时: {freshness.score:.1f}%")
            suggestions.append("更新过期数据")
        
        # 5. 连贯性评估
        coherence = self._evaluate_coherence(entity)
        dimension_scores.append(coherence)
        if coherence.score < 60:
            issues.append(f"连惯性不足: {coherence.score:.1f}%")
            suggestions.append("检查逻辑矛盾和结构问题")
        
        # 6. 可用性评估
        usefulness = self._evaluate_usefulness(entity)
        dimension_scores.append(usefulness)
        if usefulness.score < 60:
            issues.append(f"可用性不足: {usefulness.score:.1f}%")
            suggestions.append("改进数据结构和接口设计")
        
        # 计算加权总分
        total_weight = sum(self.weights.get(ds.dimension, 1.0) for ds in dimension_scores)
        weighted_sum = sum(
            ds.score * self.weights.get(ds.dimension, 1.0) 
            for ds in dimension_scores
        )
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0
        
        # 生成报告
        report = QualityReport(
            entity_id=entity_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=issues,
            suggestions=suggestions
        )
        
        # 缓存
        if entity_id:
            self._cache[entity_id] = report
        
        self._stats["total_evaluations"] += 1
        self._stats["issues_found"] += len(issues)
        
        return report

    def _evaluate_completeness(self, entity: Any) -> QualityScore:
        """评估完整性"""
        details = {"missing_fields": [], "required_fields": 0, "filled_fields": 0}
        
        # 检查必要字段
        required = ["id", "name", "type"]
        filled = 0
        
        for field in required:
            if hasattr(entity, field) and getattr(entity, field, None):
                filled += 1
            details["required_fields"] += 1
        
        # 检查属性
        if hasattr(entity, "properties"):
            props = entity.properties or {}
            details["filled_fields"] = len([v for v in props.values() if v is not None])
        
        # 计算分数
        if details["required_fields"] > 0:
            score = (filled / details["required_fields"]) * 100
        else:
            score = 50.0
        
        return QualityScore(
            dimension=QualityDimension.COMPLETENESS,
            score=score,
            weight=self.weights.get(QualityDimension.COMPLETENESS, 1.0),
            details=details
        )

    def _evaluate_consistency(self, entity: Any) -> QualityScore:
        """评估一致性"""
        details = {"conflicts": [], "checked_pairs": 0}
        
        # 简单一致性检查
        conflicts = []
        
        # 检查ID和name的一致性
        if hasattr(entity, "id") and hasattr(entity, "name"):
            details["checked_pairs"] += 1
            # 如果有重复的id或不合法的name
            if not entity.name or len(entity.name) < 1:
                conflicts.append("name为空")
        
        # 检查时间戳
        if hasattr(entity, "created_at") and hasattr(entity, "updated_at"):
            details["checked_pairs"] += 1
            if entity.updated_at < entity.created_at:
                conflicts.append("updated_at早于created_at")
        
        details["conflicts"] = conflicts
        
        # 计算分数
        if details["checked_pairs"] > 0:
            score = (1 - len(conflicts) / details["checked_pairs"]) * 100
        else:
            score = 80.0
        
        return QualityScore(
            dimension=QualityDimension.CONSISTENCY,
            score=score,
            weight=self.weights.get(QualityDimension.CONSISTENCY, 1.0),
            details=details
        )

    def _evaluate_accuracy(self, entity: Any) -> QualityScore:
        """评估准确性"""
        details = {"validations": [], "failed_validations": 0}
        
        validations = []
        
        # 检查属性值的类型
        if hasattr(entity, "properties"):
            for key, value in entity.properties.items():
                if value is not None:
                    validations.append(True)
        
        details["validations"] = validations
        details["failed_validations"] = len([v for v in validations if not v])
        
        # 计算分数
        if len(validations) > 0:
            score = (len(validations) - details["failed_validations"]) / len(validations) * 100
        else:
            score = 70.0
        
        return QualityScore(
            dimension=QualityDimension.ACCURACY,
            score=score,
            weight=self.weights.get(QualityDimension.ACCURACY, 1.0),
            details=details
        )

    def _evaluate_freshness(self, entity: Any) -> QualityScore:
        """评估时效性"""
        details = {"age_days": 0, "is_stale": False}
        
        current_time = time.time()
        age_days = 0
        is_stale = False
        
        if hasattr(entity, "updated_at"):
            age_seconds = current_time - entity.updated_at
            age_days = age_seconds / (24 * 3600)
            is_stale = age_days > self.freshness_threshold_days
        
        details["age_days"] = age_days
        details["is_stale"] = is_stale
        
        # 计算分数
        if age_days == 0:
            score = 100.0
        else:
            score = max(0, 100 - age_days * (100 / self.freshness_threshold_days))
        
        return QualityScore(
            dimension=QualityDimension.FRESHNESS,
            score=score,
            weight=self.weights.get(QualityDimension.FRESHNESS, 1.0),
            details=details
        )

    def _evaluate_coherence(self, entity: Any) -> QualityScore:
        """评估连贯性"""
        details = {"checks": [], "coherent": True}
        
        checks = []
        
        # 检查是否有必要的上下文
        if hasattr(entity, "entity_type") and hasattr(entity, "name"):
            checks.append(True)
        
        details["checks"] = checks
        details["coherent"] = len(checks) > 0
        
        # 计算分数
        if len(checks) > 0:
            score = 100.0 if details["coherent"] else 50.0
        else:
            score = 70.0
        
        return QualityScore(
            dimension=QualityDimension.COHERENCE,
            score=score,
            weight=self.weights.get(QualityDimension.COHERENCE, 1.0),
            details=details
        )

    def _evaluate_usefulness(self, entity: Any) -> QualityScore:
        """评估可用性"""
        details = {"has_interface": False, "has_metadata": False}
        
        # 检查是否有接口方法
        has_interface = len([m for m in dir(entity) if not m.startswith('_')]) > 3
        details["has_interface"] = has_interface
        
        # 检查是否有元数据
        has_metadata = hasattr(entity, "metadata") and entity.metadata
        details["has_metadata"] = has_metadata
        
        # 计算分数
        score = 0
        if has_interface:
            score += 50
        if has_metadata:
            score += 50
        
        return QualityScore(
            dimension=QualityDimension.USEFULNESS,
            score=score,
            weight=self.weights.get(QualityDimension.USEFULNESS, 1.0),
            details=details
        )

    def evaluate_batch(self, entities: List[Any]) -> List[QualityReport]:
        """批量评估"""
        return [self.evaluate_entity(e) for e in entities]

    def get_metrics(self) -> QualityMetrics:
        """获取质量指标"""
        reports = list(self._cache.values())
        
        if not reports:
            return QualityMetrics()
        
        n = len(reports)
        
        return QualityMetrics(
            total_entities=n,
            avg_completeness=sum(r.dimension_scores[0].score for r in reports) / n,
            avg_consistency=sum(r.dimension_scores[1].score for r in reports) / n,
            avg_accuracy=sum(r.dimension_scores[2].score for r in reports) / n,
            avg_freshness=sum(r.dimension_scores[3].score for r in reports) / n,
            avg_coherence=sum(r.dimension_scores[4].score for r in reports) / n,
            avg_usefulness=sum(r.dimension_scores[5].score for r in reports) / n,
            overall_avg=sum(r.overall_score for r in reports) / n
        )

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "cached_entities": len(self._cache),
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()


def create_quality_evaluator(**kwargs) -> QualityEvaluator:
    """创建质量评估器"""
    return QualityEvaluator(**kwargs)
