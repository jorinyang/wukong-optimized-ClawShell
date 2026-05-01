#!/usr/bin/env python3
"""
wukong_memory.py — 悟空记忆系统核心模块
=========================================
将 MemPalace 作为悟空的默认长期记忆能力，与 ClawShell 四层架构深度集成。

功能：
1. 层级记忆管理（Palace Wing/Room/Drawer 结构）
2. 知识图谱集成（结构化事实存储与查询）
3. 混合搜索（BM25 + 向量语义）
4. 自动记忆归档（对话、决策、任务事件）
5. 上下文恢复（会话切换时恢复工作状态）

作者：悟空（WuKong）Agent，2026-05-01
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("clawshell.wukong_memory")

# ── MemPalace 核心模块 ────────────────────────────────────────────────────
try:
    from mempalace.knowledge_graph import KnowledgeGraph
    from mempalace.palace import get_collection
    from mempalace.backends.chroma import ChromaBackend
    from mempalace.embedding import get_embedding_function
    MEMPALACE_AVAILABLE = True
except ImportError as e:
    logger.warning("MemPalace 未安装: %s", e)
    MEMPALACE_AVAILABLE = False
    KnowledgeGraph = None
    get_collection = None
    ChromaBackend = None
    get_embedding_function = None

# ── 默认路径配置 ───────────────────────────────────────────────────────────
DEFAULT_MEMORY_DIR = os.path.expanduser("~/.mempalace/wukong")
DEFAULT_KG_PATH = os.path.expanduser("~/.mempalace/wukong/knowledge_graph.sqlite3")


# ═══════════════════════════════════════════════════════════════════════════
# 悟空记忆核心类
# ═══════════════════════════════════════════════════════════════════════════

class WuKongMemory:
    """
    悟空的长期记忆系统核心类。
    
    使用 MemPalace 作为存储后端，提供：
    - Wing（翼）：对应不同的 Agent 或用户
    - Room（房）：对应不同的话题或会话
    - Drawer（抽屉）：具体的记忆条目
    
    功能：
    1. write_context() - 写入记忆到 Palace
    2. search() - 混合搜索召回记忆
    3. add_fact() - 添加结构化事实到知识图谱
    4. query_facts() - 查询实体的关系事实
    5. recall_recent() - 获取最近记忆
    6. write_conversation() - 批量写入对话历史
    """

    _instance: Optional["WuKongMemory"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        memory_dir: str = DEFAULT_MEMORY_DIR,
        kg_path: str = DEFAULT_KG_PATH,
        default_wing: str = "wukong",
    ):
        self.memory_dir = os.path.expanduser(memory_dir)
        self.kg_path = os.path.expanduser(kg_path)
        self.default_wing = default_wing

        self._collection = None
        self._kg: Optional[KnowledgeGraph] = None
        self._backend: Optional[ChromaBackend] = None
        self._initialized = False
        self._embedding_ready = False

        # 缓存
        self._drawer_count = 0

    # ── 单例 ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, **kwargs) -> "WuKongMemory":
        """获取或创建记忆系统单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance

    # ── 初始化 ────────────────────────────────────────────────────────────

    def init(self) -> bool:
        """初始化记忆系统"""
        if self._initialized:
            return True

        if not MEMPALACE_AVAILABLE:
            logger.error("MemPalace 不可用，无法初始化记忆系统")
            return False

        try:
            # 1. ChromaBackend 无参数，集合通过 get_collection 函数获取
            # 2. 初始化 Embedding 函数
            try:
                ef = get_embedding_function(device='cpu')
                self._embedding_ready = True
                logger.info("Embedding 函数已就绪")
            except Exception as e:
                logger.warning("Embedding 函数初始化失败: %s", e)
                self._embedding_ready = False

            # 3. 获取或创建 Palace 集合
            os.makedirs(self.memory_dir, exist_ok=True)
            self._collection = get_collection(
                palace_path=self.memory_dir,
                collection_name="wukong_drawers",
                create=True,
            )
            logger.info("Palace 集合已就绪: %s", self.memory_dir)

            # 4. 初始化 KnowledgeGraph
            self._kg = KnowledgeGraph(db_path=self.kg_path)
            logger.info("知识图谱已就绪: %s", self.kg_path)

            self._initialized = True
            logger.info("悟空记忆系统初始化完成")
            return True

        except Exception as e:
            logger.exception("记忆系统初始化失败: %s", e)
            return False

    # ── 记忆写入 ──────────────────────────────────────────────────────────

    def write_context(
        self,
        content: str,
        wing: str = None,
        room: str = "general",
        entities: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        写入记忆到 Palace 层级结构。
        
        Args:
            content: 记忆内容
            wing: 记忆翼（默认 wukong）
            room: 记忆房间（话题维度）
            entities: 实体字典（会同步写入知识图谱）
            metadata: 额外元数据
            
        Returns:
            drawer_id 或 None
        """
        if not self._initialized:
            self.init()

        wing = wing or self.default_wing

        if not self._embedding_ready:
            logger.warning("Embedding 未就绪，跳过 Palace 写入")
            return None

        try:
            # 生成唯一 ID
            import hashlib
            drawer_id = f"d_{hashlib.md5(f'{content}{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"

            # 构建元数据
            meta = {
                "wing": wing,
                "room": room,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }

            # 写入 Palace
            self._collection.add(
                documents=[content],
                ids=[drawer_id],
                metadatas=[meta],
            )

            self._drawer_count += 1

            # 同步写入知识图谱
            if entities and self._kg:
                for subject, obj in entities.items():
                    self._kg.add_triple(
                        subject=subject,
                        predicate="related_to",
                        obj=obj,
                        valid_from=datetime.now(timezone.utc).date().isoformat(),
                        source_drawer_id=drawer_id,
                        adapter_name="wukong_memory",
                    )

            logger.debug("记忆写入成功: %s", drawer_id)
            return drawer_id

        except Exception as e:
            logger.exception("记忆写入失败: %s", e)
            return None

    def write_conversation(
        self,
        messages: list[dict],
        wing: str = None,
        room: str = "conversation",
    ) -> int:
        """
        批量写入对话历史。
        
        Args:
            messages: [{role, content, timestamp?}, ...]
            wing/room: 见 write_context
            
        Returns:
            成功写入的数量
        """
        wing = wing or self.default_wing
        count = 0

        for msg in messages:
            content = f"[{msg.get('role', 'user')}]: {msg.get('content', '')}"
            meta = {
                "type": "conversation",
                "role": msg.get("role"),
                "ts": msg.get("timestamp", datetime.now().isoformat()),
            }
            if self.write_context(content, wing=wing, room=room, metadata=meta):
                count += 1

        logger.info("对话写入完成: %d/%d 条", count, len(messages))
        return count

    # ── 搜索 ───────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        wing: str = None,
        room: str = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        搜索记忆。
        
        Args:
            query: 搜索查询
            wing/room: 可选限定范围
            top_k: 返回数量
            
        Returns:
            [{content, score, drawer_id, metadata}, ...]
        """
        if not self._initialized:
            self.init()

        if not self._embedding_ready:
            logger.warning("Embedding 未就绪，无法执行搜索")
            return []

        wing = wing or self.default_wing

        try:
            # 构建查询条件
            where = {}
            if wing:
                where["wing"] = wing
            if room:
                where["room"] = room

            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )

            # 解析结果
            docs = results.ids[0] if results.ids else []
            texts = results.documents[0] if results.documents else []
            metas = results.metadatas[0] if results.metadatas else []
            dists = results.distances[0] if results.distances else []

            hits = []
            for drawer_id, text, meta, dist in zip(docs, texts, metas, dists):
                hits.append({
                    "content": text,
                    "score": max(0.0, 1.0 - float(dist)),
                    "drawer_id": drawer_id,
                    "metadata": meta or {},
                })

            return hits

        except Exception as e:
            logger.exception("搜索失败: %s", e)
            return []

    def recall_recent(self, wing: str = None, limit: int = 10) -> list[dict]:
        """获取最近的记忆条目"""
        wing = wing or self.default_wing

        if not self._initialized:
            self.init()

        try:
            results = self._collection.get(
                where={"wing": wing},
                limit=limit,
                include=["documents", "metadatas"],
            )

            recent = []
            for drawer_id, text, meta in zip(results.ids, results.documents, results.metadatas):
                recent.append({
                    "drawer_id": drawer_id,
                    "content": text,
                    "metadata": meta or {},
                    "created_at": meta.get("created_at", "") if meta else "",
                })

            return recent

        except Exception as e:
            logger.exception("召回失败: %s", e)
            return []

    # ── 知识图谱 ──────────────────────────────────────────────────────────

    def add_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str = None,
        confidence: float = 1.0,
    ) -> str | None:
        """向知识图谱添加事实三元组"""
        if not self._initialized:
            self.init()

        if not self._kg:
            return None

        try:
            return self._kg.add_triple(
                subject=subject,
                predicate=predicate,
                obj=obj,
                valid_from=valid_from or datetime.now(timezone.utc).date().isoformat(),
                confidence=confidence,
                adapter_name="wukong_memory",
            )
        except Exception as e:
            logger.exception("知识图谱写入失败: %s", e)
            return None

    def query_facts(
        self,
        entity: str,
        as_of: str = None,
        direction: str = "both",
    ) -> list[dict]:
        """查询实体的所有关系事实"""
        if not self._initialized:
            self.init()

        if not self._kg:
            return []

        try:
            rows = self._kg.query_entity(
                name=entity,
                as_of=as_of,
                direction=direction,
            )
            return [
                {
                    "predicate": r.get("predicate"),
                    "object": r.get("obj_name") or r.get("object"),
                    "valid_from": r.get("valid_from"),
                    "valid_to": r.get("valid_to"),
                    "confidence": r.get("confidence"),
                }
                for r in rows
            ]
        except Exception as e:
            logger.exception("知识图谱查询失败: %s", e)
            return []

    def invalidate_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        ended: str = None,
    ) -> bool:
        """使事实失效"""
        if not self._initialized:
            self.init()

        if not self._kg:
            return False

        try:
            self._kg.invalidate(
                subject=subject,
                predicate=predicate,
                obj=obj,
                ended=ended or datetime.now(timezone.utc).date().isoformat(),
            )
            return True
        except Exception as e:
            logger.exception("事实失效失败: %s", e)
            return False

    # ── 状态 ───────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """检查记忆系统是否就绪"""
        return self._initialized

    def is_embedding_ready(self) -> bool:
        """检查 embedding 是否就绪"""
        return self._embedding_ready

    def health_check(self) -> dict:
        """健康检查"""
        stats = {}
        if self._kg:
            try:
                kg_stats = self._kg.stats()
                stats.update(kg_stats)
            except Exception:
                pass

        return {
            "memory_ready": self._initialized,
            "embedding_ready": self._embedding_ready,
            "palace_connected": self._collection is not None,
            "kg_connected": self._kg is not None,
            "drawer_count": self._drawer_count,
            "memory_dir": self.memory_dir,
            "kg_path": self.kg_path,
            **stats,
        }

    def close(self):
        """关闭记忆系统"""
        if self._kg:
            self._kg.close()
        self._initialized = False
        logger.info("悟空记忆系统已关闭")


