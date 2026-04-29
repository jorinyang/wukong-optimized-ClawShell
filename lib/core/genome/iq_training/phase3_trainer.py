#!/usr/bin/env python3
"""
Phase 3: 创新思维 + 综合应用
"""

import random

class InnovationTrainer:
    """创新思维训练"""
    
    PROBLEMS = [
        {
            "id": "IN1",
            "question": "如何用AI重新定义商业综合体的用户体验？提出5个创新方向",
            "dimensions": ["用户洞察", "技术应用", "商业模式", "可行性", "创新性"],
            "max_score": 100
        },
        {
            "id": "IN2",
            "question": "设计一个'永不过时'的数字资产管理方案",
            "dimensions": ["技术架构", "长期维护", "成本控制", "可扩展性", "容灾"],
            "max_score": 100
        },
        {
            "id": "IN3",
            "question": "如何让AI具备'常识'推理能力？提出你的理论框架",
            "dimensions": ["知识表示", "推理机制", "学习方式", "评估标准", "理论创新"],
            "max_score": 100
        }
    ]
    
    @classmethod
    def evaluate(cls, problem_id: str, answer: str) -> dict:
        for p in cls.PROBLEMS:
            if p["id"] == problem_id:
                ans_lower = answer.lower()
                
                # 计算维度覆盖率
                matched = sum(1 for d in p["dimensions"] if d.lower() in ans_lower)
                coverage = matched / len(p["dimensions"])
                
                # 答案长度评估
                length_score = min(30, len(answer) // 20)
                
                # 创新性评估（简单版）
                innovation_words = ["创新", "突破", "颠覆", "全新", "首创"]
                innovation = sum(1 for w in innovation_words if w in ans_lower)
                
                score = min(100, int(coverage * 40 + length_score + innovation * 10))
                
                return {
                    "score": score,
                    "coverage": f"{matched}/{len(p['dimensions'])}",
                    "length": len(answer)
                }
        return {"error": "not found"}

class ComprehensiveTrainer:
    """综合应用训练"""
    
    SCENARIOS = [
        {
            "id": "CS1",
            "scenario": "一家中型购物中心想要数字化转型，预算300万，3年实施",
            "task": "制定一份完整的AI转型方案，包含：1) 核心场景选择 2) 技术架构 3) 实施路径 4) 预算分配 5) 风险评估"
        },
        {
            "id": "CS2",
            "scenario": "一个创业公司想要开发AI驱动的智能客服系统",
            "task": "设计技术方案，包含：1) 技术选型 2) 系统架构 3) 开发计划 4) 成本估算 5) 市场定位"
        }
    ]
    
    @classmethod
    def evaluate(cls, scenario_id: str, answer: str) -> dict:
        for s in cls.SCENARIOS:
            if s["id"] == scenario_id:
                ans_lower = answer.lower()
                
                # 检查5个要素
                elements = ["场景", "架构", "路径", "预算", "风险"]
                matched = sum(1 for e in elements if e in ans_lower)
                
                score = min(100, matched * 20 + min(20, len(answer) // 50))
                
                return {"score": score, "elements": f"{matched}/{len(elements)}"}
        return {"error": "not found"}

if __name__ == "__main__":
    print("Phase 3 Trainer loaded")
