#!/usr/bin/env python3
"""
IQ Evaluation Controller
自动评估流程控制器
Hermes出题 -> OpenClaw回答 -> Hermes评估 -> 循环
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from openclaw_iq_evaluator import get_evaluator

class IQEvaluationController:
    """
    评估流程控制器
    
    流程：
    1. Hermes获取下一题
    2. OpenClaw回答
    3. Hermes评估
    4. 循环直到完成
    5. 生成最终报告
    """
    
    def __init__(self):
        self.evaluator = get_evaluator()
        self.current_test_index = 0
        self.tests_completed = []
        self.evaluation_log = []
        
        # 初始化评估
        self.evaluator.start_evaluation()
    
    def get_next_question(self) -> Dict:
        """获取下一题"""
        suite = self.evaluator.get_test_suite()
        all_tests = suite.get('all_tests', {})
        
        # 收集所有测试
        all_test_list = []
        for dimension, tests in all_tests.items():
            for test in tests:
                test['dimension'] = dimension
                all_test_list.append(test)
        
        # 获取下一题
        if self.current_test_index < len(all_test_list):
            next_test = all_test_list[self.current_test_index]
            return {
                "status": "ready",
                "test_number": self.current_test_index + 1,
                "total": len(all_test_list),
                "test": next_test
            }
        else:
            return {
                "status": "completed",
                "test_number": len(all_test_list),
                "total": len(all_test_list),
                "final_iq": self.get_final_report()
            }
    
    def submit_openclaw_answer(
        self,
        test_id: str,
        answer: str,
        response_time: float
    ) -> Dict:
        """提交OpenClaw的答案"""
        result = self.evaluator.submit_answer(test_id, answer, response_time)
        
        # 获取评估提示
        prompt = self.evaluator.get_evaluation_prompt(test_id)
        
        return {
            "submission": result,
            "evaluation_prompt": prompt,
            "next_step": "hermes_evaluate"
        }
    
    def record_hermes_score(
        self,
        test_id: str,
        score: float,
        notes: str
    ) -> Dict:
        """记录Hermes的评分"""
        result = self.evaluator.update_score(test_id, score, notes)
        
        # 记录到日志
        self.evaluation_log.append({
            "test_id": test_id,
            "score": score,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        })
        
        self.tests_completed.append(test_id)
        self.current_test_index += 1
        
        # 检查进度
        progress = self.evaluator.get_progress()
        
        return {
            "score_recorded": result,
            "progress": progress,
            "next_step": "get_next_question" if progress['pending'] > 0 else "generate_final_report"
        }
    
    def get_final_report(self) -> Dict:
        """生成最终报告"""
        iq_result = self.evaluator.calculate_final_iq()
        
        # 按维度分析
        dimension_analysis = {}
        for dim in ['verbal', 'reasoning', 'memory', 'speed', 'knowledge', 'adaption']:
            score = iq_result.get(dim, 0)
            if score >= 90:
                level = "非常优秀"
            elif score >= 80:
                level = "优秀"
            elif score >= 70:
                level = "良好"
            elif score >= 60:
                level = "待提升"
            else:
                level = "需要改进"
            dimension_analysis[dim] = {
                "score": score,
                "level": level
            }
        
        return {
            "iq_score": iq_result['iq_score'],
            "dimension_scores": dimension_analysis,
            "tests_completed": iq_result['tests_completed'],
            "total_tests": iq_result['total_tests'],
            "evaluation_log": self.evaluation_log,
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_full_report(self) -> str:
        """生成完整报告"""
        report = self.get_final_report()
        
        report_text = f"""
# OpenClaw IQ 评估报告

## 评估概况
- 评估时间: {report['timestamp']}
- 完成测试: {report['tests_completed']}/{report['total_tests']}

## 最终IQ分数

**IQ: {report['iq_score']}**

## 维度分析

| 维度 | 得分 | 水平 |
|------|------|------|
"""
        
        dim_names = {
            "verbal": "言语理解",
            "reasoning": "知觉推理",
            "memory": "工作记忆",
            "speed": "处理速度",
            "knowledge": "知识储备",
            "adaption": "适应学习"
        }
        
        for dim, data in report['dimension_scores'].items():
            report_text += f"| {dim_names.get(dim, dim)} | {data['score']} | {data['level']} |\n"
        
        report_text += """
## 评估详情

"""
        
        for log in report['evaluation_log']:
            report_text += f"### {log['test_id']}\n"
            report_text += f"- 得分: {log['score']}\n"
            report_text += f"- 评语: {log['notes']}\n\n"
        
        return report_text

# 全局实例
_controller: Optional[IQEvaluationController] = None

def get_controller() -> IQEvaluationController:
    global _controller
    if _controller is None:
        _controller = IQEvaluationController()
    return _controller

if __name__ == "__main__":
    controller = get_controller()
    
    # 开始评估
    print("=== OpenClaw IQ 评估开始 ===\n")
    
    # 获取第一题
    result = controller.get_next_question()
    print(f"题目 {result['test_number']}/{result['total']}")
    print(f"维度: {result['test']['dimension']}")
    print(f"问题: {result['test']['question'][:100]}...")
    print(f"评分标准: {', '.join(result['test']['criteria'])}")
