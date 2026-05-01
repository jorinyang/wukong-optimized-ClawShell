#!/usr/bin/env python3
"""
Skill Optimizer - 技能持续优化器
负责技能效果评估、自动优化建议、技能废弃和A/B测试

功能：
1. 技能效果统计（使用频率、成功率）
2. 自动优化建议生成
3. 低使用率技能归档
4. A/B测试框架
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path("~/.real/logs/skill_optimizer.log").expanduser()),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SkillOptimizer:
    """技能优化器"""
    
    def __init__(self):
        self.skills_dir = Path("~/.real/skills").expanduser()
        self.archive_dir = Path("~/.real/skills/archived").expanduser()
        self.ab_test_dir = Path("~/.real/skills/ab_tests").expanduser()
        self.feedback_file = Path("~/.real/logs/skill_feedback.jsonl").expanduser()
        
        # 确保目录存在
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.ab_test_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_skill_stats(self, skill_name: str) -> Dict[str, Any]:
        """获取技能统计"""
        try:
            metadata_file = self.skills_dir / f"{skill_name}.json"
            if not metadata_file.exists():
                return {"error": "技能不存在"}
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return {
                "name": skill_name,
                "trigger_count": metadata.get("trigger_count", 0),
                "success_count": metadata.get("success_count", 0),
                "confidence": metadata.get("confidence", 0),
                "registered_at": metadata.get("registered_at"),
                "success_rate": metadata.get("success_count", 0) / metadata.get("trigger_count", 1) if metadata.get("trigger_count", 0) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取技能统计失败: {e}")
            return {"error": str(e)}
    
    def get_all_skills_stats(self) -> List[Dict[str, Any]]:
        """获取所有技能统计"""
        stats = []
        try:
            metadata_files = list(self.skills_dir.glob("*.json"))
            for meta_file in metadata_files:
                skill_name = meta_file.stem
                stat = self._get_skill_stats(skill_name)
                if "error" not in stat:
                    stats.append(stat)
            
            # 按触发次数排序
            stats.sort(key=lambda x: x.get("trigger_count", 0), reverse=True)
            return stats
            
        except Exception as e:
            logger.error(f"获取所有技能统计失败: {e}")
            return []
    
    def generate_optimization_suggestions(self, skill_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []
        
        try:
            if skill_name:
                # 单个技能优化建议
                stat = self._get_skill_stats(skill_name)
                if "error" in stat:
                    return []
                
                success_rate = stat.get("success_rate", 0)
                trigger_count = stat.get("trigger_count", 0)
                
                if trigger_count >= 5 and success_rate < 0.5:
                    suggestions.append({
                        "skill": skill_name,
                        "type": "low_success_rate",
                        "severity": "high",
                        "message": f"成功率仅 {success_rate*100:.1f}%，建议优化触发条件或执行逻辑",
                        "action": "review_and_improve"
                    })
                
                if trigger_count > 0 and trigger_count < 3:
                    suggestions.append({
                        "skill": skill_name,
                        "type": "low_usage",
                        "severity": "medium",
                        "message": f"仅触发 {trigger_count} 次，建议优化触发关键词提高匹配率",
                        "action": "optimize_triggers"
                    })
            else:
                # 全局优化建议
                all_stats = self.get_all_skills_stats()
                
                # 找出低使用率技能
                low_usage = [s for s in all_stats if s.get("trigger_count", 0) < 3]
                if low_usage:
                    suggestions.append({
                        "type": "global_low_usage",
                        "severity": "info",
                        "message": f"有 {len(low_usage)} 个技能使用率较低",
                        "skills": [s["name"] for s in low_usage],
                        "action": "review_or_archive"
                    })
                
                # 找出低成功率技能
                low_success = [s for s in all_stats if s.get("trigger_count", 0) >= 5 and s.get("success_rate", 1) < 0.5]
                if low_success:
                    suggestions.append({
                        "type": "global_low_success",
                        "severity": "high",
                        "message": f"有 {len(low_success)} 个技能成功率低于50%",
                        "skills": [s["name"] for s in low_success],
                        "action": "urgent_review"
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return []
    
    def archive_skill(self, skill_name: str, reason: str = "low_usage") -> bool:
        """归档技能"""
        try:
            skill_file = self.skills_dir / f"{skill_name}.md"
            meta_file = self.skills_dir / f"{skill_name}.json"
            
            if not skill_file.exists():
                logger.warning(f"技能不存在: {skill_name}")
                return False
            
            # 移动文件到归档目录
            archive_skill = self.archive_dir / f"{skill_name}.md"
            archive_meta = self.archive_dir / f"{skill_name}.json"
            
            shutil.move(str(skill_file), str(archive_skill))
            if meta_file.exists():
                # 更新元数据
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                metadata["archived"] = True
                metadata["archive_reason"] = reason
                metadata["archived_at"] = datetime.now().isoformat()
                with open(archive_meta, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                meta_file.unlink()
            
            logger.info(f"技能已归档: {skill_name} (原因: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"归档技能失败: {e}")
            return False
    
    def create_ab_test(self, original_skill: str, variant_skill: str, 
                       test_duration_days: int = 7) -> Optional[str]:
        """创建A/B测试"""
        try:
            test_id = f"ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            test_config = {
                "test_id": test_id,
                "original_skill": original_skill,
                "variant_skill": variant_skill,
                "created_at": datetime.now().isoformat(),
                "duration_days": test_duration_days,
                "end_at": (datetime.now() + timedelta(days=test_duration_days)).isoformat(),
                "status": "active",
                "original_triggers": 0,
                "original_success": 0,
                "variant_triggers": 0,
                "variant_success": 0
            }
            
            test_file = self.ab_test_dir / f"{test_id}.json"
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"A/B测试已创建: {test_id}")
            return test_id
            
        except Exception as e:
            logger.error(f"创建A/B测试失败: {e}")
            return None
    
    def get_ab_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """获取A/B测试结果"""
        try:
            test_file = self.ab_test_dir / f"{test_id}.json"
            if not test_file.exists():
                return None
            
            with open(test_file, 'r', encoding='utf-8') as f:
                test = json.load(f)
            
            # 计算成功率
            orig_rate = test.get("original_success", 0) / test.get("original_triggers", 1) if test.get("original_triggers", 0) > 0 else 0
            var_rate = test.get("variant_success", 0) / test.get("variant_triggers", 1) if test.get("variant_triggers", 0) > 0 else 0
            
            return {
                "test_id": test_id,
                "original": {
                    "triggers": test.get("original_triggers", 0),
                    "success": test.get("original_success", 0),
                    "success_rate": orig_rate
                },
                "variant": {
                    "triggers": test.get("variant_triggers", 0),
                    "success": test.get("variant_success", 0),
                    "success_rate": var_rate
                },
                "winner": "variant" if var_rate > orig_rate else "original" if orig_rate > var_rate else "tie",
                "status": test.get("status")
            }
            
        except Exception as e:
            logger.error(f"获取A/B测试结果失败: {e}")
            return None
    
    def auto_cleanup(self, min_trigger_count: int = 3, min_success_rate: float = 0.3) -> Dict[str, Any]:
        """自动清理"""
        result = {
            "archived": [],
            "suggested": [],
            "skipped": []
        }
        
        try:
            all_stats = self.get_all_skills_stats()
            
            for stat in all_stats:
                skill_name = stat["name"]
                trigger_count = stat.get("trigger_count", 0)
                success_rate = stat.get("success_rate", 0)
                
                # 低使用率且低成功率
                if trigger_count >= 5 and success_rate < min_success_rate:
                    if self.archive_skill(skill_name, "low_success_rate"):
                        result["archived"].append(skill_name)
                
                # 极低使用率
                elif trigger_count == 0:
                    result["suggested"].append({
                        "skill": skill_name,
                        "reason": "从未被触发",
                        "suggested_action": "review_or_archive"
                    })
                
                else:
                    result["skipped"].append(skill_name)
            
            logger.info(f"自动清理完成: 归档 {len(result['archived'])}, 建议 {len(result['suggested'])}, 保留 {len(result['skipped'])}")
            return result
            
        except Exception as e:
            logger.error(f"自动清理失败: {e}")
            return result


def main():
    """主函数"""
    optimizer = SkillOptimizer()
    
    if len(sys.argv) < 2:
        # 显示所有技能统计
        stats = optimizer.get_all_skills_stats()
        print(json.dumps({"skills": stats}, ensure_ascii=False, indent=2))
        return
    
    command = sys.argv[1]
    
    if command == "stats":
        stats = optimizer.get_all_skills_stats()
        print(json.dumps({"skills": stats}, ensure_ascii=False, indent=2))
    
    elif command == "suggest":
        skill = sys.argv[2] if len(sys.argv) > 2 else None
        suggestions = optimizer.generate_optimization_suggestions(skill)
        print(json.dumps({"suggestions": suggestions}, ensure_ascii=False, indent=2))
    
    elif command == "archive":
        if len(sys.argv) > 2:
            success = optimizer.archive_skill(sys.argv[2])
            print(json.dumps({"success": success}, ensure_ascii=False, indent=2))
    
    elif command == "cleanup":
        result = optimizer.auto_cleanup()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == "abtest":
        if len(sys.argv) >= 4:
            test_id = optimizer.create_ab_test(sys.argv[2], sys.argv[3])
            print(json.dumps({"test_id": test_id}, ensure_ascii=False, indent=2))
        elif len(sys.argv) > 2:
            results = optimizer.get_ab_test_results(sys.argv[2])
            print(json.dumps(results, ensure_ascii=False, indent=2))
    
    else:
        print("用法:")
        print("  skill_optimizer.py stats")
        print("  skill_optimizer.py suggest [skill_name]")
        print("  skill_optimizer.py archive <skill_name>")
        print("  skill_optimizer.py cleanup")
        print("  skill_optimizer.py abtest <original> <variant>")
        print("  skill_optimizer.py abtest <test_id>")


if __name__ == "__main__":
    main()
