#!/usr/bin/env python3
"""
ClawShell Swarm动态发现引擎
版本: v0.2.1-B
功能: 实现节点的自动发现和零配置接入
依赖: NodeRegistry
"""

import json
import logging
import time
import socket
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .node_registry import NodeRegistry, Node, NodeType, NodeStatus

logger = logging.getLogger(__name__)


# ============ 发现协议定义 ============

class DiscoveryProtocol:
    """发现协议"""

    # 消息类型
    ANNOUNCE = "node_announce"
    DISCOVERY_REQUEST = "node_discovery_request"
    DISCOVERY_RESPONSE = "node_discovery_response"
    HEARTBEAT = "node_heartbeat"
    GOODBYE = "node_goodbye"

    # 配置
    GOSSIP_INTERVAL = 30      # 广播间隔（秒）
    HEARTBEAT_INTERVAL = 10   # 心跳间隔（秒）
    NODE_TIMEOUT = 60         # 节点超时（秒）
    BROADCAST_PORT = 45678    # 广播端口


@dataclass
class DiscoveryMessage:
    """发现消息"""
    type: str
    node_id: str
    node_name: str
    node_type: str
    capabilities: List[str]
    endpoint: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3  # 消息生存时间

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "capabilities": self.capabilities,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "ttl": self.ttl
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DiscoveryMessage":
        return cls(**data)


