"""
mempalace_bridge.py — MemPalace v3.3.4 × ClawShell 记忆集成桥接层
=====================================================================
将 MemPalace 的记忆宫殿系统（层级记忆 + 时序知识图谱 + 混合搜索）
与 ClawShell 的 genome / eventbus / strategy / 任务市场 深度融合。

v3.3.4 适配说明：
- 使用 ChromaBackend + 函数式 API（替代旧版 Palace 类）
- Palace 层级映射：Wing → Project，Room → Aspect
- 支持 BM25 + 向量混合搜索
- 知识图谱保留原有 API（add_triple/query_entity）

作者：悟空（WuKong）Agent，2026-05-01
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("clawshell.mempalace_bridge")

# ── MemPalace v3.3.4 核心模块 ───────────────────────────────────────────────
try:
    # v3.3.4 使用函数式 API
    from mempalace.palace import (
        get_collection,
        get_closets_collection,
        build_closet_lines,
        upsert_closet_lines,
        SKIP_DIRS,
        CLOSET_CHAR_LIMIT,
    )
    from mempalace.knowledge_graph import KnowledgeGraph
    from mempalace.searcher import search as mempalace_search, SearchError
    from mempalace.backends.chroma import ChromaBackend
    MEMPALACE_AVAILABLE = True
except ImportError as e:
    logger.warning("MemPalace v3.3.4 未安装或导入失败: %s", e)
    MEMPALACE_AVAILABLE = False
    get_collection = None
    get_closets_collection = None
    build_closet_lines = None
    upsert_closet_lines = None
    KnowledgeGraph = None
    ChromaBackend = None

# ── ClawShell 内置模块 ───────────────────────────────────────────────────────
try:
    from lib.core.genome import Genome
    from lib.core.eventbus import eventbus
    from lib.core.strategy import StrategyEngine
    CLAWSHELL_CORE_AVAILABLE = True
except ImportError as e:
    logger.warning("ClawShell 核心模块导入失败: %s", e)
    CLAWSHELL_CORE_AVAILABLE = False
    Genome = None
    eventbus = None
    StrategyEngine = None

# ── 默认路径配置 ──────────────────────────────────────────────────────────────
DEFAULT_PALACE_DIR = os.path.expanduser("~/.mempalace/clawshell")
DEFAULT_KG_PATH    = os.path.expanduser("~/.mempalace/clawshell/knowledge_graph.sqlite3")


# ═══════════════════════════════════════════════════════════════════════════════
#  核心桥接类：MemPalaceBridge v3.3.4
# ═══════════════════════════════════════════════════════════════════════════════

class MemPalaceBridge:
    """
    MemPalace v3.3.4 与 ClawShell 的核心集成桥。

    v3.3.4 架构映射：
    ┌─────────────────────────────────────────────────────────────────┐
    │  ClawShell Genome      →  MemPalace Wing/Drawer                  │
    │  (短期工作记忆)             (项目维度抽屉存储)                    │
    ├─────────────────────────────────────────────────────────────────┤
    │  ClawShell Strategy    →  MemPalace KnowledgeGraph             │
    │  (策略上下文)              (结构化事实三元组)                      │
    ├─────────────────────────────────────────────────────────────────┤
    │  ClawShell EventBus    →  MemPalace upsert_closet_lines()       │
    │  (事件总线)                (事件驱动写入)                         │
    ├─────────────────────────────────────────────────────────────────┤
    │  ClawShell TaskMarket  →  MemPalace search() + BM25            │
    │  (任务市场)                (混合搜索召回)                         │
    └─────────────────────────────────────────────────────────────────┘

    Wing/Room 层级说明（v3.3.4）：
    - Wing: 项目/用户维度（对应 clawshell 的 agent_id 或 user_id）
    - Room: 话题/会话维度（对应 conversation_id 或 topic）

    使用方式：
        bridge = MemPalaceBridge(palace_dir="~/.mempalace/clawshell")
        bridge.init()

        # 写入记忆
        bridge.write_context(
            wing="clawshell",
            room="session",
            content="用户月夜偏好使用中文简洁回复",
            entities={"user": "月夜", "preference": "简洁中文"}
        )

        # 搜索召回
        results = bridge.search("用户偏好", top_k=5)

        # 查询知识图谱
        facts = bridge.query_fact("月夜")
    """

    _instance: Optional["MemPalaceBridge"] = None
    _lock_init = threading.Lock()

    def __init__(
        self,
        palace_dir: str = DEFAULT_PALACE_DIR,
        kg_path: str = DEFAULT_KG_PATH,
        wing: str = "clawshell",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.palace_dir   = os.path.expanduser(palace_dir)
        self.kg_path      = os.path.expanduser(kg_path)
        self.default_wing  = wing
        self.embedding_model = embedding_model

        self._backend: Optional[ChromaBackend] = None
        self._drawers_col = None
        self._kg: Optional[KnowledgeGraph] = None
        self._genome: Optional[Genome] = None
        self._initialized: bool = False

        # Agent Diaries：每个 ClawShell agent 一个独立 wing
        self._agent_wings: dict[str, str] = {}

    # ── 单例获取 ──────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls, **kwargs) -> "MemPalaceBridge":
        """获取或创建桥接层单例（线程安全）"""
        if cls._instance is None:
            with cls._lock_init:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance

    # ── 初始化 ────────────────────────────────────────────────────────────

    def init(self) -> bool:
        """初始化 MemPalace v3.3.4 Palace + KnowledgeGraph"""
        if self._initialized:
            return True

        if not MEMPALACE_AVAILABLE:
            logger.error("MemPalace v3.3.4 未安装，无法初始化桥接层")
            return False

        try:
            # 1. 确保目录存在
            os.makedirs(self.palace_dir, exist_ok=True)

            # 2. 初始化 ChromaBackend（v3.3.4 新架构）
            self._backend = ChromaBackend()
            self._drawers_col = get_collection(
                self.palace_dir,
                collection_name="mempalace_drawers",
                create=True,
            )
            logger.info("ChromaBackend 初始化完成 | Palace: %s", self.palace_dir)

            # 3. 初始化 KnowledgeGraph（时序知识图谱）
            self._kg = KnowledgeGraph(db_path=self.kg_path)
            logger.info("KnowledgeGraph 初始化完成 | KG: %s", self.kg_path)

            # 4. 挂载 ClawShell Genome（如可用）
            if CLAWSHELL_CORE_AVAILABLE:
                try:
                    self._genome = Genome()
                    logger.info("Genome 模块已挂载至 MemPalace 桥接层")
                except Exception as e:
                    logger.warning("Genome 挂载失败，降级运行: %s", e)

            # 5. 注册事件总线订阅（如可用）
            if eventbus is not None:
                self._subscribe_events()

            self._initialized = True
            logger.info(
                "MemPalace v3.3.4 桥接层初始化完成 | Palace: %s | KG: %s",
                self.palace_dir, self.kg_path
            )
            return True

        except Exception as e:
            logger.exception("MemPalace 桥接层初始化失败: %s", e)
            return False

    # ── 层级记忆写入 ───────────────────────────────────────────────────────

    def write_context(
        self,
        content: str,
        wing: str = None,
        room: str = "general",
        entities: dict[str, str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        将对话上下文写入 MemPalace Palace 层级记忆（v3.3.4 函数式 API）。

        Args:
            content:     记忆内容文本
            wing:        记忆翼（默认 clawshell）—— 对应 Project 维度
            room:        记忆房间（默认 general）—— 对应 Aspect 维度
            entities:    实体字典，会同步写入 KnowledgeGraph
            tags:        标签列表
            metadata:    额外元数据

        Returns:
            drawer_id: 写入成功后返回抽屉ID，失败返回 None
        """
        if not self._initialized:
            self.init()

        wing = wing or self.default_wing
        room = room or "general"

        if not self._drawers_col:
            logger.error("Drawer 集合未初始化")
            return None

        try:
            # v3.3.4: 使用 upsert_closet_lines 写入数据
            import hashlib
            import uuid

            # 生成唯一 ID
            drawer_id = hashlib.sha256(
                f"{content}{wing}{room}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]

            # 准备元数据
            meta = metadata or {}
            meta.update({
                "wing": wing,
                "room": room,
                "source_file": f"clawshell_bridge:{drawer_id}",
                "chunk_index": 0,
            })
            if tags:
                meta["tags"] = ",".join(tags)

            # 写入 Drawer 集合
            self._drawers_col.upsert(
                ids=[drawer_id],
                documents=[content],
                metadatas=[meta],
            )

            # 构建并写入 Closet 索引（v3.3.4 特性）
            closet_lines = build_closet_lines(
                source_file=f"clawshell_bridge:{drawer_id}",
                drawer_ids=[drawer_id],
                content=content,
                wing=wing,
                room=room,
            )
            if closet_lines:
                closets_col = get_closets_collection(self.palace_dir, create=True)
                closet_id = f"closet_{drawer_id}"
                closets_col.upsert(
                    ids=[closet_id],
                    documents=["\n".join(closet_lines)],
                    metadatas=[{
                        "wing": wing,
                        "room": room,
                        "source_file": f"clawshell_bridge:{drawer_id}",
                    }],
                )

            # 同步写入 KnowledgeGraph（如有实体）
            if entities and self._kg:
                for subject, obj in entities.items():
                    self._kg.add_triple(
                        subject=subject,
                        predicate="related_to",
                        obj=obj,
                        valid_from=datetime.now(timezone.utc).date().isoformat(),
                        source_drawer_id=drawer_id,
                        adapter_name="clawshell_bridge",
                    )

            # 发布写入事件到 EventBus
            if eventbus is not None:
                try:
                    eventbus.publish(
                        "memory.written",
                        {
                            "drawer_id": drawer_id,
                            "wing": wing,
                            "room": room,
                            "content_preview": content[:100],
                            "entities": list(entities.keys()) if entities else [],
                        }
                    )
                except Exception as e:
                    logger.warning("EventBus 发布失败: %s", e)

            logger.debug("记忆写入成功 | wing=%s room=%s drawer=%s", wing, room, drawer_id)
            return drawer_id

        except Exception as e:
            logger.exception("记忆写入失败: %s", e)
            return None

    def write_conversation(
        self,
        messages: list[dict],
        wing: str = None,
        room: str = "conversation",
    ) -> str | None:
        """
        将对话历史批量写入记忆。

        Args:
            messages: [{role, content, timestamp?}, ...]
            wing/room: 见 write_context

        Returns:
            最后一个 drawer_id
        """
        wing = wing or self.default_wing
        last_id = None

        for msg in messages:
            content = f"[{msg.get('role', 'user')}]: {msg.get('content', '')}"
            meta = {
                "type": "conversation",
                "role": msg.get("role"),
                "ts": msg.get("timestamp", datetime.now().isoformat()),
            }
            result = self.write_context(
                content=content,
                wing=wing,
                room=room,
                metadata=meta,
            )
            if result:
                last_id = result

        return last_id

    # ── 搜索召回 ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        wing: str = None,
        room: str = None,
        top_k: int = 5,
        include_metadata: bool = True,
    ) -> list[dict]:
        """
        混合搜索（BM25 + 向量语义）在 Palace 记忆库中召回相关内容。

        Args:
            query:          搜索查询
            wing/room:      可选限定搜索范围
            top_k:          返回结果数量
            include_metadata: 是否包含元数据

        Returns:
            [{"content", "score", "drawer_id", "metadata"}, ...]
        """
        if not self._initialized:
            self.init()

        wing = wing or self.default_wing

        if not self._drawers_col:
            logger.error("Drawer 集合未初始化")
            return []

        try:
            # v3.3.4: 使用 ChromaDB 原生查询
            import math

            where_filter = {}
            if wing:
                where_filter["wing"] = wing
            if room:
                where_filter["room"] = room

            kwargs = {
                "query_texts": [query],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where_filter:
                kwargs["where"] = where_filter

            results = self._drawers_col.query(**kwargs)

            # 解析结果
            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            dists = results.get("distances", [[]])[0] if results.get("distances") else []

            search_results = []
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
                if doc is None:
                    continue
                # Cosine 相似度转换
                vec_sim = max(0.0, 1.0 - float(dist)) if dist is not None else 0.0
                search_results.append({
                    "content": doc,
                    "score": round(vec_sim, 3),
                    "drawer_id": results.get("ids", [[]])[0][i] if results.get("ids") else f"drawer_{i}",
                    "metadata": meta if include_metadata else {},
                })

            # 按分数排序
            search_results.sort(key=lambda x: x["score"], reverse=True)

            logger.debug("搜索完成 | query=%s wing=%s results=%d", query, wing, len(search_results))
            return search_results

        except Exception as e:
            logger.exception("搜索异常: %s", e)
            return []

    def recall_recent(self, wing: str = None, limit: int = 10) -> list[dict]:
        """获取最近的记忆条目（按时间倒序）"""
        wing = wing or self.default_wing

        if not self._drawers_col:
            return []

        try:
            # 获取所有匹配的记录并按 chunk_index 排序
            where_filter = {"wing": wing} if wing else {}

            results = self._drawers_col.get(
                where=where_filter if where_filter else None,
                include=["documents", "metadatas"],
                limit=limit,
            )

            recent = []
            docs = results.get("documents", []) if results else []
            metas = results.get("metadatas", []) if results else []
            ids = results.get("ids", []) if results else []

            for drawer_id, doc, meta in zip(ids, docs, metas):
                if doc:
                    recent.append({
                        "drawer_id": drawer_id,
                        "content": doc,
                        "wing": meta.get("wing", "") if meta else "",
                        "room": meta.get("room", "") if meta else "",
                    })

            return recent[-limit:]  # 最近的在后面

        except Exception as e:
            logger.warning("获取最近记忆失败: %s", e)
            return []

    # ── 知识图谱 ──────────────────────────────────────────────────────────

    def add_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str = None,
        valid_to: str = None,
        confidence: float = 1.0,
    ) -> str | None:
        """向知识图谱写入一个事实三元组"""
        if not self._initialized:
            self.init()

        if not self._kg:
            logger.warning("KnowledgeGraph 不可用")
            return None

        try:
            return self._kg.add_triple(
                subject=subject,
                predicate=predicate,
                obj=obj,
                valid_from=valid_from or datetime.now(timezone.utc).date().isoformat(),
                valid_to=valid_to,
                confidence=confidence,
                adapter_name="clawshell_bridge",
            )
        except Exception as e:
            logger.exception("知识图谱写入失败: %s", e)
            return None

    def query_fact(
        self,
        entity: str,
        as_of: str = None,
        direction: str = "both",
    ) -> list[dict]:
        """
        查询实体的所有关系事实。

        Args:
            entity:    实体名称
            as_of:     时间点（"2026-04-30"），仅返回该时间点有效的断言
            direction: "outgoing" | "incoming" | "both"

        Returns:
            [{"predicate", "object", "valid_from", "valid_to", "confidence"}, ...]
        """
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
                    "source_drawer_id": r.get("source_drawer_id"),
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
        """使一条事实失效（设置 valid_to）"""
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
            logger.exception("事实失效操作失败: %s", e)
            return False

    # ── Genome 协同 ───────────────────────────────────────────────────────

    def sync_genome_to_memory(self) -> bool:
        """
        将 ClawShell Genome 的当前状态同步到 MemPalace 长期记忆。
        在会话切换或重要决策点调用。
        """
        if not self._genome:
            logger.debug("Genome 不可用，跳过同步")
            return False

        try:
            state = self._genome.get_state()
            content = json.dumps(state, ensure_ascii=False, indent=2)
            self.write_context(
                content=content,
                wing=self.default_wing,
                room="genome_state",
                metadata={"type": "genome_snapshot", "source": "clawshell"},
            )
            logger.info("Genome 状态已同步至 MemPalace")
            return True
        except Exception as e:
            logger.exception("Genome 同步失败: %s", e)
            return False

    def load_context_to_genome(self, wing: str = None) -> bool:
        """
        从 MemPalace 恢复上下文到 Genome。
        在恢复会话时调用。
        """
        wing = wing or self.default_wing
        if not self._genome:
            return False

        try:
            results = self.search(
                query="genome_state",
                wing=wing,
                room="genome_state",
                top_k=1,
            )
            if results:
                state = json.loads(results[0]["content"])
                self._genome.load_state(state)
                logger.info("Genome 状态已从 MemPalace 恢复")
                return True
            return False
        except Exception as e:
            logger.exception("Genome 恢复失败: %s", e)
            return False

    # ── EventBus 集成 ─────────────────────────────────────────────────────

    def _subscribe_events(self):
        """订阅 ClawShell 事件总线，自动归档关键事件"""
        try:
            if hasattr(eventbus, "subscribe"):
                eventbus.subscribe("session.message", self._on_message)
                eventbus.subscribe("task.created", self._on_task_created)
                eventbus.subscribe("agent.decision", self._on_agent_decision)
                logger.info("EventBus 事件订阅已注册")
        except Exception as e:
            logger.warning("EventBus 订阅注册失败: %s", e)

    def _on_message(self, event):
        """自动归档用户消息"""
        role    = event.get("role", "user")
        content = event.get("content", "")
        if content:
            self.write_context(
                content=f"[{role}]: {content}",
                room="conversation",
                metadata={"type": "auto_archived", "source": "eventbus"},
            )

    def _on_task_created(self, event):
        """自动归档任务创建事件"""
        task_id   = event.get("task_id")
        task_type = event.get("type", "unknown")
        summary   = event.get("summary", "")
        if task_id:
            self.add_fact(
                subject=f"task_{task_id}",
                predicate="has_type",
                obj=task_type,
            )
            self.write_context(
                content=f"[任务创建] {task_id}: {summary}",
                room="tasks",
                metadata={"type": "task_created", "task_id": task_id},
            )

    def _on_agent_decision(self, event):
        """归档 Agent 决策上下文"""
        agent  = event.get("agent", "unknown")
        action = event.get("action", "")
        reason = event.get("reason", "")
        if action:
            self.write_context(
                content=f"[Agent {agent} 决策] {action}，原因：{reason}",
                wing=self.default_wing,
                room="decisions",
                entities={agent: "agent"},
                metadata={"type": "agent_decision"},
            )

    # ── Agent Diaries 支持 ────────────────────────────────────────────────

    def register_agent(self, agent_id: str, wing: str = None) -> str:
        """
        为 ClawShell 子 Agent 注册独立记忆翼。

        Args:
            agent_id: ClawShell agent 标识符
            wing:     记忆翼名称（默认 agent_{id}）

        Returns:
            wing 名称
        """
        wing = wing or f"agent_{agent_id}"
        self._agent_wings[agent_id] = wing
        logger.debug("Agent 记忆翼已注册 | agent=%s wing=%s", agent_id, wing)
        return wing

    def get_agent_wing(self, agent_id: str) -> str:
        """获取 Agent 对应的记忆翼名称"""
        return self._agent_wings.get(agent_id, self.default_wing)

    # ── 工具注册表（供能力发现使用）────────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        """
        返回桥接层工具清单，供 ClawShell 能力发现模块使用。
        格式兼容 MCP 工具规范。
        """
        return [
            {
                "name": "mp_write_context",
                "description": "将对话上下文写入 MemPalace 长期记忆",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "记忆内容"},
                        "wing": {"type": "string", "description": "记忆翼（Agent/用户维度）"},
                        "room": {"type": "string", "description": "记忆房间（话题维度）"},
                        "entities": {"type": "object", "description": "实体字典，会同步写入知识图谱"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "mp_search",
                "description": "混合搜索召回 MemPalace 中的相关记忆",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"},
                        "wing": {"type": "string", "description": "限定记忆翼"},
                        "room": {"type": "string", "description": "限定记忆房间"},
                        "top_k": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "mp_query_facts",
                "description": "查询知识图谱中某实体的所有关系事实",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity": {"type": "string", "description": "实体名称"},
                        "as_of": {"type": "string", "description": "时间点（YYYY-MM-DD）"},
                        "direction": {"type": "string", "enum": ["outgoing", "incoming", "both"]},
                    },
                    "required": ["entity"],
                },
            },
            {
                "name": "mp_add_fact",
                "description": "向知识图谱写入结构化事实三元组",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "predicate": {"type": "string"},
                        "obj": {"type": "string"},
                        "confidence": {"type": "number", "default": 1.0},
                    },
                    "required": ["subject", "predicate", "obj"],
                },
            },
            {
                "name": "mp_recall_recent",
                "description": "获取最近记忆条目",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "wing": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
            {
                "name": "mp_sync_genome",
                "description": "将 Genome 工作记忆同步到 MemPalace 长期存储",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    # ── 状态 ─────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """检查桥接层是否已就绪"""
        return self._initialized and self._drawers_col is not None

    def health_check(self) -> dict:
        """健康检查"""
        return {
            "bridge_ready": self._initialized,
            "palace_available": MEMPALACE_AVAILABLE,
            "palace_connected": self._drawers_col is not None,
            "kg_connected": self._kg is not None,
            "genome_mounted": self._genome is not None,
            "agents_registered": list(self._agent_wings.keys()),
            "palace_dir": self.palace_dir,
            "kg_path": self.kg_path,
            "version": "3.3.4",
        }

    def close(self):
        """关闭桥接层，释放资源"""
        if self._kg:
            self._kg.close()
        self._initialized = False
        logger.info("MemPalace 桥接层已关闭")


# ═══════════════════════════════════════════════════════════════════════════════
#  便捷函数
# ═══════════════════════════════════════════════════════════════════════════════

_bridge_instance: Optional[MemPalaceBridge] = None


def get_bridge(**kwargs) -> MemPalaceBridge:
    """获取桥接层全局单例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MemPalaceBridge.get_instance(**kwargs)
        _bridge_instance.init()
    return _bridge_instance


