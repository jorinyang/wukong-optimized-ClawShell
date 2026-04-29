#!/usr/bin/env python3
"""
weekly_monthly_report.py - 周报/月报生成器
功能：汇总日报生成周报/月报
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
REPORTS_DIR = os.path.join(SHARED_DIR, "reports", "daily")

class WeeklyReportGenerator:
    """周报生成器"""
    
    def __init__(self):
        pass
    
    def generate(self, end_date: datetime = None) -> str:
        """生成周报"""
        if end_date is None:
            end_date = datetime.now()
        
        # 计算开始日期（一周前）
        start_date = end_date - timedelta(days=7)
        
        # 收集数据
        data = self.collect_data(start_date, end_date)
        
        # 生成内容
        content = self._generate_content(data, start_date, end_date)
        
        # 保存
        report_file = self._save_report(content, end_date, "weekly")
        
        return report_file
    
    def collect_data(self, start_date: datetime, end_date: datetime) -> dict:
        """收集一周数据"""
        daily_reports = []
        date_range = (end_date - start_date).days
        
        for i in range(date_range):
            date = start_date + timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            
            # 读取日报JSON
            data_file = os.path.join(REPORTS_DIR, f"daily_data_{date_str}.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    daily_reports.append(json.load(f))
        
        # 汇总数据
        summary = {
            "total_tasks_completed": sum(len(d.get("tasks_completed", [])) for d in daily_reports),
            "total_tasks_pending": len(daily_reports[-1].get("tasks_pending", [])) if daily_reports else 0,
            "daily_reports": len(daily_reports),
            "agent_activity": self._aggregate_agent_activity(daily_reports),
            "system_health": self._aggregate_system_health(daily_reports),
            "top_tasks": self._get_top_tasks(daily_reports),
            "errors": self._aggregate_errors(daily_reports)
        }
        
        return summary
    
    def _aggregate_agent_activity(self, reports: list) -> dict:
        """汇总Agent活动"""
        activity = {}
        for report in reports:
            for agent, status in report.get("agent_status", {}).items():
                if agent not in activity:
                    activity[agent] = {"online": 0, "offline": 0}
                if status == "online":
                    activity[agent]["online"] += 1
                else:
                    activity[agent]["offline"] += 1
        return activity
    
    def _aggregate_system_health(self, reports: list) -> dict:
        """汇总系统健康度"""
        if not reports:
            return {}
        
        cpu_values = [r.get("system_metrics", {}).get("cpu_percent", 0) for r in reports]
        mem_values = [r.get("system_metrics", {}).get("memory_percent", 0) for r in reports]
        disk_values = [r.get("system_metrics", {}).get("disk_percent", 0) for r in reports]
        
        return {
            "avg_cpu": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "max_cpu": max(cpu_values) if cpu_values else 0,
            "avg_memory": sum(mem_values) / len(mem_values) if mem_values else 0,
            "max_memory": max(mem_values) if mem_values else 0,
            "avg_disk": sum(disk_values) / len(disk_values) if disk_values else 0
        }
    
    def _get_top_tasks(self, reports: list) -> list:
        """获取高频任务"""
        task_counts = {}
        for report in reports:
            for task in report.get("tasks_completed", []):
                title = task.get("title", "Unknown")
                if title not in task_counts:
                    task_counts[title] = 0
                task_counts[title] += 1
        
        sorted_tasks = sorted(task_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"title": t[0], "count": t[1]} for t in sorted_tasks[:5]]
    
    def _aggregate_errors(self, reports: list) -> dict:
        """汇总错误"""
        total_errors = sum(sum(e.get("count", 0) for e in r.get("errors", [])) for r in reports)
        total_alerts = sum(len(r.get("alerts", [])) for r in reports)
        
        return {
            "total_errors": total_errors,
            "total_alerts": total_alerts
        }
    
    def _generate_content(self, data: dict, start_date: datetime, end_date: datetime) -> str:
        """生成周报内容"""
        content = f"""# ClawShell 周报

**周期**: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

---

## 📊 周度概览

| 指标 | 数值 |
|------|------|
| 完成任务总数 | {data['total_tasks_completed']} |
| 当前待处理 | {data['total_tasks_pending']} |
| 日报数据 | {data['daily_reports']}天 |
| 总错误数 | {data['errors']['total_errors']} |
| 总告警数 | {data['errors']['total_alerts']} |

---

## 🤖 Agent活动统计

