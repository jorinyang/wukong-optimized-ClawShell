#!/usr/bin/env python3
"""
ClawShell 综合集成引擎
版本: v0.2.0-A
理论依据: 钱学森《工程控制论》- 综合集成方法
功能: 从定性到定量的人机结合综合集成
"""

import time
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


# ============ 数据结构 ============

class KnowledgeLevel(Enum):
    """知识层级"""
    QUALITATIVE = "qualitative"     # 定性知识（专家经验）
    SEMI_QUANTITATIVE = "semi"     # 半定量（数据+知识）
    QUANTITATIVE = "quantitative"  # 定量（纯数据）


@dataclass
class ExpertKnowledge:
    """专家知识"""
    knowledge_id: str
    domain: str
    content: str
    level: KnowledgeLevel
    source: str
    confidence: float = 1.0
    validity: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class SynthesisInput:
    """综合集成输入"""
    problem: str
    qualitative_data: Dict = field(default_factory=dict)   # 专家意见
    quantitative_data: Dict = field(default_factory=dict) # 数据
    constraints: Dict = field(default_factory=dict)       # 约束


@dataclass
class SynthesisOutput:
    """综合集成输出"""
    solution: Dict
    confidence: float
    level: KnowledgeLevel
    reasoning: str
    human_validated: bool = False
    timestamp: float = field(default_factory=time.time)


# ============ 综合集成引擎 ============

