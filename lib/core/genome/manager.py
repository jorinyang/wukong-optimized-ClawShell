"""
Genome Manager - ClawShell v0.1
==============================

基因组管理器。
负责基因组的加载、保存、版本管理和传承。
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from shutil import copy2

from .schema import Genome, AgentType, HeritageRecord

logger = logging.getLogger(__name__)


class GenomeManager:
    """
    基因组管理器
    =============
    
    负责：
    - 基因组的加载和保存
    - 版本管理
    - 传承协议执行
    - 与Obsidian同步
    
    使用示例：
        manager = GenomeManager()
        
        # 加载基因组
        genome = manager.load_genome(AgentType.OPENCLAW)
        
        # 添加知识
        genome.add_knowledge("user_preference", "detailed_report", category="preference")
        
        # 保存基因组
        manager.save_genome(genome)
        
        # 执行传承
        manager.heritage(AgentType.OPENCLAW, heritage_type="restart")
    """
    
    def __init__(
        self,
        base_path: str = "~/.real/genome",
        backup_path: str = "~/.real/backups/genome",
    ):
        self.base_path = Path(base_path).expanduser()
        self.backup_path = Path(backup_path).expanduser()
        
        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        # 传承记录
        self.heritage_log_path = self.base_path / "heritage_log.yaml"
        
        logger.info(f"GenomeManager initialized at {self.base_path}")
    
    def _get_genome_path(self, agent_type: AgentType) -> Path:
        """获取基因组文件路径"""
        if agent_type == AgentType.SHARED:
            return self.base_path / "shared" / "genome.yaml"
        return self.base_path / agent_type.value / "genome.yaml"
    
    def load_genome(self, agent_type: AgentType) -> Genome:
        """
        加载基因组
        
        Args:
            agent_type: Agent类型
        
        Returns:
            Genome对象，如果不存在则创建新的
        """
        path = self._get_genome_path(agent_type)
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                genome = Genome.from_dict(data)
                logger.info(f"Loaded genome for {agent_type.value} from {path}")
                return genome
            except Exception as e:
                logger.error(f"Failed to load genome from {path}: {e}")
                # 尝试加载备份
                return self._load_from_backup(agent_type)
        else:
            # 创建新的基因组
            logger.info(f"Creating new genome for {agent_type.value}")
            return self._create_new_genome(agent_type)
    
    def _load_from_backup(self, agent_type: AgentType) -> Optional[Genome]:
        """从备份加载"""
        backup_dir = self.backup_path / agent_type.value
        if not backup_dir.exists():
            logger.warning(f"No backup found for {agent_type.value}")
            return self._create_new_genome(agent_type)
        
        # 找到最新的备份
        backups = sorted(backup_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            try:
                with open(backups[0], 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                logger.info(f"Loaded genome from backup: {backups[0]}")
                return Genome.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load backup: {e}")
        
        return self._create_new_genome(agent_type)
    
    def _create_new_genome(self, agent_type: AgentType) -> Genome:
        """创建新的基因组"""
        return Genome(
            agent_type=agent_type,
            version="0.1.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
    
    def save_genome(self, genome: Genome, create_backup: bool = True) -> bool:
        """
        保存基因组
        
        Args:
            genome: Genome对象
            create_backup: 是否创建备份
        
        Returns:
            是否保存成功
        """
        path = self._get_genome_path(genome.agent_type)
        
        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 先写临时文件
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(genome.to_yaml())
            
            # 原子性替换
            temp_path.replace(path)
            
            logger.info(f"Saved genome for {genome.agent_type.value} to {path}")
            
            # 创建备份
            if create_backup:
                self._create_backup(genome)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save genome: {e}")
            return False
    
    def _create_backup(self, genome: Genome) -> None:
        """创建备份"""
        try:
            backup_dir = self.backup_path / genome.agent_type.value
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"genome_{genome.version}_{timestamp}.yaml"
            backup_path = backup_dir / backup_name
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(genome.to_yaml())
            
            logger.info(f"Created backup: {backup_path}")
            
            # 保留最近10个备份
            backups = sorted(backup_dir.glob("genome_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_backup in backups[10:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
    
    def heritage(
        self,
        agent_type: AgentType,
        heritage_type: str = "restart",
        notes: str = None,
    ) -> HeritageRecord:
        """
        执行传承协议
        
        当Agent重启/升级时，保存当前状态到新版本，
        并记录传承历史。
        
        Args:
            agent_type: Agent类型
            heritage_type: 传承类型 (restart/upgrade/migration)
            notes: 备注
        
        Returns:
            HeritageRecord传承记录
        """
        # 加载当前基因组
        old_genome = self.load_genome(agent_type)
        
        # 创建传承记录
        record = HeritageRecord(
            from_version=old_genome.version,
            to_version=self._bump_version(old_genome.version),
            heritage_type=heritage_type,
            knowledge_transferred=len(old_genome.knowledge),
            errors_transferred=len(old_genome.error_patterns),
            skills_transferred=len(old_genome.skills),
            notes=notes,
        )
        
        # 更新基因组版本
        old_genome.version = record.to_version
        old_genome.updated_at = datetime.now().isoformat()
        
        # 保存
        self.save_genome(old_genome)
        
        # 记录传承日志
        self._append_heritage_log(record)
        
        logger.info(f"Heritage completed: {record.from_version} -> {record.to_version}")
        
        return record
    
    def _bump_version(self, version: str) -> str:
        """版本号递增"""
        parts = version.split('.')
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return '.'.join(parts)
    
    def _append_heritage_log(self, record: HeritageRecord) -> None:
        """追加传承日志"""
        try:
            logs = []
            if self.heritage_log_path.exists():
                with open(self.heritage_log_path, 'r', encoding='utf-8') as f:
                    logs = yaml.safe_load(f) or []
            
            logs.append(record.to_dict())
            
            with open(self.heritage_log_path, 'w', encoding='utf-8') as f:
                yaml.dump(logs, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to append heritage log: {e}")
    
    def get_heritage_log(self, agent_type: AgentType = None) -> List[HeritageRecord]:
        """获取传承日志"""
        if not self.heritage_log_path.exists():
            return []
        
        try:
            with open(self.heritage_log_path, 'r', encoding='utf-8') as f:
                logs = yaml.safe_load(f) or []
            
            if agent_type:
                # 按agent类型过滤（需要从笔记中推断）
                pass
            
            return [HeritageRecord(**log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to read heritage log: {e}")
            return []
    
    def add_knowledge(
        self,
        agent_type: AgentType,
        key: str,
        value: Any,
        category: str = "general",
        source: str = None,
        confidence: float = 1.0,
    ) -> bool:
        """快速添加知识"""
        genome = self.load_genome(agent_type)
        genome.add_knowledge(key, value, category, source, confidence)
        return self.save_genome(genome)
    
    def add_error_pattern(
        self,
        agent_type: AgentType,
        error_type: str,
        description: str,
        solution: str,
        tags: List[str] = None,
    ) -> bool:
        """快速添加错误模式"""
        genome = self.load_genome(agent_type)
        genome.add_error_pattern(error_type, description, solution, tags)
        return self.save_genome(genome)
    
    def find_error_solution(self, agent_type: AgentType, error_type: str) -> Optional[str]:
        """查找错误解决方案"""
        genome = self.load_genome(agent_type)
        return genome.find_error_solution(error_type)
    
    def evolve(
        self,
        agent_type: AgentType,
        changes: List[str],
        improvements: List[str] = None,
        notes: str = None,
    ) -> bool:
        """记录进化"""
        genome = self.load_genome(agent_type)
        genome.record_evolution(
            version=self._bump_version(genome.version),
            changes=changes,
            improvements=improvements,
            notes=notes,
        )
        return self.save_genome(genome)
    
    def get_stats(self, agent_type: AgentType) -> Dict:
        """获取基因组统计"""
        genome = self.load_genome(agent_type)
        return {
            "agent_type": agent_type.value,
            "version": genome.version,
            "knowledge_count": len(genome.knowledge),
            "error_patterns_count": len(genome.error_patterns),
            "skills_count": len(genome.skills),
            "evolution_count": len(genome.evolution),
            "last_updated": genome.updated_at,
        }


# 全局单例
_genome_manager: Optional[GenomeManager] = None


def get_genome_manager() -> GenomeManager:
    """获取全局基因组管理器实例"""
    global _genome_manager
    if _genome_manager is None:
        _genome_manager = GenomeManager()
    return _genome_manager
