import time
"""
MemPalace MCP Tools - 记忆宫殿 MCP 工具接口
============================================

提供 memory_search, memory_write, memory_recall 等工具。
"""

import sys
import json
import traceback
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MemPalaceMCP")

# 确保路径正确
CLAWSHELL_ROOT = Path(__file__).parent.parent.parent
if str(CLAWSHELL_ROOT) not in sys.path:
    sys.path.insert(0, str(CLAWSHELL_ROOT))

from lib.bridge.persistence.mempalace_bridge import MemPalaceBridge


class MemPalaceMCPTools:
    """
    MemPalace MCP 工具集
    
    提供悟空与记忆宫殿之间的接口。
    """
    
    def __init__(self):
        self._bridge = None
        self._chroma_client = None
        self._embedding_fn = None
        self._chroma_collection = None
        self._init_bridge()
        self._init_vector_search()
    
    def _init_bridge(self):
        """初始化 SQLite Bridge"""
        try:
            self._bridge = MemPalaceBridge()
        except Exception as e:
            logger.warning("[MemPalaceMCP] Bridge初始化失败")
            self._bridge = None
    
    def _init_vector_search(self):
        """初始化向量搜索 (ChromaDB)"""
        self._chroma_client = None
        self._chroma_collection = None
        self._embedding_fn = None
        try:
            import chromadb
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
            
            # ChromaDB 1.5.8 API
            self._chroma_client = chromadb.Client()
            self._embedding_fn = ONNXMiniLM_L6_V2()
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="wukong_memories",
                embedding_function=self._embedding_fn,
                metadata={"description": "悟空记忆向量库"}
            )
            print(f"[MemPalaceMCP] 向量搜索已就绪，模型: ONNXMiniLM-L6-v2 (384维)")
        except ImportError:
            print("[MemPalaceMCP] ChromaDB 未安装，向量搜索不可用")
        except Exception as e:
            print(f"[MemPalaceMCP] ChromaDB初始化失败: {e}")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定工具"""
        method_map = {
            "memory_search": self._search,
            "memory_write": self._write,
            "memory_recall": self._recall,
            "memory_list": self._list,
            "memory_stats": self._stats,
            "memory_delete": self._delete,
        }
        
        handler = method_map.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return handler(arguments)
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}
    
    def _search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        语义搜索记忆
        
        参数:
            query: 搜索查询文本
            limit: 返回数量限制 (默认5)
            mode: 搜索模式 "semantic" 或 "keyword" (默认"semantic")
        """
        query = args.get("query", "")
        limit = min(args.get("limit", 5), 20)
        mode = args.get("mode", "semantic")
        
        if not query:
            return {"error": "query is required"}
        
        # 优先使用向量搜索
        if mode == "semantic" and self._chroma_collection:
            try:
                results = self._chroma_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                memories = []
                if results and results.get("documents"):
                    for i, doc in enumerate(results["documents"][0]):
                        metadata = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                        memories.append({
                            "id": results["ids"][0][i] if results.get("ids") else f"result_{i}",
                            "content": doc,
                            "distance": results["distances"][0][i] if results.get("distances") else 0,
                            "metadata": metadata
                        })
                
                return {
                    "results": memories,
                    "mode": "semantic",
                    "query": query,
                    "count": len(memories)
                }
            except Exception as e:
                logger.warning("[MemPalaceMCP] 向量搜索失败，回退到关键词")
        
        # 关键词搜索 (fallback)
        if self._bridge:
            raw_results = self._bridge.search(query)
            return {
                "results": raw_results[:limit],
                "mode": "keyword",
                "query": query,
                "count": len(raw_results)
            }
        
        return {"error": "No search backend available", "results": []}
    
    def _write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        写入记忆
        
        参数:
            content: 记忆内容
            key: 可选的记忆键名
            metadata: 可选的元数据
            enable_vector: 是否启用向量索引 (默认True)
        """
        content = args.get("content", "")
        key = args.get("key") or f"memory_{int(time.time() * 1000)}"
        metadata = args.get("metadata", {})
        enable_vector = args.get("enable_vector", True)
        
            
        if not content:
            return {"error": "content is required"}
        
        # SQLite 持久化
        if self._bridge:
            self._bridge.save(key, content)
        
        # 向量索引
        vector_id = None
        if enable_vector and self._chroma_collection:
            try:
                vector_id = f"vec_{key}"
                self._chroma_collection.add(
                    documents=[content],
                    ids=[vector_id],
                    metadatas=[{
                        "key": key,
                        "created_at": time.time(),
                        **metadata
                    }]
                )
            except Exception as e:
                logger.warning("[MemPalaceMCP] 向量索引失败")
        
        return {
            "success": True,
            "key": key,
            "vector_id": vector_id,
            "content_preview": content[:200]
        }
    
    def _recall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        精确回忆 (按键名获取)
        
        参数:
            key: 记忆键名
        """
        key = args.get("key")
        
        if not key:
            return {"error": "key is required"}
        
        if self._bridge:
            value = self._bridge.load(key)
            if value:
                return {"key": key, "content": value, "found": True}
        
        return {"key": key, "content": None, "found": False}
    
    def _list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出记忆
        
        参数:
            limit: 返回数量限制
            offset: 偏移量
        """
        limit = min(args.get("limit", 50), 200)
        offset = args.get("offset", 0)
        
        if self._bridge:
            try:
                import sqlite3
                conn = sqlite3.connect(str(self._bridge.db_path))
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT key, value, created_at FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?',
                    (limit, offset)
                )
                rows = cursor.fetchall()
                conn.close()
                
                return {
                    "memories": [
                        {"key": r[0], "content": r[1][:200], "created_at": r[2]}
                        for r in rows
                    ],
                    "count": len(rows)
                }
            except Exception as e:
                return {"error": str(e)}
        
        return {"memories": [], "count": 0}
    
    def _stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取记忆统计"""
        stats = {
            "bridge_available": self._bridge is not None,
            "vector_search_available": self._chroma_collection is not None,
            "palace_dir": str(self._bridge.db_path) if self._bridge else None if self._bridge else None
        }
        
        if self._bridge:
            try:
                import sqlite3
                conn = sqlite3.connect(str(self._bridge.db_path))
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM memories')
                stats["total_memories"] = cursor.fetchone()[0]
                conn.close()
            except:
                stats["total_memories"] = 0
        
        return stats
    
    def _delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """删除记忆"""
        key = args.get("key")
        
        if not key:
            return {"error": "key is required"}
        
        # SQLite 删除
        if self._bridge:
            try:
                import sqlite3
                conn = sqlite3.connect(str(self._bridge.db_path))
                cursor = conn.cursor()
                cursor.execute('DELETE FROM memories WHERE key = ?', (key,))
                conn.commit()
                conn.close()
            except Exception as e:
                return {"error": str(e)}
        
        # 向量删除
        if self._chroma_collection:
            try:
                self._chroma_collection.delete(ids=[f"vec_{key}"])
            except:
                pass
        
        return {"success": True, "key": key}