class SwarmDiscovery:
    """
    Swarm动态发现引擎
    ===================

    功能：
    - 节点自动发现
    - 零配置接入
    - Gossip协议传播
    - 心跳保活

    使用示例：
        discovery = SwarmDiscovery(node_registry)

        # 启动发现服务
        discovery.start()

        # 广播自身节点
        discovery.announce_self()

        # 停止
        discovery.stop()
    """

    def __init__(
        self,
        node_registry: NodeRegistry,
        broadcast_port: int = DiscoveryProtocol.BROADCAST_PORT,
        gossip_interval: int = DiscoveryProtocol.GOSSIP_INTERVAL
    ):
        self.node_registry = node_registry
        self.broadcast_port = broadcast_port
        self.gossip_interval = gossip_interval

        # 运行状态
        self.running = False
        self.gossip_thread: Optional[threading.Thread] = None
        self.udp_socket = None

        # 已发现的节点
        self.known_nodes: Dict[str, float] = {}  # node_id -> last_seen

        # 事件回调
        self.callbacks: Dict[str, List[Callable]] = {}

        logger.info("SwarmDiscovery initialized")
        logger.info(f"Broadcast port: {broadcast_port}")

    def start(self):
        """启动发现服务"""
        if self.running:
            logger.warning("SwarmDiscovery already running")
            return

        self.running = True

        # 启动UDP socket
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.settimeout(1.0)
            self.udp_socket.bind(('0.0.0.0', self.broadcast_port))
            logger.info(f"UDP socket bound to port {self.broadcast_port}")
        except Exception as e:
            logger.error(f"Failed to bind UDP socket: {e}")
            self.udp_socket = None

        # 启动Gossip线程
        self.gossip_thread = threading.Thread(target=self._gossip_loop, daemon=True)
        self.gossip_thread.start()

        logger.info("SwarmDiscovery started")

    def stop(self):
        """停止发现服务"""
        if not self.running:
            return

        self.running = False

        # 发送GOODBYE消息
        self._send_goodbye()

        # 关闭socket
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
            self.udp_socket = None

        # 等待线程结束
        if self.gossip_thread:
            self.gossip_thread.join(timeout=5)

        logger.info("SwarmDiscovery stopped")

    def announce_self(self):
        """广播自身节点"""
        # 获取本节点信息
        local_node = self._get_local_node_info()
        if not local_node:
            logger.warning("No local node to announce")
            return

        message = DiscoveryMessage(
            type=DiscoveryProtocol.ANNOUNCE,
            node_id=local_node["node_id"],
            node_name=local_node["node_name"],
            node_type=local_node["node_type"],
            capabilities=local_node["capabilities"],
            endpoint=local_node.get("endpoint"),
            metadata=local_node.get("metadata", {})
        )

        self._broadcast(message)

    def _get_local_node_info(self) -> Optional[Dict]:
        """获取本节点信息"""
        # 从NodeRegistry获取本地注册的节点
        for node in self.node_registry.nodes.values():
            if node.endpoint and ("localhost" in node.endpoint or "127.0.0.1" in node.endpoint):
                return {
                    "node_id": node.id,
                    "node_name": node.name,
                    "node_type": node.type.value,
                    "capabilities": node.capabilities,
                    "endpoint": node.endpoint,
                    "metadata": node.metadata
                }

        # 如果没有本地节点，创建一个虚拟的
        hostname = socket.gethostname()
        return {
            "node_id": f"local_{hostname}",
            "node_name": f"Local ({hostname})",
            "node_type": NodeType.OPENCLAW.value,
            "capabilities": ["local"],
            "endpoint": f"http://localhost:{self.broadcast_port}",
            "metadata": {}
        }

    def _gossip_loop(self):
        """Gossip协议主循环"""
        while self.running:
            try:
                # 1. 发送自身的广播
                self.announce_self()

                # 2. 接收其他节点的广播
                self._receive_broadcasts()

                # 3. 清理超时的节点
                self._cleanup_timedout_nodes()

                # 4. 等待下一个间隔
                time.sleep(self.gossip_interval)

            except Exception as e:
                logger.error(f"Gossip loop error: {e}")
                time.sleep(5)

    def _broadcast(self, message: DiscoveryMessage):
        """广播消息"""
        if not self.udp_socket:
            return

        try:
            data = json.dumps(message.to_dict()).encode('utf-8')
            self.udp_socket.sendto(
                data,
                ('<broadcast>', self.broadcast_port)
            )
            logger.debug(f"Broadcast sent: {message.type} from {message.node_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast: {e}")

    def _receive_broadcasts(self):
        """接收广播消息"""
        if not self.udp_socket:
            return

        try:
            while True:
                try:
                    data, addr = self.udp_socket.recvfrom(4096)
                    message = DiscoveryMessage.from_dict(json.loads(data.decode('utf-8')))
                    self._handle_message(message)
                except socket.timeout:
                    break
        except Exception as e:
            logger.error(f"Failed to receive broadcasts: {e}")

    def _handle_message(self, message: DiscoveryMessage):
        """处理发现消息"""
        # 跳过自身消息
        if message.node_id == getattr(self, '_local_node_id', None):
            return

        # 更新已知节点
        self.known_nodes[message.node_id] = time.time()

        if message.type == DiscoveryProtocol.ANNOUNCE:
            self._handle_announce(message)
        elif message.type == DiscoveryProtocol.DISCOVERY_REQUEST:
            self._handle_discovery_request(message)
        elif message.type == DiscoveryProtocol.HEARTBEAT:
            self._handle_heartbeat(message)
        elif message.type == DiscoveryProtocol.GOODBYE:
            self._handle_goodbye(message)

    def _handle_announce(self, message: DiscoveryMessage):
        """处理节点广播"""
        # 检查节点是否已注册
        existing = self.node_registry.get(message.node_id)

        if not existing:
            # 注册新节点
            node = Node(
                id=message.node_id,
                name=message.node_name,
                type=NodeType(message.node_type),
                endpoint=message.endpoint,
                capabilities=message.capabilities,
                metadata=message.metadata,
                status=NodeStatus.IDLE
            )
            self.node_registry.register_node(node)
            logger.info(f"Discovered new node: {message.node_name} ({message.node_id})")

            # 触发回调
            self._emit_callback("node_discovered", node)

        else:
            # 更新已有节点
            self.node_registry.heartbeat(message.node_id, NodeStatus.ACTIVE)

    def _handle_discovery_request(self, message: DiscoveryMessage):
        """处理发现请求"""
        # 回复本节点信息
        local = self._get_local_node_info()
        if local:
            response = DiscoveryMessage(
                type=DiscoveryProtocol.DISCOVERY_RESPONSE,
                node_id=local["node_id"],
                node_name=local["node_name"],
                node_type=local["node_type"],
                capabilities=local["capabilities"],
                endpoint=local.get("endpoint")
            )
            self._send_to(message.node_id, response)

    def _handle_heartbeat(self, message: DiscoveryMessage):
        """处理心跳"""
        self.node_registry.heartbeat(message.node_id)

    def _handle_goodbye(self, message: DiscoveryMessage):
        """处理节点离开"""
        self.node_registry.update_status(message.node_id, NodeStatus.OFFLINE)
        logger.info(f"Node left: {message.node_name}")

    def _send_to(self, target_node_id: str, message: DiscoveryMessage):
        """发送消息到指定节点"""
        # 在实际实现中，需要维护节点的地址信息
        # 这里简化为广播
        self._broadcast(message)

    def _cleanup_timedout_nodes(self):
        """清理超时的节点"""
        now = time.time()
        timeout_nodes = []

        for node_id, last_seen in self.known_nodes.items():
            if now - last_seen > DiscoveryProtocol.NODE_TIMEOUT:
                timeout_nodes.append(node_id)

        for node_id in timeout_nodes:
            self.known_nodes.pop(node_id, None)
            self.node_registry.update_status(node_id, NodeStatus.OFFLINE)
            logger.info(f"Node timed out: {node_id}")

    def _send_goodbye(self):
        """发送离开消息"""
        local = self._get_local_node_info()
        if local:
            message = DiscoveryMessage(
                type=DiscoveryProtocol.GOODBYE,
                node_id=local["node_id"],
                node_name=local["node_name"],
                node_type=local["node_type"],
                capabilities=local["capabilities"]
            )
            self._broadcast(message)

    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)

    def _emit_callback(self, event: str, data: Any):
        """触发回调"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_discovered_nodes(self) -> List[str]:
        """获取已发现的节点ID列表"""
        return list(self.known_nodes.keys())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "running": self.running,
            "discovered_nodes": len(self.known_nodes),
            "known_nodes": list(self.known_nodes.keys()),
            "gossip_interval": self.gossip_interval
        }
