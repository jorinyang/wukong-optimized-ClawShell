#!/usr/bin/env python3
"""
ClawShell Tech Knowledge Base
技术知识库 - Phase 4
版本: v1.0.1
"""

from typing import Dict, List, Set

class TechKnowledgeBase:
    """技术知识库"""
    
    def __init__(self):
        # 软件架构模式
        self.architecture_patterns = {
            "microservices": {
                "description": "微服务架构",
                "pros": ["可扩展", "可独立部署", "技术多样性"],
                "cons": ["复杂度高", "运维困难", "数据一致性"]
            },
            "monolithic": {
                "description": "单体架构",
                "pros": ["简单", "部署容易", "性能好"],
                "cons": ["扩展性差", "技术锁定", "部署慢"]
            },
            "serverless": {
                "description": "无服务器架构",
                "pros": ["成本低", "自动扩展", "无需运维"],
                "cons": ["冷启动", "供应商锁定", "调试困难"]
            }
        }
        
        # 设计模式
        self.design_patterns = {
            "singleton": ["单例模式"],
            "factory": ["工厂模式"],
            "observer": ["观察者模式"],
            "strategy": ["策略模式"],
            "decorator": ["装饰器模式"],
            "adapter": ["适配器模式"],
            "facade": ["门面模式"]
        }
        
        # 编程范式
        self.programming_paradigms = {
            "oop": ["面向对象编程", "封装", "继承", "多态"],
            "functional": ["函数式编程", "纯函数", "不可变性", "高阶函数"],
            "reactive": ["响应式编程", "流", "背压", "观察者"]
        }
        
        # AI/ML概念
        self.ai_concepts = {
            "machine_learning": ["监督学习", "无监督学习", "强化学习"],
            "deep_learning": ["神经网络", "CNN", "RNN", "Transformer"],
            "nlp": ["词向量", "注意力机制", "BERT", "GPT"]
        }
    
    def get_pattern(self, pattern_name: str) -> Dict:
        """获取架构模式"""
        return self.architecture_patterns.get(pattern_name.lower(), {})
    
    def get_design_patterns(self) -> List[str]:
        """获取所有设计模式"""
        patterns = []
        for category, pattern_list in self.design_patterns.items():
            patterns.extend(pattern_list)
        return patterns
    
    def get_concepts(self, domain: str) -> List[str]:
        """获取领域概念"""
        return self.ai_concepts.get(domain.lower(), [])
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """搜索知识"""
        query_lower = query.lower()
        results = []
        
        # 搜索架构模式
        for name, pattern in self.architecture_patterns.items():
            desc = pattern.get("description", "").lower()
            if query_lower in name or query_lower in desc:
                results.append({
                    "type": "architecture_pattern",
                    "name": name,
                    "data": pattern
                })
        
        # 搜索设计模式
        for category, patterns in self.design_patterns.items():
            for pattern in patterns:
                if query_lower in pattern.lower():
                    results.append({
                        "type": "design_pattern",
                        "name": pattern,
                        "category": category
                    })
        
        # 搜索AI概念
        for domain, concepts in self.ai_concepts.items():
            for concept in concepts:
                if query_lower in concept.lower():
                    results.append({
                        "type": "ai_concept",
                        "domain": domain,
                        "name": concept
                    })
        
        return results

if __name__ == "__main__":
    kb = TechKnowledgeBase()
    
    print("=== 技术知识库测试 ===")
    
    # 获取架构模式
    pattern = kb.get_pattern("microservices")
    print(f"\n微服务架构: {pattern}")
    
    # 搜索知识
    results = kb.search_knowledge("neural")
    print(f"\n搜索 'neural' 结果: {len(results)}")
    for r in results:
        print(f"  - {r}")
    
    # 搜索设计模式
    results2 = kb.search_knowledge("singleton")
    print(f"\n搜索 'singleton' 结果: {len(results2)}")
