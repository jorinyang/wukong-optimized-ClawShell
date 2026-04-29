#!/usr/bin/env python3
"""
ClawShell Hermes 同步模块
版本: v0.2.2-B
功能: Hermes洞察同步、执行联动、双向事件
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

# ============ 配置 ============

HERMES_CONFIG_PATH = Path("~/.openclaw/.hermes_config.json").expanduser()
HERMES_SHARED_PATH = Path("~/.openclaw/shared/hermes").expanduser()
HERMES_SYNC_STATE_PATH = Path("~/.openclaw/.hermes_sync_state.json").expanduser()


# ============ 数据结构 ============

@dataclass
class Insight:
    """洞察"""
    id: str
    type: str  # pattern, anomaly, trend, recommendation
    content: str
    source: str  # hermes, openclaw, user
    timestamp: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class HermesCommand:
    """Hermes命令"""
    id: str
    command: str
    params: Dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "command": self.command,
            "params": self.params,
            "status": self.status,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


@dataclass
class SyncReport:
    """同步报告"""
    timestamp: float
    insights_synced: int
    commands_synced: int
    events_forwarded: int
    errors: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "insights_synced": self.insights_synced,
            "commands_synced": self.commands_synced,
            "events_forwarded": self.events_forwarded,
            "errors": self.errors
        }


# ============ Hermes 同步 ============

class HermesSync:
    """Hermes深度同步"""
    
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
        self._ensure_directories()
        
        # 事件回调
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if HERMES_CONFIG_PATH.exists():
            try:
                with open(HERMES_CONFIG_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "hermes_path": str(Path.home() / ".hermes"),
            "insights_dir": "insights",
            "commands_dir": "commands",
            "events_dir": "events",
            "sync_interval": 30  # 秒
        }
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if HERMES_SYNC_STATE_PATH.exists():
            try:
                with open(HERMES_SYNC_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": 0,
            "last_insight_id": None,
            "pending_commands": []
        }
    
    def _save_state(self):
        """保存状态"""
        with open(HERMES_SYNC_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _ensure_directories(self):
        """确保必要目录存在"""
        HERMES_SHARED_PATH.mkdir(parents=True, exist_ok=True)
        
        for subdir in ["insights", "commands", "events", "pending"]:
            (HERMES_SHARED_PATH / subdir).mkdir(exist_ok=True)
    
    # ---- 洞察同步 ----
    
    def sync_insights_to_genome(self) -> List[Insight]:
        """
        从Hermes同步洞察到GenomeStore
        """
        insights = []
        errors = []
        
        hermes_path = Path(self.config.get("hermes_path", "~/.hermes"))
        insights_dir = hermes_path / self.config.get("insights_dir", "insights")
        
        if not insights_dir.exists():
            return []
        
        # 扫描新洞察
        last_id = self.state.get("last_insight_id")
        found_last = last_id is None  # 如果没有记录，取所有
        
        for insight_file in sorted(insights_dir.glob("*.json")):
            if not found_last:
                if insight_file.stem == last_id:
                    found_last = True
                continue
            
            try:
                with open(insight_file) as f:
                    data = json.load(f)
                
                insight = Insight(
                    id=data.get("id", insight_file.stem),
                    type=data.get("type", "unknown"),
                    content=data.get("content", ""),
                    source="hermes",
                    timestamp=data.get("timestamp", time.time()),
                    metadata=data.get("metadata", {})
                )
                
                insights.append(insight)
                
                # 复制到ClawShell共享目录
                dest = HERMES_SHARED_PATH / "insights" / insight_file.name
                shutil.copy2(insight_file, dest)
                
                # 更新状态
                self.state["last_insight_id"] = insight.id
                
            except Exception as e:
                errors.append(f"Failed to sync {insight_file.name}: {e}")
        
        if insights:
            self._save_state()
        
        return insights
    
    def save_insight(self, insight: Insight) -> bool:
        """
        保存洞察到Hermes共享目录
        """
        try:
            # 保存到pending目录
            pending_file = HERMES_SHARED_PATH / "pending" / f"{insight.id}.json"
            
            with open(pending_file, 'w') as f:
                json.dump(insight.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            print(f"Save insight failed: {e}")
            return False
    
    # ---- 执行联动 ----
    
    def execute_hermes_command(self, command: str, params: Optional[Dict] = None) -> Optional[HermesCommand]:
        """
        执行Hermes命令
        """
        cmd = HermesCommand(
            id=f"cmd_{int(time.time() * 1000)}",
            command=command,
            params=params or {},
            status="pending"
        )
        
        try:
            # 保存命令到共享目录
            cmd_file = HERMES_SHARED_PATH / "commands" / f"{cmd.id}.json"
            
            with open(cmd_file, 'w') as f:
                json.dump(cmd.to_dict(), f, indent=2)
            
            # 添加到待处理列表
            self.state["pending_commands"].append(cmd.id)
            self._save_state()
            
            return cmd
            
        except Exception as e:
            cmd.status = "failed"
            cmd.error = str(e)
            return cmd
    
    def get_command_result(self, command_id: str) -> Optional[HermesCommand]:
        """
        获取命令执行结果
        """
        # 检查本地状态
        cmd_file = HERMES_SHARED_PATH / "commands" / f"{command_id}.json"
        
        if cmd_file.exists():
            try:
                with open(cmd_file) as f:
                    data = json.load(f)
                
                return HermesCommand(
                    id=data["id"],
                    command=data["command"],
                    params=data.get("params", {}),
                    status=data.get("status", "unknown"),
                    result=data.get("result"),
                    error=data.get("error"),
                    created_at=data.get("created_at", time.time()),
                    completed_at=data.get("completed_at")
                )
            except:
                pass
        
        return None
    
    def check_pending_commands(self) -> List[HermesCommand]:
        """
        检查并更新待处理命令状态
        """
        completed = []
        still_pending = []
        
        for cmd_id in self.state.get("pending_commands", []):
            cmd = self.get_command_result(cmd_id)
            
            if cmd:
                if cmd.status in ["completed", "failed"]:
                    completed.append(cmd)
                else:
                    still_pending.append(cmd_id)
            else:
                # 命令文件不存在，认为已完成（可能被Hermes消费）
                still_pending.append(cmd_id)
        
        self.state["pending_commands"] = still_pending
        self._save_state()
        
        return completed
    
    # ---- 双向事件 ----
    
    def forward_event_to_hermes(self, event_type: str, event_data: Dict) -> bool:
        """
        转发事件到Hermes
        """
        try:
            event = {
                "type": event_type,
                "data": event_data,
                "source": "clawshell",
                "timestamp": time.time()
            }
            
            event_file = HERMES_SHARED_PATH / "events" / f"{event_type}_{int(time.time() * 1000)}.json"
            
            with open(event_file, 'w') as f:
                json.dump(event, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Forward event failed: {e}")
            return False
    
    def receive_event_from_hermes(self) -> List[Dict]:
        """
        接收Hermes事件
        """
        events = []
        
        hermes_events_dir = Path(self.config.get("hermes_path", "~/.hermes")) / "events"
        
        if not hermes_events_dir.exists():
            return events
        
        # 扫描新事件
        for event_file in sorted(hermes_events_dir.glob("*.json")):
            try:
                with open(event_file) as f:
                    event = json.load(f)
                
                events.append(event)
                
                # 移动到已处理目录
                processed_dir = HERMES_SHARED_PATH / "events" / "processed"
                processed_dir.mkdir(exist_ok=True)
                
                dest = processed_dir / event_file.name
                shutil.move(str(event_file), str(dest))
                
                # 触发处理器
                self._dispatch_event(event)
                
            except Exception as e:
                print(f"Process event failed: {e}")
        
        return events
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
    
    def _dispatch_event(self, event: Dict):
        """
        分发事件到处理器
        """
        event_type = event.get("type", "")
        
        handlers = self._event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")
        
        # 也触发通配符处理器
        wildcard_handlers = self._event_handlers.get("*", [])
        for handler in wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Wildcard handler error: {e}")
    
    # ---- 批量同步 ----
    
    def sync_all(self) -> SyncReport:
        """
        执行全量同步
        """
        errors = []
        
        # 1. 同步洞察
        insights = self.sync_insights_to_genome()
        
        # 2. 检查命令结果
        commands = self.check_pending_commands()
        
        # 3. 接收事件
        events = self.receive_event_from_hermes()
        
        # 更新状态
        self.state["last_sync"] = time.time()
        self._save_state()
        
        return SyncReport(
            timestamp=time.time(),
            insights_synced=len(insights),
            commands_synced=len(commands),
            events_forwarded=len(events),
            errors=errors
        )
    
    # ---- 便捷方法 ----
    
    def send_insight(self, content: str, insight_type: str = "observation") -> bool:
        """
        发送洞察到Hermes
        """
        insight = Insight(
            id=f"insight_{int(time.time() * 1000)}",
            type=insight_type,
            content=content,
            source="clawshell",
            timestamp=time.time()
        )
        
        return self.save_insight(insight)
    
    def request_analysis(self, topic: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        请求Hermes分析
        """
        cmd = self.execute_hermes_command(
            "analyze",
            params={
                "topic": topic,
                "context": context or {}
            }
        )
        
        return cmd.id if cmd else None


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell Hermes同步")
    parser.add_argument("--sync", action="store_true", help="执行全量同步")
    parser.add_argument("--insights", action="store_true", help="同步洞察")
    parser.add_argument("--commands", action="store_true", help="检查命令")
    parser.add_argument("--events", action="store_true", help="接收事件")
    parser.add_argument("--send", metavar="TEXT", help="发送洞察")
    parser.add_argument("--analyze", metavar="TOPIC", help="请求分析")
    args = parser.parse_args()
    
    sync = HermesSync()
    
    if args.sync:
        report = sync.sync_all()
        print("=" * 60)
        print("Hermes 同步报告")
        print("=" * 60)
        print(f"洞察同步: {report.insights_synced}")
        print(f"命令同步: {report.commands_synced}")
        print(f"事件转发: {report.events_forwarded}")
        if report.errors:
            print(f"错误: {len(report.errors)}")
            for err in report.errors:
                print(f"  - {err}")
    
    elif args.insights:
        insights = sync.sync_insights_to_genome()
        print(f"同步到 {len(insights)} 个洞察:")
        for insight in insights:
            print(f"  [{insight.type}] {insight.content[:60]}...")
    
    elif args.commands:
        completed = sync.check_pending_commands()
        print(f"完成 {len(completed)} 个命令:")
        for cmd in completed:
            status_icon = "✅" if cmd.status == "completed" else "❌"
            print(f"  {status_icon} {cmd.command}: {cmd.status}")
            if cmd.result:
                print(f"      结果: {str(cmd.result)[:60]}")
            if cmd.error:
                print(f"      错误: {cmd.error}")
    
    elif args.events:
        events = sync.receive_event_from_hermes()
        print(f"接收 {len(events)} 个事件:")
        for event in events:
            print(f"  [{event.get('type')}] {str(event.get('data'))[:60]}")
    
    elif args.send:
        success = sync.send_insight(args.send)
        print(f"{'✅' if success else '❌'} 洞察已发送")
    
    elif args.analyze:
        cmd_id = sync.request_analysis(args.analyze)
        if cmd_id:
            print(f"✅ 分析请求已发送: {cmd_id}")
        else:
            print("❌ 请求失败")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
