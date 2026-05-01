#!/usr/bin/env python3
"""
ClawShell 节点注册表 (Node Registry)
版本: v0.2.5-A
功能: OpenClaw/Hermes/N8N 统一节点注册、心跳管理
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading

# ============ 配置 ============

NODE_REGISTRY_PATH = Path("~/.real/.node_registry.json").expanduser()
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）
NODE_TIMEOUT = 120  # 节点超时（秒）


# ============ 数据结构 ============

class NodeType(Enum):
    """节点类型"""
    OPENCLAW = "openclaw"
    HERMES = "hermes"
    N8N = "n8n"
    MEMOS = "memos"
    OBSIDIAN = "obsidian"
    AGENT = "agent"
    SKILL = "skill"
    UNKNOWN = "unknown"


class NodeStatus(Enum):
    """节点状态"""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class Node:
    """节点"""
    id: str
    name: str
    type: NodeType
    endpoint: Optional[str] = None
    status: NodeStatus = NodeStatus.UNKNOWN
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    heartbeat_interval: int = HEARTBEAT_INTERVAL
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Node":
        return cls(
            id=data["id"],
            name=data["name"],
            type=NodeType(data.get("type", "unknown")),
            endpoint=data.get("endpoint"),
            status=NodeStatus(data.get("status", "unknown")),
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
            registered_at=data.get("registered_at", time.time()),
            last_heartbeat=data.get("last_heartbeat", time.time()),
            heartbeat_interval=data.get("heartbeat_interval", HEARTBEAT_INTERVAL)
        )


# ============ 节点注册表 ============

class NodeRegistry:
    """节点注册表"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {
            "register": [],
            "unregister": [],
            "heartbeat": [],
            "status_change": []
        }
        self._load()
    
    def _load(self):
        """加载注册表"""
        if NODE_REGISTRY_PATH.exists():
            try:
                with open(NODE_REGISTRY_PATH) as f:
                    data = json.load(f)
                    for node_data in data.get("nodes", {}).values():
                        node = Node.from_dict(node_data)
                        self.nodes[node.id] = node
            except Exception as e:
                print(f"Load registry failed: {e}")
    
    def _save(self):
        """保存注册表"""
        with self._lock:
            data = {
                "last_update": time.time(),
                "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()}
            }
            with open(NODE_REGISTRY_PATH, 'w') as f:
                json.dump(data, f, indent=2)
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, node: Node):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(node)
            except Exception as e:
                print(f"Callback error: {e}")
    
    # ---- 节点管理 ----
    
    def register(self, name: str, node_type: NodeType, endpoint: Optional[str] = None,
                 capabilities: Optional[List[str]] = None, metadata: Optional[Dict] = None) -> str:
        """
        注册节点
        
        Returns:
            节点ID
        """
        node_id = str(uuid.uuid4())[:8]
        
        node = Node(
            id=node_id,
            name=name,
            type=node_type,
            endpoint=endpoint,
            status=NodeStatus.ACTIVE,
            capabilities=capabilities or [],
            metadata=metadata or {}
        )
        
        with self._lock:
            self.nodes[node_id] = node
        
        self._emit("register", node)
        self._save()
        
        return node_id
    
    def unregister(self, node_id: str) -> bool:
        """注销节点"""
        with self._lock:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes.pop(node_id)
        
        self._emit("unregister", node)
        self._save()
        return True
    
    def heartbeat(self, node_id: str, status: Optional[NodeStatus] = None) -> bool:
        """节点心跳"""
        with self._lock:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            old_status = node.status
            
            node.last_heartbeat = time.time()
            if status:
                node.status = status
            elif node.status == NodeStatus.OFFLINE:
                node.status = NodeStatus.ACTIVE
            
            # 检查状态变化
            if old_status != node.status:
                self._emit("status_change", node)
            
            self._emit("heartbeat", node)
        
        self._save()
        return True
    
    def update_status(self, node_id: str, status: NodeStatus) -> bool:
        """更新节点状态"""
        with self._lock:
            if node_id not in self.nodes:
                return False
            
            node = self.nodes[node_id]
            old_status = node.status
            node.status = status
            
            if old_status != status:
                self._emit("status_change", node)
        
        self._save()
        return True
    
    # ---- 查询 ----
    
    def get(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_by_name(self, name: str) -> Optional[Node]:
        """通过名称获取节点"""
        for node in self.nodes.values():
            if node.name == name:
                return node
        return None
    
    def get_by_type(self, node_type: NodeType) -> List[Node]:
        """获取指定类型的所有节点"""
        return [n for n in self.nodes.values() if n.type == node_type]
    
    def get_active(self) -> List[Node]:
        """获取所有活跃节点"""
        return [n for n in self.nodes.values() if n.status != NodeStatus.OFFLINE]
    
    def get_capable(self, capability: str) -> List[Node]:
        """获取具有指定能力的节点"""
        return [
            n for n in self.nodes.values()
            if n.status != NodeStatus.OFFLINE and capability in n.capabilities
        ]
    
    # ---- 超时检测 ----
    
    def check_timeouts(self) -> List[str]:
        """检查超时节点，返回超时的节点ID列表"""
        now = time.time()
        timed_out = []
        
        with self._lock:
            for node_id, node in self.nodes.items():
                if node.status != NodeStatus.OFFLINE:
                    if now - node.last_heartbeat > NODE_TIMEOUT:
                        node.status = NodeStatus.OFFLINE
                        timed_out.append(node_id)
                        self._emit("status_change", node)
        
        if timed_out:
            self._save()
        
        return timed_out
    
    # ---- 统计 ----
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            "total": len(self.nodes),
            "by_type": {},
            "by_status": {},
            "active": len([n for n in self.nodes.values() if n.status != NodeStatus.OFFLINE])
        }
        
        for node in self.nodes.values():
            # by_type
            t = node.type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            
            # by_status
            s = node.status.value
            stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
        
        return stats


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 节点注册表")
    subparsers = parser.add_subparsers(dest="command")
    
    # 注册
    reg_parser = subparsers.add_parser("register", help="注册节点")
    reg_parser.add_argument("--name", required=True)
    reg_parser.add_argument("--type", required=True, choices=[t.value for t in NodeType])
    reg_parser.add_argument("--endpoint")
    reg_parser.add_argument("--cap", nargs="+")
    
    # 心跳
    hb_parser = subparsers.add_parser("heartbeat", help="心跳")
    hb_parser.add_argument("node_id")
    
    # 列表
    list_parser = subparsers.add_parser("list", help="列出节点")
    list_parser.add_argument("--type", choices=[t.value for t in NodeType])
    
    # 状态
    subparsers.add_parser("stats", help="统计")
    
    # 超时检查
    subparsers.add_parser("check", help="检查超时")
    
    args = parser.parse_args()
    
    registry = NodeRegistry()
    
    if args.command == "register":
        node_id = registry.register(
            name=args.name,
            node_type=NodeType(args.type),
            endpoint=args.endpoint,
            capabilities=args.cap
        )
        print(f"✅ 节点已注册: {node_id}")
    
    elif args.command == "heartbeat":
        success = registry.heartbeat(args.node_id)
        print(f"{'✅' if success else '❌'} 心跳 {'成功' if success else '失败'}")
    
    elif args.command == "list":
        if args.type:
            nodes = registry.get_by_type(NodeType(args.type))
        else:
            nodes = list(registry.nodes.values())
        
        print(f"节点列表 ({len(nodes)} 个):")
        for node in nodes:
            status_icon = {"active": "🟢", "idle": "🟡", "busy": "🔴", "offline": "⚫"}.get(node.status.value, "⚪")
            print(f"  {status_icon} [{node.id}] {node.name} ({node.type.value})")
            if node.endpoint:
                print(f"      {node.endpoint}")
    
    elif args.command == "stats":
        stats = registry.get_stats()
        print("=" * 60)
        print("节点注册表统计")
        print("=" * 60)
        print(f"总节点: {stats['total']}")
        print(f"活跃: {stats['active']}")
        print()
        print("按类型:")
        for t, count in stats["by_type"].items():
            print(f"  {t}: {count}")
        print()
        print("按状态:")
        for s, count in stats["by_status"].items():
            print(f"  {s}: {count}")
    
    elif args.command == "check":
        timed_out = registry.check_timeouts()
        print(f"检查完成: {len(timed_out)} 个节点超时")
        for node_id in timed_out:
            print(f"  ⚠️  {node_id}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
