#!/usr/bin/env python3
"""
OpenClaw IQ Evaluation System
完整的IQ评估系统 - 支持Hermes外部评估
版本: v2.0
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from iq_challenge_questions import DeepChallengeIQTest

@dataclass
class Answer:
    """答案记录"""
    test_id: str
    dimension: str
    answer: str
    response_time: float
    submitted_at: str
    score: Optional[float] = None
    evaluator_notes: Optional[str] = None

class OpenClawIQEvaluator:
    """
    OpenClaw IQ评估系统
    
    用法：
    1. 获取测试题目: get_test_suite()
    2. 提交答案: submit_answer()
    3. 获取评估提示: get_evaluation_prompt()  
    4. 更新评分: update_score()
    5. 计算IQ: calculate_final_iq()
    """
    
    def __init__(self):
        self.test_bank = DeepChallengeIQTest()
        self.answers: List[Answer] = []
        self.test_started_at: Optional[str] = None
        
        # 维度权重 (WAIS-IV标准)
        self.weights = {
            "verbal": 0.15,
            "reasoning": 0.20,
            "memory": 0.20,
            "speed": 0.15,
            "knowledge": 0.15,
            "adaption": 0.15
        }
    
    def start_evaluation(self) -> Dict:
        """开始评估"""
        self.test_started_at = datetime.now().isoformat()
        self.answers = []
        
        return {
            "status": "started",
            "started_at": self.test_started_at,
            "total_questions": self.test_bank.get_test_count(),
            "dimensions": list(self.weights.keys())
        }
    
    def get_test_suite(self, dimension: str = None) -> Dict:
        """获取测试套件"""
        if dimension:
            tests = self.test_bank.get_all_tests().get(dimension, [])
            return {
                "dimension": dimension,
                "count": len(tests),
                "tests": tests
            }
        else:
            all_tests = self.test_bank.get_all_tests()
            return {
                "total": self.test_bank.get_test_count(),
                "dimensions": {
                    dim: len(tests) for dim, tests in all_tests.items()
                },
                "all_tests": all_tests
            }
    
    def get_random_test(self, dimension: str = None) -> Dict:
        """获取随机一道测试题"""
        import random
        
        if dimension:
            tests = self.test_bank.get_all_tests().get(dimension, [])
        else:
            all_tests = self.test_bank.get_all_tests()
            tests = []
            for t in all_tests.values():
                tests.extend(t)
        
        if not tests:
            return {"error": "No tests available"}
        
        selected = random.choice(tests)
        return selected
    
    def submit_answer(
        self,
        test_id: str,
        answer: str,
        response_time: float
    ) -> Dict:
        """提交答案"""
        # 找到测试信息
        test_info = self._find_test(test_id)
        if not test_info:
            return {"error": f"Test {test_id} not found"}
        
        answer_record = Answer(
            test_id=test_id,
            dimension=test_info["dimension"],
            answer=answer,
            response_time=response_time,
            submitted_at=datetime.now().isoformat()
        )
        
        self.answers.append(answer_record)
        
        return {
            "status": "submitted",
            "test_id": test_id,
            "dimension": test_info["dimension"],
            "pending_evaluation": True
        }
    
    def _find_test(self, test_id: str) -> Optional[Dict]:
        """查找测试"""
        all_tests = self.test_bank.get_all_tests()
        for dimension, tests in all_tests.items():
            for test in tests:
                if test["id"] == test_id:
                    return {"dimension": dimension, "test": test}
        return None
    
    def get_evaluation_prompt(self, test_id: str) -> Optional[str]:
        """生成Hermes评估提示"""
        test_info = self._find_test(test_id)
        if not test_info:
            return None
        
        test = test_info["test"]
        answer_record = self._find_answer(test_id)
        
        prompt = f"""请评估以下OpenClaw的答案：

## 测试信息
- 测试ID: {test_id}
- 维度: {test_info["dimension"]}
- 难度: {test.get("level", "N/A")}
- 时间限制: {test.get("time_limit", "N/A")}秒

