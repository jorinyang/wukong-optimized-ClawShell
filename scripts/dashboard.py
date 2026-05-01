#!/usr/bin/env python3
"""
Dashboard - 多Agent集群统计面板
职责：
1. 收集各组件状态数据
2. 生成可视化统计报告
3. 支持多种输出格式（文本/JSON/HTML）
4. 定时生成报告
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# 路径配置
WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QUEUE_FILE = os.path.join(SHARED_DIR, "task-queue.json")
MARKET_FILE = os.path.join(SHARED_DIR, "task-market.json")
AGENT_STATUS_FILE = os.path.join(SHARED_DIR, "agent-status.json")
ALERT_HISTORY_FILE = os.path.join(SHARED_DIR, "alert_history.json")
DASHBOARD_FILE = os.path.join(SHARED_DIR, "dashboard.json")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "dashboard.log")

class Dashboard:
    def __init__(self):
        self.queue_file = QUEUE_FILE
        self.market_file = MARKET_FILE
        self.agent_status_file = AGENT_STATUS_FILE
        self.alert_history_file = ALERT_HISTORY_FILE
        self.dashboard_file = DASHBOARD_FILE
        self.log_file = LOG_FILE
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    def _load_json(self, filepath: str, default: any = None) -> any:
        """安全加载JSON"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
            return default
        except:
            return default
    
    def _load_queue(self) -> Dict:
        return self._load_json(self.queue_file, {"tasks": []})
    
    def _load_market(self) -> Dict:
        return self._load_json(self.market_file, {"tasks": []})
    
    def _load_agent_status(self) -> Dict:
        return self._load_json(self.agent_status_file, {"agents": {}})
    
    def _load_alert_history(self) -> Dict:
        return self._load_json(self.alert_history_file, {"alerts": []})
    
    def get_agent_stats(self) -> Dict:
        """获取Agent统计"""
        status = self._load_agent_status()
        agents = status.get("agents", {})
        
        stats = {
            "total": len(agents),
            "online": 0,
            "busy": 0,
            "offline": 0,
            "by_agent": {}
        }
        
        now = datetime.now()
        offline_threshold = timedelta(minutes=10)
        
        for agent_id, info in agents.items():
            agent_status = info.get("status", "offline")
            last_heartbeat = info.get("last_heartbeat")
            
            # 检查是否真的离线
            if last_heartbeat:
                try:
                    hb_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    hb_time = hb_time.replace(tzinfo=None)
                    if (now - hb_time) > offline_threshold:
                        agent_status = "offline"
                except:
                    pass
            
            if agent_status == "online":
                stats["online"] += 1
                if info.get("current_tasks", 0) >= info.get("max_tasks", 0):
                    stats["busy"] += 1
            elif agent_status == "offline":
                stats["offline"] += 1
            
            stats["by_agent"][agent_id] = {
                "name": info.get("name", agent_id),
                "status": agent_status,
                "current_tasks": info.get("current_tasks", 0),
                "max_tasks": info.get("max_tasks", 0),
                "last_heartbeat": last_heartbeat
            }
        
        return stats
    
    def get_task_stats(self) -> Dict:
        """获取任务统计"""
        queue = self._load_queue()
        market = self._load_market()
        
        queue_tasks = queue.get("tasks", [])
        market_tasks = market.get("tasks", [])
        
        # 队列状态分布
        status_dist = {}
        for t in queue_tasks:
            s = t.get("status", "unknown")
            status_dist[s] = status_dist.get(s, 0) + 1
        
        # 市场状态分布
        market_status_dist = {}
        for t in market_tasks:
            s = t.get("status", "unknown")
            market_status_dist[s] = market_status_dist.get(s, 0) + 1
        
        # 按类型分布
        type_dist = {}
        for t in queue_tasks:
            t_type = t.get("type", "unknown")
            type_dist[t_type] = type_dist.get(t_type, 0) + 1
        
        # 今日完成统计
        today = datetime.now().date()
        completed_today = 0
        failed_today = 0
        
        for t in market_tasks:
            completed_at = t.get("completed_at")
            if completed_at:
                try:
                    ct = datetime.fromisoformat(completed_at.replace('Z', '+00:00')).date()
                    if ct == today:
                        completed_today += 1
                        if t.get("status") == "failed":
                            failed_today += 1
                except:
                    pass
        
        return {
            "queue_total": len(queue_tasks),
            "market_total": len(market_tasks),
            "queue_by_status": status_dist,
            "market_by_status": market_status_dist,
            "queue_by_type": type_dist,
            "completed_today": completed_today,
            "failed_today": failed_today
        }
    
    def get_alert_stats(self) -> Dict:
        """获取告警统计"""
        history = self._load_alert_history()
        alerts = history.get("alerts", [])
        
        now = datetime.now()
        today = now.date()
        
        # 今日告警
        alerts_today = 0
        alerts_by_category = {}
        active_count = 0
        
        for alert in alerts:
            try:
                alert_time = datetime.fromisoformat(alert["timestamp"]).date()
                if alert_time == today:
                    alerts_today += 1
                
                cat = alert.get("category", "unknown")
                alerts_by_category[cat] = alerts_by_category.get(cat, 0) + 1
                
                if alert.get("status") == "active":
                    active_count += 1
            except:
                pass
        
        return {
            "total": len(alerts),
            "today": alerts_today,
            "active": active_count,
            "by_category": alerts_by_category
        }
    
    def get_system_stats(self) -> Dict:
        """获取系统统计"""
        stats = {
            "uptime": "N/A",
            "components": {}
        }
        
        # EventBus状态
        try:
            import subprocess
            result = subprocess.run(
                ["launchctl", "list", "|", "grep", "event-bus"],
                shell=True, capture_output=True, text=True, timeout=5
            )
            if "event-bus" in result.stdout:
                stats["components"]["eventbus"] = {"status": "running"}
            else:
                stats["components"]["eventbus"] = {"status": "stopped"}
        except:
            stats["components"]["eventbus"] = {"status": "unknown"}
        
        # 守护进程检查
        daemon_processes = ["event-bus"]
        for proc in daemon_processes:
            try:
                result = subprocess.run(
                    ["pgrep", "-f", proc],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    stats["components"][proc] = {"status": "running", "pid": result.stdout.strip().split()[0]}
                else:
                    stats["components"][proc] = {"status": "stopped"}
            except:
                stats["components"][proc] = {"status": "unknown"}
        
        return stats
    
    def generate_report(self, format: str = "text") -> str:
        """生成报告"""
        agent_stats = self.get_agent_stats()
        task_stats = self.get_task_stats()
        alert_stats = self.get_alert_stats()
        system_stats = self.get_system_stats()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if format == "json":
            report = {
                "timestamp": timestamp,
                "agents": agent_stats,
                "tasks": task_stats,
                "alerts": alert_stats,
                "system": system_stats
            }
            return json.dumps(report, indent=2, ensure_ascii=False)
        
        # 文本格式
        lines = []
        lines.append("=" * 60)
        lines.append("📊 多Agent集群统计面板")
        lines.append(f"生成时间: {timestamp}")
        lines.append("=" * 60)
        
        # Agent状态
        lines.append("")
        lines.append("🤖 Agent 状态")
        lines.append("-" * 40)
        
        total = agent_stats["total"]
        online = agent_stats["online"]
        busy = agent_stats["busy"]
        offline = agent_stats["offline"]
        
        lines.append(f"在线: {online} | 忙碌: {busy} | 离线: {offline} | 总计: {total}")
        lines.append("")
        
        for agent_id, info in agent_stats.get("by_agent", {}).items():
            status_icon = "🟢" if info["status"] == "online" else "🔴"
            load = f"{info['current_tasks']}/{info['max_tasks']}"
            lines.append(f"  {status_icon} {info['name']} ({load})")
        
        # 任务状态
        lines.append("")
        lines.append("📋 任务状态")
        lines.append("-" * 40)
        
        qt = task_stats["queue_total"]
        mt = task_stats["market_total"]
        ct = task_stats["completed_today"]
        ft = task_stats["failed_today"]
        
        lines.append(f"队列待处理: {qt} | 历史完成: {mt} | 今日完成: {ct} | 今日失败: {ft}")
        lines.append("")
        
        if task_stats["queue_by_status"]:
            for status, count in task_stats["queue_by_status"].items():
                lines.append(f"  [{status}] {count}")
        
        # 告警状态
        lines.append("")
        lines.append("🚨 告警状态")
        lines.append("-" * 40)
        
        active = alert_stats["active"]
        today = alert_stats["today"]
        total_alerts = alert_stats["total"]
        
        lines.append(f"活跃: {active} | 今日: {today} | 总计: {total_alerts}")
        
        if alert_stats["by_category"]:
            lines.append("")
            for cat, count in alert_stats["by_category"].items():
                lines.append(f"  [{cat}] {count}")
        
        # 系统状态
        lines.append("")
        lines.append("⚙️ 系统组件")
        lines.append("-" * 40)
        
        for comp, info in system_stats.get("components", {}).items():
            status = info.get("status", "unknown")
            icon = "✅" if status == "running" else "❌" if status == "stopped" else "⚠️"
            pid = info.get("pid", "")
            pid_str = f" (PID: {pid})" if pid else ""
            lines.append(f"  {icon} {comp}{pid_str}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_dashboard(self) -> bool:
        """保存面板数据"""
        try:
            agent_stats = self.get_agent_stats()
            task_stats = self.get_task_stats()
            alert_stats = self.get_alert_stats()
            
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "agents": agent_stats,
                "tasks": task_stats,
                "alerts": alert_stats
            }
            
            with open(self.dashboard_file, 'w') as f:
                json.dump(dashboard, f, indent=2, ensure_ascii=False)
            
            self.log("✅ 面板数据已保存")
            return True
        except Exception as e:
            self.log(f"⚠️ 保存面板失败: {e}")
            return False


# CLI接口
if __name__ == "__main__":
    import sys
    
    dashboard = Dashboard()
    action = sys.argv[1] if len(sys.argv) > 1 else "report"
    
    if action == "report":
        fmt = sys.argv[2] if len(sys.argv) > 2 else "text"
        print(dashboard.generate_report(fmt))
    
    elif action == "agents":
        stats = dashboard.get_agent_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif action == "tasks":
        stats = dashboard.get_task_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif action == "alerts":
        stats = dashboard.get_alert_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif action == "save":
        success = dashboard.save_dashboard()
        print(f"保存{'成功' if success else '失败'}")
    
    elif action == "status":
        # 快速状态
        agent_stats = dashboard.get_agent_stats()
        task_stats = dashboard.get_task_stats()
        alert_stats = dashboard.get_alert_stats()
        
        print(f"🤖 Agent: {agent_stats['online']}🟢/{agent_stats['busy']}🟡/{agent_stats['offline']}🔴")
        print(f"📋 任务: {task_stats['queue_total']}待处理, {task_stats['completed_today']}今日完成")
        print(f"🚨 告警: {alert_stats['active']}活跃, {alert_stats['today']}今日")
    
    else:
        print(f"未知操作: {action}")
        print("用法: dashboard.py <report|agents|tasks|alerts|save|status>")
        print("  report [text|json] - 生成报告")