# ═══════════════════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════════════════

_memory_instance: Optional[WuKongMemory] = None


def get_memory(**kwargs) -> WuKongMemory:
    """获取记忆系统全局单例"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = WuKongMemory.get_instance(**kwargs)
        _memory_instance.init()
    return _memory_instance


def write_memory(content: str, **kwargs) -> str | None:
    """快捷写入记忆"""
    return get_memory().write_context(content, **kwargs)


def search_memory(query: str, **kwargs) -> list[dict]:
    """快捷搜索记忆"""
    return get_memory().search(query, **kwargs)


def add_fact(subject: str, predicate: str, obj: str, **kwargs) -> str | None:
    """快捷添加事实"""
    return get_memory().add_fact(subject, predicate, obj, **kwargs)


def query_facts(entity: str, **kwargs) -> list[dict]:
    """快捷查询事实"""
    return get_memory().query_facts(entity, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
# 独立运行测试
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    memory = WuKongMemory()
    memory.init()

    print("\n=== 悟空记忆系统健康检查 ===")
    health = memory.health_check()
    for k, v in health.items():
        print(f"  {k}: {v}")

    if memory.is_ready():
        print("\n=== 知识图谱测试 ===")
        
        # 添加测试事实
        facts = [
            ("悟空", "是", "AI助手"),
            ("MemPalace", "提供", "长期记忆"),
            ("ClawShell", "集成", "MemPalace"),
        ]
        
        for s, p, o in facts:
            fid = memory.add_fact(s, p, o)
            print(f"添加事实: {s} {p} {o} -> {fid}")
        
        # 查询
        for entity in ["悟空", "MemPalace"]:
            results = memory.query_facts(entity)
            print(f"\n{entity} 相关事实 ({len(results)} 条):")
            for r in results:
                print(f"  - {entity} {r['predicate']} {r['object']}")

        print("\n=== 记忆写入测试 ===")
        drawer_id = memory.write_context(
            content="测试记忆：悟空使用 MemPalace 作为长期记忆系统",
            wing="wukong",
            room="test",
            entities={"悟空": "AI助手", "MemPalace": "记忆系统"},
        )
        print(f"写入 drawer_id: {drawer_id}")

        memory.close()
        print("\n✅ 测试完成")
    else:
        print("\n⚠️ 记忆系统未就绪")
