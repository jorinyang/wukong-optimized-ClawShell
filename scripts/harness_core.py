#!/usr/bin/env python3
"""
Harness Core - 统一触发引擎
整合了trigger_engine和auto_trigger的功能

功能：
1. 触发条件匹配（解析SKILL.md）
2. 自动/手动模式切换
3. 技能执行
4. 反馈收集
"""

import os
import sys
import json
import re
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# 配置
OPENCLAW_DIR = Path(os.path.expanduser("~/.real"))
SKILLS_DIR = OPENCLAW_DIR / "workspace" / "skills"
CONFIG_FILE = OPENCLAW_DIR / ".auto_trigger_config.json"
FEEDBACK_FILE = OPENCLAW_DIR / "logs" / "skill_feedback.jsonl"


class TriggerCondition:
    """触发条件"""
    
    def __init__(self, condition_type: str, pattern: str, weight: float = 1.0):
        self.type = condition_type  # keyword, regex, semantic
        self.pattern = pattern
        self.weight = weight
    
    def match(self, text: str) -> float:
        """匹配文本，返回置信度 0-1"""
        text_lower = text.lower()
        
        if self.type == "keyword":
            keywords = [k.strip().lower() for k in self.pattern.split(",")]
            valid_keywords = [k for k in keywords if len(k) >= 2 or any('\u4e00' <= c <= '\u9fff' for c in k)]
            if not valid_keywords:
                return 0.0
            matched = sum(1 for k in valid_keywords if k in text_lower)
            return self.weight if matched > 0 else 0.0
        
        elif self.type == "regex":
            try:
                if re.search(self.pattern, text_lower):
                    return self.weight
            except:
                pass
        return 0.0


class HarnessConfig:
    """Harness配置"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "mode": "auto",  # manual, auto, semi
            "auto_threshold": 0.8,
            "semi_threshold": 0.7,
            "require_confirmation_for": ["delete", "exec", "write"],
            "feedback_collection": True,
            "last_updated": datetime.now().isoformat()
        }
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Config load error: {e}")
        
        return default_config
    
    def save(self):
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()


class SkillTrigger:
    """技能触发器"""
    
    def __init__(self, skill_path: Path):
        self.path = skill_path
        self.name = skill_path.stem
        self.conditions: List[TriggerCondition] = []
        self.description = ""
        self.load_skill_md()
    
    def load_skill_md(self):
        """解析SKILL.md获取触发条件"""
        skill_md = self.path / "SKILL.md"
        if not skill_md.exists():
            return
        
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取描述
            desc_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if desc_match:
                self.description = desc_match.group(1).strip()
            
            # 提取所有文本作为关键词来源
            # 移除markdown格式符
            text = re.sub(r'[#*`\-\[\]]', ' ', content).lower()
            # 提取有意义的词（长度>=3）
            words = re.findall(r'\b[a-z\u4e00-\u9fff]{3,}\b', text)
            # 去重
            seen = set()
            for word in words:
                if word not in seen and word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'use', 'using', 'with', 'this', 'that', 'from', 'have', 'more', 'they', 'will', 'would', 'there', 'could', 'other']:
                    seen.add(word)
                    self.conditions.append(TriggerCondition("keyword", word, 0.5))
                        
        except Exception as e:
            print(f"Error loading skill {self.name}: {e}")
    
    def match(self, text: str) -> float:
        """计算匹配置信度"""
        if not self.conditions:
            return 0.0
        return max(c.match(text) for c in self.conditions)


class HarnessCore:
    """统一触发引擎核心"""
    
    def __init__(self):
        self.config = HarnessConfig()
        self.skills: Dict[str, SkillTrigger] = {}
        self.load_skills()
    
    def load_skills(self):
        """加载所有技能"""
        if not SKILLS_DIR.exists():
            return
        
        for skill_path in SKILLS_DIR.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill = SkillTrigger(skill_path)
                if skill.conditions:
                    self.skills[skill.name] = skill
    
    def match_trigger(self, text: str) -> List[Tuple[str, float]]:
        """匹配触发条件，返回[(skill_name, confidence)]"""
        results = []
        for name, skill in self.skills.items():
            confidence = skill.match(text)
            if confidence > 0:
                results.append((name, confidence))
        
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def get_recommendation(self, text: str) -> Optional[Dict[str, Any]]:
        """获取技能推荐"""
        matches = self.match_trigger(text)
        
        if not matches:
            return None
        
        top_skill, confidence = matches[0]
        
        # 根据模式决定是否需要确认
        mode = self.config.get("mode", "auto")
        threshold = self.config.get(f"{mode}_threshold", 0.8)
        
        need_confirmation = confidence < threshold
        
        # 检查是否需要高风险确认
        high_risk_keywords = self.config.get("require_confirmation_for", [])
        risk_level = "high" if any(k in text.lower() for k in high_risk_keywords) else "normal"
        
        return {
            "skill": top_skill,
            "confidence": confidence,
            "mode": mode,
            "threshold": threshold,
            "need_confirmation": need_confirmation,
            "risk_level": risk_level,
            "all_matches": matches[:5]
        }
    
    def execute_skill(self, skill_name: str) -> Dict[str, Any]:
        """执行技能（返回执行信息）"""
        return {
            "status": "ready",
            "skill": skill_name,
            "message": f"Skill {skill_name} ready for execution"
        }
    
    def collect_feedback(self, skill_name: str, user_input: str, 
                        result: Dict[str, Any], user_feedback: Optional[str] = None) -> bool:
        """收集反馈"""
        if not self.config.get("feedback_collection", True):
            return False
        
        try:
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            feedback = {
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "user_input": user_input,
                "result": result,
                "user_feedback": user_feedback,
                "auto_collected": user_feedback is None
            }
            
            with open(FEEDBACK_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback, ensure_ascii=False) + "\n")
            
            return True
        except Exception as e:
            print(f"Feedback collection error: {e}")
            return False


def main():
    if len(sys.argv) < 2:
        print("Harness Core - 统一触发引擎")
        print("用法:")
        print("  harness_core.py match <文本>")
        print("  harness_core.py recommend <文本>")
        print("  harness_core.py list")
        print("  harness_core.py mode [auto|semi|manual]")
        return
    
    command = sys.argv[1]
    harness = HarnessCore()
    
    if command == "match":
        if len(sys.argv) < 3:
            print("Usage: harness_core.py match <文本>")
            return
        text = sys.argv[2]
        matches = harness.match_trigger(text)
        print(f"Matches ({len(matches)}):")
        for name, conf in matches[:10]:
            print(f"  {name}: {conf:.2f}")
    
    elif command == "recommend":
        if len(sys.argv) < 3:
            print("Usage: harness_core.py recommend <文本>")
            return
        text = sys.argv[2]
        rec = harness.get_recommendation(text)
        if rec:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
        else:
            print("No matching skill found")
    
    elif command == "list":
        print(f"Loaded skills ({len(harness.skills)}):")
        for name in sorted(harness.skills.keys()):
            skill = harness.skills[name]
            print(f"  {name}: {len(skill.conditions)} conditions")
    
    elif command == "mode":
        if len(sys.argv) < 3:
            print(f"Current mode: {harness.config.get('mode')}")
        else:
            new_mode = sys.argv[2]
            harness.config.set("mode", new_mode)
            print(f"Mode set to: {new_mode}")


if __name__ == "__main__":
    main()
