#!/usr/bin/env python3
"""
ClawShell Relation Engine
关系推理引擎 - Phase 1 升级
版本: v1.0.0
功能: 抽象关系理解、归纳推理、演绎推理
"""

import json
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

RELATION_TYPES = [
    "opposite",      # 相反关系: A→非A
    "similar",       # 相似关系: A≈B
    "part_whole",    # 部分-整体: A∈B
    "cause_effect",   # 因果关系: A导致B
    "condition",      # 条件关系: A则B
    "temporal",      # 时间关系: A先于B
    "spatial",       # 空间关系: A位于B
    "reference",     # 引用关系: A引用B
]

@dataclass
class Relation:
    """关系"""
    id: str
    relation_type: str
    source: str
    target: str
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class RelationEngine:
    """
    关系推理引擎
    
    功能：
    - 关系识别: 从文本中识别关系
    - 关系推理: 基于已知关系推断新关系
    - 关系验证: 验证关系的一致性
    """
    
    def __init__(self):
        self.relations: Dict[str, List[Relation]] = {}
        self.relation_graph: Dict[str, Set[str]] = {}
        
    def add_relation(self, relation_type: str, source: str, target: str, confidence: float = 1.0):
        """添加关系"""
        rel_id = f"{source}|{relation_type}|{target}"
        relation = Relation(
            id=rel_id,
            relation_type=relation_type,
            source=source,
            target=target,
            confidence=confidence
        )
        
        if relation_type not in self.relations:
            self.relations[relation_type] = []
        self.relations[relation_type].append(relation)
        
        # 更新关系图
        if source not in self.relation_graph:
            self.relation_graph[source] = set()
        self.relation_graph[source].add(target)
        
        return relation
    
    def find_opposite(self, entity: str) -> List[str]:
        """找相反关系"""
        opposites = []
        for rel in self.relations.get("opposite", []):
            if rel.source == entity:
                opposites.append(rel.target)
            elif rel.target == entity:
                opposites.append(rel.source)
        return opposites
    
    def find_similar(self, entity: str) -> List[str]:
        """找相似关系"""
        similar = []
        for rel in self.relations.get("similar", []):
            if rel.source == entity:
                similar.append(rel.target)
            elif rel.target == entity:
                similar.append(rel.source)
        return similar
    
    def find_causes(self, entity: str) -> List[str]:
        """找原因"""
        causes = []
        for rel in self.relations.get("cause_effect", []):
            if rel.target == entity:
                causes.append(rel.source)
        return causes
    
    def find_effects(self, entity: str) -> List[str]:
        """找结果"""
        effects = []
        for rel in self.relations.get("cause_effect", []):
            if rel.source == entity:
                effects.append(rel.target)
        return effects
    
    def transitive_inference(self, entity: str, relation_type: str) -> Set[str]:
        """传递推理: A→B, B→C => A→C"""
        result = set()
        visited = set()
        queue = [entity]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            for rel in self.relations.get(relation_type, []):
                if rel.source == current and rel.target not in visited:
                    result.add(rel.target)
                    queue.append(rel.target)
        
        return result
    
    def deduce_from_opposites(self, entity: str) -> Dict[str, any]:
        """演绎推理: opposite(opposite(A)) = A"""
        return {
            "entity": entity,
            "opposites": self.find_opposite(entity),
            "double_negation": entity if self.find_opposite(entity) else None
        }
    
    def deduce_from_causes(self, entity: str) -> Dict[str, List[str]]:
        """演绎推理: 原因链"""
        chain = []
        current = entity
        
        while True:
            causes = self.find_causes(current)
            if not causes:
                break
            chain.append(causes[0])
            current = causes[0]
        
        return {
            "entity": entity,
            "root_causes": chain,
            "effects": self.find_effects(entity)
        }
    
    def export_graph(self) -> Dict:
        """导出关系图"""
        return {
            "nodes": list(self.relation_graph.keys()),
            "edges": [
                {"source": k, "target": v}
                for k, vs in self.relation_graph.items()
                for v in vs
            ],
            "relation_counts": {
                rel_type: len(rels)
                for rel_type, rels in self.relations.items()
            }
        }
    
    def import_from_json(self, data: Dict):
        """从JSON导入"""
        self.relations = {}
        self.relation_graph = {}
        
        for rel_type, rels in data.get("relations", {}).items():
            for rel_data in rels:
                self.add_relation(
                    rel_type,
                    rel_data["source"],
                    rel_data["target"],
                    rel_data.get("confidence", 1.0)
                )

if __name__ == "__main__":
    engine = RelationEngine()
    
    # 测试关系添加
    engine.add_relation("opposite", "hot", "cold", 0.95)
    engine.add_relation("opposite", "cold", "hot", 0.95)
    engine.add_relation("similar", "hot", "warm", 0.8)
    engine.add_relation("cause_effect", "fire", "smoke", 0.9)
    engine.add_relation("cause_effect", "smoke", "alarm", 0.85)
    
    # 测试推理
    print("=== 关系推理引擎测试 ===")
    print(f"hot的反义: {engine.find_opposite('hot')}")
    print(f"hot的相似: {engine.find_similar('hot')}")
    print(f"alarm的原因: {engine.find_causes('alarm')}")
    print(f"fire的传递结果: {engine.transitive_inference('fire', 'cause_effect')}")
    
    # 导出图
    graph = engine.export_graph()
    print(f"\n关系图: {json.dumps(graph, indent=2, ensure_ascii=False)}")
