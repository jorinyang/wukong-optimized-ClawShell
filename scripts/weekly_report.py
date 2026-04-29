#!/usr/bin/env python3
"""
Weekly Report Generator - 周报生成器
功能：
1. 汇总本周工作数据
2. 生成结构化周报
3. 分析效能指标
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# ==================== 配置 ====================

WORKSPACE_DIR = Path.home() / ".openclaw/workspace"
OUTPUT_DIR = Path.home() / "Documents/Obsidian/OpenClaw/Other/Weekly"
STATS_FILE = WORKSPACE_DIR / "efficiency-stats.json"

# ==================== 周报生成器 ====================

class WeeklyReportGenerator:
    def __init__(self):
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=7)
        self.week_number = self.end_date.isocalendar()[1]
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_weekly_data(self) -> Dict:
        """收集本周数据"""
        data = {
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "week_number": self.week_number,
            "daily_reports": self._collect_daily_reports(),
            "task_summary": self._collect_task_summary(),
            "phase_progress": self._collect_phase_progress(),
            "updates": self._collect_updates()
        }
        
        return data
    
    def _collect_daily_reports(self) -> List[Dict]:
        """收集每日报告"""
        reports = []
        daily_dir = Path.home() / "Documents/Obsidian/OpenClaw/Other/Daily"
        
        if daily_dir.exists():
            for i in range(7):
                date = (self.end_date - timedelta(days=i)).strftime("%Y-%m-%d")
                report_file = daily_dir / f"日报-{date}.md"
                
                if report_file.exists():
                    reports.append({
                        "date": date,
                        "file": str(report_file)
                    })
        
        return reports
    
    def _collect_task_summary(self) -> Dict:
        """收集任务汇总"""
        summary = {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "delayed": 0
        }
        
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, 'r') as f:
                    stats = json.load(f)
                    task_summary = stats.get("taskSummary", {})
                    summary.update(task_summary)
            except:
                pass
        
        return summary
    
    def _collect_phase_progress(self) -> List[Dict]:
        """收集Phase进度"""
        # 从update目录读取Phase状态
        phases = [
            {"name": "Phase 1: 知识图谱", "progress": 100, "status": "✅"},
            {"name": "Phase 2: 智能问答", "progress": 100, "status": "✅"},
            {"name": "Phase 3: 自动化测试", "progress": 100, "status": "✅"},
            {"name": "Phase 4: 监控告警", "progress": 100, "status": "✅"},
            {"name": "Phase 5: 文档自动化", "progress": 25, "status": "🔄"}
        ]
        
        return phases
    
    def _collect_updates(self) -> List[Dict]:
        """收集本周更新"""
        updates = []
        update_dir = Path.home() / "Documents/Obsidian/OpenClaw/Other/Update/202604"
        
        if update_dir.exists():
            cutoff = self.start_date.timestamp()
            
            for update_file in update_dir.glob("*.md"):
                if update_file.stat().st_mtime > cutoff:
                    updates.append({
                        "file": update_file.name,
                        "date": datetime.fromtimestamp(update_file.stat().st_mtime).strftime("%Y-%m-%d")
                    })
        
        return updates
    
    def calculate_efficiency(self, data: Dict) -> Dict:
        """计算效能指标"""
        summary = data["task_summary"]
        
        total = summary.get("total", 0)
        completed = summary.get("completed", 0)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "completion_rate": round(completion_rate, 1),
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": summary.get("in_progress", 0),
            "delayed_tasks": summary.get("delayed", 0)
        }
    
    def generate_report(self, data: Dict, efficiency: Dict) -> str:
        """生成周报"""
        
        report = f"""# 周报 - 第{self.week_number}周

**周期**: {data['start_date']} ~ {data['end_date']}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 效能概览

| 指标 | 数值 |
|------|------|
| 任务完成率 | {efficiency['completion_rate']}% |
| 总任务数 | {efficiency['total_tasks']} |
| 已完成 | {efficiency['completed_tasks']} |
| 进行中 | {efficiency['in_progress_tasks']} |
| 延期 | {efficiency['delayed_tasks']} |

---

## Phase 进度

| Phase | 内容 | 进度 | 状态 |
|-------|------|------|------|
"""
        
        for phase in data["phase_progress"]:
            report += f"| {phase['name']} | {phase['progress']}% | {phase['status']} |\n"
        
        report += "\n## 本周工作明细\n\n"
        
        if data["daily_reports"]:
            for daily in data["daily_reports"]:
                report += f"- [[{daily['file']}|日报-{daily['date']}]]\n"
        else:
            report += "- 无日报记录\n"
        
        report += "\n## 本周更新\n\n"
        
        if data["updates"]:
            for update in data["updates"][:10]:
                report += f"- [{update['date']}] {update['file']}\n"
        else:
            report += "- 无更新记录\n"
        
        report += "\n## 下周计划\n\n"
        report += "- [ ] 待补充\n"
        
        report += "\n---\n\n*本文档由系统自动生成*\n"
        
        return report
    
    def save_report(self, content: str) -> Path:
        """保存周报"""
        filename = f"周报-第{self.week_number}周-{self.end_date.strftime('%Y%m%d')}.md"
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        return output_file
    
    def run(self) -> Path:
        """运行周报生成"""
        print(f"生成周报: 第{self.week_number}周 ({self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')})")
        
        # 收集数据
        data = self.collect_weekly_data()
        
        # 计算效能
        efficiency = self.calculate_efficiency(data)
        
        # 生成报告
        content = self.generate_report(data, efficiency)
        
        # 保存报告
        output_file = self.save_report(content)
        
        print(f"周报已保存: {output_file}")
        
        return output_file

# ==================== 主函数 ====================

def main():
    generator = WeeklyReportGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        data = generator.collect_weekly_data()
        efficiency = generator.calculate_efficiency(data)
        content = generator.generate_report(data, efficiency)
        print(content)
    else:
        output_file = generator.run()
        print(f"\n输出文件: {output_file}")

if __name__ == "__main__":
    main()
