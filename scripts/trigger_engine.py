#!/usr/bin/env python3
"""
Trigger Engine - 触发引擎
负责解析用户指令，匹配技能触发条件，执行技能

功能：
1. 解析 SKILL.md 中的触发条件
2. 意图匹配（关键词、正则、语义相似度）
3. 上下文注入
4. 执行技能
5. 记录触发日志
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path("~/.openclaw/logs/trigger_engine.log").expanduser()),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


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
            # 关键词匹配（改进：中英文分开处理）
            keywords = [k.strip().lower() for k in self.pattern.split(",")]
            # 过滤掉太短的英文词（避免误判）
            valid_keywords = [k for k in keywords if len(k) >= 2 or any('\u4e00' <= c <= '\u9fff' for c in k)]
            if not valid_keywords:
                return 0.0
            matched = sum(1 for k in valid_keywords if k in text_lower)
            # 只要匹配任意关键词即返回权重
            return self.weight if matched > 0 else 0.0
        
        elif self.type == "regex":
            # 正则匹配
            try:
                if re.search(self.pattern, text, re.IGNORECASE):
                    return 1.0 * self.weight
            except re.error:
                pass
            return 0.0
        
        elif self.type == "semantic":
            # 语义相似度（简化版：计算共同词汇比例）
            text_words = set(text_lower.split())
            pattern_words = set(self.pattern.lower().split())
            if pattern_words:
                similarity = len(text_words & pattern_words) / len(pattern_words)
                return similarity * self.weight
            return 0.0
        
        return 0.0


class SkillTrigger:
    """技能触发器"""
    
    def __init__(self, skill_name: str, metadata: Dict[str, Any]):
        self.name = skill_name
        self.metadata = metadata
        self.conditions: List[TriggerCondition] = []
        self._parse_conditions()
    
    def _parse_conditions(self):
        """从元数据解析触发条件"""
        # 从 triggers 配置读取
        triggers = self.metadata.get("triggers", {})
        keywords = triggers.get("keywords", [])
        
        if keywords:
            self.conditions.append(TriggerCondition("keyword", ", ".join(keywords), 1.0))
        
        # 从描述中提取关键词作为备选
        description = self.metadata.get("description", "")
        if description and not keywords:
            words = [w for w in description.lower().split() if len(w) > 2]
            if words:
                keywords_str = ", ".join(words[:3])
                self.conditions.append(TriggerCondition("keyword", keywords_str, 0.8))
        
        # 从技能名称创建条件
        name_parts = self.name.replace("_", " ").split()
        if name_parts:
            self.conditions.append(TriggerCondition("keyword", ", ".join(name_parts), 0.6))
    
    def match(self, user_input: str) -> Tuple[bool, float]:
        """匹配用户输入"""
        scores = [cond.match(user_input) for cond in self.conditions]
        max_score = max(scores) if scores else 0.0
        
        # 阈值：0.5
        return max_score >= 0.5, max_score


class TriggerEngine:
    """触发引擎"""
    
    def __init__(self):
        self.skills_dir = Path("~/.openclaw/skills").expanduser()
        self.trigger_log_file = Path("~/.openclaw/logs/trigger_events.jsonl").expanduser()
        self.skills: Dict[str, SkillTrigger] = {}
        
        # 加载技能
        self._load_skills()
    
    def _load_skills(self):
        """加载所有已注册的技能"""
        try:
            metadata_files = list(self.skills_dir.glob("*.json"))
            logger.info(f"加载 {len(metadata_files)} 个技能")
            
            for meta_file in metadata_files:
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    if metadata.get("enabled", True):
                        skill_name = metadata["name"]
                        self.skills[skill_name] = SkillTrigger(skill_name, metadata)
                        
                except Exception as e:
                    logger.error(f"加载技能失败 {meta_file}: {e}")
            
            logger.info(f"成功加载 {len(self.skills)} 个可用技能")
            
        except Exception as e:
            logger.error(f"加载技能出错: {e}")
    
    def _log_trigger_event(self, user_input: str, matched_skill: Optional[str], 
                          confidence: float, executed: bool, result: Dict[str, Any]):
        """记录触发事件"""
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "matched_skill": matched_skill,
                "confidence": confidence,
                "executed": executed,
                "result": result
            }
            
            with open(self.trigger_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"记录触发事件失败: {e}")
    
    def _update_skill_stats(self, skill_name: str, success: bool):
        """更新技能统计"""
        try:
            metadata_file = self.skills_dir / f"{skill_name}.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata["trigger_count"] = metadata.get("trigger_count", 0) + 1
                if success:
                    metadata["success_count"] = metadata.get("success_count", 0) + 1
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"更新技能统计失败: {e}")
    
    def _execute_skill(self, skill_name: str, user_input: str) -> Dict[str, Any]:
        """执行技能（简化版）"""
        try:
            # 读取技能文件
            skill_file = self.skills_dir / f"{skill_name}.md"
            if not skill_file.exists():
                return {"success": False, "error": "技能文件不存在"}
            
            with open(skill_file, 'r', encoding='utf-8') as f:
                skill_content = f.read()
            
            # 这里应该调用实际的技能执行逻辑
            # 简化版：返回技能内容摘要
            return {
                "success": True,
                "skill": skill_name,
                "action": "triggered",
                "summary": skill_content[:200] + "..." if len(skill_content) > 200 else skill_content
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process(self, user_input: str, auto_execute: bool = False) -> Dict[str, Any]:
        """处理用户输入"""
        logger.info(f"处理输入: {user_input[:50]}...")
        
        result = {
            "matched": False,
            "skill": None,
            "confidence": 0.0,
            "executed": False,
            "output": None
        }
        
        try:
            # 匹配技能
            best_match = None
            best_confidence = 0.0
            
            for skill_name, trigger in self.skills.items():
                matched, confidence = trigger.match(user_input)
                if matched and confidence > best_confidence:
                    best_match = skill_name
                    best_confidence = confidence
            
            if best_match:
                result["matched"] = True
                result["skill"] = best_match
                result["confidence"] = best_confidence
                
                logger.info(f"匹配技能: {best_match} (置信度: {best_confidence:.2f})")
                
                # 是否自动执行
                if auto_execute and best_confidence >= 0.7:
                    execution_result = self._execute_skill(best_match, user_input)
                    result["executed"] = execution_result["success"]
                    result["output"] = execution_result
                    
                    # 更新统计
                    self._update_skill_stats(best_match, execution_result["success"])
                else:
                    result["output"] = {"action": "matched_but_not_executed", "requires_confirmation": True}
            else:
                logger.info("未匹配到任何技能")
            
            # 记录事件
            self._log_trigger_event(user_input, best_match, best_confidence, 
                                   result["executed"], result.get("output", {}))
            
            return result
            
        except Exception as e:
            logger.error(f"处理输入出错: {e}")
            result["error"] = str(e)
            return result
    
    def get_skill_list(self) -> List[Dict[str, Any]]:
        """获取技能列表"""
        skills = []
        for skill_name, trigger in self.skills.items():
            skills.append({
                "name": skill_name,
                "description": trigger.metadata.get("description", ""),
                "confidence": trigger.metadata.get("confidence", 0),
                "enabled": trigger.metadata.get("enabled", True)
            })
        return skills


def main():
    """主函数"""
    engine = TriggerEngine()
    
    # 测试模式
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        result = engine.process(user_input, auto_execute=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 列出技能
        skills = engine.get_skill_list()
        print(json.dumps({"skills": skills}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
