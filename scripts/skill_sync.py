#!/usr/bin/env python3
"""
OpenClaw Skill Sync - 技能同步器
负责轮询检测 Hermes 生成的技能并注册到 OpenClaw

功能：
1. 扫描 ~/.hermes/skills/generated/ 目录
2. 检测新技能文件
3. 解析 SKILL.md 文件
4. 注册到 OpenClaw 技能系统
5. 处理技能更新和冲突
"""

import os
import sys
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path("~/.openclaw/logs/skill_sync.log").expanduser()),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SkillSync:
    """技能同步器"""
    
    def __init__(self):
        self.hermes_skills_dir = Path("~/.hermes/skills/generated").expanduser()
        self.openclaw_skills_dir = Path("~/.openclaw/skills").expanduser()
        self.sync_state_file = Path("~/.openclaw/.skill_sync_state.json").expanduser()
        self.conflicts_dir = Path("~/.openclaw/skills/conflicts").expanduser()
        
        # 确保目录存在
        self.hermes_skills_dir.mkdir(parents=True, exist_ok=True)
        self.openclaw_skills_dir.mkdir(parents=True, exist_ok=True)
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载同步状态
        self.sync_state = self._load_sync_state()
    
    def _load_sync_state(self) -> Dict[str, Any]:
        """加载同步状态"""
        if self.sync_state_file.exists():
            try:
                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载同步状态失败: {e}")
        return {"synced_skills": {}, "last_sync": None}
    
    def _save_sync_state(self):
        """保存同步状态"""
        try:
            with open(self.sync_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.sync_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同步状态失败: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return ""
    
    def _parse_skill_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """解析 SKILL.md 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据
            skill_info = {
                "name": "",
                "description": "",
                "version": "1.0.0",
                "confidence": 0.0,
                "pattern": {},
                "content": content
            }
            
            # 解析文件名作为技能名
            skill_info["name"] = file_path.stem
            
            # 提取置信度（从文件内容或文件名）
            if "confidence" in content.lower():
                import re
                match = re.search(r'confidence[:\s]+([\d.]+)', content, re.IGNORECASE)
                if match:
                    skill_info["confidence"] = float(match.group(1))
            
            # 提取描述（第一个段落）
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    skill_info["description"] = line[:200]
                    break
            
            return skill_info
            
        except Exception as e:
            logger.error(f"解析技能文件失败 {file_path}: {e}")
            return None
    
    def _detect_conflict(self, skill_name: str, new_skill: Dict[str, Any]) -> Optional[Path]:
        """检测技能冲突"""
        # 检查 OpenClaw 技能目录
        existing_skill = self.openclaw_skills_dir / f"{skill_name}.md"
        if existing_skill.exists():
            return existing_skill
        
        # 检查 Hermes 技能目录（是否已存在不同版本）
        hermes_existing = self.hermes_skills_dir / f"{skill_name}.md"
        if hermes_existing.exists():
            old_hash = self.sync_state["synced_skills"].get(skill_name, {}).get("hash", "")
            new_hash = self._calculate_file_hash(hermes_existing)
            if old_hash and old_hash != new_hash:
                return hermes_existing
        
        return None
    
    def _handle_conflict(self, skill_name: str, new_file: Path, existing_file: Path) -> bool:
        """处理技能冲突"""
        try:
            logger.warning(f"检测到技能冲突: {skill_name}")
            
            # 将冲突文件移动到冲突目录
            conflict_file = self.conflicts_dir / f"{skill_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            shutil.copy2(existing_file, conflict_file)
            
            # 记录冲突
            conflict_record = {
                "skill_name": skill_name,
                "new_file": str(new_file),
                "existing_file": str(existing_file),
                "conflict_file": str(conflict_file),
                "timestamp": datetime.now().isoformat(),
                "resolution": "merged"
            }
            
            # 保存冲突记录
            conflict_log = self.conflicts_dir / "conflicts.json"
            conflicts = []
            if conflict_log.exists():
                with open(conflict_log, 'r', encoding='utf-8') as f:
                    conflicts = json.load(f)
            conflicts.append(conflict_record)
            with open(conflict_log, 'w', encoding='utf-8') as f:
                json.dump(conflicts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"冲突已记录到: {conflict_log}")
            return True
            
        except Exception as e:
            logger.error(f"处理冲突失败: {e}")
            return False
    
    def _register_skill(self, skill_info: Dict[str, Any], source_file: Path) -> bool:
        """注册技能到 OpenClaw"""
        try:
            skill_name = skill_info["name"]
            target_file = self.openclaw_skills_dir / f"{skill_name}.md"
            
            # 检测冲突
            existing = self._detect_conflict(skill_name, skill_info)
            if existing:
                if not self._handle_conflict(skill_name, source_file, existing):
                    return False
            
            # 复制技能文件
            shutil.copy2(source_file, target_file)
            
            # 创建技能元数据
            metadata = {
                "name": skill_name,
                "description": skill_info["description"],
                "version": skill_info["version"],
                "confidence": skill_info["confidence"],
                "source": "hermes",
                "source_file": str(source_file),
                "registered_at": datetime.now().isoformat(),
                "enabled": True,
                "trigger_count": 0,
                "success_count": 0
            }
            
            # 保存元数据
            metadata_file = self.openclaw_skills_dir / f"{skill_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"技能已注册: {skill_name} (置信度: {skill_info['confidence']})")
            return True
            
        except Exception as e:
            logger.error(f"注册技能失败: {e}")
            return False
    
    def sync(self) -> Dict[str, Any]:
        """执行同步"""
        logger.info("=== 开始技能同步 ===")
        
        result = {
            "synced": 0,
            "updated": 0,
            "conflicts": 0,
            "failed": 0,
            "skills": []
        }
        
        try:
            # 扫描 Hermes 技能目录
            skill_files = list(self.hermes_skills_dir.glob("*.md"))
            logger.info(f"发现 {len(skill_files)} 个技能文件")
            
            for skill_file in skill_files:
                try:
                    skill_name = skill_file.stem
                    file_hash = self._calculate_file_hash(skill_file)
                    
                    # 检查是否已同步
                    if skill_name in self.sync_state["synced_skills"]:
                        old_hash = self.sync_state["synced_skills"][skill_name].get("hash", "")
                        if old_hash == file_hash:
                            logger.debug(f"技能未变化，跳过: {skill_name}")
                            continue
                        else:
                            logger.info(f"技能已更新: {skill_name}")
                    
                    # 解析技能文件
                    skill_info = self._parse_skill_file(skill_file)
                    if not skill_info:
                        result["failed"] += 1
                        continue
                    
                    # 注册技能
                    if self._register_skill(skill_info, skill_file):
                        if skill_name in self.sync_state["synced_skills"]:
                            result["updated"] += 1
                        else:
                            result["synced"] += 1
                        
                        # 更新同步状态
                        self.sync_state["synced_skills"][skill_name] = {
                            "hash": file_hash,
                            "synced_at": datetime.now().isoformat(),
                            "confidence": skill_info["confidence"]
                        }
                        result["skills"].append(skill_name)
                    else:
                        result["failed"] += 1
                        
                except Exception as e:
                    logger.error(f"处理技能文件失败 {skill_file}: {e}")
                    result["failed"] += 1
            
            # 保存同步状态
            self.sync_state["last_sync"] = datetime.now().isoformat()
            self._save_sync_state()
            
            logger.info(f"=== 同步完成: 新增 {result['synced']}, 更新 {result['updated']}, 冲突 {result['conflicts']}, 失败 {result['failed']} ===")
            return result
            
        except Exception as e:
            logger.error(f"同步过程出错: {e}")
            return result


def main():
    """主函数"""
    sync = SkillSync()
    result = sync.sync()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["failed"] == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
