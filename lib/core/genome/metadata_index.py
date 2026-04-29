#!/usr/bin/env python3
"""
ClawShell Genome Metadata Index
元数据索引模块
版本: v0.2.0-A
功能: 元数据存储、索引构建、快速查询
"""

import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict


# ============ 数据结构 ============

@dataclass
class MetadataEntry:
    """元数据条目"""
    entry_id: str
    entity_id: str
    entity_type: str
    key: str
    value: Any
    value_type: str  # string, number, boolean, list, dict
    indexed: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class IndexEntry:
    """索引条目"""
    term: str
    entry_ids: List[str]
    count: int


# ============ 元数据索引 ============

class MetadataIndex:
    """
    元数据索引
    
    功能：
    - 元数据存储
    - 索引构建
    - 快速查询
    - 全文搜索
    
    使用示例：
        indexer = MetadataIndex()
        
        # 添加元数据
        indexer.add(entity_id, "author", "John")
        
        # 查询
        results = indexer.search("author", "John")
        
        # 范围查询
        results = indexer.range_query("count", min=10, max=100)
        
        # 获取实体的所有元数据
        all_meta = indexer.get_entity_metadata(entity_id)
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        
        # 元数据存储: entry_id -> MetadataEntry
        self._entries: Dict[str, MetadataEntry] = {}
        
        # 实体索引: entity_id -> [entry_ids]
        self._entity_index: Dict[str, List[str]] = defaultdict(list)
        
        # 倒排索引: key -> value -> [entry_ids]
        self._inverted_index: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        
        # 类型索引: entity_type -> [entry_ids]
        self._type_index: Dict[str, List[str]] = defaultdict(list)
        
        # 数字范围索引: key -> {value -> [entry_ids]}
        self._range_index: Dict[str, Dict[float, List[str]]] = defaultdict(dict)
        
        # 统计
        self._stats = {
            "total_entries": 0,
            "total_entities": 0,
            "query_count": 0,
            "index_build_time_ms": 0
        }
        
        self._load()

    def add(
        self,
        entity_id: str,
        entity_type: str,
        key: str,
        value: Any,
        indexed: bool = True
    ) -> MetadataEntry:
        """添加元数据"""
        entry_id = f"{entity_id}_{key}"
        
        # 判断类型
        value_type = self._get_value_type(value)
        
        entry = MetadataEntry(
            entry_id=entry_id,
            entity_id=entity_id,
            entity_type=entity_type,
            key=key,
            value=value,
            value_type=value_type,
            indexed=indexed
        )
        
        # 存储
        self._entries[entry_id] = entry
        
        # 更新索引
        self._entity_index[entity_id].append(entry_id)
        self._type_index[entity_type].append(entry_id)
        
        if indexed:
            self._add_to_inverted_index(entry)
        
        self._stats["total_entries"] += 1
        self._stats["total_entities"] = len(self._entity_index)
        
        self._save()
        return entry

    def update(self, entity_id: str, key: str, value: Any) -> bool:
        """更新元数据"""
        entry_id = f"{entity_id}_{key}"
        
        if entry_id not in self._entries:
            return False
        
        entry = self._entries[entry_id]
        
        # 移除旧索引
        if entry.indexed:
            self._remove_from_inverted_index(entry)
        
        # 更新
        entry.value = value
        entry.value_type = self._get_value_type(value)
        entry.updated_at = time.time()
        
        # 添加新索引
        if entry.indexed:
            self._add_to_inverted_index(entry)
        
        self._save()
        return True

    def get(self, entity_id: str, key: str) -> Optional[MetadataEntry]:
        """获取元数据"""
        entry_id = f"{entity_id}_{key}"
        return self._entries.get(entry_id)

    def get_entity_metadata(self, entity_id: str) -> List[MetadataEntry]:
        """获取实体的所有元数据"""
        entry_ids = self._entity_index.get(entity_id, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def search(self, key: str, value: str, limit: int = 100) -> List[MetadataEntry]:
        """搜索元数据"""
        self._stats["query_count"] += 1
        
        entry_ids = self._inverted_index.get(key, {}).get(str(value), [])
        results = [self._entries[eid] for eid in entry_ids[:limit] if eid in self._entries]
        
        return results

    def search_by_type(
        self,
        entity_type: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        limit: int = 100
    ) -> List[MetadataEntry]:
        """按类型搜索"""
        self._stats["query_count"] += 1
        
        entry_ids = self._type_index.get(entity_type, [])
        
        if key and value:
            entry_ids = [
                eid for eid in entry_ids
                if eid in self._entries
                and self._entries[eid].key == key
                and str(self._entries[eid].value) == str(value)
            ]
        
        return [self._entries[eid] for eid in entry_ids[:limit] if eid in self._entries]

    def range_query(
        self,
        key: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> List[MetadataEntry]:
        """范围查询"""
        self._stats["query_count"] += 1
        
        results = []
        
        for entry in self._entries.values():
            if entry.key != key or entry.value_type not in ("number", "integer"):
                continue
            
            try:
                num_value = float(entry.value)
                
                if min_value is not None and num_value < min_value:
                    continue
                if max_value is not None and num_value > max_value:
                    continue
                
                results.append(entry)
            except (ValueError, TypeError):
                continue
        
        return results

    def wildcard_search(self, key: str, pattern: str) -> List[MetadataEntry]:
        """通配符搜索"""
        self._stats["query_count"] += 1
        
        results = []
        pattern_lower = pattern.lower()
        
        for entry in self._entries.values():
            if entry.key != key:
                continue
            
            value_str = str(entry.value).lower()
            
            # 简单通配符：* 匹配任意
            if "*" in pattern_lower:
                import fnmatch
                if fnmatch.fnmatch(value_str, pattern_lower):
                    results.append(entry)
            elif pattern_lower in value_str:
                results.append(entry)
        
        return results

    def delete(self, entity_id: str, key: str) -> bool:
        """删除元数据"""
        entry_id = f"{entity_id}_{key}"
        
        if entry_id not in self._entries:
            return False
        
        entry = self._entries[entry_id]
        
        # 移除索引
        if entry.indexed:
            self._remove_from_inverted_index(entry)
        
        # 移除实体索引
        if entry_id in self._entity_index.get(entity_id, []):
            self._entity_index[entity_id].remove(entry_id)
        
        # 移除类型索引
        if entry_id in self._type_index.get(entry.entity_type, []):
            self._type_index[entry.entity_type].remove(entry_id)
        
        # 删除
        del self._entries[entry_id]
        
        self._save()
        return True

    def bulk_add(self, items: List[Dict]) -> int:
        """批量添加"""
        count = 0
        for item in items:
            try:
                self.add(
                    entity_id=item["entity_id"],
                    entity_type=item["entity_type"],
                    key=item["key"],
                    value=item["value"],
                    indexed=item.get("indexed", True)
                )
                count += 1
            except Exception as e:
                print(f"❌ Failed to add metadata: {e}")
        
        return count

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "unique_keys": len(self._inverted_index),
            "unique_types": len(self._type_index)
        }

    def rebuild_index(self):
        """重建索引"""
        start = time.time()
        
        # 清空索引
        self._entity_index.clear()
        self._type_index.clear()
        self._inverted_index.clear()
        
        # 重建
        for entry in self._entries.values():
            self._entity_index[entry.entity_id].append(entry.entry_id)
            self._type_index[entry.entity_type].append(entry.entry_id)
            
            if entry.indexed:
                self._add_to_inverted_index(entry)
        
        self._stats["index_build_time_ms"] = (time.time() - start) * 1000
        self._save()

    def _add_to_inverted_index(self, entry: MetadataEntry):
        """添加到倒排索引"""
        value_key = str(entry.value)
        self._inverted_index[entry.key][value_key].append(entry.entry_id)

    def _remove_from_inverted_index(self, entry: MetadataEntry):
        """从倒排索引移除"""
        value_key = str(entry.value)
        if entry.key in self._inverted_index:
            if value_key in self._inverted_index[entry.key]:
                try:
                    self._inverted_index[entry.key][value_key].remove(entry.entry_id)
                except ValueError:
                    pass

    def _get_value_type(self, value: Any) -> str:
        """获取值的类型"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, dict):
            return "dict"
        else:
            return "unknown"

    def _save(self):
        """保存数据"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "entries": {
                    k: v.__dict__
                    for k, v in self._entries.items()
                }
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Failed to save metadata index: {e}")

    def _load(self):
        """加载数据"""
        if not self.persistence_path:
            return
        
        try:
            with open(self.persistence_path) as f:
                data = json.load(f)
            
            for eid, edata in data.get("entries", {}).items():
                entry = MetadataEntry(**edata)
                self._entries[eid] = entry
                
                # 重建索引
                self._entity_index[entry.entity_id].append(eid)
                self._type_index[entry.entity_type].append(eid)
                
                if entry.indexed:
                    self._add_to_inverted_index(entry)
            
            self._stats["total_entries"] = len(self._entries)
            self._stats["total_entities"] = len(self._entity_index)
        except Exception as e:
            print(f"❌ Failed to load metadata index: {e}")


# ============ 便捷函数 ============

def create_metadata_index(persistence_path: Optional[str] = None) -> MetadataIndex:
    """创建元数据索引"""
    return MetadataIndex(persistence_path=persistence_path)
