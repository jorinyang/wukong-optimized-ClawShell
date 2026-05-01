"""
mempalace_mcp.py — MemPalace MCP Server 适配层
===============================================
将 MemPalace 桥接层的工具注册为标准 MCP 工具格式，
供 ClawShell 能力发现系统使用。

使用方法:
    # 在 ClawShell 配置中注册
    from lib.bridge.mempalace_mcp import get_mcp_tools, MemPalaceMCPTools
    
    # 获取所有 MCP 工具
    tools = get_mcp_tools()
"""
from typing import Any, Optional
import logging

logger = logging.getLogger('mempalace_mcp')

# MCP 工具清单（符合 MCP 工具规范）
MCP_TOOLS = [
    {
        "name": "mempalace_write_memory",
        "description": "将对话上下文写入 MemPalace 长期记忆（层级结构：Wing → Room → Drawer）",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "记忆内容文本"
                },
                "wing": {
                    "type": "string",
                    "description": "记忆翼（维度），如 'clawshell'、'agent_001'、用户ID等",
                    "default": "clawshell"
                },
                "room": {
                    "type": "string", 
                    "description": "记忆房间（话题），如 'conversation'、'tasks'、'decisions'",
                    "default": "general"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签列表"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "mempalace_search",
        "description": "混合搜索（BM25 + 向量语义）在 MemPalace 记忆库中召回相关内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询文本"
                },
                "wing": {
                    "type": "string",
                    "description": "限定记忆翼范围（可选）"
                },
                "room": {
                    "type": "string",
                    "description": "限定记忆房间范围（可选）"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "mempalace_add_fact",
        "description": "向 MemPalace 知识图谱写入结构化事实三元组（主语-谓语-宾语）",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "主语（实体名称）"
                },
                "predicate": {
                    "type": "string",
                    "description": "谓语（关系），如 'related_to'、'has_type'、'created_by'"
                },
                "object": {
                    "type": "string",
                    "description": "宾语（另一个实体或属性值）"
                },
                "confidence": {
                    "type": "number",
                    "description": "置信度 0-1",
                    "default": 1.0
                }
            },
            "required": ["subject", "predicate", "object"]
        }
    },
    {
        "name": "mempalace_query_facts",
        "description": "查询知识图谱中某实体的所有关系事实",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": "实体名称"
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "description": "关系方向",
                    "default": "both"
                }
            },
            "required": ["entity"]
        }
    },
    {
        "name": "mempalace_recall_recent",
        "description": "获取最近的记忆条目（按时间倒序）",
        "input_schema": {
            "type": "object",
            "properties": {
                "wing": {
                    "type": "string",
                    "description": "记忆翼",
                    "default": "clawshell"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量上限",
                    "default": 10
                }
            }
        }
    },
    {
        "name": "mempalace_write_conversation",
        "description": "将对话历史批量写入记忆",
        "input_schema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "消息列表，每个消息包含 role 和 content",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    }
                },
                "wing": {
                    "type": "string",
                    "description": "记忆翼",
                    "default": "clawshell"
                },
                "room": {
                    "type": "string",
                    "description": "记忆房间",
                    "default": "conversation"
                }
            },
            "required": ["messages"]
        }
    },
    {
        "name": "mempalace_sync_genome",
        "description": "将 ClawShell Genome 工作记忆同步到 MemPalace 长期存储",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "mempalace_register_agent",
        "description": "为 ClawShell 子 Agent 注册独立记忆翼",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent 标识符"
                },
                "wing": {
                    "type": "string",
                    "description": "记忆翼名称（可选，默认 agent_{agent_id}）"
                }
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "mempalace_health",
        "description": "获取 MemPalace 桥接层健康状态",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


class MemPalaceMCPTools:
    """
    MemPalace MCP 工具执行器
    
    将 MCP 工具调用路由到 MemPalaceBridge 实例。
    """
    
    def __init__(self, bridge=None):
        self._bridge = bridge
    
    @property
    def bridge(self):
        """延迟加载桥接层"""
        if self._bridge is None:
            from lib.bridge.mempalace_bridge import MemPalaceBridge
            self._bridge = MemPalaceBridge.get_instance()
            self._bridge.init()
        return self._bridge
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """
        执行 MCP 工具调用
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            符合 MCP 规范的响应
        """
        try:
            if name == "mempalace_write_memory":
                return self._write_memory(arguments)
            elif name == "mempalace_search":
                return self._search(arguments)
            elif name == "mempalace_add_fact":
                return self._add_fact(arguments)
            elif name == "mempalace_query_facts":
                return self._query_facts(arguments)
            elif name == "mempalace_recall_recent":
                return self._recall_recent(arguments)
            elif name == "mempalace_write_conversation":
                return self._write_conversation(arguments)
            elif name == "mempalace_sync_genome":
                return self._sync_genome(arguments)
            elif name == "mempalace_register_agent":
                return self._register_agent(arguments)
            elif name == "mempalace_health":
                return self._health(arguments)
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            logger.exception(f"工具调用失败: {name}")
            return {"error": str(e)}
    
    def _write_memory(self, args: dict) -> dict:
        result = self.bridge.write_context(
            content=args["content"],
            wing=args.get("wing"),
            room=args.get("room", "general"),
            tags=args.get("tags")
        )
        return {"drawer_id": result, "success": result is not None}
    
    def _search(self, args: dict) -> dict:
        results = self.bridge.search(
            query=args["query"],
            wing=args.get("wing"),
            room=args.get("room"),
            top_k=args.get("limit", 5)
        )
        return {"results": results, "count": len(results)}
    
    def _add_fact(self, args: dict) -> dict:
        result = self.bridge.add_fact(
            subject=args["subject"],
            predicate=args["predicate"],
            obj=args["object"],
            confidence=args.get("confidence", 1.0)
        )
        return {"fact_id": result, "success": result is not None}
    
    def _query_facts(self, args: dict) -> dict:
        results = self.bridge.query_fact(
            entity=args["entity"],
            direction=args.get("direction", "both")
        )
        return {"facts": results, "count": len(results)}
    
    def _recall_recent(self, args: dict) -> dict:
        results = self.bridge.recall_recent(
            wing=args.get("wing", "clawshell"),
            limit=args.get("limit", 10)
        )
        return {"memories": results, "count": len(results)}
    
    def _write_conversation(self, args: dict) -> dict:
        result = self.bridge.write_conversation(
            messages=args["messages"],
            wing=args.get("wing", "clawshell"),
            room=args.get("room", "conversation")
        )
        return {"drawer_id": result, "success": result is not None}
    
    def _sync_genome(self, args: dict) -> dict:
        result = self.bridge.sync_genome_to_memory()
        return {"success": result}
    
    def _register_agent(self, args: dict) -> dict:
        wing = self.bridge.register_agent(
            agent_id=args["agent_id"],
            wing=args.get("wing")
        )
        return {"wing": wing}
    
    def _health(self, args: dict) -> dict:
        return self.bridge.health_check()


def get_mcp_tools():
    """获取所有 MemPalace MCP 工具定义"""
    return MCP_TOOLS


def create_mcp_server():
    """创建 MCP Server 实例"""
    return MemPalaceMCPTools()
