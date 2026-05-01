#!/usr/bin/env python3
"""
Auto Trigger - 自动触发模式
支持手动/自动模式切换，置信度阈值配置，用户确认机制

功能：
1. 模式切换（手动/自动/半自动）
2. 置信度阈值配置
3. 高风险操作前确认
4. 反馈收集
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path("~/.real/logs/auto_trigger.log").expanduser()),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AutoTriggerConfig:
    """自动触发配置"""
    
    def __init__(self):
        self.config_file = Path("~/.real/.auto_trigger_config.json").expanduser()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        default_config = {
            "mode": "manual",  # manual, auto, semi
            "auto_threshold": 0.8,
            "semi_threshold": 0.7,
            "require_confirmation_for": ["delete", "exec", "write"],
            "feedback_collection": True,
            "last_updated": datetime.now().isoformat()
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
        
        return default_config
    
    def save(self):
        """保存配置"""
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
        self.save()


class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self):
        self.feedback_file = Path("~/.real/logs/skill_feedback.jsonl").expanduser()
    
    def collect(self, skill_name: str, user_input: str, 
                result: Dict[str, Any], user_feedback: Optional[str] = None) -> bool:
        """收集反馈"""
        try:
            feedback = {
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "user_input": user_input,
                "result": result,
                "user_feedback": user_feedback,
                "auto_collected": user_feedback is None
            }
            
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback, ensure_ascii=False) + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"收集反馈失败: {e}")
            return False
    
    def get_stats(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """获取反馈统计"""
        try:
            if not self.feedback_file.exists():
                return {"total": 0, "positive": 0, "negative": 0}
            
            total = 0
            positive = 0
            negative = 0
            
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback = json.loads(line.strip())
                        if skill_name and feedback.get("skill") != skill_name:
                            continue
                        
                        total += 1
                        user_fb = feedback.get("user_feedback", "")
                        if user_fb and ("好" in user_fb or "good" in user_fb.lower() or "成功" in user_fb):
                            positive += 1
                        elif user_fb and ("差" in user_fb or "bad" in user_fb.lower() or "失败" in user_fb):
                            negative += 1
                            
                    except json.JSONDecodeError:
                        continue
            
            return {
                "total": total,
                "positive": positive,
                "negative": negative,
                "neutral": total - positive - negative
            }
            
        except Exception as e:
            logger.error(f"获取反馈统计失败: {e}")
            return {"total": 0, "positive": 0, "negative": 0}


class AutoTrigger:
    """自动触发管理器"""
    
    def __init__(self):
        self.config = AutoTriggerConfig()
        self.feedback = FeedbackCollector()
    
    def should_auto_execute(self, skill_name: str, confidence: float) -> bool:
        """是否应该自动执行"""
        mode = self.config.get("mode", "manual")
        
        if mode == "manual":
            # 手动模式：从不自动执行
            return False
        
        elif mode == "auto":
            # 自动模式：达到阈值即可
            threshold = self.config.get("auto_threshold", 0.8)
            return confidence >= threshold
        
        elif mode == "semi":
            # 半自动模式：高置信度自动，中等置信度询问
            auto_threshold = self.config.get("auto_threshold", 0.8)
            semi_threshold = self.config.get("semi_threshold", 0.7)
            
            if confidence >= auto_threshold:
                return True
            elif confidence >= semi_threshold:
                # 半自动模式下中等置信度需要确认
                return False
            else:
                return False
        
        return False
    
    def requires_confirmation(self, skill_name: str, action_type: str) -> bool:
        """是否需要用户确认"""
        require_list = self.config.get("require_confirmation_for", [])
        return action_type in require_list
    
    def process(self, skill_name: str, user_input: str, 
                confidence: float, action_type: str = "general") -> Dict[str, Any]:
        """处理技能触发决策"""
        result = {
            "skill": skill_name,
            "confidence": confidence,
            "mode": self.config.get("mode"),
            "auto_execute": False,
            "requires_confirmation": False,
            "can_proceed": False
        }
        
        # 检查是否自动执行
        if self.should_auto_execute(skill_name, confidence):
            # 检查是否需要确认（高风险操作）
            if self.requires_confirmation(skill_name, action_type):
                result["requires_confirmation"] = True
                result["can_proceed"] = False
                result["reason"] = "high_risk_action"
            else:
                result["auto_execute"] = True
                result["can_proceed"] = True
        else:
            # 未达到自动执行阈值，需要确认
            result["requires_confirmation"] = True
            result["can_proceed"] = False
            result["reason"] = "confidence_below_threshold"
        
        return result
    
    def record_result(self, skill_name: str, user_input: str, 
                     execution_result: Dict[str, Any], user_feedback: Optional[str] = None):
        """记录执行结果"""
        self.feedback.collect(skill_name, user_input, execution_result, user_feedback)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "mode": self.config.get("mode"),
            "auto_threshold": self.config.get("auto_threshold"),
            "semi_threshold": self.config.get("semi_threshold"),
            "require_confirmation_for": self.config.get("require_confirmation_for"),
            "feedback_collection": self.config.get("feedback_collection"),
            "feedback_stats": self.feedback.get_stats()
        }
    
    def set_mode(self, mode: str):
        """设置模式"""
        valid_modes = ["manual", "auto", "semi"]
        if mode in valid_modes:
            self.config.set("mode", mode)
            logger.info(f"模式已切换为: {mode}")
        else:
            raise ValueError(f"无效模式: {mode}. 有效值: {valid_modes}")
    
    def set_threshold(self, threshold_type: str, value: float):
        """设置阈值"""
        if not 0 <= value <= 1:
            raise ValueError("阈值必须在 0-1 之间")
        
        if threshold_type == "auto":
            self.config.set("auto_threshold", value)
        elif threshold_type == "semi":
            self.config.set("semi_threshold", value)
        else:
            raise ValueError(f"无效阈值类型: {threshold_type}")


def main():
    """主函数"""
    auto_trigger = AutoTrigger()
    
    if len(sys.argv) < 2:
        # 显示当前配置
        print(json.dumps(auto_trigger.get_config_summary(), ensure_ascii=False, indent=2))
        return
    
    command = sys.argv[1]
    
    if command == "mode":
        if len(sys.argv) >= 3:
            auto_trigger.set_mode(sys.argv[2])
            print(f"模式已设置为: {sys.argv[2]}")
        else:
            print(f"当前模式: {auto_trigger.config.get('mode')}")
    
    elif command == "threshold":
        if len(sys.argv) >= 4:
            auto_trigger.set_threshold(sys.argv[2], float(sys.argv[3]))
            print(f"阈值已设置: {sys.argv[2]} = {sys.argv[3]}")
        else:
            print(f"自动阈值: {auto_trigger.config.get('auto_threshold')}")
            print(f"半自动阈值: {auto_trigger.config.get('semi_threshold')}")
    
    elif command == "test":
        # 测试决策逻辑
        if len(sys.argv) >= 4:
            skill = sys.argv[2]
            confidence = float(sys.argv[3])
            result = auto_trigger.process(skill, "test input", confidence)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print("用法:")
        print("  auto_trigger.py mode [manual|auto|semi]")
        print("  auto_trigger.py threshold [auto|semi] <value>")
        print("  auto_trigger.py test <skill> <confidence>")


if __name__ == "__main__":
    main()
