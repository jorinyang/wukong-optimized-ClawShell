#!/usr/bin/env python3
"""
Hermes × 悟空 双通道集成模块 (MCP主 + 文件系统备)
=====================================================

通信方式:
- 主通道: MCP stdio 协议 (tools/call: eventbus_publish/subscribe/query/stats)
- 备通道: 文件系统 ~/.real/users/{user_id}/workspace/shared/hermes_bridge/
- 自动切换: MCP 超时/失败 → 降级到文件系统

悟空配置:
- MCP Server: ~/.real/users/{user_id}/.mcp/mcpServerConfig.json
- 脚本路径: ~/.real/users/{user_id}/workspace/tmp/mcp_server.py
- HTTP Bridge: 127.0.0.1:47832
"""

import sys
import json
import time
import uuid
import os
import threading
import subprocess
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

# ============ 配置 ============

# 悟空用户目录 (根据实际情况调整)
WUKONG_USER_ID = "user-bd1b229d4eff8f6a45c456149072cb3b"
REAL_BASE = Path.home() / ".real"
WUKONG_USER_DIR = REAL_BASE / "users" / WUKONG_USER_ID
WUKONG_WORKSPACE = WUKONG_USER_DIR / "workspace"
WUKONG_MCP_CONFIG = WUKONG_USER_DIR / ".mcp" / "mcpServerConfig.json"
WUKONG_MCP_SCRIPT = WUKONG_WORKSPACE / "tmp" / "mcp_server.py"

# 备通道: 文件系统桥接目录
FS_BRIDGE_DIR = WUKONG_WORKSPACE / "shared" / "hermes_bridge"
FS_INBOX = FS_BRIDGE_DIR / "inbox"      # 悟空 → Hermes
FS_OUTBOX = FS_BRIDGE_DIR / "outbox"     # Hermes → 悟空
FS_ARCHIVE = FS_BRIDGE_DIR / "archive"   # 已处理归档

# MCP 配置
MCP_SERVER_NAME = "clawshell-mcp"
MCP_TIMEOUT = 30  # 秒
HTTP_BRIDGE_PORT = 47832

# Hermes 节点标识
HERMES_NODE_ID = "hermes-agent-primary"
HERMES_NODE_NAME = "Hermes Agent (前脑进化引擎)"


# ============ Hermes 事件定义 ============

@dataclass
class HermesInsight:
    insight_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_event_id: str = ""
    insight_type: str = "analysis"
    priority: str = "P2"
    content: str = ""
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.8
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "insight_id": self.insight_id,
            "source_event_id": self.source_event_id,
            "insight_type": self.insight_type,
            "priority": self.priority,
            "content": self.content,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


# ============ 双通道通信核心 ============

