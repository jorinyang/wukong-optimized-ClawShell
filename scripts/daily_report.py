#!/usr/bin/env python3
"""
Daily Report Generator - 日报生成器
功能：
1. 收集今日工作数据
2. 生成结构化日报
3. 输出到Obsidian
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# ==================== 配置 ====================

WORKSPACE_DIR = Path.home() / ".openclaw/workspace"
OUTPUT_DIR = Path.home() / "Documents/Obsidian/OpenClaw/Other/Daily"
TEMPLATE_DIR = Path.home() / ".openclaw/templates"

# ==================== 日报生成器 ====================

class DailyReportGenerator:
    def __init__(self):
        self.date = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_task_data(self) -> Dict:
        """收集今日任务数据"""
        # 从task-tracking.json读取
        task_file = WORKSPACE_DIR / "task-tracking.json"
        
        data = {
            "date": self.date,
            "tasks_completed": [],
            "tasks_in_progress": [],
            "tasks_delayed": [],
            "new_tasks": []
        }
        
        if task_file.exists():
            try:
                with open(task_file, 'r') as f:
                    tracking = json.load(f)
                    data["tasks_completed"] = tracking.get("completedTasks", [])
                    data["tasks_in_progress"] = tracking.get("activeTasks", [])
                    data["tasks_delayed"] = tracking.get("delayedTasks", [])
            except:
                pass
        
        # 从update目录读取今日更新
        update_data = self._collect_updates()
        data["updates"] = update_data
        
        return data
    
    def _collect_updates(self) -> List[Dict]:
        """收集今日更新"""
        updates = []
        
        update_dir = Path.home() / "Documents/Obsidian/OpenClaw/Other/Update/202604"
        
        if update_dir.exists():
            for update_file in update_dir.glob("*.md"):
                # 检查是否是今天的更新
                content = update_file.read_text()
                if self.date in content or update_file.stat().st_mtime > (datetime.now() - timedelta(days=1)).timestamp():
                    updates.append({
                        "file": update_file.name,
                        "title": self._extract_title(content)
                    })
        
        return updates
    
    def _extract_title(self, content: str) -> str:
        """提取标题"""
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "无标题"
    
    def generate_report(self, data: Dict) -> str:
        """生成日报"""
        
        report = f"""# 日报 - {data['date']}

**生成时间**: {datetime.now().strftime('%H:%M:%S')}

---

## 今日完成

"""
        
        if data["tasks_completed"]:
            for task in data["tasks_completed"]:
                report += f"- [x] {task}\n"
        else:
            report += "- 无\n"
        
        report += "\n## 进行中\n\n"
        
        if data["tasks_in_progress"]:
            for task in data["tasks_in_progress"]:
                report += f"- [ ] {task}\n"
        else:
            report += "- 无\n"
        
        report += "\n## 延期任务\n\n"
        
        if data["tasks_delayed"]:
            for task in data["tasks_delayed"]:
                report += f"- ⚠️ {task}\n"
        else:
            report += "- 无\n"
        
        report += "\n## 今日更新\n\n"
        
        if data.get("updates"):
            for update in data["updates"]:
                report += f"- [[{update['file']}|{update['title']}]]\n"
        else:
            report += "- 无\n"
        
        report += "\n---\n\n*本文档由系统自动生成*\n"
        
        return report
    
    def save_report(self, content: str) -> Path:
        """保存日报"""
        filename = f"日报-{self.date}.md"
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        return output_file
    
    def run(self) -> Path:
        """运行日报生成"""
        print(f"生成日报: {self.date}")
        
        # 收集数据
        data = self.collect_task_data()
        
        # 生成报告
        content = self.generate_report(data)
        
        # 保存报告
        output_file = self.save_report(content)
        
        print(f"日报已保存: {output_file}")
        
        return output_file

# ==================== 主函数 ====================

def main():
    generator = DailyReportGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        data = generator.collect_task_data()
        content = generator.generate_report(data)
        print(content)
    else:
        output_file = generator.run()
        print(f"\n输出文件: {output_file}")

if __name__ == "__main__":
    main()
