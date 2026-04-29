#!/usr/bin/env python3
"""
Speed Training Module
处理速度专项训练
"""

import random
import time

class SpeedTraining:
    
    CHALLENGES = [
        {
            "code": "O(n) to O(1) optimization",
            "issue": "Unnecessary loop iteration",
            "fix": "Use direct calculation",
            "points": 10
        },
        {
            "code": "O(n^2) list operation", 
            "issue": "Repeated list search",
            "fix": "Use set for O(1) lookup",
            "points": 15
        },
        {
            "code": "Nested loop optimization",
            "issue": "Redundant iteration",
            "fix": "Use list comprehension",
            "points": 20
        }
    ]
    
    @classmethod
    def train(cls, duration: int = 60) -> dict:
        start = time.time()
        score = 0
        completed = 0
        
        challenges = random.sample(cls.CHALLENGES, min(5, len(cls.CHALLENGES)))
        results = []
        
        for c in challenges:
            if time.time() - start > duration:
                break
            results.append({"issue": c["issue"], "fix": c["fix"], "points": c["points"]})
            score += c["points"]
            completed += 1
        
        elapsed = time.time() - start
        
        return {
            "completed": completed,
            "score": score,
            "elapsed": elapsed,
            "speed_score": min(100, (score / elapsed) * 10) if elapsed > 0 else 0
        }

if __name__ == "__main__":
    result = SpeedTraining.train(60)
    print(f"Completed: {result['completed']}, Score: {result['score']}, Speed: {result['speed_score']:.1f}")
