#!/usr/bin/env python3
"""
ClawShell Genome Evolution Tracker
知识进化追踪模块
版本: v0.2.0
功能: 知识版本管理、变更追踪、回滚支持
"""

import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    SPLIT = "split"
    RESTORE = "restore"


@dataclass
class Change:
    """变更记录"""
    id: str
    entity_id: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    parent_id: Optional[str] = None


@dataclass
class Version:
    """版本快照"""
    id: str
    entity_id: str
    version_number: int
    content: Any
    changes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    checksum: str = ""


@dataclass
class EvolutionBranch:
    """进化分支"""
    id: str
    name: str
    head_version_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    merged_at: Optional[float] = None
    parent_branch_id: Optional[str] = None


class EvolutionTracker:
    """
    知识进化追踪器
    
    功能：
    - 版本管理
    - 变更追踪
    - 分支管理
    - 回滚支持
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        
        # 变更记录
        self._changes: Dict[str, Change] = {}
        
        # 版本快照
        self._versions: Dict[str, Version] = {}
        
        # 实体版本历史
        self._entity_versions: Dict[str, List[str]] = {}
        
        # 分支
        self._branches: Dict[str, EvolutionBranch] = {}
        self._current_branch: str = "main"
        
        # 统计
        self._stats = {
            "total_changes": 0,
            "total_versions": 0,
            "total_branches": 1,
            "rollback_count": 0,
        }
        
        # 钩子函数
        self._pre_change_hooks: List[Callable] = []
        self._post_change_hooks: List[Callable] = []

    def register_pre_change_hook(self, hook: Callable[[Change], None]) -> None:
        """注册变更前钩子"""
        self._pre_change_hooks.append(hook)

    def register_post_change_hook(self, hook: Callable[[Change], None]) -> None:
        """注册变更后钩子"""
        self._post_change_hooks.append(hook)

    def _generate_id(self, prefix: str) -> str:
        """生成ID"""
        timestamp = str(time.time())
        hash_val = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"{prefix}_{timestamp}_{hash_val}"

    def _calculate_checksum(self, content: Any) -> str:
        """计算校验和"""
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def _execute_pre_hooks(self, change: Change) -> None:
        """执行变更前钩子"""
        for hook in self._pre_change_hooks:
            hook(change)

    def _execute_post_hooks(self, change: Change) -> None:
        """执行变更后钩子"""
        for hook in self._post_change_hooks:
            hook(change)

    def record_change(
        self,
        entity_id: str,
        change_type: ChangeType,
        old_value: Any = None,
        new_value: Any = None,
        metadata: Dict = None
    ) -> Change:
        """记录变更"""
        change = Change(
            id=self._generate_id("chg"),
            entity_id=entity_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {}
        )
        
        # 执行前钩子
        self._execute_pre_hooks(change)
        
        # 记录变更
        self._changes[change.id] = change
        self._stats["total_changes"] = len(self._changes)
        
        # 创建版本快照
        if change_type in [ChangeType.CREATE, ChangeType.UPDATE, ChangeType.RESTORE]:
            self.create_version(entity_id, new_value, change_id=change.id)
        
        # 执行后钩子
        self._execute_post_hooks(change)
        
        return change

    def create_version(
        self,
        entity_id: str,
        content: Any,
        change_id: Optional[str] = None
    ) -> Version:
        """创建版本快照"""
        # 获取当前版本号
        if entity_id in self._entity_versions:
            version_numbers = [self._versions[vid].version_number 
                              for vid in self._entity_versions[entity_id]]
            next_version = max(version_numbers) + 1
        else:
            next_version = 1
        
        version = Version(
            id=self._generate_id("ver"),
            entity_id=entity_id,
            version_number=next_version,
            content=content,
            changes=[change_id] if change_id else [],
            checksum=self._calculate_checksum(content)
        )
        
        self._versions[version.id] = version
        
        if entity_id not in self._entity_versions:
            self._entity_versions[entity_id] = []
        self._entity_versions[entity_id].append(version.id)
        
        self._stats["total_versions"] = len(self._versions)
        
        return version

    def get_version(self, version_id: str) -> Optional[Version]:
        """获取版本"""
        return self._versions.get(version_id)

    def get_entity_versions(self, entity_id: str) -> List[Version]:
        """获取实体的所有版本"""
        version_ids = self._entity_versions.get(entity_id, [])
        return [self._versions[vid] for vid in version_ids if vid in self._versions]

    def get_latest_version(self, entity_id: str) -> Optional[Version]:
        """获取最新版本"""
        versions = self.get_entity_versions(entity_id)
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)

    def rollback(self, entity_id: str, target_version: int) -> Optional[Version]:
        """回滚到指定版本"""
        versions = self.get_entity_versions(entity_id)
        
        target = None
        for v in versions:
            if v.version_number == target_version:
                target = v
                break
        
        if target is None:
            return None
        
        # 获取当前版本
        current = self.get_latest_version(entity_id)
        if current is None:
            return None
        
        # 记录回滚变更
        self.record_change(
            entity_id=entity_id,
            change_type=ChangeType.RESTORE,
            old_value=current.content,
            new_value=target.content,
            metadata={"rolled_back_from": current.version_number}
        )
        
        self._stats["rollback_count"] += 1
        
        return target

    def get_change_history(self, entity_id: str) -> List[Change]:
        """获取实体的变更历史"""
        entity_changes = []
        for change in self._changes.values():
            if change.entity_id == entity_id:
                entity_changes.append(change)
        return sorted(entity_changes, key=lambda c: c.timestamp)

    def create_branch(self, name: str, from_version_id: Optional[str] = None) -> EvolutionBranch:
        """创建分支"""
        branch = EvolutionBranch(
            id=self._generate_id("brn"),
            name=name,
            head_version_id=from_version_id,
            parent_branch_id=self._current_branch if from_version_id else None
        )
        
        self._branches[branch.id] = branch
        self._stats["total_branches"] = len(self._branches)
        
        return branch

    def switch_branch(self, branch_id: str) -> bool:
        """切换分支"""
        if branch_id in self._branches:
            self._current_branch = branch_id
            return True
        return False

    def merge_branch(self, source_branch_id: str, target_branch_id: Optional[str] = None) -> bool:
        """合并分支"""
        if target_branch_id is None:
            target_branch_id = self._current_branch
        
        source = self._branches.get(source_branch_id)
        target = self._branches.get(target_branch_id)
        
        if source is None or target is None:
            return False
        
        # 标记分支已合并
        source.merged_at = time.time()
        
        return True

    def diff_versions(self, version1_id: str, version2_id: str) -> Dict:
        """对比两个版本"""
        v1 = self._versions.get(version1_id)
        v2 = self._versions.get(version2_id)
        
        if v1 is None or v2 is None:
            return {"error": "Version not found"}
        
        return {
            "version1": {"id": v1.id, "version": v1.version_number, "checksum": v1.checksum},
            "version2": {"id": v2.id, "version": v2.version_number, "checksum": v2.checksum},
            "same_content": v1.checksum == v2.checksum,
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "current_branch": self._current_branch,
            "tracked_entities": len(self._entity_versions),
        }

    def get_entity_timeline(self, entity_id: str) -> List[Dict]:
        """获取实体的时间线"""
        versions = self.get_entity_versions(entity_id)
        changes = self.get_change_history(entity_id)
        
        events = []
        
        for v in versions:
            events.append({
                "type": "version",
                "id": v.id,
                "timestamp": v.created_at,
                "data": {"version_number": v.version_number, "checksum": v.checksum}
            })
        
        for c in changes:
            events.append({
                "type": "change",
                "id": c.id,
                "timestamp": c.timestamp,
                "data": {"change_type": c.change_type.value}
            })
        
        return sorted(events, key=lambda e: e["timestamp"])

    def export_history(self, entity_id: str) -> Dict:
        """导出实体的完整历史"""
        return {
            "entity_id": entity_id,
            "versions": [
                {"id": v.id, "version": v.version_number, "checksum": v.checksum, 
                 "created_at": v.created_at}
                for v in self.get_entity_versions(entity_id)
            ],
            "changes": [
                {"id": c.id, "type": c.change_type.value, "timestamp": c.timestamp,
                 "old_value": c.old_value, "new_value": c.new_value}
                for c in self.get_change_history(entity_id)
            ],
            "timeline": self.get_entity_timeline(entity_id)
        }


def create_evolution_tracker(persistence_path: Optional[str] = None) -> EvolutionTracker:
    """创建进化追踪器"""
    return EvolutionTracker(persistence_path)
