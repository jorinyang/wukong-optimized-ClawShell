"""
mcp_server.py — MemPalace + EventBus MCP Server
===============================================
同时运行两种传输层：
  1. stdio 模式   → ClawShell MCP 运行时（subprocess）
  2. HTTP Bridge  → Real 通过 mcp_runtime call_tool 调用
                    （监听 127.0.0.1:47832，双工 JSON-RPC）
所有工具注册到同一工具实例，事件直接注入 EventBus。
"""

import sys
import json
import io
import os
import threading
import logging
import traceback
import socketserver
import http.server
from datetime import datetime
from urllib.parse import parse_qs

# ── 环境隔离 ────────────────────────────────────────────────────────────────
os.environ['PYTHONWARNINGS'] = 'ignore'
import logging
logging.getLogger().handlers = [logging.NullHandler()]  # 避免 EventBus logging → stderr 阻塞
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding='utf-8')
# 注意：不重定向 sys.stderr，让 logging 输出到真实 stderr，避免进程 hang

# ── 路径配置 ────────────────────────────────────────────────────────────────
CLAWSHELL_ROOT = r"C:\Users\Aorus\.ClawShell"
sys.path.insert(0, CLAWSHELL_ROOT)

# ── 阻止 lib.core.__init__ 的 auto-register（它会在 MCP Server 环境中阻塞）
os.environ["CLAWSHELL_NO_AUTO_HOOKS"] = "1"

# ── 加载核心模块 ────────────────────────────────────────────────────────────
try:
    from lib.bridge.mempalace_mcp import MemPalaceMCPTools, get_mcp_tools as _get_tools
    from lib.core.eventbus.core  import get_eventbus, EventBus
    from lib.core.eventbus.schema import Event, EventType
    from lib.core.eventbus.lifecycle_hooks import MemPalaceHookSubscriber
    BOOT_OK = True
except ImportError as e:
    BOOT_OK = False
    print(json.dumps({"jsonrpc":"2.0","error":f"Boot failed: {e}"}, ensure_ascii=False), flush=True)

# ── 日志配置 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(io.StringIO())]
)
logger = logging.getLogger("mcp_server")

# ── 全局状态 ────────────────────────────────────────────────────────────────
HTTP_PORT   = 47832
_g_eventbus: EventBus       = None
_mempalace: MemPalaceMCPTools = None
_hooks_subscriber: MemPalaceHookSubscriber = None
_http_server = None
_stdio_lock  = threading.Lock()


# ════════════════════════════════════════════════════════════════════════════
# 工具层：MemPalace + EventBus 事件发布
# ════════════════════════════════════════════════════════════════════════════

def _build_tools() -> list:
    """构建完整工具清单（MemPalace + EventBus lifecycle）"""

    # ── MemPalace 原有工具 ──────────────────────────────────────────────────
    base_tools = _get_tools()

    # ── EventBus lifecycle 事件发布工具 ─────────────────────────────────────
    lifecycle_tools = [
        {
            "name": "eventbus_publish",
            "description": "发布事件到 ClawShell EventBus（内部 Python 消息总线）。"
                          "用于将 Real 端的对话生命周期事件注入 Python 事件流，"
                          "触发 MemPalaceHookSubscriber 等订阅者。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": (
                            "事件类型。可用值：\n"
                            "  conversation.started    — 对话开始\n"
                            "  conversation.ended       — 对话结束\n"
                            "  turn.started             — 轮次开始（用户发消息）\n"
                            "  turn.ended               — 轮次结束（助手回复完毕）\n"
                            "  response.generated       — 响应已生成\n"
                            "  task.started             — 任务开始\n"
                            "  task.completed           — 任务完成\n"
                            "  memory.written           — 记忆已写入\n"
                            "  memory.queried           — 记忆已查询\n"
                            "  error.occurred           — 错误发生\n"
                            "  custom                   — 自定义类型"
                        )
                    },
                    "payload": {
                        "type": "object",
                        "description": "事件负载数据",
                        "properties": {
                            "user_id":     {"type": "string",  "description": "用户 ID"},
                            "session_id":  {"type": "string",  "description": "会话 ID"},
                            "topic":       {"type": "string",  "description": "对话主题"},
                            "turn":        {"type": "integer", "description": "轮次编号"},
                            "user_query":  {"type": "string",  "description": "用户本轮输入"},
                            "agent_response": {"type": "string", "description": "助手回复"},
                            "turn_count":  {"type": "integer", "description": "总轮次数"},
                            "summary":     {"type": "string",  "description": "对话摘要"},
                            "task_id":     {"type": "string",  "description": "任务 ID"},
                            "error":       {"type": "string",  "description": "错误信息"},
                            "extra":       {"type": "object",  "description": "其他扩展字段"}
                        }
                    },
                    "source": {
                        "type": "string",
                        "description": "事件来源标识，默认为 'mcp_runtime'",
                        "default": "mcp_runtime"
                    },
                    "trace_id": {
                        "type": "string",
                        "description": "追踪 ID（可选）"
                    }
                },
                "required": ["event_type"]
            }
        },
        {
            "name": "eventbus_subscribe",
            "description": "为当前会话订阅 EventBus 事件回调。"
                          "当 EventBus 收到匹配事件时，回调内容会被追加到响应中返回。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "要订阅的事件类型（与 eventbus_publish 相同）"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "订阅者的会话 ID，用于路由回调"
                    }
                },
                "required": ["event_type", "session_id"]
            }
        },
        {
            "name": "eventbus_query",
            "description": "查询 EventBus 历史事件（最近 N 条）",
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "按事件类型过滤（可选）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量上限",
                        "default": 20
                    }
                }
            }
        },
        {
            "name": "eventbus_stats",
            "description": "获取 EventBus 运行统计（订阅者数、事件总数、各类型计数）",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "mempalace_register_hooks",
            "description": "将 MemPalaceHookSubscriber 注册到 EventBus。"
                          "注册后，所有 lifecycle 事件（conversation.started 等）"
                          "会自动触发 MemPalace 记忆写入。",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "mempalace_hooks_status",
            "description": "查询 MemPalaceHookSubscriber 注册状态",
            "input_schema": {"type": "object", "properties": {}}
        }
    ]

    return base_tools + lifecycle_tools


