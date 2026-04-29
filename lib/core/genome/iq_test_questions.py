#!/usr/bin/env python3
"""
ClawShell IQ Test Questions
标准化IQ测试题库
版本: v1.0.0
"""

from typing import Dict, List, Tuple

class IQTestQuestions:
    """IQ测试题库"""
    
    # 言语理解测试
    VERBAL_TESTS = [
        {
            "id": "V1",
            "question": "请解释'授人以鱼不如授人以渔'的含义，并举一个实际例子",
            "max_score": 100,
            "criteria": ["准确解释", "例子恰当", "应用场景"]
        },
        {
            "id": "V2", 
            "question": "如果有人说'时间就是金钱'，请从三个不同角度解读这句话",
            "max_score": 100,
            "criteria": ["经济学角度", "个人发展角度", "社会角度"]
        },
        {
            "id": "V3",
            "question": "请将'Rome was not built in a day'翻译成中文并解释其含义",
            "max_score": 100,
            "criteria": ["翻译准确", "解释完整", "实际应用"]
        }
    ]
    
    # 知觉推理测试
    REASONING_TESTS = [
        {
            "id": "R1",
            "question": """以下代码使用了什么设计模式？请分析其优缺点：
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance""",
            "max_score": 100,
            "criteria": ["识别准确", "优点分析", "缺点分析"]
        },
        {
            "id": "R2",
            "question": "请分析这个系统的瓶颈在哪里：用户说系统慢，数据库CPU 100%，内存80%，应用服务器CPU 20%",
            "max_score": 100,
            "criteria": ["瓶颈定位", "原因分析", "解决方案"]
        },
        {
            "id": "R3",
            "question": "如果A > B, B > C, C > D, A和D是什么关系？请推理",
            "max_score": 100,
            "criteria": ["推理正确", "逻辑清晰", "结论明确"]
        }
    ]
    
    # 工作记忆测试
    MEMORY_TESTS = [
        {
            "id": "M1",
            "question": "请依次记住并复述：苹果、飞机、太阳、书本、河流（按原顺序）",
            "max_score": 100,
            "criteria": ["完全正确", "顺序正确", "回忆完整"]
        },
        {
            "id": "M2",
            "question": "请记住并倒序复述：7、3、9、1、5",
            "max_score": 100,
            "criteria": ["完全正确", "倒序正确"]
        },
        {
            "id": "M3",
            "question": "请在记住后5分钟复述：量子、混沌、涌现、涌现、涌现",
            "max_score": 100,
            "criteria": ["准确记忆", "无遗漏"]
        }
    ]
    
    # 处理速度测试
    SPEED_TESTS = [
        {
            "id": "S1",
            "question": "计算：256 + 128 = ?",
            "max_score": 100,
            "criteria": ["答案正确", "速度快"]
        },
        {
            "id": "S2",
            "question": "查找：数组 [5,2,8,1,9] 中最大的数",
            "max_score": 100,
            "criteria": ["答案正确", "速度快"]
        },
        {
            "id": "S3",
            "question": "判断：3721是质数吗？请快速判断",
            "max_score": 100,
            "criteria": ["判断正确", "速度<5秒"]
        }
    ]
    
    # 知识储备测试
    KNOWLEDGE_TESTS = [
        {
            "id": "K1",
            "question": "请解释什么是微服务架构，它与单体架构的核心区别是什么？",
            "max_score": 100,
            "criteria": ["定义准确", "区别清晰", "优缺点说明"]
        },
        {
            "id": "K2",
            "question": "请说明TCP协议的三次握手过程",
            "max_score": 100,
            "criteria": ["步骤完整", "描述准确", "理解正确"]
        },
        {
            "id": "K3",
            "question": "什么是机器学习中的'过拟合'？如何避免？",
            "max_score": 100,
            "criteria": ["概念正确", "避免方法可行"]
        }
    ]
    
    # 适应学习测试
    ADAPTION_TESTS = [
        {
            "id": "A1",
            "question": "面对一个从未见过的复杂问题，你会如何解决？请描述你的思考过程",
            "max_score": 100,
            "criteria": ["方法论", "系统性", "可操作性"]
        },
        {
            "id": "A2",
            "question": "如果你的方案被专家批评为'不可行'，你会如何应对？",
            "max_score": 100,
            "criteria": ["态度正确", "分析方法", "改进方案"]
        },
        {
            "id": "A3",
            "question": "请用你熟悉的领域的知识，解释一个完全陌生领域的概念",
            "max_score": 100,
            "criteria": ["类比恰当", "解释清晰", "创新性"]
        }
    ]
    
    @classmethod
    def get_all_tests(cls) -> Dict[str, List]:
        """获取所有测试"""
        return {
            "verbal": cls.VERBAL_TESTS,
            "reasoning": cls.REASONING_TESTS,
            "memory": cls.MEMORY_TESTS,
            "speed": cls.SPEED_TESTS,
            "knowledge": cls.KNOWLEDGE_TESTS,
            "adaption": cls.ADAPTION_TESTS
        }
    
    @classmethod
    def get_tests_by_dimension(cls, dimension: str) -> List:
        """按维度获取测试"""
        tests = cls.get_all_tests()
        return tests.get(dimension, [])

if __name__ == "__main__":
    print("=== IQ测试题库 ===")
    questions = IQTestQuestions()
    
    for dim, tests in questions.get_all_tests().items():
        print(f"\n{dim.upper()} ({len(tests)}题):")
        for t in tests:
            print(f"  [{t['id']}] {t['question'][:50]}...")
