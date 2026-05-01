#!/usr/bin/env python3
"""
daily_report_generator.py - 日报生成器
功能：自动收集当日数据生成结构化日报
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
REPORTS_DIR = os.path.join(SHARED_DIR, "reports")
TEMPLATE_DIR = os.path.join(WORKSPACE, "templates")

class DailyReportGenerator:
    """日报生成器"""
    
    def __init__(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        
    def generate(self, date: datetime = None) -> str:
        """生成日报"""
        if date is None:
            date = datetime.now()
        
        # 1. 收集数据
        data = self.collect_data(date)
        
        # 2. 生成内容
        content = self._generate_content(data, date)
        
        # 3. 保存报告
        report_file = self._save_report(content, date)
        
        return report_file
    
    def collect_data(self, date: datetime) -> dict:
        """收集当日数据"""
        data = {
            "date": date.strftime("%Y-%m-%d"),
            "tasks_completed": self._get_tasks_completed(date),
            "tasks_pending": self._get_tasks_pending(),
            "agent_status": self._get_agent_status(),
            "system_metrics": self._get_system_metrics(),
            "events": self._get_events(date),
            "errors": self._get_errors(date),
            "alerts": self._get_alerts()
        }
        
        return data
    
    def _get_tasks_completed(self, date: datetime) -> list:
        """获取已完成任务"""
        queue_file = os.path.join(SHARED_DIR, "task-queue.json")
        if not os.path.exists(queue_file):
            return []
        
        try:
            with open(queue_file, 'r') as f:
                data = json.load(f)
            
            completed = []
            for task in data.get("tasks", []):
                completed_at = task.get("completed_at", "")
                if completed_at.startswith(date.strftime("%Y-%m-%d")):
                    completed.append({
                        "id": task.get("id"),
                        "title": task.get("title"),
                        "agent": task.get("assigned_to"),
                        "duration": task.get("duration_minutes", 0)
                    })
            
            return completed
        except:
            return []
    
    def _get_tasks_pending(self) -> list:
        """获取待处理任务"""
        queue_file = os.path.join(SHARED_DIR, "task-queue.json")
        if not os.path.exists(queue_file):
            return []
        
        try:
            with open(queue_file, 'r') as f:
                data = json.load(f)
            
            pending = []
            for task in data.get("tasks", []):
                if task.get("status") == "pending":
                    pending.append({
                        "id": task.get("id"),
                        "title": task.get("title"),
                        "priority": task.get("priority", "P3")
                    })
            
            return pending[:10]  # 最多10个
        except:
            return []
    
    def _get_agent_status(self) -> dict:
        """获取Agent状态"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "--all-agents"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            status = {}
            lines = result.stdout.split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    agent = parts[0].strip()
                    if agent in ["lab", "dev", "doc", "pub", "lib", "dat"]:
                        status[agent] = "online" if any(x in line for x in ["m ago", "now"]) else "offline"
            
            return status
        except:
            return {}
    
    def _get_system_metrics(self) -> dict:
        """获取系统指标"""
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    
    def _get_events(self, date: datetime) -> list:
        """获取当日事件"""
        events_dir = os.path.join(SHARED_DIR, "events")
        if not os.path.exists(events_dir):
            return []
        
        events = []
        date_str = date.strftime("%Y-%m-%d")
        
        for filename in os.listdir(events_dir):
            if filename.endswith(".json") and date_str in filename:
                filepath = os.path.join(events_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        event = json.load(f)
                        events.append(event.get("type", "unknown"))
                except:
                    pass
        
        return events
    
    def _get_errors(self, date: datetime) -> list:
        """获取当日错误"""
        logs_dir = os.path.join(WORKSPACE, "logs")
        errors = []
        
        # 检查错误日志
        err_file = os.path.join(logs_dir, "gateway.err.log")
        if os.path.exists(err_file):
            try:
                with open(err_file, 'r') as f:
                    content = f.read()
                    # 简单统计
                    error_count = content.lower().count("error")
                    errors.append({"source": "gateway", "count": error_count})
            except:
                pass
        
        return errors
    
    def _get_alerts(self) -> list:
        """获取告警"""
        alert_dir = os.path.join(SHARED_DIR, "alerts")
        alert_file = os.path.join(alert_dir, "alert_state.json")
        
        if not os.path.exists(alert_file):
            return []
        
        try:
            with open(alert_file, 'r') as f:
                state = json.load(f)
                return list(state.get("active_alerts", {}).values())
        except:
            return []
    
    def _generate_content(self, data: dict, date: datetime) -> str:
        """生成报告内容"""
        content = f"""# ClawShell 日报

**日期**: {data['date']}  
**生成时间**: {datetime.now().strftime('%H:%M:%S')}  
**系统**: macOS Darwin  

---

## 📊 任务概览

| 指标 | 数值 |
|------|------|
| 完成任务 | {len(data['tasks_completed'])} |
| 待处理任务 | {len(data['tasks_pending'])} |
| 活跃事件 | {len(data['events'])} |
| 错误数 | {sum(e.get('count', 0) for e in data['errors'])} |
| 活跃告警 | {len(data['alerts'])} |

---

## ✅ 已完成任务

"""
        
        if data['tasks_completed']:
            for task in data['tasks_completed']:
                content += f"- [{task.get('agent', 'unknown')}] {task.get('title', 'Unknown task')}\n"
        else:
            content += "_今日无完成任务_\n"
        
        content += f"""

## 📋 待处理任务

"""
        
        if data['tasks_pending']:
            for task in data['tasks_pending']:
                content += f"- [{task.get('priority', 'P3')}] {task.get('title', 'Unknown task')}\n"
        else:
            content += "_暂无待处理任务_\n"
        
        content += f"""

## 🤖 Agent状态

"""
        
        agent_status = data.get('agent_status', {})
        for agent, status in agent_status.items():
            icon = "🟢" if status == "online" else "🔴"
            content += f"- {icon} **{agent.upper()}**: {status}\n"
        
        if not agent_status:
            content += "_暂无Agent状态数据_\n"
        
        content += f"""

## 📈 系统指标

| 指标 | 数值 | 状态 |
|------|------|------|
| CPU | {data['system_metrics'].get('cpu_percent', 0):.1f}% | {'⚠️ 高' if data['system_metrics'].get('cpu_percent', 0) > 80 else '✅ 正常'} |
| 内存 | {data['system_metrics'].get('memory_percent', 0):.1f}% | {'⚠️ 高' if data['system_metrics'].get('memory_percent', 0) > 85 else '✅ 正常'} |
| 磁盘 | {data['system_metrics'].get('disk_percent', 0):.1f}% | {'⚠️ 高' if data['system_metrics'].get('disk_percent', 0) > 90 else '✅ 正常'} |

"""
        
        if data['alerts']:
            content += f"""

## 🚨 活跃告警

"""
            for alert in data['alerts']:
                severity_icon = {"critical": "🔴", "warning": "⚠️", "info": "🔵"}.get(alert.get("severity", "info"), "🔵")
                content += f"- {severity_icon} [{alert.get('severity', 'unknown').upper()}] {alert.get('name', 'Unknown')}: {alert.get('value', '')} (阈值: {alert.get('threshold', '')})"
                content += f"\n"
        
        content += f"""

---

_日报生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        
        return content
    
    def _save_report(self, content: str, date: datetime) -> str:
        """保存报告"""
        date_str = date.strftime("%Y%m%d")
        report_dir = os.path.join(REPORTS_DIR, "daily")
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"daily_report_{date_str}.md")
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        # 同时保存JSON数据
        data_file = os.path.join(report_dir, f"daily_data_{date_str}.json")
        data = self.collect_data(date)
        with open(data_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return report_file


if __name__ == "__main__":
    generator = DailyReportGenerator()
    
    print("=" * 50)
    print("日报生成器测试")
    print("=" * 50)
    
    # 生成今日日报
    print("\n📰 生成日报...")
    report_file = generator.generate()
    print(f"报告已保存: {report_file}")
    
    # 读取并显示
    with open(report_file, 'r') as f:
        content = f.read()
    
    print("\n" + "=" * 50)
    print("日报内容预览")
    print("=" * 50)
    print(content[:1500] + "...")