class MetaSynthesisEngine:
    """
    综合集成引擎
    
    依据: 工程控制论的"从定性到定量的综合集成方法"
    
    架构:
    专家群体智慧(定性) → 数据与知识结合(半定量) → 计算机技术支撑(定量) → 人机结合、以人为主
    
    使用示例:
        engine = MetaSynthesisEngine()
        
        # 添加专家知识
        engine.add_expert_knowledge(
            domain="system_optimization",
            content="CPU使用率超过80%时应该触发节能策略",
            level=KnowledgeLevel.QUALITATIVE
        )
        
        # 执行综合集成
        result = engine.synthesize(
            problem="如何降低系统CPU使用率",
            qualitative_data={"专家意见": [...]},
            quantitative_data={"cpu_history": [...]}
        )
        
        # 请求人工验证
        if not result.human_validated:
            engine.request_validation(result)
    """

    def __init__(self):
        # 专家知识库
        self.expert_knowledge: Dict[str, List[ExpertKnowledge]] = {}
        
        # 验证回调
        self.validation_callback: Optional[Callable] = None
        
        # 统计
        self.stats = {
            "total_syntheses": 0,
            "successful_syntheses": 0,
            "human_validations": 0,
            "knowledge_integrated": 0
        }

    def add_expert_knowledge(
        self,
        domain: str,
        content: str,
        level: KnowledgeLevel,
        source: str = "hermes",
        confidence: float = 1.0
    ) -> str:
        """添加专家知识"""
        knowledge_id = f"ek_{int(time.time() * 1000)}"
        
        knowledge = ExpertKnowledge(
            knowledge_id=knowledge_id,
            domain=domain,
            content=content,
            level=level,
            source=source,
            confidence=confidence
        )
        
        if domain not in self.expert_knowledge:
            self.expert_knowledge[domain] = []
        
        self.expert_knowledge[domain].append(knowledge)
        self.stats["knowledge_integrated"] += 1
        
        return knowledge_id

    def get_knowledge(self, domain: str) -> List[ExpertKnowledge]:
        """获取领域知识"""
        return self.expert_knowledge.get(domain, [])

    def synthesize(
        self,
        problem: str,
        qualitative_data: Optional[Dict] = None,
        quantitative_data: Optional[Dict] = None,
        constraints: Optional[Dict] = None,
        verbose: bool = False
    ) -> SynthesisOutput:
        """
        执行综合集成
        
        步骤:
        1. 专家群体智慧（定性）- 从知识库获取相关专家知识
        2. 数据与知识结合（半定量）- 融合定性知识和数据
        3. 计算机技术支撑（定量）- 计算求解
        4. 人机结合、以人为主 - 准备人工验证
        """
        self.stats["total_syntheses"] += 1
        
        if verbose:
            print(f"[MetaSynthesis] 问题: {problem}")
        
        # Step 1: 定性分析 - 专家群体智慧
        qualitative_knowledge = self._get_relevant_knowledge(problem)
        if verbose:
            print(f"[MetaSynthesis] 找到{len(qualitative_knowledge)}条专家知识")
        
        # Step 2: 半定量融合
        semi_result = self._semi_quantitative_fusion(
            qualitative_knowledge,
            quantitative_data or {}
        )
        if verbose:
            print(f"[MetaSynthesis] 半定量融合完成")
        
        # Step 3: 定量计算
        final_solution = self._quantitative_compute(
            semi_result,
            constraints or {}
        )
        if verbose:
            print(f"[MetaSynthesis] 定量计算完成")
        
        # 构建输出
        output = SynthesisOutput(
            solution=final_solution,
            confidence=semi_result.get("confidence", 0.5),
            level=self._determine_level(qualitative_knowledge, quantitative_data),
            reasoning=self._generate_reasoning(problem, qualitative_knowledge, final_solution)
        )
        
        self.stats["successful_syntheses"] += 1
        
        return output

    def _get_relevant_knowledge(self, problem: str) -> List[ExpertKnowledge]:
        """获取相关专家知识"""
        relevant = []
        
        for domain, knowledge_list in self.expert_knowledge.items():
            # 简单的关键词匹配
            for knowledge in knowledge_list:
                if any(keyword in problem.lower() for keyword in knowledge.content.lower().split()[:5]):
                    relevant.append(knowledge)
        
        return relevant

    def _semi_quantitative_fusion(
        self,
        knowledge: List[ExpertKnowledge],
        data: Dict
    ) -> Dict:
        """半定量融合"""
        if not knowledge and not data:
            return {"result": {}, "confidence": 0.3}
        
        # 融合专家置信度和数据置信度
        total_confidence = 0.0
        weighted_sum = 0.0
        
        # 知识贡献
        for k in knowledge:
            weighted_sum += k.confidence * k.validity
            total_confidence += k.confidence * k.validity
        
        # 数据贡献
        if data:
            data_confidence = data.get("confidence", 0.7)
            weighted_sum += data_confidence * len(data)
            total_confidence += data_confidence
        
        confidence = weighted_sum / (total_confidence + 0.001)
        
        # 融合结果
        result = {
            "knowledge_count": len(knowledge),
            "data_keys": list(data.keys()) if data else [],
            "confidence": confidence,
            "has_expert_input": len(knowledge) > 0,
            "has_data_input": bool(data)
        }
        
        return result

    def _quantitative_compute(
        self,
        semi_result: Dict,
        constraints: Dict
    ) -> Dict:
        """定量计算"""
        # 简化实现：基于半定量结果生成解决方案
        solution = {
            "action": "optimize",
            "parameters": {
                "target_metric": constraints.get("target", "cpu"),
                "threshold": 0.7 if semi_result["has_expert_input"] else 0.8
            },
            "confidence": semi_result["confidence"],
            "method": "meta_synthesis",
            "knowledge_contribution": semi_result["knowledge_count"],
            "data_contribution": len(semi_result["data_keys"])
        }
        
        return solution

    def _determine_level(
        self,
        knowledge: List[ExpertKnowledge],
        data: Optional[Dict]
    ) -> KnowledgeLevel:
        """确定知识层级"""
        has_knowledge = len(knowledge) > 0
        has_data = data and len(data) > 0
        
        if has_knowledge and has_data:
            return KnowledgeLevel.SEMI_QUANTITATIVE
        elif has_knowledge:
            return KnowledgeLevel.QUALITATIVE
        elif has_data:
            return KnowledgeLevel.QUANTITATIVE
        else:
            return KnowledgeLevel.QUALITATIVE

    def _generate_reasoning(
        self,
        problem: str,
        knowledge: List[ExpertKnowledge],
        solution: Dict
    ) -> str:
        """生成推理说明"""
        reasoning = f"基于{len(knowledge)}条专家知识，"
        reasoning += f"通过综合集成方法得出解决方案。"
        reasoning += f"采用{self._determine_level(knowledge, None).value}方法，"
        reasoning += f"置信度{solution['confidence']:.2f}。"
        return reasoning

    def request_validation(self, output: SynthesisOutput) -> str:
        """
        请求人工验证
        
        Returns:
            validation_id
        """
        validation_id = f"val_{int(time.time() * 1000)}"
        
        if self.validation_callback:
            self.validation_callback(output)
        
        return validation_id

    def confirm_validation(self, output: SynthesisOutput) -> bool:
        """
        确认人工验证通过
        
        Returns:
            bool
        """
        output.human_validated = True
        self.stats["human_validations"] += 1
        
        # 记录验证通过的知识到知识库
        if output.reasoning:
            self.add_expert_knowledge(
                domain="validated",
                content=output.reasoning,
                level=KnowledgeLevel.QUANTITATIVE,
                source="validation"
            )
        
        return True

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            **self.stats,
            "domains": len(self.expert_knowledge),
            "total_knowledge": sum(len(v) for v in self.expert_knowledge.values())
        }


# ============ 便捷函数 ============

def create_synthesis_engine() -> MetaSynthesisEngine:
    """创建综合集成引擎"""
    return MetaSynthesisEngine()