# ─────────────────────────────────────────────────────────────────────────────
# MCP 工具清单
# ─────────────────────────────────────────────────────────────────────────────

def get_mcp_tools() -> List[Dict[str, Any]]:
    """返回 MCP 工具清单"""
    return [
        {
            "name": "memory_search",
            "description": "在记忆宫殿中语义搜索历史记忆。支持向量相似度搜索和关键词搜索。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询文本"},
                    "limit": {"type": "integer", "description": "返回结果数量限制", "default": 5},
                    "mode": {"type": "string", "description": "搜索模式: semantic/keyword", "default": "semantic"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "memory_write",
            "description": "将重要信息写入记忆宫殿持久化存储。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要记忆的内容"},
                    "key": {"type": "string", "description": "可选的记忆键名"},
                    "metadata": {"type": "object", "description": "可选的元数据"},
                    "enable_vector": {"type": "boolean", "description": "是否启用向量索引", "default": True}
                },
                "required": ["content"]
            }
        },
        {
            "name": "memory_recall",
            "description": "精确回忆 - 通过键名精确获取记忆内容。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆键名"}
                },
                "required": ["key"]
            }
        },
        {
            "name": "memory_list",
            "description": "列出记忆宫殿中的所有记忆。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回数量限制", "default": 50},
                    "offset": {"type": "integer", "description": "偏移量", "default": 0}
                }
            }
        },
        {
            "name": "memory_stats",
            "description": "获取记忆宫殿统计信息。",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "memory_delete",
            "description": "删除指定记忆。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "要删除的记忆键名"}
                },
                "required": ["key"]
            }
        }
    ]