# ════════════════════════════════════════════════════════════════════════════
# 工具执行器
# ════════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """统一执行 MemPalace + EventBus 工具"""

    def __init__(self):
        global _g_eventbus, _mempalace, _hooks_subscriber

        if not BOOT_OK:
            self._ok = False
            return
        self._ok = True

        # EventBus
        _g_eventbus = get_eventbus()
        _g_eventbus.start_async_processing()
        logger.info("EventBus started (async)")

        # MemPalace
        _mempalace = MemPalaceMCPTools()
        logger.info("MemPalaceMCPTools initialized")

        # HooksSubscriber（延迟注册，需显式调用）
        _hooks_subscriber = MemPalaceHookSubscriber.get_instance(
            eventbus=_g_eventbus,
            wing="wukong",
            auto_init=True
        )

    def call(self, name: str, arguments: dict) -> dict:
        try:
            # ── MemPalace 原有工具 ────────────────────────────────────────
            if name.startswith("mempalace_") and name != "mempalace_register_hooks" \
                                            and name != "mempalace_hooks_status":
                return _mempalace.call_tool(name, arguments)

            # ── EventBus 工具 ─────────────────────────────────────────────
            if name == "eventbus_publish":
                return self._publish_event(arguments)
            if name == "eventbus_subscribe":
                return self._subscribe_event(arguments)
            if name == "eventbus_query":
                return self._query_events(arguments)
            if name == "eventbus_stats":
                return self._get_stats()
            if name == "mempalace_register_hooks":
                return self._register_hooks()
            if name == "mempalace_hooks_status":
                return self._get_hooks_status()

            return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            logger.exception(f"Tool call failed: {name}")
            return {"error": str(e), "trace": traceback.format_exc()}

    # ── EventBus 实现 ────────────────────────────────────────────────────────

    def _publish_event(self, args: dict) -> dict:
        event_type_str = args.get("event_type", "custom")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.CUSTOM

        payload = args.get("payload") or {}
        event = Event(
            type=event_type,
            source=args.get("source", "mcp_runtime"),
            payload=payload,
            trace_id=args.get("trace_id"),
            tags=["mcp_published"]
        )

        _g_eventbus.publish(event)

        return {
            "event_id": event.id,
            "event_type": event_type.value,
            "published_at": event.timestamp,
            "subscribers_notified": True,
            "message": f"Event '{event_type.value}' published successfully"
        }

    def _subscribe_event(self, args: dict) -> dict:
        session_id = args.get("session_id", "default")
        event_type_str = args.get("event_type", "custom")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.CUSTOM

        # 将 session_id 存入 payload，订阅者可通过此识别回调归属
        def session_callback(event: Event):
            logger.info(f"[Callback→{session_id}] {event.type.value}: {str(event.payload)[:80]}")

        _g_eventbus.subscribe(event_type, session_callback)
        return {
            "subscribed": True,
            "event_type": event_type.value,
            "session_id": session_id,
            "message": f"Subscribed to '{event_type.value}' for session '{session_id}'"
        }

    def _query_events(self, args: dict) -> dict:
        event_type_str = args.get("event_type")
        limit = args.get("limit", 20)

        if event_type_str:
            try:
                et = EventType(event_type_str)
            except ValueError:
                et = None
        else:
            et = None

        history = _g_eventbus.get_history(event_type=et, limit=limit)
        return {
            "events": [e.to_dict() for e in history],
            "count": len(history)
        }

    def _get_stats(self) -> dict:
        stats = _g_eventbus.get_stats()
        stats["hooks_registered"] = (
            _hooks_subscriber._initialized
            if _hooks_subscriber else False
        )
        return stats

    # ── MemPalace Hooks ────────────────────────────────────────────────────

    def _register_hooks(self) -> dict:
        if not _hooks_subscriber:
            return {"error": "HooksSubscriber not initialized", "registered": False}

        ok = _hooks_subscriber.register(eventbus=_g_eventbus)
        if ok:
            logger.info("MemPalaceHookSubscriber registered to EventBus ✓")
        return {
            "registered": ok,
            "message": "MemPalaceHookSubscriber registered" if ok
                       else "Registration failed (check logs)"
        }

    def _get_hooks_status(self) -> dict:
        if not _hooks_subscriber:
            return {"initialized": False, "registered": False}

        return {
            "initialized": _hooks_subscriber._initialized,
            "palace_dir":  _hooks_subscriber._palace_dir,
            "wing":        _hooks_subscriber._wing,
            "collection_exists": _hooks_subscriber._collection is not None,
        }


