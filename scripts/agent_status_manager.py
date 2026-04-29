#!/usr/bin/env python3
"""
Agent Status Manager - 解决Agent状态失联问题
功能：
1. 实时追踪各Agent的任务负载
2. 维护 agent-status.json 状态文件
3. 提供Agent可用性查询接口
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# 配置
AGENT_STATUS_FILE = os.path.expanduser("~/.openclaw/shared/agent-status.json")
LOCK_FILE = os.path.expanduser("~/.openclaw/shared/.agent-status.lock")

# Agent配置
AGENT_CONFIG = {
    "ceo": {"max_tasks": 5, "type": "coordinator", "description": "首席执行官"},
    "lab": {"max_tasks": 3, "type": "analyst", "description": "智囊团分析师"},
    "dev": {"max_tasks": 3, "type": "developer", "description": "程序猿开发者"},
    "doc": {"max_tasks": 3, "type": "writer", "description": "笔杆子创作者"},
    "pub": {"max_tasks": 3, "type": "publisher", "description": "广播站发布者"},
    "lib": {"max_tasks": 3, "type": "librarian", "description": "图书馆知识库"},
    "dat": {"max_tasks": 3, "type": "data", "description": "数据师"},
}

@dataclass
class AgentInfo:
    name: str
    type: str
    description: str
    max_tasks: int
    current_tasks: int
    status: str  # available, busy, offline
    last_heartbeat: Optional[str]
    active_slots: int

class AgentStatusManager:
    """Agent状态管理器"""
    
    def __init__(self):
        self.status_file = Path(AGENT_STATUS_FILE)
        self.lock_file = Path(LOCK_FILE)
        self.agents = {}
        self._ensure_directory()
        self._load_or_init()
    
    def _ensure_directory(self):
        """确保目录存在"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_or_init(self):
        """加载或初始化状态"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    self.agents = data.get("agents", {})
                    # 确保所有配置的agent都存在
                    for name, config in AGENT_CONFIG.items():
                        if name not in self.agents:
                            self.agents[name] = {
                                "name": name,
                                "type": config["type"],
                                "description": config["description"],
                                "max_tasks": config["max_tasks"],
                                "current_tasks": 0,
                                "status": "offline",
                                "last_heartbeat": None,
                                "active_slots": config["max_tasks"]
                            }
            except Exception as e:
                print(f"[WARN] 加载状态失败: {e}, 重新初始化")
                self._init_agents()
        else:
            self._init_agents()
    
    def _init_agents(self):
        """初始化所有Agent"""
        self.agents = {}
        for name, config in AGENT_CONFIG.items():
            self.agents[name] = {
                "name": name,
                "type": config["type"],
                "description": config["description"],
                "max_tasks": config["max_tasks"],
                "current_tasks": 0,
                "status": "offline",
                "last_heartbeat": None,
                "active_slots": config["max_tasks"]
            }
        self.save()
    
    def save(self):
        """保存状态到文件"""
        try:
            # 使用锁防止并发写入
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "agents": self.agents
            }
            
            with open(self.status_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.lock_file.unlink(missing_ok=True)
            return True
        except Exception as e:
            print(f"[ERROR] 保存状态失败: {e}")
            self.lock_file.unlink(missing_ok=True)
            return False
    
    def update_heartbeat(self, agent_name: str) -> bool:
        """更新Agent心跳"""
        if agent_name not in self.agents:
            return False
        
        self.agents[agent_name]["last_heartbeat"] = datetime.now().isoformat()
        
        # 如果状态是offline，改为available
        if self.agents[agent_name]["status"] == "offline":
            self.agents[agent_name]["status"] = "available"
        
        return self.save()
    
    def set_busy(self, agent_name: str) -> bool:
        """标记Agent为忙碌"""
        if agent_name not in self.agents:
            return False
        
        self.agents[agent_name]["status"] = "busy"
        return self.save()
    
    def set_offline(self, agent_name: str) -> bool:
        """标记Agent为离线"""
        if agent_name not in self.agents:
            return False
        
        self.agents[agent_name]["status"] = "offline"
        return self.save()
    
    def increment_tasks(self, agent_name: str) -> bool:
        """增加任务计数"""
        if agent_name not in self.agents:
            return False
        
        agent = self.agents[agent_name]
        if agent["current_tasks"] < agent["max_tasks"]:
            agent["current_tasks"] += 1
            agent["active_slots"] = agent["max_tasks"] - agent["current_tasks"]
            
            # 如果任务数达到上限，标记为忙碌
            if agent["current_tasks"] >= agent["max_tasks"]:
                agent["status"] = "busy"
            else:
                agent["status"] = "available"
            
            return self.save()
        return False
    
    def decrement_tasks(self, agent_name: str) -> bool:
        """减少任务计数"""
        if agent_name not in self.agents:
            return False
        
        agent = self.agents[agent_name]
        if agent["current_tasks"] > 0:
            agent["current_tasks"] -= 1
            agent["active_slots"] = agent["max_tasks"] - agent["current_tasks"]
            
            # 如果有可用槽位，标记为available
            if agent["current_tasks"] < agent["max_tasks"]:
                agent["status"] = "available"
            
            return self.save()
        return False
    
    def get_available_agent(self, task_type: str) -> Optional[str]:
        """获取可用的Agent"""
        type_mapping = {
            "dev": ["dev"],
            "develop": ["dev"],
            "lab": ["lab"],
            "analyze": ["lab"],
            "analysis": ["lab"],
            "doc": ["doc"],
            "write": ["doc"],
            "document": ["doc"],
            "pub": ["pub"],
            "publish": ["pub"],
            "distribute": ["pub"],
            "lib": ["lib"],
            "archive": ["lib"],
            "knowledge": ["lib"],
            "dat": ["dat"],
            "data": ["dat"],
        }
        
        candidates = type_mapping.get(task_type, [])
        
        for agent_name in candidates:
            if agent_name not in self.agents:
                continue
            agent = self.agents[agent_name]
            if agent["status"] != "offline" and agent["current_tasks"] < agent["max_tasks"]:
                return agent_name
        
        return None
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        total_slots = sum(a["max_tasks"] for a in self.agents.values())
        used_slots = sum(a["current_tasks"] for a in self.agents.values())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(self.agents),
            "total_slots": total_slots,
            "used_slots": used_slots,
            "available_slots": total_slots - used_slots,
            "agents": self.agents
        }
    
    def get_agent_info(self, agent_name: str) -> Optional[Dict]:
        """获取单个Agent信息"""
        return self.agents.get(agent_name)
    
    def is_available(self, agent_name: str) -> bool:
        """检查Agent是否可用"""
        if agent_name not in self.agents:
            return False
        agent = self.agents[agent_name]
        return agent["status"] != "offline" and agent["current_tasks"] < agent["max_tasks"]

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="Agent Status Manager")
    parser.add_argument("action", choices=["status", "heartbeat", "inc", "dec", "busy", "offline", "available", "summary"])
    parser.add_argument("--agent", "-a", default=None, help="Agent名称")
    parser.add_argument("--type", "-t", default=None, help="任务类型")
    
    args = parser.parse_args()
    manager = AgentStatusManager()
    
    if args.action == "status":
        if args.agent:
            info = manager.get_agent_info(args.agent)
            print(json.dumps(info, indent=2, ensure_ascii=False) if info else "Agent不存在")
        else:
            print(json.dumps(manager.agents, indent=2, ensure_ascii=False))
    
    elif args.action == "heartbeat":
        if args.agent:
            manager.update_heartbeat(args.agent)
            print(f"✅ {args.agent} 心跳已更新")
        else:
            print("❌ 需要指定 --agent")
    
    elif args.action == "inc":
        if args.agent:
            manager.increment_tasks(args.agent)
            print(f"✅ {args.agent} 任务计数+1")
        else:
            print("❌ 需要指定 --agent")
    
    elif args.action == "dec":
        if args.agent:
            manager.decrement_tasks(args.agent)
            print(f"✅ {args.agent} 任务计数-1")
        else:
            print("❌ 需要指定 --agent")
    
    elif args.action == "busy":
        if args.agent:
            manager.set_busy(args.agent)
            print(f"✅ {args.agent} 状态设为忙碌")
        else:
            print("❌ 需要指定 --agent")
    
    elif args.action == "offline":
        if args.agent:
            manager.set_offline(args.agent)
            print(f"✅ {args.agent} 状态设为离线")
        else:
            print("❌ 需要指定 --agent")
    
    elif args.action == "available":
        agent = manager.get_available_agent(args.type) if args.type else None
        if agent:
            print(f"✅ 可用Agent: {agent}")
        else:
            print(f"❌ 没有可用的 {args.type} Agent")
    
    elif args.action == "summary":
        print(json.dumps(manager.get_status_summary(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
