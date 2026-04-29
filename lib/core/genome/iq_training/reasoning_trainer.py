#!/usr/bin/env python3
"""
Reasoning Trainer v2.0
形式化推理专项训练 - 强化版
"""

class ReasoningTrainer:
    """形式化推理训练"""
    
    PROBLEMS = [
        {
            "id": "LP1",
            "problem": "证明: 如果P→Q和Q→R成立，则P→R成立",
            "key_points": ["modus ponens", "conditional proof"],
            "max_score": 20
        },
        {
            "id": "LP2", 
            "problem": "分析悖论: '这句话是假的' 是否构成悖论?",
            "key_points": ["self-reference", "truth paradox", "contradiction"],
            "max_score": 25
        },
        {
            "id": "LP3",
            "problem": "用形式化方法证明: 任意有限集合的幂集基数大于原集合",
            "key_points": ["power set", "cardinality", "induction"],
            "max_score": 30
        },
        {
            "id": "LP4",
            "problem": "分析: 归纳法为什么是有效的证明方法? 它依赖于什么假设?",
            "key_points": ["induction base", "inductive step", "well-ordering"],
            "max_score": 25
        },
        {
            "id": "LP5",
            "problem": "解释哥德尔不完备性定理的核心思想及其对数学基础的影响",
            "key_points": ["consistency", "completeness", "self-reference", "Godel numbering"],
            "max_score": 30
        }
    ]
    
    @classmethod
    def evaluate(cls, problem_id: str, answer: str) -> dict:
        for p in cls.PROBLEMS:
            if p["id"] == problem_id:
                score = 0
                matched = []
                answer_lower = answer.lower()
                
                for kp in p["key_points"]:
                    if kp.lower() in answer_lower:
                        score += p["max_score"] // len(p["key_points"])
                        matched.append(kp)
                
                # 额外检查：答案长度是否足够详细
                if len(answer) > 200:
                    score = min(score + 5, p["max_score"])
                
                return {
                    "problem_id": problem_id,
                    "score": min(score, p["max_score"]),
                    "max_score": p["max_score"],
                    "matched": matched,
                    "answer_length": len(answer)
                }
        return {"error": "Problem not found"}

if __name__ == "__main__":
    # 测试所有问题
    total = 0
    for p in ReasoningTrainer.PROBLEMS:
        result = ReasoningTrainer.evaluate(p["id"], "detailed answer with " + " ".join(p["key_points"]))
        print(f"{p['id']}: {result['score']}/{result['max_score']}")
        total += result["score"]
    print(f"Total: {total}/{sum(p['max_score'] for p in ReasoningTrainer.PROBLEMS)}")
