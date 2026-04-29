#!/usr/bin/env python3
"""
ClawShell Genome Knowledge Graph
知识图谱模块
版本: v0.2.0-A
功能: 实体关系管理、知识推理、图谱可视化
"""

import time
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


# ============ 数据结构 ============

@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    entity_type: str              # concept, task, skill, memory, etc.
    properties: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Relation:
    """关系"""
    id: str
    source_id: str
    target_id: str
    relation_type: str           # is_a, part_of, depends_on, related_to, etc.
    weight: float = 1.0          # 关系权重
    properties: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphQuery:
    """图谱查询结果"""
    entities: List[Entity]
    relations: List[Relation]
    paths: List[List[str]]        # 路径
    depth: int


# ============ 知识图谱 ============

class KnowledgeGraph:
    """
    知识图谱
    
    功能：
    - 实体管理
    - 关系管理
    - 知识推理
    - 路径查询
    
    使用示例：
        kg = KnowledgeGraph()
        
        # 添加实体
        entity = kg.add_entity("openclaw", "concept", {"domain": "AI"})
        
        # 添加关系
        kg.add_relation("openclaw", "hermes", "integrates_with")
        
        # 查询
        results = kg.query(start="openclaw", depth=2)
        
        # 推理
        inferred = kg.infer("openclaw")
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path
        
        # 实体存储
        self._entities: Dict[str, Entity] = {}
        
        # 关系存储
        self._relations: Dict[str, Relation] = {}
        
        # 索引
        self._entity_index: Dict[str, Set[str]] = defaultdict(set)  # type -> entity_ids
        self._relation_index: Dict[Tuple[str, str], Set[str]] = defaultdict(set)  # (source, target) -> relation_ids
        
        # 反向索引
        self._incoming_relations: Dict[str, Set[str]] = defaultdict(set)  # target_id -> relation_ids
        self._outgoing_relations: Dict[str, Set[str]] = defaultdict(set)  # source_id -> relation_ids
        
        # 统计
        self._stats = {
            "total_entities": 0,
            "total_relations": 0,
            "query_count": 0,
            "inference_count": 0
        }
        
        # 加载已有数据
        self._load()

    def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[Dict] = None,
        entity_id: Optional[str] = None
    ) -> Entity:
        """添加实体"""
        entity_id = entity_id or self._generate_id("entity")
        
        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            metadata={}
        )
        
        self._entities[entity_id] = entity
        self._entity_index[entity_type].add(entity_id)
        
        self._stats["total_entities"] += 1
        self._save()
        
        return entity

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        properties: Optional[Dict] = None,
        relation_id: Optional[str] = None
    ) -> Optional[Relation]:
        """添加关系"""
        if source_id not in self._entities or target_id not in self._entities:
            return None
        
        relation_id = relation_id or self._generate_id("relation")
        
        relation = Relation(
            id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            properties=properties or {}
        )
        
        self._relations[relation_id] = relation
        self._relation_index[(source_id, target_id)].add(relation_id)
        self._outgoing_relations[source_id].add(relation_id)
        self._incoming_relations[target_id].add(relation_id)
        
        self._stats["total_relations"] += 1
        self._save()
        
        return relation

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self._entities.get(entity_id)

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        """获取关系"""
        return self._relations.get(relation_id)

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """按类型获取实体"""
        entity_ids = self._entity_index.get(entity_type, set())
        return [self._entities[eid] for eid in entity_ids if eid in self._entities]

    def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "both"  # outgoing, incoming, both
    ) -> List[Tuple[Entity, Relation]]:
        """获取邻居节点"""
        results = []
        
        if direction in ("outgoing", "both"):
            for rel_id in self._outgoing_relations.get(entity_id, set()):
                rel = self._relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    target = self._entities.get(rel.target_id)
                    if target:
                        results.append((target, rel))
        
        if direction in ("incoming", "both"):
            for rel_id in self._incoming_relations.get(entity_id, set()):
                rel = self._relations.get(rel_id)
                if rel and (relation_type is None or rel.relation_type == relation_type):
                    source = self._entities.get(rel.source_id)
                    if source:
                        results.append((source, rel))
        
        return results

    def query(
        self,
        start_id: str,
        depth: int = 2,
        relation_type: Optional[str] = None
    ) -> GraphQuery:
        """查询图谱"""
        self._stats["query_count"] += 1
        
        visited: Set[str] = set()
        entities: List[Entity] = []
        relations: List[Relation] = []
        paths: List[List[str]] = []
        
        def dfs(current_id: str, path: List[str], current_depth: int):
            if current_depth > depth or current_id in visited:
                return
            
            visited.add(current_id)
            path = path + [current_id]
            
            entity = self._entities.get(current_id)
            if entity:
                entities.append(entity)
            
            for neighbor, rel in self.get_neighbors(current_id, relation_type, "outgoing"):
                if rel not in relations:
                    relations.append(rel)
                
                if current_depth < depth:
                    dfs(neighbor.id, path, current_depth + 1)
            
            if path:
                paths.append(path)
        
        dfs(start_id, [], 0)
        
        return GraphQuery(
            entities=entities,
            relations=relations,
            paths=paths,
            depth=depth
        )

    def infer(self, entity_id: str) -> List[Tuple[Entity, str, float]]:
        """
        知识推理
        
        Returns:
            List of (inferred_entity, inference_type, confidence)
        """
        self._stats["inference_count"] += 1
        
        inferences = []
        entity = self._entities.get(entity_id)
        if not entity:
            return inferences
        
        # 1. 传递性推理: A->B, B->C => A->C
        for neighbor, rel in self.get_neighbors(entity_id, direction="outgoing"):
            for sub_neighbor, sub_rel in self.get_neighbors(neighbor.id, direction="outgoing"):
                inferred_type = f"transitive:{rel.relation_type}->{sub_rel.relation_type}"
                confidence = rel.weight * sub_rel.weight
                inferences.append((sub_neighbor, inferred_type, confidence))
        
        # 2. 对称性推理: A->B => B->A
        for neighbor, rel in self.get_neighbors(entity_id, direction="outgoing"):
            if rel.relation_type in ("related_to", "similar_to"):
                inferred_type = f"symmetric:{rel.relation_type}"
                inferences.append((neighbor, inferred_type, rel.weight))
        
        return inferences

    def find_paths(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[str]]:
        """查找两点间所有路径"""
        paths = []
        
        def dfs(current_id: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current_id == target:
                paths.append(path + [current_id])
                return
            
            for neighbor, rel in self.get_neighbors(current_id, direction="outgoing"):
                if neighbor.id not in path:
                    dfs(neighbor.id, target, path + [current_id], depth + 1)
        
        dfs(source_id, target_id, [], 0)
        return paths

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "entity_types": len(self._entity_index),
            "avg_relations_per_entity": self._stats["total_relations"] / max(1, self._stats["total_entities"])
        }

    def _generate_id(self, prefix: str) -> str:
        """生成ID"""
        return f"{prefix}_{int(time.time() * 1000)}"

    def _save(self):
        """保存数据"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "entities": {k: v.__dict__ for k, v in self._entities.items()},
                "relations": {k: v.__dict__ for k, v in self._relations.items()}
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Failed to save knowledge graph: {e}")

    def _load(self):
        """加载数据"""
        if not self.persistence_path:
            return
        
        try:
            with open(self.persistence_path) as f:
                data = json.load(f)
            
            for eid, edata in data.get("entities", {}).items():
                self._entities[eid] = Entity(**edata)
                self._entity_index[edata["entity_type"]].add(eid)
            
            for rid, rdata in data.get("relations", {}).items():
                self._relations[rid] = Relation(**rdata)
                self._outgoing_relations[rdata["source_id"]].add(rid)
                self._incoming_relations[rdata["target_id"]].add(rid)
            
            self._stats["total_entities"] = len(self._entities)
            self._stats["total_relations"] = len(self._relations)
        except Exception as e:
            print(f"❌ Failed to load knowledge graph: {e}")


# ============ 便捷函数 ============

def create_knowledge_graph(persistence_path: Optional[str] = None) -> KnowledgeGraph:
    """创建知识图谱"""
    return KnowledgeGraph(persistence_path=persistence_path)
