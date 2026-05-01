"""mempalace_hooks.py — MemPalace × EventBus lifecycle hooks
==============================================================
Trigger: Real/Wukong publishes lifecycle event → EventBus → MemPalaceHookSubscriber
Usage: subscriber = MemPalaceHookSubscriber(); subscriber.register()
"""
from __future__ import annotations
import logging, os, hashlib
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("clawshell.mempalace_hooks")

try:
    from mempalace.palace import get_collection
    from mempalace.knowledge_graph import KnowledgeGraph
    MEMPALACE_OK = True
except ImportError as e:
    logger.warning("MemPalace unavailable: %s", e)
    MEMPALACE_OK = False

try:
    from .schema import Event, EventType
except ImportError:
    from lib.core.eventbus.schema import Event, EventType


class MemPalaceHookSubscriber:
    _instance = None

    def __init__(self, eventbus=None, palace_dir=None, kg_path=None,
                 wing="wukong", auto_init=True):
        self._bus = eventbus
        self._palace_dir = palace_dir or os.path.expanduser("~/.mempalace/clawshell")
        self._kg_path    = kg_path    or os.path.expanduser("~/.mempalace/clawshell/kg.sqlite3")
        self._wing       = wing
        self._auto_init  = auto_init
        self._collection = None
        self._kg         = None
        self._initialized = False
        self._last_context = []

    @classmethod
    def get_instance(cls, **kw):
        if cls._instance is None: cls._instance = cls(**kw)
        return cls._instance

    def init(self):
        if self._initialized or not MEMPALACE_OK: return self._initialized
        try:
            os.makedirs(self._palace_dir, exist_ok=True)
            self._collection = get_collection(palace_path=self._palace_dir,
                collection_name="mempalace_drawers", create=True)
            self._kg = KnowledgeGraph(db_path=self._kg_path)
            self._initialized = True
            logger.info("MemPalaceHookSubscriber init OK | palace=%s", self._palace_dir)
            return True
        except Exception as e:
            logger.error("MemPalaceHookSubscriber init FAIL: %s", e)
            return False

    def register(self, eventbus=None):
        if eventbus: self._bus = eventbus
        if self._bus is None:
            try:
                from .core import get_eventbus
                self._bus = get_eventbus()
            except Exception:
                logger.error("Cannot get EventBus instance"); return False
        if not self._initialized and self._auto_init: self.init()
        for ev in [EventType.CONVERSATION_STARTED, EventType.CONVERSATION_ENDED,
                   EventType.TURN_STARTED, EventType.TURN_ENDED,
                   EventType.RESPONSE_GENERATED]:
            self._bus.subscribe_async(ev, self._on_event)
        logger.info("MemPalaceHookSubscriber registered to EventBus")
        return True

    def unregister(self):
        if self._bus:
            for ev in [EventType.CONVERSATION_STARTED, EventType.CONVERSATION_ENDED,
                       EventType.TURN_STARTED, EventType.TURN_ENDED,
                       EventType.RESPONSE_GENERATED]:
                try: self._bus.unsubscribe(ev, self._on_event)
                except Exception: pass
        logger.info("MemPalaceHookSubscriber unregistered")

    def _on_event(self, event):
        if not self._initialized: self.init()
        try:
            if   event.type == EventType.CONVERSATION_STARTED: self._on_conv_start(event)
            elif event.type == EventType.CONVERSATION_ENDED:  self._on_conv_end(event)
            elif event.type == EventType.TURN_STARTED:        self._on_turn_start(event)
            elif event.type == EventType.TURN_ENDED:          self._on_turn_end(event)
            elif event.type == EventType.RESPONSE_GENERATED:  self._on_response(event)
        except Exception as e:
            logger.error("MemPalaceHookSubscriber event error: %s", e)

    def _on_conv_start(self, event):
        p = event.payload or {}
        uid, topic, sid = p.get("user_id","default"), p.get("topic",""), p.get("session_id","")
        recalled = self._recall(query="user "+str(uid), top_k=5)
        logger.info("conversation.started user=%s topic=%s recalled=%d", uid, topic, len(recalled))
        self._write(content="[SessionStart] user="+str(uid)+" topic="+str(topic)+" session="+str(sid),
            wing=self._wing, room=("s_"+sid[:8]) if sid else "default",
            meta={"type":"conversation_started","user_id":uid,"topic":topic,"session_id":sid})
        if self._bus:
            self._bus.publish(Event(type=EventType.MEMORY_QUERIED, source="mempalace_hooks",
                payload={"session_id":sid,"recalled":len(recalled)}))

    def _on_conv_end(self, event):
        p = event.payload or {}
        sid, turns, summary = p.get("session_id",""), p.get("turn_count",0), p.get("summary","")
        logger.info("conversation.ended session=%s turns=%d", sid, turns)
        self._write(content="[SessionEnd] session="+str(sid)+" turns="+str(turns)+" summary="+str(summary),
            wing=self._wing, room=("s_"+sid[:8]) if sid else "default",
            meta={"type":"conversation_ended","session_id":sid,"turn_count":turns})

    def _on_turn_start(self, event):
        p = event.payload or {}
        query, turn = p.get("user_query",""), p.get("turn",0)
        if not query: return
        self._last_context = self._recall(query=query, top_k=3)
        logger.debug("turn.started turn=%d query=%s recalled=%d", turn, query[:40], len(self._last_context))

    def _on_turn_end(self, event):
        p = event.payload or {}
        uq, ar, turn = p.get("user_query",""), p.get("agent_response",""), p.get("turn",0)
        if not uq and not ar: return
        parts = []
        if uq: parts.append("[User]: "+str(uq))
        if ar: parts.append("[WuKong]: "+str(ar))
        self._write(content="\n".join(parts), wing=self._wing, room="general",
            meta={"type":"turn","turn":turn,"query":str(uq)[:200]})
        logger.debug("turn.ended turn=%d", turn)

    def _on_response(self, event): pass

    def _write(self, content, wing, room, meta=None):
        if not self._initialized or not self._collection: return None
        did = hashlib.sha1((content+wing+room).encode()).hexdigest()[:16]
        m = {"wing":wing,"room":room,"source_file":"eventbus_lifecycle","chunk_index":0}
        if meta:
            import json
            for k, v in meta.items():
                if isinstance(v, (dict, list, tuple)):
                    m[k] = json.dumps(v, ensure_ascii=False)
                elif v is None:
                    m[k] = ""
                else:
                    m[k] = v
        try:
            self._collection.upsert(ids=[did], documents=[content], metadatas=[m])
            if self._bus:
                self._bus.publish(Event(type=EventType.MEMORY_WRITTEN,
                    source="mempalace_hooks", payload={"drawer_id":did,"wing":wing,"room":room}))
            return did
        except Exception as e:
            logger.error("Memory write FAIL: %s", e); return None

    def _recall(self, query=None, user_id=None, topic=None, top_k=5):
        if not self._initialized or not self._collection: return []
        sq = query or (("user "+str(user_id)+" "+str(topic)) if (user_id or topic) else "")
        if not sq: return []
        try:
            r = self._collection.query(query_texts=[sq], n_results=top_k,
                include=["documents","metadatas","distances"])
            docs  = (r.get("documents",  [[]])[0] or []) if r.get("documents")  else []
            metas = (r.get("metadatas", [[]])[0] or []) if r.get("metadatas") else []
            dists = (r.get("distances", [[]])[0] or []) if r.get("distances") else []
            ids   = (r.get("ids",       [[]])[0] or []) if r.get("ids")       else []
            out = []
            for i,(doc,meta,dist) in enumerate(zip(docs,metas,dists)):
                if doc is None: continue
                sim = max(0.0, 1.0-float(dist)) if dist is not None else 0.0
                out.append({"content":doc,"score":round(sim,3),
                    "drawer_id":ids[i] if i<len(ids) else "d_"+str(i),"metadata":meta or {}})
            out.sort(key=lambda x:x["score"], reverse=True)
            return out
        except Exception as e:
            logger.error("Memory recall FAIL: %s", e); return []

    def get_last_context(self): return self._last_context
    def search(self, query, top_k=5): return self._recall(query=query, top_k=top_k)
    def write(self, content, wing=None, room="general", **kw):
        return self._write(content, wing or self._wing, room, kw)