class DualChannelBridge:
    """
    双通道桥接器: MCP主 + 文件系统备
    """

    def __init__(self):
        self.channel = "mcp"  # 当前通道: mcp / filesystem
        self.mcp_process: Optional[subprocess.Popen] = None
        self.mcp_lock = threading.Lock()
        self._ok = False

        # 备通道目录初始化
        FS_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
        FS_INBOX.mkdir(exist_ok=True)
        FS_OUTBOX.mkdir(exist_ok=True)
        FS_ARCHIVE.mkdir(exist_ok=True)

        # 统计
        self.stats = {
            "mcp_calls": 0,
            "mcp_failures": 0,
            "fs_writes": 0,
            "fs_reads": 0,
            "channel_switches": 0
        }

    # ── 通道检测 ──

    def _check_mcp_available(self) -> bool:
        """检测 MCP 是否可用"""
        # 1. 检查配置文件存在
        if not WUKONG_MCP_CONFIG.exists():
            return False

        # 2. 检查脚本存在
        if not WUKONG_MCP_SCRIPT.exists():
            return False

        # 3. 检查 HTTP Bridge 端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", HTTP_BRIDGE_PORT))
            sock.close()
            return result == 0
        except:
            return False

    def _ensure_channel(self):
        """确保使用正确的通道"""
        if self.channel == "mcp" and not self._check_mcp_available():
            self.channel = "filesystem"
            self.stats["channel_switches"] += 1
            print(f"[WARN] MCP 不可用，降级到文件系统通道")
        elif self.channel == "filesystem" and self._check_mcp_available():
            self.channel = "mcp"
            self.stats["channel_switches"] += 1
            print(f"[INFO] MCP 恢复，升级到 MCP 通道")

    # ── MCP 通道 ──

    def _mcp_call(self, tool_name: str, arguments: Dict) -> Optional[Dict]:
        """通过 HTTP Bridge 调用 MCP 工具"""
        try:
            import urllib.request
            req_body = json.dumps({
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4())[:8],
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(
                f"http://127.0.0.1:{HTTP_BRIDGE_PORT}/",
                data=req_body,
                headers={"Content-Type": "application/json", "Content-Length": str(len(req_body))},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=MCP_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            self.stats["mcp_failures"] += 1
            print(f"[ERROR] MCP 调用失败: {e}")
            return None

    # ── 文件系统通道 ──

    def _fs_publish(self, event_type: str, payload: Dict, source: str = "hermes_agent") -> str:
        """通过文件系统发布事件到悟空"""
        event_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}_hermes_{event_type}_{event_id}.json"
        filepath = FS_OUTBOX / filename

        event_data = {
            "id": event_id,
            "type": event_type,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "payload": payload,
            "channel": "filesystem",
            "tags": ["hermes", event_type, "dual_channel"]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)

        self.stats["fs_writes"] += 1
        print(f"[FS] 发布事件: {event_type} → {filepath.name}")
        return event_id

    def _fs_poll(self) -> List[Dict]:
        """通过文件系统轮询悟空事件"""
        events = []
        for f in sorted(FS_INBOX.glob("*.json")):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    event = json.load(fh)
                events.append(event)
                # 归档
                archive_path = FS_ARCHIVE / f.name
                f.rename(archive_path)
                self.stats["fs_reads"] += 1
            except Exception as e:
                print(f"[ERROR] 读取 FS 事件失败: {e}")
        return events

    # ── 统一接口 ──

    def publish_event(self, event_type: str, payload: Dict, source: str = "hermes_agent") -> Optional[str]:
        """
        发布事件到悟空
        优先 MCP，失败降级文件系统
        """
        self._ensure_channel()

        if self.channel == "mcp":
            result = self._mcp_call("eventbus_publish", {
                "event_type": event_type,
                "payload": payload,
                "source": source
            })
            if result and "result" in result:
                self.stats["mcp_calls"] += 1
                event_id = result.get("result", {}).get("content", [{}])[0].get("text", "")
                try:
                    event_data = json.loads(event_id)
                    return event_data.get("event_id")
                except:
                    return event_id
            else:
                # MCP 失败，降级
                self.channel = "filesystem"
                self.stats["channel_switches"] += 1

        # 文件系统通道
        return self._fs_publish(event_type, payload, source)

    def query_events(self, event_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        查询事件历史
        优先 MCP，失败降级文件系统
        """
        self._ensure_channel()

        if self.channel == "mcp":
            result = self._mcp_call("eventbus_query", {
                "event_type": event_type,
                "limit": limit
            })
            if result and "result" in result:
                self.stats["mcp_calls"] += 1
                try:
                    text = result["result"]["content"][0]["text"]
                    data = json.loads(text)
                    return data.get("events", [])
                except:
                    pass

        # 文件系统通道: 读取 inbox + outbox
        events = []
        for d in [FS_INBOX, FS_OUTBOX, FS_ARCHIVE]:
            for f in sorted(d.glob("*.json"))[-limit:]:
                try:
                    with open(f) as fh:
                        events.append(json.load(fh))
                except:
                    pass
        return events[-limit:]

    def get_stats(self) -> Dict:
        """获取通信统计"""
        return {
            "channel": self.channel,
            **self.stats,
            "mcp_available": self._check_mcp_available(),
            "fs_bridge_dir": str(FS_BRIDGE_DIR)
        }


# ============ Hermes 悟空集成器 ============

class HermesWukongIntegration:
    """
    Hermes × 悟空 集成器
    ====================

    双通道通信:
    - MCP (主): eventbus_publish / eventbus_subscribe / eventbus_query
    - 文件系统 (备): ~/.real/users/{user}/workspace/shared/hermes_bridge/

    生态位: 前脑/进化引擎
    职责: 深度思考、洞察生成、模式识别、技能进化
    """

    def __init__(self):
        self.bridge = DualChannelBridge()
        self.running = False
        self.poll_thread = None
        self.processed_events = set()

        # 统计
        self.stats = {
            "events_received": 0,
            "insights_generated": 0,
            "skills_generated": 0
        }

        # 回调
        self.insight_callbacks: List[Callable] = []
        self.event_callbacks: List[Callable] = []

    def start(self):
        """启动集成服务"""
        if self.running:
            return
        self.running = True

        # 启动事件轮询
        self.poll_thread = threading.Thread(target=self._event_poll_loop, daemon=True)
        self.poll_thread.start()

        print("[✓] Hermes × 悟空 双通道集成已启动")
        print(f"    MCP 脚本: {WUKONG_MCP_SCRIPT}")
        print(f"    HTTP Bridge: 127.0.0.1:{HTTP_BRIDGE_PORT}")
        print(f"    FS 备通道: {FS_BRIDGE_DIR}")

    def stop(self):
        """停止集成服务"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=5)
        print("[✓] Hermes × 悟空 集成已停止")

    def _event_poll_loop(self):
        """事件轮询循环"""
        while self.running:
            try:
                self._poll_events()
                time.sleep(2.0)
            except Exception as e:
                print(f"[ERROR] 轮询错误: {e}")
                time.sleep(5)

    def _poll_events(self):
        """轮询事件 (双通道)"""
        # MCP 通道查询
        events = self.bridge.query_events(limit=10)

        for event in events:
            event_id = event.get("id", "")
            if event_id in self.processed_events:
                continue

            self.processed_events.add(event_id)
            self.stats["events_received"] += 1

            # 触发回调
            for cb in self.event_callbacks:
                try:
                    cb(event)
                except:
                    pass

            # 根据事件类型处理
            self._handle_event(event)

    def _handle_event(self, event: Dict):
        """处理悟空事件"""
        event_type = event.get("type", "")
        source = event.get("source", "")

        print(f"[→] 收到事件: {event_type} (source={source})")

        if "task.completed" in event_type:
            self._generate_task_review(event)
        elif "error" in event_type:
            self._generate_error_analysis(event)
        elif "conversation" in event_type or "turn" in event_type:
            # 悟空对话事件，记录但不处理
            pass
        else:
            self._generate_general_insight(event)

    def _generate_task_review(self, event: Dict):
        """生成任务复盘"""
        insight = HermesInsight(
            source_event_id=event.get("id", ""),
            insight_type="review",
            priority="P2",
            content="任务已完成，建议复盘执行过程",
            recommendations=["分析执行时间", "检查可自动化步骤", "评估输出质量"],
            confidence=0.85
        )
        self.publish_insight(insight)

    def _generate_error_analysis(self, event: Dict):
        """生成错误分析"""
        insight = HermesInsight(
            source_event_id=event.get("id", ""),
            insight_type="analysis",
            priority="P1",
            content="检测到错误，建议立即分析根因",
            recommendations=["检查日志", "验证配置", "评估回滚"],
            confidence=0.9
        )
        self.publish_insight(insight)

    def _generate_general_insight(self, event: Dict):
        """生成通用洞察"""
        insight = HermesInsight(
            source_event_id=event.get("id", ""),
            insight_type="analysis",
            priority="P3",
            content=f"收到事件 {event.get('type')}，已记录",
            recommendations=["等待更多数据识别模式"],
            confidence=0.6
        )
        self.publish_insight(insight)

    def publish_insight(self, insight: HermesInsight):
        """发布洞察到悟空"""
        event_id = self.bridge.publish_event(
            "hermes.insight.generated",
            insight.to_dict(),
            source="hermes_agent"
        )
        if event_id:
            self.stats["insights_generated"] += 1
            print(f"[←] 发布洞察: {insight.insight_type} ({event_id})")

            for cb in self.insight_callbacks:
                try:
                    cb(insight)
                except:
                    pass

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            **self.stats,
            "bridge": self.bridge.get_stats()
        }


# ============ 快速启动 ============

def quick_start():
    """快速启动 Hermes × 悟空 集成"""
    integration = HermesWukongIntegration()
    integration.start()
    return integration


if __name__ == "__main__":
    integration = quick_start()
    try:
        while True:
            time.sleep(1)
            stats = integration.get_stats()
            print(f"[STATS] events={stats['events_received']} insights={stats['insights_generated']} channel={stats['bridge']['channel']}")
    except KeyboardInterrupt:
        integration.stop()
