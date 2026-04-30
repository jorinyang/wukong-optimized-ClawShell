#!/usr/bin/env python3
"""
悟空日报生成器 - 每日工作汇总
功能：收集当日工作数据，生成结构化日报并保存到Obsidian
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "daily_report.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WuKongDailyReportGenerator:
    """悟空日报生成器"""

    def __init__(self):
        self.today = datetime.now()
        self.date_str = self.today.strftime("%Y-%m-%d")
        self.time_str = self.today.strftime("%H:%M:%S")
        
        # 输出路径配置
        self.output_dir = Path.home() / "Documents" / "Obsidian" / "WuKong" / "Daily"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 工作空间路径
        self.workspace_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace"
        
        self.data = {
            "date": self.date_str,
            "tasks_completed": [],
            "tasks_in_progress": [],
            "tasks_delayed": [],
            "new_tasks": [],
            "updates": [],
            "cron_tasks_run": [],
            "health_check": None,
            "skills_used": []
        }

    def collect_task_data(self) -> Dict:
        """收集任务数据"""
        logger.info("收集任务数据...")
        
        # 从任务跟踪文件读取
        task_file = self.workspace_dir / "task_tracking.json"
        
        if task_file.exists():
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    tracking = json.load(f)
                    self.data["tasks_completed"] = tracking.get("completedTasks", [])
                    self.data["tasks_in_progress"] = tracking.get("activeTasks", [])
                    self.data["tasks_delayed"] = tracking.get("delayedTasks", [])
                    self.data["new_tasks"] = tracking.get("newTasks", [])
                    logger.info(f"从 {task_file} 读取任务数据成功")
            except Exception as e:
                logger.warning(f"读取任务文件失败: {e}")
        
        return self.data

    def collect_cron_execution_data(self) -> List[Dict]:
        """收集定时任务执行数据"""
        logger.info("收集定时任务执行数据...")
        
        health_log_dir = self.workspace_dir / "health_logs"
        if health_log_dir.exists():
            # 查找今天的健康检查报告
            today_prefix = self.today.strftime("%Y%m%d")
            for report_file in health_log_dir.glob(f"health_report_*.json"):
                if today_prefix in report_file.name:
                    try:
                        with open(report_file, 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            self.data["health_check"] = {
                                "status": report.get("overall_status"),
                                "score": report.get("overall_score"),
                                "issues": len(report.get("issues", []))
                            }
                            break
                    except Exception as e:
                        logger.warning(f"读取健康报告失败: {e}")
        
        # 从健康检查日志读取
        health_log = health_log_dir / "health_check.log"
        if health_log.exists():
            try:
                content = health_log.read_text(encoding='utf-8')
                lines = content.split('\n')
                today_lines = [l for l in lines if self.date_str in l]
                self.data["cron_tasks_run"].append({
                    "name": "健康检查",
                    "last_run": today_lines[-1][:19] if today_lines else None
                })
            except Exception as e:
                logger.warning(f"读取健康日志失败: {e}")
        
        return self.data["cron_tasks_run"]

    def collect_skill_usage(self) -> List[str]:
        """收集今日使用的技能"""
        logger.info("收集技能使用情况...")
        
        # 从会话记录读取（如果有）
        sessions_dir = Path.home() / ".real" / "sessions"
        if sessions_dir.exists():
            today_sessions = []
            for session_dir in sessions_dir.glob("2026-*"):
                if session_dir.is_dir():
                    # 检查是否有今天的活动
                    session_json = session_dir / "session.json"
                    if session_json.exists():
                        try:
                            with open(session_json, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                                # 统计使用的技能
                                skills = session_data.get("skills_used", [])
                                self.data["skills_used"].extend(skills)
                        except Exception:
                            pass
        
        return self.data["skills_used"]

    def collect_updates(self) -> List[Dict]:
        """收集今日更新"""
        logger.info("收集今日更新...")
        
        # 从Obsidian更新目录读取
        update_dir = Path.home() / "Documents" / "Obsidian" / "WuKong" / "Update"
        
        if update_dir.exists():
            month_dir = update_dir / self.today.strftime("%Y%m")
            if month_dir.exists():
                for update_file in month_dir.glob("*.md"):
                    try:
                        content = update_file.read_text(encoding='utf-8')
                        # 检查是否是今天的更新
                        if self.date_str in content or \
                           update_file.stat().st_mtime > (self.today - timedelta(days=1)).timestamp():
                            self.data["updates"].append({
                                "file": update_file.name,
                                "title": self._extract_title(content)
                            })
                    except Exception as e:
                        logger.warning(f"读取更新文件失败: {e}")
        
        return self.data["updates"]

    def _extract_title(self, content: str) -> str:
        """提取标题"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "无标题"

    def generate_report(self) -> str:
        """生成日报内容"""
        logger.info("生成日报...")
        
        report = f"""# 日报 - {self.date_str}

**生成时间**: {self.time_str}  
**助手**: 悟空(WuKong)

---

## 📊 今日概况

| 指标 | 数值 |
|------|------|
| 已完成任务 | {len(self.data['tasks_completed'])} |
| 进行中任务 | {len(self.data['tasks_in_progress'])} |
| 延期任务 | {len(self.data['tasks_delayed'])} |
| 新增任务 | {len(self.data['new_tasks'])} |

"""
        
        # 健康状态
        if self.data["health_check"]:
            hc = self.data["health_check"]
            status_emoji = {"healthy": "✅", "warning": "⚠️", "unhealthy": "❌"}.get(hc["status"], "❓")
            report += f"""## 🏥 系统健康

{status_emoji} 今日健康评分: **{hc['score']}/100** ({hc['status']})
- 发现问题: {hc['issues']} 个

"""
        
        # 已完成任务
        report += "## ✅ 今日完成\n\n"
        if self.data["tasks_completed"]:
            for task in self.data["tasks_completed"]:
                report += f"- [x] {task}\n"
        else:
            report += "- 无\n"
        report += "\n"
        
        # 进行中任务
        report += "## 🔄 进行中\n\n"
        if self.data["tasks_in_progress"]:
            for task in self.data["tasks_in_progress"]:
                report += f"- [ ] {task}\n"
        else:
            report += "- 无\n"
        report += "\n"
        
        # 延期任务
        report += "## ⚠️ 延期任务\n\n"
        if self.data["tasks_delayed"]:
            for task in self.data["tasks_delayed"]:
                report += f"- 🔴 {task}\n"
        else:
            report += "- 无\n"
        report += "\n"
        
        # 新增任务
        if self.data["new_tasks"]:
            report += "## ➕ 新增任务\n\n"
            for task in self.data["new_tasks"]:
                report += f"- [ ] {task}\n"
            report += "\n"
        
        # 今日更新
        report += "## 📝 今日更新\n\n"
        if self.data["updates"]:
            for update in self.data["updates"]:
                report += f"- [[{update['file']}|{update['title']}]]\n"
        else:
            report += "- 无\n"
        report += "\n"
        
        # 定时任务执行记录
        if self.data["cron_tasks_run"]:
            report += "## ⏰ 定时任务\n\n"
            for task in self.data["cron_tasks_run"]:
                report += f"- ✅ {task['name']}"
                if task.get('last_run'):
                    report += f" ({task['last_run']})"
                report += "\n"
            report += "\n"
        
        # 使用的技能
        if self.data["skills_used"]:
            report += "## 🛠️ 使用技能\n\n"
            for skill in set(self.data["skills_used"]):
                report += f"- [[Skills/{skill}|{skill}]]\n"
            report += "\n"
        
        report += f"""---

*本日报由悟空自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report

    def save_report(self, content: str) -> Path:
        """保存日报"""
        filename = f"日报-{self.date_str}.md"
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"日报已保存: {output_file}")
        return output_file

    def run(self) -> Path:
        """执行日报生成"""
        logger.info("=" * 50)
        logger.info(f"悟空日报生成开始: {self.date_str}")
        logger.info("=" * 50)
        
        # 收集数据
        self.collect_task_data()
        self.collect_cron_execution_data()
        self.collect_skill_usage()
        self.collect_updates()
        
        # 生成报告
        content = self.generate_report()
        
        # 保存报告
        output_file = self.save_report(content)
        
        logger.info("=" * 50)
        logger.info(f"日报生成完成: {output_file}")
        logger.info("=" * 50)
        
        return output_file


def main():
    """主函数"""
    generator = WuKongDailyReportGenerator()
    
    # 支持 --preview 参数预览
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        generator.collect_task_data()
        generator.collect_updates()
        content = generator.generate_report()
        print(content)
    else:
        output_file = generator.run()
        print(f"\n日报已生成: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