## 问题
{test['question']}

## 答案
{answer_record.answer if answer_record else "未提交答案"}

## 评分标准
{chr(10).join(f"- {c}" for c in test['criteria'])}

## 评分要求
1. 根据评分标准给出0-{test['max_score']}的得分
2. 简要评语
3. 亮点和不足

请以JSON格式返回：
{{"score": <分数>, "notes": "<评语>"}}
"""
        return prompt
    
    def _find_answer(self, test_id: str) -> Optional[Answer]:
        """查找答案"""
        for answer in self.answers:
            if answer.test_id == test_id:
                return answer
        return None
    
    def update_score(
        self,
        test_id: str,
        score: float,
        evaluator_notes: str = ""
    ) -> Dict:
        """更新评分"""
        answer = self._find_answer(test_id)
        if not answer:
            return {"error": "Answer not found"}
        
        answer.score = score
        answer.evaluator_notes = evaluator_notes
        
        return {
            "status": "updated",
            "test_id": test_id,
            "score": score
        }
    
    def calculate_final_iq(self) -> Dict:
        """计算最终IQ分数"""
        if not self.answers:
            return {"error": "No answers submitted"}
        
        # 计算各维度得分
        dimension_scores = {}
        dimension_counts = {}
        
        for answer in self.answers:
            dim = answer.dimension
            if answer.score is None:
                continue
                
            if dim not in dimension_scores:
                dimension_scores[dim] = 0
                dimension_counts[dim] = 0
            
            dimension_scores[dim] += answer.score
            dimension_counts[dim] += 1
        
        # 计算维度平均分
        dimension_averages = {}
        for dim in dimension_scores:
            if dimension_counts[dim] > 0:
                dimension_averages[dim] = dimension_scores[dim] / dimension_counts[dim]
        
        # 计算综合得分 (加权)
        overall = sum(
            dimension_averages.get(dim, 0) * weight
            for dim, weight in self.weights.items()
        )
        
        # IQ换算 (WAIS标准)
        iq_score = 70 + (overall * 0.6)
        
        return {
            "iq_score": round(iq_score, 1),
            "verbal": round(dimension_averages.get("verbal", 0), 1),
            "reasoning": round(dimension_averages.get("reasoning", 0), 1),
            "memory": round(dimension_averages.get("memory", 0), 1),
            "speed": round(dimension_averages.get("speed", 0), 1),
            "knowledge": round(dimension_averages.get("knowledge", 0), 1),
            "adaption": round(dimension_averages.get("adaption", 0), 1),
            "tests_completed": len([a for a in self.answers if a.score is not None]),
            "total_tests": len(self.answers)
        }
    
    def get_progress(self) -> Dict:
        """获取评估进度"""
        all_tests = self.test_bank.get_all_tests()
        total = sum(len(tests) for tests in all_tests.values())
        
        completed = len(self.answers)
        scored = len([a for a in self.answers if a.score is not None])
        
        return {
            "total_questions": total,
            "submitted": completed,
            "evaluated": scored,
            "pending": total - completed
        }

# 全局实例
_evaluator: Optional[OpenClawIQEvaluator] = None

def get_evaluator() -> OpenClawIQEvaluator:
    """获取评估器实例"""
    global _evaluator
    if _evaluator is None:
        _evaluator = OpenClawIQEvaluator()
    return _evaluator

if __name__ == "__main__":
    ev = get_evaluator()
    
    print("=== OpenClaw IQ评估系统 ===")
    print(f"\n开始评估...")
    result = ev.start_evaluation()
    print(f"状态: {result['status']}")
    print(f"总题数: {result['total_questions']}")
    
    print(f"\n获取测试套件...")
    suite = ev.get_test_suite()
    print(f"总题数: {suite['total']}")
    print(f"维度分布: {suite['dimensions']}")
    
    print(f"\n获取随机测试...")
    test = ev.get_random_test()
    print(f"随机题目: [{test['id']}] {test['question'][:50]}...")
