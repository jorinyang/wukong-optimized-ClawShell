#!/usr/bin/env python3
"""
ClawShell Hermes Evaluator
Hermes评估接口 - 用于外部评估OpenClaw的IQ
版本: v1.0.0
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from iq_test_questions import IQTestQuestions

class HermesEvaluator:
    """
    Hermes评估器
    
    Hermes调用此接口对OpenClaw进行IQ评估
    """
    
    def __init__(self):
        self.questions = IQTestQuestions()
        self.test_history: List[Dict] = []
    
    def get_test_suite(self, dimension: str = None) -> Dict:
        """获取测试套件"""
        if dimension:
            tests = self.questions.get_tests_by_dimension(dimension)
            return {
                "dimension": dimension,
                "tests": tests,
                "count": len(tests)
            }
        else:
            all_tests = self.questions.get_all_tests()
            return {
                "dimensions": list(all_tests.keys()),
                "total_tests": sum(len(t) for t in all_tests.values()),
                "tests": all_tests
            }
    
    def submit_answer(self, test_id: str, answer: str, response_time: float) -> Dict:
        """提交答案用于评估"""
        # 找到对应测试
        test_info = self._find_test(test_id)
        if not test_info:
            return {"error": "Test not found"}
        
        # 保存答案
        submission = {
            "test_id": test_id,
            "answer": answer,
            "response_time": response_time,
            "dimension": test_info["dimension"],
            "submitted_at": datetime.now().isoformat(),
            "scored": False,
            "score": None
        }
        
        self.test_history.append(submission)
        return {
            "status": "submitted",
            "test_id": test_id,
            "pending_evaluation": True
        }
    
    def _find_test(self, test_id: str) -> Optional[Dict]:
        """查找测试"""
        all_tests = self.questions.get_all_tests()
        for dimension, tests in all_tests.items():
            for test in tests:
                if test["id"] == test_id:
                    return {"dimension": dimension, "test": test}
        return None
    
    def get_evaluation_prompt(self, test_id: str, answer: str) -> str:
        """生成评估提示词（供Hermes使用）"""
        test_info = self._find_test(test_id)
        if not test_info:
            return "Test not found"
        
        test = test_info["test"]
        
        prompt = f"""请评估以下答案：

问题ID: {test_id}
问题: {test['question']}

答案: {answer}

评分标准: {', '.join(test['criteria'])}
满分: {test['max_score']}

请给出：
1. 得分 (0-{test['max_score']})
2. 简要评语
"""
        return prompt
    
    def calculate_iq_score(self) -> Dict:
        """计算IQ分数"""
        if not self.test_history:
            return {"error": "No tests completed"}
        
        # 按维度分组计算
        dimension_scores = {}
        dimension_counts = {}
        
        for submission in self.test_history:
            dim = submission["dimension"]
            if dim not in dimension_scores:
                dimension_scores[dim] = 0
                dimension_counts[dim] = 0
            
            # 这里需要Hermes评估后的分数
            if submission["scored"]:
                dimension_scores[dim] += submission["score"]
                dimension_counts[dim] += 1
        
        # 计算各维度平均分
        dimension_averages = {}
        for dim in dimension_scores:
            if dimension_counts[dim] > 0:
                dimension_averages[dim] = dimension_scores[dim] / dimension_counts[dim]
        
        # 综合得分 (加权平均)
        weights = {
            "verbal": 0.15,
            "reasoning": 0.20,
            "memory": 0.20,
            "speed": 0.15,
            "knowledge": 0.15,
            "adaption": 0.15
        }
        
        overall_score = sum(
            dimension_averages.get(dim, 0) * weights.get(dim, 0)
            for dim in weights
        )
        
        # IQ换算
        iq_score = 70 + (overall_score * 0.6)
        
        return {
            "iq_score": round(iq_score, 1),
            "dimension_scores": dimension_averages,
            "tests_completed": len(self.test_history),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    evaluator = HermesEvaluator()
    
    print("=== Hermes评估器测试 ===")
    
    # 获取测试套件
    suite = evaluator.get_test_suite()
    print(f"\n总测试数: {suite['total_tests']}")
    print(f"维度: {suite['dimensions']}")
    
    # 获取言语理解测试
    verbal_tests = evaluator.get_test_suite("verbal")
    print(f"\n言语理解测试 ({verbal_tests['count']}题):")
    for t in verbal_tests['tests']:
        print(f"  [{t['id']}] {t['question'][:40]}...")
