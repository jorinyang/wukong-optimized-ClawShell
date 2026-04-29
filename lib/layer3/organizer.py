#!/usr/bin/env python3
"""
ClawShell 生态位协调器 (Ecology Coordinator)
版本: v0.2.1-C
功能: 基于能力的动态任务分配、负载均衡、生态位匹配
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

# ============ 配置 ============

ECOLOGY_STATE_PATH = Path("~/.openclaw/.ecology_state.json").expanduser()
NODES_DIR = Path("~/.openclaw/organizer/nodes").expanduser()


# ============ 数据结构 ============

@dataclass
class Capability:
    """能力描述"""
    name: str
    level: int = 1  # 能力等级 1-5
    tags: List[str] = field(default_factory=list)  # 能力标签
    
    def matches(self, requirement: "CapabilityRequirement") -> bool:
        """检查是否匹配需求"""
        if requirement.name != self.name:
            return False
        if self.level < requirement.min_level:
            return False
        if requirement.tags:
            return not bool(set(self.tags) & set(requirement.tags))  # 标签不匹配
        return True


@dataclass 
class CapabilityRequirement:
    """能力需求"""
    name: str
    min_level: int = 1
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0  # 在任务匹配中的权重


@dataclass
class Node:
    """节点"""
    id: str
    name: str
    capabilities: List[Capability] = field(default_factory=list)
    load: float = 0.0  # 当前负载 0-1
    max_load: float = 1.0  # 最大负载
    status: str = "active"  # active, idle, busy, offline
    metadata: Dict = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    
    def can_handle(self, requirement: CapabilityRequirement) -> bool:
        """检查是否能处理需求"""
        if self.status == "offline":
            return False
        if self.load >= self.max_load:
            return False
        return any(cap.matches(requirement) for cap in self.capabilities)
    
    def get_match_score(self, requirements: List[CapabilityRequirement]) -> float:
        """计算任务匹配分数"""
        if not requirements:
            return 0.0
        
        total_score = 0.0
        for req in requirements:
            best_match = 0.0
            for cap in self.capabilities:
                if cap.name == req.name and cap.level >= req.min_level:
                    # 匹配度 = 能力等级 / 需求等级 * 权重
                    score = min(cap.level / req.min_level, 2.0) * req.weight
                    best_match = max(best_match, score)
            total_score += best_match
        
        # 考虑负载因素
        load_factor = 1.0 - (self.load / self.max_load) * 0.5
        
        return total_score * load_factor / len(requirements)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "capabilities": [
                {"name": c.name, "level": c.level, "tags": c.tags} 
                for c in self.capabilities
            ],
            "load": self.load,
            "max_load": self.max_load,
            "status": self.status,
            "metadata": self.metadata,
            "last_heartbeat": self.last_heartbeat
        }


@dataclass
class Task:
    """任务"""
    id: str
    name: str
    requirements: List[CapabilityRequirement] = field(default_factory=list)
    priority: int = 0
    deadline: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "requirements": [
                {"name": r.name, "min_level": r.min_level, "tags": r.tags, "weight": r.weight}
                for r in self.requirements
            ],
            "priority": self.priority,
            "deadline": self.deadline,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


@dataclass
class Allocation:
    """分配结果"""
    task_id: str
    node_id: str
    score: float
    reason: str
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "node_id": self.node_id,
            "score": self.score,
            "reason": self.reason
        }


# ============ 生态位协调器 ============

class EcologyCoordinator:
    """生态位协调器"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.tasks: Dict[str, Task] = {}
        self.allocations: Dict[str, Allocation] = {}  # task_id -> allocation
        self._load_state()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        NODES_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        """加载状态"""
        if ECOLOGY_STATE_PATH.exists():
            try:
                with open(ECOLOGY_STATE_PATH) as f:
                    state = json.load(f)
                    
                    for node_data in state.get("nodes", {}).values():
                        capabilities = [
                            Capability(
                                name=c["name"],
                                level=c.get("level", 1),
                                tags=c.get("tags", [])
                            ) for c in node_data.get("capabilities", [])
                        ]
                        node = Node(
                            id=node_data["id"],
                            name=node_data["name"],
                            capabilities=capabilities,
                            load=node_data.get("load", 0.0),
                            max_load=node_data.get("max_load", 1.0),
                            status=node_data.get("status", "active"),
                            metadata=node_data.get("metadata", {}),
                            last_heartbeat=node_data.get("last_heartbeat", time.time())
                        )
                        self.nodes[node.id] = node
                    
                    for task_data in state.get("tasks", {}).values():
                        requirements = [
                            CapabilityRequirement(
                                name=r["name"],
                                min_level=r.get("min_level", 1),
                                tags=r.get("tags", []),
                                weight=r.get("weight", 1.0)
                            ) for r in task_data.get("requirements", [])
                        ]
                        task = Task(
                            id=task_data["id"],
                            name=task_data["name"],
                            requirements=requirements,
                            priority=task_data.get("priority", 0),
                            deadline=task_data.get("deadline"),
                            metadata=task_data.get("metadata", {}),
                            created_at=task_data.get("created_at", time.time())
                        )
                        self.tasks[task.id] = task
            except Exception as e:
                print(f"加载状态失败: {e}")
    
    def _save_state(self):
        """保存状态"""
        state = {
            "last_update": time.time(),
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
            "allocations": {aid: alloc.to_dict() for aid, alloc in self.allocations.items()}
        }
        with open(ECOLOGY_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    # ---- 节点管理 ----
    
    def register_node(self, node: Node) -> bool:
        """注册节点"""
        if node.id in self.nodes:
            return False
        
        self.nodes[node.id] = node
        self._save_state()
        return True
    
    def unregister_node(self, node_id: str) -> bool:
        """注销节点"""
        if node_id not in self.nodes:
            return False
        
        del self.nodes[node_id]
        
        # 清除该节点的分配
        self.allocations = {
            aid: alloc for aid, alloc in self.allocations.items()
            if alloc.node_id != node_id
        }
        
        self._save_state()
        return True
    
    def heartbeat(self, node_id: str, load: Optional[float] = None) -> bool:
        """节点心跳"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        node.last_heartbeat = time.time()
        
        if load is not None:
            node.load = min(max(load, 0.0), node.max_load)
        
        # 检查节点是否应该离线
        if time.time() - node.last_heartbeat > 300:  # 5分钟无心跳
            node.status = "offline"
        
        self._save_state()
        return True
    
    def update_node_load(self, node_id: str, delta: float) -> bool:
        """更新节点负载"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        node.load = min(max(node.load + delta, 0.0), node.max_load)
        
        # 更新状态
        if node.load >= node.max_load:
            node.status = "busy"
        elif node.load > 0.3:
            node.status = "active"
        else:
            node.status = "idle"
        
        self._save_state()
        return True
    
    # ---- 任务管理 ----
    
    def submit_task(self, task: Task) -> bool:
        """提交任务"""
        if task.id in self.tasks:
            return False
        
        self.tasks[task.id] = task
        self._save_state()
        return True    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id not in self.tasks:
            return False
        
        del self.tasks[task_id]
        
        if task_id in self.allocations:
            del self.allocations[task_id]
        
        self._save_state()
        return True
    
    # ---- 任务匹配 ----
    
    def match_task_to_node(self, task_id: str) -> Optional[Allocation]:
        """匹配任务到最适节点"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        # 获取所有可用节点
        available_nodes = [
            (node_id, node) for node_id, node in self.nodes.items()
            if node.status != "offline" and node.load < node.max_load
        ]
        
        if not available_nodes:
            return None
        
        # 计算每个节点的匹配分数
        candidates = []
        for node_id, node in available_nodes:
            score = node.get_match_score(task.requirements)
            if score > 0:
                candidates.append((node_id, score))
        
        if not candidates:
            return None
        
        # 选择最佳匹配
        candidates.sort(key=lambda x: -x[1])
        best_node_id, best_score = candidates[0]
        
        # 确定匹配原因
        matched_caps = []
        for req in task.requirements:
            for cap in self.nodes[best_node_id].capabilities:
                if cap.name == req.name and cap.level >= req.min_level:
                    matched_caps.append(cap.name)
                    break
        
        reason = f"Matched capabilities: {', '.join(matched_caps)}"
        
        allocation = Allocation(
            task_id=task_id,
            node_id=best_node_id,
            score=best_score,
            reason=reason
        )
        
        self.allocations[task_id] = allocation
        
        # 更新节点负载
        self.update_node_load(best_node_id, 0.1)  # 假设每个任务增加10%负载
        
        self._save_state()
        return allocation
    
    def rebalance(self) -> Dict[str, Any]:
        """
        负载再平衡
        返回再平衡报告
        """
        report = {
            "timestamp": time.time(),
            "actions": [],
            "summary": {"moved": 0, "failed": 0}
        }
        
        # 计算平均负载
        active_nodes = [n for n in self.nodes.values() if n.status != "offline"]
        if not active_nodes:
            return report
        
        avg_load = sum(n.load for n in active_nodes) / len(active_nodes)
        
        # 找出高负载和低负载节点
        overloaded = [(n.id, n) for n in active_nodes if n.load > avg_load * 1.3]
        underloaded = [(n.id, n) for n in active_nodes if n.load < avg_load * 0.7]
        
        # 尝试将任务从高负载节点移动到低负载节点
        for over_id, over_node in overloaded:
            # 获取该节点的任务
            node_tasks = [
                (tid, task) for tid, task in self.tasks.items()
                if self.allocations.get(tid, Allocation("", "", 0, "")).node_id == over_id
            ]
            
            for tid, task in node_tasks:
                # 寻找更合适的低负载节点
                for under_id, under_node in underloaded:
                    if under_id == over_id:
                        continue
                    
                    # 检查低负载节点是否能处理该任务
                    if under_node.can_handle(task.requirements[0]):
                        # 执行移动
                        old_allocation = self.allocations[tid]
                        self.allocations[tid] = Allocation(
                            task_id=tid,
                            node_id=under_id,
                            score=under_node.get_match_score(task.requirements),
                            reason=f"Rebalanced from {over_id}"
                        )
                        
                        # 更新负载
                        self.update_node_load(over_id, -0.1)
                        self.update_node_load(under_id, 0.1)
                        
                        report["actions"].append({
                            "task_id": tid,
                            "from": over_id,
                            "to": under_id
                        })
                        report["summary"]["moved"] += 1
                        break
        
        self._save_state()
        return report
    
    # ---- 报告 ----
    
    def get_ecology_report(self) -> Dict:
        """获取生态报告"""
        active_nodes = [n for n in self.nodes.values() if n.status != "offline"]
        
        # 按能力分组节点
        capability_map = defaultdict(list)
        for node in self.nodes.values():
            for cap in node.capabilities:
                capability_map[cap.name].append(node.id)
        
        return {
            "timestamp": time.time(),
            "nodes": {
                "total": len(self.nodes),
                "active": len(active_nodes),
                "offline": len(self.nodes) - len(active_nodes)
            },
            "tasks": {
                "total": len(self.tasks),
                "allocated": len(self.allocations),
                "pending": len(self.tasks) - len(self.allocations)
            },
            "capabilities": {
                cap: len(node_ids) for cap, node_ids in capability_map.items()
            },
            "load_distribution": {
                "avg": sum(n.load for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                "max": max((n.load for n in active_nodes), default=0),
                "min": min((n.load for n in active_nodes), default=0)
            }
        }
    
    def get_node_status(self, node_id: str) -> Optional[Dict]:
        """获取节点状态"""
        if node_id not in self.nodes:
            return None
        
        node = self.nodes[node_id]
        
        # 获取该节点的任务
        node_tasks = [
            tid for tid, alloc in self.allocations.items()
            if alloc.node_id == node_id
        ]
        
        return {
            **node.to_dict(),
            "tasks": node_tasks,
            "capacity_remaining": 1.0 - (node.load / node.max_load)
        }


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 生态位协调器")
    subparsers = parser.add_subparsers(dest="command")
    
    # 节点管理
    node_parser = subparsers.add_parser("node", help="节点管理")
    node_parser.add_argument("--register", metavar="ID")
    node_parser.add_argument("--unregister", metavar="ID")
    node_parser.add_argument("--heartbeat", metavar="ID")
    node_parser.add_argument("--list", action="store_true")
    node_parser.add_argument("--status", metavar="ID")
    
    # 任务管理
    task_parser = subparsers.add_parser("task", help="任务管理")
    task_parser.add_argument("--submit", metavar="ID")
    task_parser.add_argument("--remove", metavar="ID")
    task_parser.add_argument("--match", metavar="ID")
    task_parser.add_argument("--list", action="store_true")
    
    # 协调器
    subparsers.add_parser("rebalance", help="负载再平衡")
    subparsers.add_parser("report", help="生态报告")
    
    args = parser.parse_args()
    
    eco = EcologyCoordinator()
    
    if args.command == "node":
        if args.register:
            node = Node(
                id=args.register,
                name=f"Node-{args.register}",
                capabilities=[
                    Capability(name="default", level=1)
                ]
            )
            eco.register_node(node)
            print(f"✅ 节点 {args.register} 注册成功")
        
        elif args.unregister:
            eco.unregister_node(args.unregister)
            print(f"✅ 节点 {args.unregister} 已注销")
        
        elif args.heartbeat:
            eco.heartbeat(args.heartbeat)
            print(f"✅ 心跳已接收")
        
        elif args.list:
            print(f"节点列表 ({len(eco.nodes)} 个):")
            for nid, node in eco.nodes.items():
                print(f"  [{node.status}] {nid}: {node.name} (负载 {node.load:.1%})")
        
        elif args.status:
            status = eco.get_node_status(args.status)
            if status:
                print(f"节点: {status['name']}")
                print(f"状态: {status['status']}")
                print(f"负载: {status['load']:.1%}")
                print(f"能力: {len(status['capabilities'])} 个")
                print(f"任务: {len(status['tasks'])} 个")
            else:
                print(f"❌ 节点 {args.status} 不存在")
    
    elif args.command == "task":
        if args.submit:
            task = Task(id=args.submit, name=f"Task-{args.submit}")
            eco.submit_task(task)
            print(f"✅ 任务 {args.submit} 提交成功")
        
        elif args.remove:
            eco.remove_task(args.remove)
            print(f"✅ 任务 {args.remove} 已移除")
        
        elif args.match:
            alloc = eco.match_task_to_node(args.match)
            if alloc:
                print(f"✅ 任务 {args.match} 已分配到节点 {alloc.node_id}")
                print(f"   匹配分数: {alloc.score:.2f}")
                print(f"   原因: {alloc.reason}")
            else:
                print(f"❌ 无法为任务 {args.match} 找到合适的节点")
        
        elif args.list:
            print(f"任务列表 ({len(eco.tasks)} 个):")
            for tid, task in eco.tasks.items():
                alloc = eco.allocations.get(tid)
                status = f"→ {alloc.node_id}" if alloc else "⏳ 待分配"
                print(f"  {tid}: {task.name} {status}")
    
    elif args.command == "rebalance":
        report = eco.rebalance()
        print(f"再平衡完成:")
        print(f"  移动任务: {report['summary']['moved']}")
        print(f"  失败: {report['summary']['failed']}")
    
    elif args.command == "report":
        report = eco.get_ecology_report()
        print("=" * 60)
        print("ClawShell 生态位协调器 - 生态报告")
        print("=" * 60)
        print(f"节点: {report['nodes']['total']} 个 (活跃 {report['nodes']['active']})")
        print(f"任务: {report['tasks']['total']} 个 (已分配 {report['tasks']['allocated']})")
        print()
        print("能力分布:")
        for cap, count in report["capabilities"].items():
            print(f"  {cap}: {count} 个节点")
        print()
        print(f"负载分布: 平均 {report['load_distribution']['avg']:.1%}")
        print(f"  最大: {report['load_distribution']['max']:.1%}")
        print(f"  最小: {report['load_distribution']['min']:.1%}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
