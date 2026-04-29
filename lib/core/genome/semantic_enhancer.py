#!/usr/bin/env python3
"""
ClawShell Semantic Enhancer
语义理解增强 - Phase 1 升级
版本: v1.0.0
功能: 歧义消解、多意图识别、情感分析
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Intent:
    """意图"""
    action: str
    object: str
    confidence: float
    params: Dict = field(default_factory=dict)

class SemanticEnhancer:
    """
    语义理解增强器
    
    功能：
    - 歧义消解: 根据上下文消除歧义
    - 多意图识别: 识别同一句话中的多个意图
    - 情感分析: 判断情感倾向
    """
    
    def __init__(self):
        # 常用词的多义词消歧
        self.disambiguation_rules = {
            "打": {
                "打电话": ["给", "电话"],
                "打球": ["球", "运动"],
                "打印": ["文件", "资料"],
                "打扫": ["房间", "卫生"]
            },
            "取消": {
                "取消订单": ["订单", "取消"],
                "取消关注": ["关注", "粉丝"]
            }
        }
        
        # 意图模式
        self.intent_patterns = {
            "create": ["创建", "新建", "添加", "增加"],
            "read": ["查看", "查询", "获取", "读取"],
            "update": ["修改", "更新", "编辑", "调整"],
            "delete": ["删除", "取消", "移除"],
            "execute": ["执行", "运行", "启动", "触发"],
            "schedule": ["安排", "预约", "定时", "计划"]
        }
        
        # 情感词典
        self.positive_words = {"好", "棒", "优秀", "完美", "赞", "不错", "成功", "完成"}
        self.negative_words = {"差", "坏", "糟糕", "失败", "错误", "问题", "取消"}
    
    def disambiguate(self, word: str, context: str) -> List[str]:
        """消歧: 根据上下文确定词义"""
        candidates = []
        
        if word in self.disambiguation_rules:
            for meaning, keywords in self.disambiguation_rules[word].items():
                if any(kw in context for kw in keywords):
                    candidates.append(meaning)
        
        return candidates if candidates else [word]
    
    def extract_intents(self, text: str) -> List[Intent]:
        """提取意图"""
        intents = []
        
        for action, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    # 提取动作对象
                    obj_match = re.search(f"{keyword}(.+?)(?:并|且|或|$)", text)
                    obj = obj_match.group(1).strip() if obj_match else "unknown"
                    
                    intent = Intent(
                        action=action,
                        object=obj,
                        confidence=0.8
                    )
                    intents.append(intent)
                    break
        
        return intents
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """情感分析"""
        positive_count = sum(1 for w in self.positive_words if w in text)
        negative_count = sum(1 for w in self.negative_words if w in text)
        
        total = positive_count + negative_count
        if total == 0:
            return {"sentiment": "neutral", "score": 0.5}
        
        positive_ratio = positive_count / total
        
        return {
            "sentiment": "positive" if positive_ratio > 0.6 else "negative" if positive_ratio < 0.4 else "neutral",
            "score": positive_ratio,
            "positive_count": positive_count,
            "negative_count": negative_count
        }
    
    def understand_metaphor(self, text: str) -> Optional[Dict]:
        """隐喻理解"""
        metaphors = {
            "瓶颈": "限制因素",
            "突破口": "解决方案",
            "深水区": "复杂阶段"
        }
        
        for metaphor, literal in metaphors.items():
            if metaphor in text:
                return {
                    "metaphor": metaphor,
                    "literal": literal,
                    "confidence": 0.85
                }
        
        return None
    
    def enhance_understanding(self, text: str, context: str = "") -> Dict:
        """综合增强理解"""
        return {
            "original": text,
            "context": context,
            "disambiguated": [self.disambiguate(w, context or text) for w in text],
            "intents": [
                {"action": i.action, "object": i.object, "confidence": i.confidence}
                for i in self.extract_intents(text)
            ],
            "sentiment": self.analyze_sentiment(text),
            "metaphor": self.understand_metaphor(text)
        }

if __name__ == "__main__":
    enhancer = SemanticEnhancer()
    
    # 测试
    print("=== 语义增强测试 ===")
    
    # 歧义消解
    print("\n1. 歧义消解:")
    print(f"   '打'在'打电话给妈妈'中: {enhancer.disambiguate('打', '打电话给妈妈')}")
    print(f"   '打'在'打篮球'中: {enhancer.disambiguate('打', '打篮球')}")
    
    # 意图识别
    print("\n2. 多意图识别:")
    intents = enhancer.extract_intents("创建文档并安排明天的会议")
    for intent in intents:
        print(f"   动作: {intent.action}, 对象: {intent.object}, 置信度: {intent.confidence}")
    
    # 情感分析
    print("\n3. 情感分析:")
    print(f"   '系统运行很好很完美': {enhancer.analyze_sentiment('系统运行很好很完美')}")
    print(f"   '出现严重错误': {enhancer.analyze_sentiment('出现严重错误')}")
    
    # 隐喻理解
    print("\n4. 隐喻理解:")
    print(f"   '遇到技术深水区': {enhancer.understand_metaphor('遇到技术深水区')}")