"""
        
        for agent, stats in data.get("agent_activity", {}).items():
            total = stats.get("online", 0) + stats.get("offline", 0)
            online_rate = (stats.get("online", 0) / total * 100) if total > 0 else 0
            content += f"- **{agent.upper()}**: 🟢 {stats.get('online', 0)}天 在线, 🔴 {stats.get('offline', 0)}天 离线 ({online_rate:.0f}%)\n"
        
        content += f"""

## 📈 系统健康度

| 指标 | 平均值 | 峰值 |
|------|--------|------|
| CPU | {data['system_health'].get('avg_cpu', 0):.1f}% | {data['system_health'].get('max_cpu', 0):.1f}% |
| 内存 | {data['system_health'].get('avg_memory', 0):.1f}% | {data['system_health'].get('max_memory', 0):.1f}% |
| 磁盘 | {data['system_health'].get('avg_disk', 0):.1f}% | - |

"""
        
        if data.get("top_tasks"):
            content += f"""

## ✅ 高频完成任务

"""
            for task in data["top_tasks"]:
                content += f"- {task['title']} ({task['count']}次)\n"
        
        content += f"""

---

_周报生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        
        return content
    
    def _save_report(self, content: str, date: datetime, report_type: str) -> str:
        """保存报告"""
        date_str = date.strftime("%Y%m%d")
        report_dir = os.path.join(WORKSPACE, "reports", report_type)
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"{report_type}_report_{date_str}.md")
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        return report_file


class MonthlyReportGenerator:
    """月报生成器"""
    
    def __init__(self):
        pass
    
    def generate(self, year: int = None, month: int = None) -> str:
        """生成月报"""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        # 获取周报列表
        weekly_reports = self._collect_weekly_reports(year, month)
        
        # 汇总数据
        data = self._aggregate_monthly_data(weekly_reports)
        
        # 生成内容
        content = self._generate_content(data, year, month)
        
        # 保存
        report_file = self._save_report(content, year, month)
        
        return report_file
    
    def _collect_weekly_reports(self, year: int, month: int) -> list:
        """收集月内周报"""
        weekly_dir = os.path.join(WORKSPACE, "reports", "weekly")
        if not os.path.exists(weekly_dir):
            return []
        
        reports = []
        for filename in os.listdir(weekly_dir):
            if filename.endswith(".md") and str(year) in filename:
                filepath = os.path.join(weekly_dir, filename)
                with open(filepath, 'r') as f:
                    reports.append(f.read())
        
        return reports
    
    def _aggregate_monthly_data(self, weekly_reports: list) -> dict:
        """汇总月度数据"""
        # 简单汇总
        return {
            "weeks": len(weekly_reports),
            "summary": "月度数据汇总"  # 简化实现
        }
    
    def _generate_content(self, data: dict, year: int, month: int) -> str:
        """生成月报内容"""
        month_name = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                     "七月", "八月", "九月", "十月", "十一月", "十二月"][month]
        
        content = f"""# ClawShell 月报

**月份**: {year}年 {month_name}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

---

## 📊 月度概览

| 指标 | 数值 |
|------|------|
| 周报数据 | {data.get('weeks', 0)}周 |
| 总结 | {data.get('summary', 'N/A')} |

---

## 📈 趋势分析

（待完善：需要更详细的数据收集）

---

## 🎯 下月计划

（待完善：需要人工输入）

---

_月报生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        
        return content
    
    def _save_report(self, content: str, year: int, month: int) -> str:
        """保存报告"""
        report_dir = os.path.join(WORKSPACE, "reports", "monthly")
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"monthly_report_{year}{month:02d}.md")
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        return report_file


if __name__ == "__main__":
    print("=" * 50)
    print("周报/月报生成器测试")
    print("=" * 50)
    
    # 测试周报
    print("\n📰 生成周报...")
    weekly = WeeklyReportGenerator()
    try:
        report_file = weekly.generate()
        print(f"周报已保存: {report_file}")
        
        # 显示内容
        with open(report_file, 'r') as f:
            content = f.read()
        print("\n周报预览:")
        print(content[:800] + "...")
    except Exception as e:
        print(f"周报生成失败: {e}")
    
    # 测试月报
    print("\n📰 生成月报...")
    monthly = MonthlyReportGenerator()
    try:
        report_file = monthly.generate()
        print(f"月报已保存: {report_file}")
    except Exception as e:
        print(f"月报生成失败: {e}")
    
    print("\n✅ 周报/月报测试完成")