# ════════════════════════════════════════════════════════════════════════════
# HTTP Bridge 层（socketserver，双工 JSON-RPC）
# ════════════════════════════════════════════════════════════════════════════

class JSONRPCHandler(socketserver.BaseRequestHandler):
    """处理 HTTP POST / JSON-RPC 请求"""

    def handle(self):
        try:
            # ── 读取完整 HTTP 请求（先 header，再按 Content-Length 读 body）──
            data = b""
            header_end = b"\r\n\r\n"
            while header_end not in data:
                chunk = self.request.recv(1)
                if not chunk:
                    break
                data += chunk
                if len(data) > 8192:  # 防恶意构造
                    self._respond({"jsonrpc":"2.0","error":"Header too large"}, status=400)
                    return

            header_text = data.decode("utf-8", errors="replace")
            header_end_idx = header_text.index("\r\n\r\n") if "\r\n\r\n" in header_text else len(header_text)
            headers = {}
            for line in header_text[:header_end_idx].split("\r\n"):
                if ": " in line:
                    k, v = line.split(": ", 1)
                    headers[k.strip().lower()] = v.strip()

            body_len = int(headers.get("content-length", 0))
            body_received = data[header_end_idx + 4:]  # 已在 buffer 中的 body
            while len(body_received) < body_len:
                body_received += self.request.recv(body_len - len(body_received))
            body_text = body_received.decode("utf-8", errors="replace").strip()

            if not body_text:
                self._respond({"jsonrpc":"2.0","error":"Empty body"}, status=400)
                return

            req = json.loads(body_text)
            method  = req.get("method", "")
            req_id  = req.get("id")
            params  = req.get("params", {})

            logger.debug(f"HTTP RPC: method={method} id={req_id}")

            # ── 工具列表 ────────────────────────────────────────────────────
            if method == "tools/list":
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"tools": _build_tools()}
                })

            # ── 工具调用 ────────────────────────────────────────────────────
            elif method == "tools/call":
                name = params.get("name", "")
                args = params.get("arguments", {})
                result = executor.call(name, args)
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text",
                        "text": json.dumps(result, ensure_ascii=False)}]}
                })

            # ── 健康检查 ────────────────────────────────────────────────────
            elif method == "health":
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "status": "ok",
                        "eventbus": _g_eventbus.get_stats() if _g_eventbus else {},
                        "booted": BOOT_OK,
                        "server": "mcp_server v1.0 (HTTP Bridge)",
                        "http_port": HTTP_PORT,
                        "stdio_running": True
                    }
                })

            # ── 发布事件的快捷端点 ─────────────────────────────────────────
            elif method == "publish":
                # 快捷调用：{method:"publish", params:{event_type:"...",payload:{...}}}
                result = executor.call("eventbus_publish", params)
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text",
                        "text": json.dumps(result, ensure_ascii=False)}]}
                })

            # ── EventBus 统计（快捷端点）─────────────────────────────────────
            elif method == "eventbus_stats":
                result = executor.call("eventbus_stats", params)
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text",
                        "text": json.dumps(result, ensure_ascii=False)}]}
                })

            else:
                self._respond({
                    "jsonrpc": "2.0", "id": req_id,
                    "error": f"Unknown method: {method}"
                }, status=404)

        except json.JSONDecodeError as e:
            self._respond({"jsonrpc": "2.0", "error": f"JSON decode error: {e}"}, status=400)
        except Exception as e:
            logger.exception("HTTP handler error")
            self._respond({"jsonrpc": "2.0", "error": str(e)}, status=500)

    def _respond(self, body: dict, status: int = 200):
        body_str = json.dumps(body, ensure_ascii=False)
        response = (
            f"HTTP/1.1 {status} OK\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body_str.encode('utf-8'))}\r\n"
            f"Connection: close\r\n"
            f"\r\n{body_str}"
        )
        self.request.sendall(response.encode("utf-8"))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """允许多线程并发，长连接"""
    allow_reuse_address = True
    daemon_threads = True


