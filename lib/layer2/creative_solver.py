#!/usr/bin/env python3
"""
ClawShell Creative Problem Solver
创造性问题解决器 - Phase 3
版本: v1.0.0
功能: 发散思维(多解生成) + 收敛思维(方案优选)
"""

import json
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Solution:
    """解决方案"""
    id: str
    description: str
    score: float = 0.0
    confidence: float = 0.0
    novelty: float = 0.0,  # 创新度
    feasibility: float = 0.0,  # 可行性
    strategy: str = "general",  # 策略
    category: str = "general"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class CreativeSolver:
    """
    创造性问题解决器
    
    功能：
    - 发散思维: 生成多个可能的解决方案
    - 收敛思维: 从多解中选择最优
    - 远迁移: 跨领域应用知识
    """
    
    def __init__(self):
        self.solutions: List[Solution] = []
        self.domain_knowledge: Dict[str, List[str]] = {}
        
        # 启发式策略
        self.divergence_strategies = [
            "analogy",      # 类比
            "reversal",     # 逆转
            "combination",  # 组合
            "abstract",     # 抽象
            "concrete"      # 具体化
        ]
    
    def add_domain_knowledge(self, domain: str, patterns: List[str]):
        """添加领域知识"""
        if domain not in self.domain_knowledge:
            self.domain_knowledge[domain] = []
        self.domain_knowledge[domain].extend(patterns)
    
    def generate_divergent(self, problem: str, num_solutions: int = 5) -> List[Solution]:
        """发散思维: 生成多个解决方案"""
        solutions = []
        
        for i in range(num_solutions):
            strategy = random.choice(self.divergence_strategies)
            
            solution = Solution(
                id=f"sol_{len(self.solutions) + i + 1}",
                description=self._apply_strategy(problem, strategy),
                strategy=strategy,
                novelty=random.uniform(0.6, 0.95),
                feasibility=random.uniform(0.5, 0.9)
            )
            solution.score = (solution.novelty + solution.feasibility) / 2
            solutions.append(solution)
        
        self.solutions.extend(solutions)
        return solutions
    
    def _apply_strategy(self, problem: str, strategy: str) -> str:
        """应用策略生成解决方案"""
        strategies = {
            "analogy": f"类比方案: {problem} 类似场景...",
            "reversal": f"逆转方案: 反向思考 {problem}...",
            "combination": f"组合方案: 结合多个元素 {problem}...",
            "abstract": f"抽象方案: 提取 {problem} 的核心本质...",
            "concrete": f"具体方案: 将 {problem} 细化为具体步骤..."
        }
        return strategies.get(strategy, f"方案: {problem}")
    
    def converge(self, solutions: List[Solution], top_k: int = 3) -> List[Solution]:
        """收敛思维: 选择最优方案"""
        # 按评分排序
        sorted_solutions = sorted(solutions, key=lambda s: s.score, reverse=True)
        return sorted_solutions[:top_k]
    
    def far_transfer(self, source_domain: str, target_domain: str, solution: Solution) -> Solution:
        """远迁移: 将一个领域的解决方案应用到另一个领域"""
        if source_domain in self.domain_knowledge and target_domain in self.domain_knowledge:
            # 获取目标领域的知识
            target_knowledge = self.domain_knowledge[target_domain]
            
            # 修改解决方案以适应新领域
            transferred = Solution(
                id=f"{solution.id}_transferred",
                description=f"[{target_domain}] {solution.description}",
                novelty=solution.novelty * 0.8,  # 迁移会降低创新度
                feasibility=solution.feasibility * 0.9,
                category=target_domain
            )
            transferred.score = (transferred.novelty + transferred.feasibility) / 2
            return transferred
        
        return solution
    
    def solve(self, problem: str, domain: str = "general") -> Dict[str, Any]:
        """完整解决流程"""
        # 1. 发散生成
        divergent_solutions = self.generate_divergent(problem, num_solutions=7)
        
        # 2. 收敛选择
        best_solutions = self.converge(divergent_solutions, top_k=3)
        
        # 3. 如果有领域知识，尝试远迁移
        if domain != "general" and domain in self.domain_knowledge:
            transferred = []
            for sol in best_solutions[:2]:
                transfer = self.far_transfer("general", domain, sol)
                transferred.append(transfer)
            best_solutions.extend(transferred)
        
        return {
            "problem": problem,
            "all_solutions": [
                {"id": s.id, "description": s.description, "score": s.score}
                for s in divergent_solutions
            ],
            "best_solutions": [
                {"id": s.id, "description": s.description, "score": s.score}
                for s in best_solutions
            ],
            "stats": {
                "total_generated": len(divergent_solutions),
                "top_score": best_solutions[0].score if best_solutions else 0
            }
        }

if __name__ == "__main__":
    solver = CreativeSolver()
    
    # 添加领域知识
    solver.add_domain_knowledge("software", ["模式", "架构", "重构"])
    solver.add_domain_knowledge("business", ["流程", "优化", "增长"])
    
    print("=== 创造性问题解决测试 ===")
    
    # 测试
    result = solver.solve("如何提高系统性能", domain="software")
    
    print(f"\n问题: {result['problem']}")
    print(f"\n生成方案数: {result['stats']['total_generated']}")
    print(f"\n最优方案:")
    for sol in result['best_solutions']:
        print(f"  [{sol['score']:.2f}] {sol['description']}")
