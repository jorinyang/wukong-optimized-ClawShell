"""
Heritage Protocol - ClawShell v0.1
==================================

代际传承协议。
实现Agent升级/重启时的知识传递。
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from .schema import Genome, AgentType, HeritageRecord
from .manager import GenomeManager

logger = logging.getLogger(__name__)


class HeritageProtocol:
    """
    传承协议
    =========
    
    定义Agent在以下情况时的传承行为：
    - 重启 (restart)
    - 升级 (upgrade)
    - 迁移 (migration)
    
    核心原则：
    1. 每次传承都携带前任的全部知识
    2. 传承后生成新的版本号
    3. 传承历史永久记录
    
    使用示例：
        protocol = HeritageProtocol()
        
        # 初始化（首次启动）
        protocol.initialize(AgentType.OPENCLAW)
        
        # 传承（重启/升级时）
        record = protocol.heritage(
            agent_type=AgentType.OPENCLAW,
            heritage_type="restart",
        )
        
        # 查询传承历史
        history = protocol.get_heritage_history()
    """
    
    def __init__(self, manager: GenomeManager = None):
        self.manager = manager or GenomeManager()
    
    def initialize(self, agent_type: AgentType) -> Genome:
        """
        初始化基因组（首次启动）
        
        Args:
            agent_type: Agent类型
        
        Returns:
            新创建的Genome对象
        """
        genome = self.manager.load_genome(agent_type)
        
        if not genome.knowledge:
            # 首次初始化，添加基础信息
            genome.add_knowledge(
                key="system",
                value="ClawShell v0.1",
                category="system",
                source="initialization",
            )
            genome.add_knowledge(
                key="initialized_at",
                value=datetime.now().isoformat(),
                category="system",
            )
            
            self.manager.save_genome(genome)
            logger.info(f"Initialized genome for {agent_type.value}")
        
        return genome
    
    def heritage(
        self,
        agent_type: AgentType,
        heritage_type: str = "restart",
        notes: str = None,
    ) -> HeritageRecord:
        """
        执行传承
        
        Args:
            agent_type: Agent类型
            heritage_type: 传承类型
            notes: 备注
        
        Returns:
            HeritageRecord传承记录
        """
        # 检查是否有未完成的pending_issues
        genome = self.manager.load_genome(agent_type)
        
        if genome.pending_issues:
            logger.warning(
                f"Heritage with pending issues: {genome.pending_issues}. "
                f"Consider resolving before heritage."
            )
        
        # 执行传承
        record = self.manager.heritage(
            agent_type=agent_type,
            heritage_type=heritage_type,
            notes=notes,
        )
        
        logger.info(
            f"Heritage completed for {agent_type.value}: "
            f"{record.from_version} -> {record.to_version}"
        )
        
        return record
    
    def get_heritage_history(
        self,
        agent_type: AgentType = None,
        limit: int = 10,
    ) -> List[HeritageRecord]:
        """
        获取传承历史
        
        Args:
            agent_type: 可选，按Agent类型过滤
            limit: 返回数量限制
        
        Returns:
            传承记录列表
        """
        return self.manager.get_heritage_log(agent_type)[-limit:]
    
    def check_genome_health(self, agent_type: AgentType) -> Dict[str, Any]:
        """
        检查基因组健康状态
        
        Args:
            agent_type: Agent类型
        
        Returns:
            健康检查结果
        """
        genome = self.manager.load_genome(agent_type)
        
        issues = []
        
        # 检查知识数量
        if len(genome.knowledge) == 0:
            issues.append("No knowledge entries")
        
        # 检查更新时间
        last_updated = datetime.fromisoformat(genome.updated_at)
        hours_since_update = (datetime.now() - last_updated).total_seconds() / 3600
        if hours_since_update > 24:
            issues.append(f"Genome not updated in {hours_since_update:.1f} hours")
        
        # 检查版本
        if genome.version == "0.1.0":
            issues.append("Genome never evolved beyond initial version")
        
        return {
            "agent_type": agent_type.value,
            "version": genome.version,
            "knowledge_count": len(genome.knowledge),
            "error_patterns_count": len(genome.error_patterns),
            "skills_count": len(genome.skills),
            "last_updated": genome.updated_at,
            "issues": issues,
            "healthy": len(issues) == 0,
        }
    
    def suggest_improvements(self, agent_type: AgentType) -> List[str]:
        """
        基于当前状态建议改进
        
        Args:
            agent_type: Agent类型
        
        Returns:
            改进建议列表
        """
        genome = self.manager.load_genome(agent_type)
        suggestions = []
        
        # 知识数量建议
        if len(genome.knowledge) < 10:
            suggestions.append(
                "Consider adding more knowledge entries to improve context retention"
            )
        
        # 错误模式建议
        if len(genome.error_patterns) < 5:
            suggestions.append(
                "Consider adding error patterns to improve error handling"
            )
        
        # 技能状态建议
        if not genome.skills:
            suggestions.append(
                "Consider tracking skill states for better performance monitoring"
            )
        
        # 进化历史建议
        if len(genome.evolution) == 0:
            suggestions.append(
                "No evolution records yet. Consider running evolve() after significant changes"
            )
        
        return suggestions


class GenomeComparator:
    """
    基因组比较器
    ============
    
    比较两个基因组的差异，用于传承前的检查。
    """
    
    @staticmethod
    def compare(genome1: Genome, genome2: Genome) -> Dict[str, Any]:
        """
        比较两个基因组
        
        Args:
            genome1: 当前基因组
            genome2: 目标基因组
        
        Returns:
            差异报告
        """
        return {
            "version_diff": GenomeComparator._compare_versions(
                genome1.version, genome2.version
            ),
            "knowledge_diff": {
                "added": len(genome2.knowledge) - len(genome1.knowledge),
                "current": len(genome1.knowledge),
                "target": len(genome2.knowledge),
            },
            "error_patterns_diff": {
                "added": len(genome2.error_patterns) - len(genome1.error_patterns),
                "current": len(genome1.error_patterns),
                "target": len(genome2.error_patterns),
            },
            "skills_diff": {
                "added": len(genome2.skills) - len(genome1.skills),
                "current": len(genome1.skills),
                "target": len(genome2.skills),
            },
        }
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> str:
        """比较版本号"""
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        
        if parts1 < parts2:
            return "downgrade"
        elif parts1 > parts2:
            return "upgrade"
        return "same"
