#!/usr/bin/env python3
"""
ClawShell Hermes反馈接口
版本: v0.2.0-A
功能: Hermes ↔ ClawShell双向反馈通道
理论依据: 钱学森《工程控制论》综合集成方法
"""

import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


# ============ 数据结构 ============

class FeedbackType(Enum):
    """反馈类型"""
    INSIGHT = "insight"           # 洞察反馈
    SUGGESTION = "suggestion"     # 建议反馈
    WARNING = "warning"           # 警告反馈
    EVOLUTION = "evolution"       # 进化反馈
    VALIDATION = "validation"     # 验证反馈


@dataclass
class HermesFeedback:
    """Hermes反馈"""
    feedback_id: str
    feedback_type: FeedbackType
    content: Any                  # 反馈内容
    source: str = "hermes"        # 来源
    confidence: float = 1.0       # 置信度
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvolutionProposal:
    """进化提案"""
    proposal_id: str
    problem: str                  # 问题描述
    solutions: List[Dict]         # 解决方案列表
    selected_index: int = -1      # 选中的方案索引
    status: str = "pending"       # pending, approved, rejected, implemented
    hermes_analysis: Dict = field(default_factory=dict)
    experiment_results: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    implemented_at: Optional[float] = None


@dataclass
class ExpertKnowledge:
    """专家知识"""
    knowledge_id: str
    domain: str                  # 领域
    content: str                 # 知识内容
    source: str = "hermes"      # 来源
    validity: float = 1.0       # 有效度
    applicability: float = 0.5    # 适用度
    created_at: float = field(default_factory=time.time)


# ============ Hermes反馈接口 ============

