#!/usr/bin/env python3
"""
ClawShell Genome Semantic Search
语义搜索模块
版本: v0.2.0-A
功能: 语义向量、相似度计算、搜索排序
"""

import time
import math
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict


# ============ 数据结构 ============

@dataclass
class SemanticVector:
    """语义向量"""
    entity_id: str
    vector: List[float]
    dimension: int
    created_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """搜索结果"""
    entity_id: str
    score: float
    highlights: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


# ============ 简单语义搜索（基于TF-IDF）============

class SemanticSearch:
    """
    语义搜索
    
    功能：
    - 文本向量化（TF-IDF）
    - 相似度计算
    - 搜索排序
    - 关键词高亮
    
    使用示例：
        search = SemanticSearch()
        
        # 索引文档
        search.index_document("doc1", "OpenClaw is an AI agent framework")
        
        # 搜索
        results = search.search("AI framework", top_k=5)
        
        # 获取相关文档
        similar = search.get_similar("doc1", top_k=3)
    """

    def __init__(
        self,
        dimension: int = 100,
        persistence_path: Optional[str] = None
    ):
        self.dimension = dimension
        self.persistence_path = persistence_path
        
        # 文档存储: entity_id -> {text, metadata}
        self._documents: Dict[str, Dict] = {}
        
        # 向量存储: entity_id -> SemanticVector
        self._vectors: Dict[str, SemanticVector] = {}
        
        # 词汇表: term -> index
        self._vocabulary: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}  # 逆文档频率
        
        # 统计
        self._stats = {
            "total_documents": 0,
            "total_terms": 0,
            "search_count": 0,
            "avg_search_time_ms": 0
        }
        
        self._load()

    def index_document(
        self,
        entity_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """索引文档"""
        # 存储文档
        self._documents[entity_id] = {
            "text": text,
            "metadata": metadata or {}
        }
        
        # 计算TF
        tf = self._compute_tf(text)
        
        # 更新IDF
        for term in tf.keys():
            if term not in self._vocabulary:
                self._vocabulary[term] = len(self._vocabulary)
            self._idf[term] = self._idf.get(term, 0) + 1
        
        # 计算TF-IDF向量
        vector = self._compute_tfidf_vector(tf)
        
        # 存储向量
        self._vectors[entity_id] = SemanticVector(
            entity_id=entity_id,
            vector=vector,
            dimension=self.dimension
        )
        
        self._stats["total_documents"] += 1
        self._stats["total_terms"] = len(self._vocabulary)
        
        self._save()

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """搜索"""
        start = time.time()
        self._stats["search_count"] += 1
        
        # 计算查询向量
        query_tf = self._compute_tf(query)
        query_vector = self._compute_tfidf_vector(query_tf)
        
        # 计算相似度
        scores = []
        for entity_id, doc_vector in self._vectors.items():
            similarity = self._cosine_similarity(query_vector, doc_vector.vector)
            
            if similarity >= min_score:
                # 获取高亮
                highlights = self._get_highlights(query, self._documents[entity_id]["text"])
                
                scores.append(SearchResult(
                    entity_id=entity_id,
                    score=similarity,
                    highlights=highlights,
                    metadata=self._documents[entity_id].get("metadata", {})
                ))
        
        # 排序
        scores.sort(key=lambda x: x.score, reverse=True)
        
        elapsed = (time.time() - start) * 1000
        self._stats["avg_search_time_ms"] = (
            (self._stats["avg_search_time_ms"] * (self._stats["search_count"] - 1) + elapsed)
            / self._stats["search_count"]
        )
        
        return scores[:top_k]

    def get_similar(
        self,
        entity_id: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """获取相似文档"""
        if entity_id not in self._vectors:
            return []
        
        source_vector = self._vectors[entity_id].vector
        
        similarities = []
        for eid, vec in self._vectors.items():
            if eid != entity_id:
                sim = self._cosine_similarity(source_vector, vec.vector)
                similarities.append((eid, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def search_by_keyword(
        self,
        keyword: str,
        top_k: int = 10
    ) -> List[SearchResult]:
        """关键词搜索"""
        keyword_lower = keyword.lower()
        
        results = []
        for entity_id, doc in self._documents.items():
            text_lower = doc["text"].lower()
            
            if keyword_lower in text_lower:
                # 计算出现次数作为简单得分
                count = text_lower.count(keyword_lower)
                
                results.append(SearchResult(
                    entity_id=entity_id,
                    score=float(count),
                    highlights=[keyword],
                    metadata=doc.get("metadata", {})
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def delete_document(self, entity_id: str) -> bool:
        """删除文档"""
        if entity_id not in self._documents:
            return False
        
        del self._documents[entity_id]
        
        if entity_id in self._vectors:
            del self._vectors[entity_id]
        
        self._stats["total_documents"] -= 1
        self._save()
        
        return True

    def get_document(self, entity_id: str) -> Optional[Dict]:
        """获取文档"""
        return self._documents.get(entity_id)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "vocabulary_size": len(self._vocabulary),
            "avg_vector_norm": self._compute_avg_norm()
        }

    def _compute_tf(self, text: str) -> Dict[str, float]:
        """计算词频"""
        words = text.lower().split()
        word_count = len(words)
        
        if word_count == 0:
            return {}
        
        tf = defaultdict(int)
        for word in words:
            # 简单分词
            word = ''.join(c for c in word if c.isalnum())
            if word:
                tf[word] += 1
        
        # 归一化
        for word in tf:
            tf[word] /= word_count
        
        return dict(tf)

    def _compute_tfidf_vector(self, tf: Dict[str, float]) -> List[float]:
        """计算TF-IDF向量"""
        N = self._stats["total_documents"] or 1
        
        vector = [0.0] * min(self.dimension, len(self._vocabulary))
        
        for term, tf_value in tf.items():
            if term not in self._vocabulary:
                continue
            
            idx = self._vocabulary[term]
            if idx >= self.dimension:
                continue
            
            # IDF = log(N / df)
            df = self._idf.get(term, 1)
            idf = math.log(N / df)
            
            vector[idx] = tf_value * idf
        
        return vector

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """余弦相似度"""
        if len(v1) != len(v2):
            # 调整长度
            max_len = max(len(v1), len(v2))
            v1 = v1 + [0.0] * (max_len - len(v1))
            v2 = v2 + [0.0] * (max_len - len(v2))
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def _get_highlights(self, query: str, text: str, window: int = 50) -> List[str]:
        """获取高亮片段"""
        words = query.lower().split()
        text_lower = text.lower()
        
        highlights = []
        for word in words:
            word = ''.join(c for c in word if c.isalnum())
            if not word:
                continue
            
            idx = text_lower.find(word)
            if idx >= 0:
                start = max(0, idx - window)
                end = min(len(text), idx + len(word) + window)
                snippet = text[start:end].strip()
                
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                
                highlights.append(snippet)
        
        return highlights[:3]  # 最多3个高亮

    def _compute_avg_norm(self) -> float:
        """计算平均向量范数"""
        if not self._vectors:
            return 0.0
        
        total_norm = sum(
            math.sqrt(sum(v * v for v in vec.vector))
            for vec in self._vectors.values()
        )
        
        return total_norm / len(self._vectors)

    def _save(self):
        """保存数据"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "documents": self._documents,
                "vectors": {
                    k: {"entity_id": v.entity_id, "vector": v.vector, "dimension": v.dimension}
                    for k, v in self._vectors.items()
                },
                "vocabulary": self._vocabulary,
                "idf": self._idf
            }
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save semantic search: {e}")

    def _load(self):
        """加载数据"""
        if not self.persistence_path:
            return
        
        try:
            with open(self.persistence_path) as f:
                data = json.load(f)
            
            self._documents = data.get("documents", {})
            
            for eid, vdata in data.get("vectors", {}).items():
                self._vectors[eid] = SemanticVector(**vdata)
            
            self._vocabulary = data.get("vocabulary", {})
            self._idf = data.get("idf", {})
            
            self._stats["total_documents"] = len(self._documents)
            self._stats["total_terms"] = len(self._vocabulary)
        except Exception as e:
            print(f"❌ Failed to load semantic search: {e}")


# ============ 便捷函数 ============

def create_semantic_search(
    dimension: int = 100,
    persistence_path: Optional[str] = None
) -> SemanticSearch:
    """创建语义搜索"""
    return SemanticSearch(dimension=dimension, persistence_path=persistence_path)
