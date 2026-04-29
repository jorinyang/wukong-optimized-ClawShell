#!/usr/bin/env python3
"""
ClawShell Genome Version Manager
版本管理模块
版本: v0.2.0-A
功能: 基因版本追踪、版本对比、回滚机制
"""

import time
import hashlib
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


# ============ 数据结构 ============

@dataclass
class GeneVersion:
    """基因版本"""
    version_id: str
    gene_id: str
    version_number: int
    content_hash: str
    content: Dict[str, Any]
    changes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"
    message: str = ""


@dataclass
class VersionDiff:
    """版本差异"""
    version_id: str
    previous_version_id: str
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)


@dataclass
class RollbackPoint:
    """回滚点"""
    checkpoint_id: str
    gene_id: str
    version_id: str
    timestamp: float
    snapshot: Dict[str, Any]


# ============ 版本管理器 ============

class VersionManager:
    """
    版本管理器
    
    功能：
    - 基因版本追踪
    - 版本对比
    - 回滚机制
    - 版本历史
    
    使用示例：
        vm = VersionManager()
        
        # 创建版本
        version = vm.create_version("gene1", {"data": "value"}, "Initial version")
        
        # 更新版本
        vm.update_version("gene1", {"data": "new_value"}, "Update data")
        
        # 获取历史
        history = vm.get_history("gene1")
        
        # 回滚
        vm.rollback("gene1", version_id)
        
        # 对比版本
        diff = vm.diff("gene1", v1_id, v2_id)
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        
        # 基因版本存储: gene_id -> [versions]
        self._versions: Dict[str, List[GeneVersion]] = {}
        
        # 回滚点存储
        self._rollback_points: Dict[str, RollbackPoint] = {}
        
        # 当前版本指针: gene_id -> version_id
        self._current_versions: Dict[str, str] = {}
        
        # 统计数据
        self._stats = {
            "total_versions": 0,
            "total_genes": 0,
            "total_rollbacks": 0,
            "checkpoints_created": 0
        }
        
        self._load()

    def create_version(
        self,
        gene_id: str,
        content: Dict[str, Any],
        message: str = "",
        created_by: str = "system"
    ) -> GeneVersion:
        """创建版本"""
        # 获取下一个版本号
        versions = self._versions.get(gene_id, [])
        next_version = len(versions) + 1
        
        # 计算内容hash
        content_hash = self._compute_hash(content)
        
        # 创建版本
        version = GeneVersion(
            version_id=f"{gene_id}_v{next_version}",
            gene_id=gene_id,
            version_number=next_version,
            content_hash=content_hash,
            content=content,
            created_by=created_by,
            message=message
        )
        
        # 存储
        if gene_id not in self._versions:
            self._versions[gene_id] = []
        self._versions[gene_id].append(version)
        
        # 更新当前版本指针
        self._current_versions[gene_id] = version.version_id
        
        self._stats["total_versions"] += 1
        self._stats["total_genes"] = len(self._versions)
        
        self._save()
        return version

    def update_version(
        self,
        gene_id: str,
        content: Dict[str, Any],
        message: str = "",
        created_by: str = "system"
    ) -> Optional[GeneVersion]:
        """更新版本（创建新版本）"""
        if gene_id not in self._versions:
            return self.create_version(gene_id, content, message, created_by)
        
        # 检测是否有变化
        current = self.get_current_version(gene_id)
        if current and self._compute_hash(current.content) == self._compute_hash(content):
            return current  # 无变化
        
        return self.create_version(gene_id, content, message, created_by)

    def get_version(self, gene_id: str, version_id: str) -> Optional[GeneVersion]:
        """获取指定版本"""
        versions = self._versions.get(gene_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    def get_current_version(self, gene_id: str) -> Optional[GeneVersion]:
        """获取当前版本"""
        version_id = self._current_versions.get(gene_id)
        if version_id:
            return self.get_version(gene_id, version_id)
        
        versions = self._versions.get(gene_id, [])
        return versions[-1] if versions else None

    def get_history(
        self,
        gene_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[GeneVersion]:
        """获取版本历史"""
        versions = self._versions.get(gene_id, [])
        return versions[offset:offset + limit]

    def diff(
        self,
        gene_id: str,
        version_id1: str,
        version_id2: str
    ) -> Optional[VersionDiff]:
        """对比两个版本"""
        v1 = self.get_version(gene_id, version_id1)
        v2 = self.get_version(gene_id, version_id2)
        
        if not v1 or not v2:
            return None
        
        # 简单key对比
        keys1 = set(v1.content.keys())
        keys2 = set(v2.content.keys())
        
        return VersionDiff(
            version_id=v2.version_id,
            previous_version_id=v1.version_id,
            added=list(keys2 - keys1),
            removed=list(keys1 - keys2),
            modified=[k for k in keys1 & keys2 if v1.content[k] != v2.content[k]],
            unchanged=[k for k in keys1 & keys2 if v1.content[k] == v2.content[k]]
        )

    def create_checkpoint(self, gene_id: str) -> RollbackPoint:
        """创建检查点"""
        version = self.get_current_version(gene_id)
        if not version:
            raise ValueError(f"No version found for gene {gene_id}")
        
        checkpoint = RollbackPoint(
            checkpoint_id=f"cp_{gene_id}_{int(time.time())}",
            gene_id=gene_id,
            version_id=version.version_id,
            timestamp=time.time(),
            snapshot=version.content.copy()
        )
        
        self._rollback_points[checkpoint.checkpoint_id] = checkpoint
        self._stats["checkpoints_created"] += 1
        
        self._save()
        return checkpoint

    def rollback(
        self,
        gene_id: str,
        version_id: str
    ) -> bool:
        """回滚到指定版本"""
        version = self.get_version(gene_id, version_id)
        if not version:
            return False
        
        # 创建当前版本的检查点（以防万一）
        current = self.get_current_version(gene_id)
        if current and current.version_id != version_id:
            self.create_checkpoint(gene_id)
        
        # 更新指针
        self._current_versions[gene_id] = version_id
        
        self._stats["total_rollbacks"] += 1
        self._save()
        
        return True

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """回滚到检查点"""
        checkpoint = self._rollback_points.get(checkpoint_id)
        if not checkpoint:
            return False
        
        return self.rollback(checkpoint.gene_id, checkpoint.version_id)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[RollbackPoint]:
        """获取检查点"""
        return self._rollback_points.get(checkpoint_id)

    def list_checkpoints(self, gene_id: str) -> List[RollbackPoint]:
        """列出基因的所有检查点"""
        return [
            cp for cp in self._rollback_points.values()
            if cp.gene_id == gene_id
        ]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "total_versions": self._stats["total_versions"],
            "total_genes": self._stats["total_genes"],
            "total_checkpoints": len(self._rollback_points)
        }

    def _compute_hash(self, content: Dict[str, Any]) -> str:
        """计算内容hash"""
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _save(self):
        """保存数据"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "versions": {
                    k: [v.__dict__ for v in vs]
                    for k, vs in self._versions.items()
                },
                "current_versions": self._current_versions,
                "rollback_points": {
                    k: v.__dict__
                    for k, v in self._rollback_points.items()
                }
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Failed to save version manager: {e}")

    def _load(self):
        """加载数据"""
        if not self.persistence_path:
            return
        
        try:
            with open(self.persistence_path) as f:
                data = json.load(f)
            
            self._versions = {
                k: [GeneVersion(**v) for v in vs]
                for k, vs in data.get("versions", {}).items()
            }
            self._current_versions = data.get("current_versions", {})
            self._rollback_points = {
                k: RollbackPoint(**v)
                for k, v in data.get("rollback_points", {}).items()
            }
            
            self._stats["total_versions"] = sum(len(vs) for vs in self._versions.values())
            self._stats["total_genes"] = len(self._versions)
        except Exception as e:
            print(f"❌ Failed to load version manager: {e}")


# ============ 便捷函数 ============

def create_version_manager(persistence_path: Optional[str] = None) -> VersionManager:
    """创建版本管理器"""
    return VersionManager(persistence_path=persistence_path)