def embedding_model() -> str:
    """获取当前使用的 embedding 模型名称"""
    return "all-MiniLM-L6-v2"  # MemPalace 默认模型


# ═══════════════════════════════════════════════════════════════════════════════
#  独立运行测试
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    # 确保 venv site-packages 在路径中
    venv_site = r"C:\Users\Aorus\.real\users\user-bd1b229d4eff8f6a45c456149072cb3b\workspace\.venv\Lib\site-packages"
    if venv_site not in sys.path:
        sys.path.insert(0, venv_site)

    bridge = MemPalaceBridge(palace_dir=r"C:\Users\Aorus\.mempalace\clawshell")
    print("健康检查:", json.dumps(bridge.health_check(), ensure_ascii=False, indent=2))

    if bridge.is_ready():
        # 写入测试
        drawer = bridge.write_context(
            content="月夜用户偏好简洁中文回复，关注 ClawShell 项目优化",
            wing="test",
            room="user_profile",
            entities={"月夜": "用户", "ClawShell": "项目"},
        )
        print(f"写入 drawer: {drawer}")

        # 搜索测试
        results = bridge.search("用户偏好", wing="test")
        print(f"搜索结果: {len(results)} 条")
        for r in results:
            print(f"  [{r['score']:.3f}] {r['content'][:60]}...")

        # 知识图谱测试
        facts = bridge.query_fact("月夜")
        print(f"月夜相关事实: {len(facts)} 条")

        bridge.close()
    else:
        print("桥接层初始化失败，请检查 MemPalace v3.3.4 是否正确安装")
