#!/usr/bin/env python3
"""
Monthly Report Generator - 月报生成器
功能：
1. 汇总本月工作数据
2. 生成结构化月报
3. 分析月度趋势
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# ==================== 配置 ====================

WORKSPACE_DIR = Path.home() / ".openclaw/workspace"
OUTPUT_DIR = Path.home() / "Documents/Obsidian/OpenClaw/Other/Monthly"
STATS_FILE = WORKSPACE_DIR / "efficiency-stats.json"

# ==================== 月报生成器 ====================

class MonthlyReportGenerator:
    def __init__(self):
        self.date = datetime.now()
        self.year = self.date.year
        self.month = self.date.month
        self.month_str = self.date.strftime("%Y年%m月")
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 计算本月时间范围
        self.start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            self.next_month = datetime(self.year + 1, 1, 1)
        else:
            self.next_month = datetime(self.year, self.month + 1, 1)
        self.end_date = self.next_month - timedelta(days=1)
    
    def collect_monthly_data(self) -> Dict:
        """收集本月数据"""
        data = {
            "year": self.year,
            "month": self.month,
            "month_str": self.month_str,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "weekly_reports": self._collect_weekly_reports(),
            "task_summary": self._collect_task_summary(),
            "phase_progress": self._collect_phase_progress(),
            "updates": self._collect_updates()
        }
        
        return data
    
    def _collect_weekly_reports(self) -> List[Dict]:
        """收集周报"""
        reports = []
        weekly_dir = Path.home() / "Documents/Obsidian/OpenClaw/Other/Weekly"
        
        if weekly_dir.exists():
            for report_file in weekly_dir.glob("周报-*.md"):
                content = report_file.read_text()
                # 检查是否是本月的周报
                if f"{self.year}" in content:
                    reports.append({
                        "file": str(report_file),
                        "name": report_file.name
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
        phases = [
            {"name": "Phase 1: 知识图谱", "progress": 100, "status": "✅"},
            {"name": "Phase 2: 智能问答", "progress": 100, "status": "✅"},
            {"name": "Phase 3: 自动化测试", "progress": 100, "status": "✅"},
            {"name": "Phase 4: 监控告警", "progress": 100, "status": "✅"},
            {"name": "Phase 5: 文档自动化", "progress": 50, "status": "🔄"}
        ]
        
        return phases
    
    def _collect_updates(self) -> List[Dict]:
        """收集本月更新"""
        updates = []
        
        # 确定月份目录
        month_str = f"{self.year}{self.month:02d}"
        update_dir = Path.home() / f"Documents/Obsidian/OpenClaw/Other/Update/{month_str}"
        
        if update_dir.exists():
            cutoff = self.start_date.timestamp()
            
            for update_file in update_dir.glob("*.md"):
                if update_file.stat().st_mtime > cutoff:
                    updates.append({
                        "file": update_file.name,
                        "date": datetime.fromtimestamp(update_file.stat().st_mtime).strftime("%Y-%m-%d")
                    })
        
        return updates
    
    def calculate_metrics(self, data: Dict) -> Dict:
        """计算月度指标"""
        summary = data["task_summary"]
        
        total = summary.get("total", 0)
        completed = summary.get("completed", 0)
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            "completion_rate": round(completion_rate, 1),
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": summary.get("in_progress", 0),
            "delayed_tasks": summary.get("delayed", 0),
            "weekly_reports_count": len(data["weekly_reports"]),
            "updates_count": len(data["updates"])
        }
    
    def generate_report(self, data: Dict, metrics: Dict) -> str:
        """生成月报"""
        
        report = f"""# 月报 - {data['month_str']}

**周期**: {data['start_date']} ~ {data['end_date']}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 月度概览

| 指标 | 数值 |
|------|------|
| 任务完成率 | {metrics['completion_rate']}% |
| 总任务数 | {metrics['total_tasks']} |
| 已完成 | {metrics['completed_tasks']} |
| 进行中 | {metrics['in_progress_tasks']} |
| 延期 | {metrics['delayed_tasks']} |
| 周报数 | {metrics['weekly_reports_count']} |
| 更新数 | {metrics['updates_count']} |

---

## Phase 进度总览

| Phase | 内容 | 进度 | 状态 |
|-------|------|------|------|
"""
        
        for phase in data["phase_progress"]:
            report += f"| {phase['name']} | {phase['progress']}% | {phase['status']} |\n"
        
        report += "\n## 本月周报\n\n"
        
        if data["weekly_reports"]:
            for weekly in data["weekly_reports"]:
                report += f"- [{weekly['name']}]\n"
        else:
            report += "- 无周报记录\n"
        
        report += "\n## 本月更新汇总\n\n"
        
        if data["updates"]:
            report += f"共 {len(data['updates'])} 条更新\n\n"
            for update in data["updates"][:15]:
                report += f"- [{update['date']}] {update['file']}\n"
            if len(data["updates"]) > 15:
                report += f"\n... 还有 {len(data['updates']) - 15} 条\n"
        else:
            report += "- 无更新记录\n"
        
        report += "\n## 本月总结\n\n"
        report += "- [ ] 待补充\n"
        
        report += "\n## 下月计划\n\n"
        report += "- [ ] 待补充\n"
        
        report += "\n---\n\n*本文档由系统自动生成*\n"
        
        return report
    
    def save_report(self, content: str) -> Path:
        """保存月报"""
        filename = f"月报-{self.year}年{self.month:02d}月.md"
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        return output_file
    
    def run(self) -> Path:
        """运行月报生成"""
        print(f"生成月报: {self.month_str} ({self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')})")
        
        # 收集数据
        data = self.collect_monthly_data()
        
        # 计算指标
        metrics = self.calculate_metrics(data)
        
        # 生成报告
        content = self.generate_report(data, metrics)
        
        # 保存报告
        output_file = self.save_report(content)
        
        print(f"月报已保存: {output_file}")
        
        return output_file

# ==================== 主函数 ====================

def main():
    generator = MonthlyReportGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        data = generator.collect_monthly_data()
        metrics = generator.calculate_metrics(data)
        content = generator.generate_report(data, metrics)
        print(content)
    else:
        output_file = generator.run()
        print(f"\n输出文件: {output_file}")

if __name__ == "__main__":
    main()
