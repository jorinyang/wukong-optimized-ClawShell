#!/usr/bin/env python3
"""
Adaption Trainer v3.2
适应学习专项训练 - 最终版
"""

import random

class AdaptionTrainer:
    
    TRANSFER_CHALLENGES = [
        {"id": "AT1", "source": "蜂群", "target": "管理",
         "transfer_ideas": ["去中心化", "分工", "协调", "涌现", "适应"],
         "creativity_weight": 5},
        {"id": "AT2", "source": "热力学", "target": "组织",
         "transfer_ideas": ["开放", "做功", "负熵", "平衡", "自组织"],
         "creativity_weight": 5},
        {"id": "AT3", "source": "生态", "target": "AI架构",
         "transfer_ideas": ["多样", "冗余", "分工", "共生", "平衡"],
         "creativity_weight": 4},
    ]
    
    METACOGNITION_CHALLENGES = [
        {"id": "MC1", "question": "思考策略", 
         "keywords": ["策略", "方法", "改进", "评估", "监控"]},
        {"id": "MC2", "question": "理解判断",
         "keywords": ["理解", "测试", "验证", "知道", "判断"]},
        {"id": "MC3", "question": "陌生问题",
         "keywords": ["分解", "搜索", "策略", "验证", "迭代"]},
    ]
    
    @classmethod
    def evaluate_transfer(cls, cid, answer):
        for c in cls.TRANSFER_CHALLENGES:
            if c["id"] == cid:
                ans_lower = answer.lower()
                matched = sum(1 for idea in c["transfer_ideas"] if idea in ans_lower)
                coverage = matched / len(c["transfer_ideas"])
                score = min(100, int(coverage * 50 + (len(answer) > 200) * 20 + c["creativity_weight"] * 5))
                return {"score": score, "coverage": f"{matched}/{len(c['transfer_ideas'])}"}
        return {"error": "not found"}
    
    @classmethod
    def evaluate_metacognition(cls, cid, answer):
        for c in cls.METACOGNITION_CHALLENGES:
            if c["id"] == cid:
                ans_lower = answer.lower()
                matched = sum(1 for kw in c["keywords"] if kw in ans_lower)
                coverage = matched / len(c["keywords"])
                score = min(100, int(coverage * 60 + (len(answer) > 100) * 20 + (matched >= 3) * 20))
                return {"score": score, "matched": matched, "total": len(c["keywords"])}
        return {"error": "not found"}

if __name__ == "__main__":
    print("Adaption Trainer v3.2 loaded")