def _run_http_bridge():
    """HTTP Bridge 线程入口"""
    global _http_server
    try:
        _http_server = ThreadedHTTPServer(
            ("127.0.0.1", HTTP_PORT), JSONRPCHandler
        )
        logger.info(f"HTTP Bridge listening on http://127.0.0.1:{HTTP_PORT}")
        _http_server.serve_forever()
    except OSError as e:
        if e.errno == 10048:  # 端口已被占用
            logger.warning(f"HTTP port {HTTP_PORT} already in use — HTTP Bridge skipped")
        else:
            logger.error(f"HTTP Bridge failed: {e}")


# ════════════════════════════════════════════════════════════════════════════
# STDIO 主循环
# ════════════════════════════════════════════════════════════════════════════

def _run_stdio():
    """stdio 主循环——标准 MCP 协议"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.info("STDIN closed — exiting")
                break

            req = json.loads(line.strip())
            method = req.get("method", "")
            req_id  = req.get("id")
            params  = req.get("params", {})

            logger.debug(f"STDIO RPC: method={method} id={req_id}")

            # 初始化
            if method == "initialize":
                print(json.dumps({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "mempalace-eventbus",
                            "version": "1.0.0"
                        }
                    }
                }, ensure_ascii=False), flush=True)

            # 工具列表
            elif method == "tools/list":
                print(json.dumps({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"tools": _build_tools()}
                }, ensure_ascii=False), flush=True)

            # 工具调用
            elif method == "tools/call":
                name = params.get("name", "")
                args = params.get("arguments", {})
                result = executor.call(name, args)
                print(json.dumps({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "content": [{"type": "text",
                            "text": json.dumps(result, ensure_ascii=False)}]
                    }
                }, ensure_ascii=False), flush=True)

            # 通知（无需响应）
            elif method in ("initialized", "notifications/initialized",
                            "workspace/ Diagnostic"):
                pass  # 空响应

            else:
                print("", flush=True)

        except json.JSONDecodeError as e:
            try:
                print(json.dumps({
                    "jsonrpc": "2.0", "error": f"JSON error: {e}"
                }), flush=True)
            except Exception:
                pass
        except Exception:
            logger.exception("stdio loop error")
            try:
                print(json.dumps({
                    "jsonrpc": "2.0", "error": traceback.format_exc()
                }), flush=True)
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(json.dumps({
        "jsonrpc": "2.0",
        "method": "server/info",
        "result": {
            "name": "mempalace-eventbus",
            "version": "1.0.0",
            "boot_ok": BOOT_OK,
            "http_port": HTTP_PORT
        }
    }, ensure_ascii=False), flush=True)

    if not BOOT_OK:
        logger.error("Boot failed — exiting")
        sys.exit(1)

    executor = ToolExecutor()

    # 启动 HTTP Bridge（后台线程）
    http_thread = threading.Thread(target=_run_http_bridge, daemon=True, name="HTTP-Bridge")
    http_thread.start()

    logger.info("MCP Server ready — stdio + HTTP Bridge running")

    # stdio 主循环（阻塞）
    _run_stdio()