class HermesFeedbackInterface:
    """
    Hermes反馈接口
    
    功能：
    - 接收Hermes的洞察和建议
    - 向Hermes发送执行反馈
    - 管理进化提案
    - 知识回流
    
    依据: 综合集成方法 - "从定性到定量的人机结合"
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        
        # 反馈队列
        self.feedback_queue: List[HermesFeedback] = []
        
        # 进化提案
        self.proposals: Dict[str, EvolutionProposal] = {}
        
        # 专家知识库
        self.expert_knowledge: Dict[str, ExpertKnowledge] = {}
        
        # 回调函数
        self.on_insight: Optional[Callable] = None
        self.on_suggestion: Optional[Callable] = None
        self.on_evolution: Optional[Callable] = None
        self.on_validation: Optional[Callable] = None
        
        # 统计
        self.stats = {
            "total_feedback": 0,
            "insights_received": 0,
            "suggestions_received": 0,
            "proposals_created": 0,
            "proposals_implemented": 0,
            "knowledge_integrated": 0
        }
        
        self._load()

    def receive_feedback(self, feedback: HermesFeedback):
        """
        接收Hermes反馈
        
        Args:
            feedback: HermesFeedback对象
        """
        self.feedback_queue.append(feedback)
        self.stats["total_feedback"] += 1
        
        # 触发对应回调
        if feedback.feedback_type == FeedbackType.INSIGHT:
            self.stats["insights_received"] += 1
            if self.on_insight:
                self.on_insight(feedback)
        
        elif feedback.feedback_type == FeedbackType.SUGGESTION:
            self.stats["suggestions_received"] += 1
            if self.on_suggestion:
                self.on_suggestion(feedback)
        
        elif feedback.feedback_type == FeedbackType.EVOLUTION:
            if self.on_evolution:
                self.on_evolution(feedback)
        
        elif feedback.feedback_type == FeedbackType.VALIDATION:
            if self.on_validation:
                self.on_validation(feedback)
        
        self._save()

    def send_to_hermes(
        self,
        message_type: str,
        content: Any,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        向Hermes发送消息
        
        Args:
            message_type: 消息类型 (request_analysis, report_result, etc.)
            content: 消息内容
            metadata: 元数据
        
        Returns:
            发送结果
        """
        message = {
            "type": message_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "sender": "openclaw"
        }
        
        # 实际发送需要通过外部通道
        # 这里记录到日志
        print(f"[→Hermes] {message_type}: {content}")
        
        return {"status": "sent", "message": message}

    def create_evolution_proposal(
        self,
        problem: str,
        solutions: List[Dict],
        hermes_analysis: Optional[Dict] = None
    ) -> str:
        """
        创建进化提案
        
        依据: Hermes生成多个解决草案 → 快速实验 → 评估结果 → 选择最优方案
        
        Args:
            problem: 问题描述
            solutions: 解决方案列表
            hermes_analysis: Hermes的分析结果
        
        Returns:
            proposal_id
        """
        proposal_id = f"proposal_{int(time.time() * 1000)}"
        
        proposal = EvolutionProposal(
            proposal_id=proposal_id,
            problem=problem,
            solutions=solutions,
            hermes_analysis=hermes_analysis or {}
        )
        
        self.proposals[proposal_id] = proposal
        self.stats["proposals_created"] += 1
        
        # 请求Hermes深度分析
        self.send_to_hermes(
            "analyze_proposal",
            {
                "proposal_id": proposal_id,
                "problem": problem,
                "solutions": solutions
            }
        )
        
        self._save()
        return proposal_id

    def report_experiment_result(
        self,
        proposal_id: str,
        solution_index: int,
        result: Dict
    ) -> bool:
        """
        报告实验结果
        
        Args:
            proposal_id: 提案ID
            solution_index: 方案索引
            result: 实验结果
        
        Returns:
            是否成功
        """
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        proposal.experiment_results.append({
            "solution_index": solution_index,
            "result": result,
            "timestamp": time.time()
        })
        
        # 发送结果给Hermes
        self.send_to_hermes(
            "experiment_result",
            {
                "proposal_id": proposal_id,
                "solution_index": solution_index,
                "result": result
            }
        )
        
        # 检查是否所有方案都测试完毕
        if len(proposal.experiment_results) >= len(proposal.solutions):
            # 请求Hermes选择最优方案
            self.send_to_hermes(
                "select_solution",
                {
                    "proposal_id": proposal_id,
                    "all_results": proposal.experiment_results
                }
            )
        
        return True

    def receive_solution_selection(
        self,
        proposal_id: str,
        selected_index: int
    ) -> bool:
        """
        接收Hermes的方案选择
        
        Args:
            proposal_id: 提案ID
            selected_index: 选中的方案索引
        
        Returns:
            是否成功
        """
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        proposal.selected_index = selected_index
        proposal.status = "approved"
        
        print(f"[Hermes→] Selected solution {selected_index} for proposal {proposal_id}")
        
        return True

    def implement_proposal(self, proposal_id: str) -> bool:
        """
        执行已批准的提案
        
        Args:
            proposal_id: 提案ID
        
        Returns:
            是否成功
        """
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != "approved":
            return False
        
        # 执行选中的方案
        selected_solution = proposal.solutions[proposal.selected_index]
        
        # 这里应该调用实际的执行逻辑
        # 简化处理：标记为已实现
        proposal.status = "implemented"
        proposal.implemented_at = time.time()
        
        self.stats["proposals_implemented"] += 1
        
        # 沉淀知识
        self._extract_knowledge(proposal)
        
        self._save()
        return True

    def add_expert_knowledge(
        self,
        domain: str,
        content: str,
        source: str = "hermes"
    ) -> str:
        """
        添加专家知识
        
        Args:
            domain: 领域
            content: 知识内容
            source: 来源
        
        Returns:
            knowledge_id
        """
        knowledge_id = f"knowledge_{int(time.time() * 1000)}"
        
        knowledge = ExpertKnowledge(
            knowledge_id=knowledge_id,
            domain=domain,
            content=content,
            source=source
        )
        
        self.expert_knowledge[knowledge_id] = knowledge
        self.stats["knowledge_integrated"] += 1
        
        self._save()
        return knowledge_id

    def get_pending_proposals(self) -> List[EvolutionProposal]:
        """获取待处理的提案"""
        return [
            p for p in self.proposals.values()
            if p.status in ("pending", "approved")
        ]

    def get_expert_knowledge(self, domain: Optional[str] = None) -> List[ExpertKnowledge]:
        """获取专家知识"""
        if domain:
            return [
                k for k in self.expert_knowledge.values()
                if k.domain == domain
            ]
        return list(self.expert_knowledge.values())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "pending_proposals": len(self.get_pending_proposals()),
            "total_knowledge": len(self.expert_knowledge),
            "feedback_queue_size": len(self.feedback_queue)
        }

    def _extract_knowledge(self, proposal: EvolutionProposal):
        """从提案中提取知识"""
        if not proposal.experiment_results:
            return
        
        # 提取成功的模式
        successful_results = [
            r for r in proposal.experiment_results
            if r.get("result", {}).get("success", False)
        ]
        
        if successful_results:
            # 简化处理：直接添加为专家知识
            self.add_expert_knowledge(
                domain="system_optimization",
                content=f"Problem: {proposal.problem}\n"
                        f"Successful solution: {proposal.solutions[proposal.selected_index]}\n"
                        f"Evidence: {successful_results}",
                source="experiment"
            )

    def _save(self):
        """保存数据"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "proposals": {
                    k: v.__dict__ for k, v in self.proposals.items()
                },
                "expert_knowledge": {
                    k: v.__dict__ for k, v in self.expert_knowledge.items()
                },
                "stats": self.stats
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Failed to save Hermes feedback interface: {e}")

    def _load(self):
        """加载数据"""
        if not self.persistence_path:
            return
        
        try:
            with open(self.persistence_path) as f:
                data = json.load(f)
            
            for pid, pdata in data.get("proposals", {}).items():
                self.proposals[pid] = EvolutionProposal(**pdata)
            
            for kid, kdata in data.get("expert_knowledge", {}).items():
                self.expert_knowledge[kid] = ExpertKnowledge(**kdata)
            
            self.stats = data.get("stats", self.stats)
        except Exception as e:
            print(f"❌ Failed to load Hermes feedback interface: {e}")


# ============ 便捷函数 ============

def create_hermes_interface(
    persistence_path: Optional[str] = None
) -> HermesFeedbackInterface:
    """创建Hermes反馈接口"""
    return HermesFeedbackInterface(persistence_path=persistence_path)
