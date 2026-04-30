#!/usr/bin/env python3
"""
悟空晨报推送 - 每日信息早餐
功能：生成并推送每日晨报，包含昨日总结、今日提醒、天气信息等
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "morning_news.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WuKongMorningNews:
    """悟空晨报生成器"""

    def __init__(self):
        self.today = datetime.now()
        self.date_str = self.today.strftime("%Y-%m-%d")
        self.time_str = self.today.strftime("%H:%M:%S")
        self.weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][self.today.weekday()]
        
        # 路径配置
        self.workspace_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace"
        self.obsidian_dir = Path.home() / "Documents" / "Obsidian" / "WuKong"
        
        # 钉钉Webhook配置
        self.dingtalk_webhook = self._load_dingtalk_config()
        
        self.news = {
            "date": self.date_str,
            "weekday": self.weekday,
            "yesterday_summary": {},
            "today_reminders": [],
            "system_status": {},
            "pending_tasks": []
        }

    def _load_dingtalk_config(self) -> Optional[str]:
        """加载钉钉配置"""
        config_path = Path.home() / ".openclaw" / "plugins" / "cicd-deploy" / "config" / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 钉钉webhook通常在环境变量或单独配置
                    return None  # 暂时返回None，需要手动配置
            except Exception as e:
                logger.warning(f"加载钉钉配置失败: {e}")
        
        return None

    def get_yesterday_summary(self) -> Dict:
        """获取昨日日报摘要"""
        logger.info("获取昨日日报...")
        
        yesterday = self.today - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        
        # 查找昨日日报
        daily_dir = self.obsidian_dir / "Daily"
        if daily_dir.exists():
            yesterday_file = daily_dir / f"日报-{yesterday_str}.md"
            if yesterday_file.exists():
                try:
                    content = yesterday_file.read_text(encoding='utf-8')
                    self.news["yesterday_summary"] = {
                        "file": str(yesterday_file),
                        "date": yesterday_str,
                        "content_preview": content[:500]  # 截取前500字符
                    }
                    logger.info(f"已读取昨日日报: {yesterday_file}")
                except Exception as e:
                    logger.warning(f"读取昨日日报失败: {e}")
        
        return self.news["yesterday_summary"]

    def get_health_status(self) -> Dict:
        """获取系统健康状态"""
        logger.info("获取系统健康状态...")
        
        health_log_dir = self.workspace_dir / "health_logs"
        
        if health_log_dir.exists():
            # 查找最新的健康报告
            reports = sorted(health_log_dir.glob("health_report_*.json"), 
                           key=lambda p: p.stat().st_mtime, 
                           reverse=True)
            
            if reports:
                latest = reports[0]
                try:
                    with open(latest, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        self.news["system_status"] = {
                            "status": report.get("overall_status"),
                            "score": report.get("overall_score"),
                            "issues_count": len(report.get("issues", [])),
                            "report_time": report.get("timestamp")
                        }
                except Exception as e:
                    logger.warning(f"读取健康报告失败: {e}")
        
        return self.news["system_status"]

    def get_pending_tasks(self) -> List[str]:
        """获取待办任务"""
        logger.info("获取待办任务...")
        
        task_file = self.workspace_dir / "task_tracking.json"
        
        if task_file.exists():
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    tracking = json.load(f)
                    pending = tracking.get("activeTasks", []) + tracking.get("delayedTasks", [])
                    self.news["pending_tasks"] = pending[:5]  # 只取前5个
            except Exception as e:
                logger.warning(f"读取任务文件失败: {e}")
        
        return self.news["pending_tasks"]

    def get_reminders(self) -> List[Dict]:
        """获取提醒事项"""
        logger.info("获取提醒事项...")
        
        # 从日程文件读取
        calendar_file = self.workspace_dir / "calendar.json"
        
        if calendar_file.exists():
            try:
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    calendar = json.load(f)
                    today_str = self.date_str
                    reminders = []
                    
                    for event in calendar.get("events", []):
                        if event.get("date", "").startswith(today_str):
                            reminders.append({
                                "time": event.get("time", "全天"),
                                "title": event.get("title", "无标题"),
                                "priority": event.get("priority", "normal")
                            })
                    
                    self.news["today_reminders"] = reminders
            except Exception as e:
                logger.warning(f"读取日程文件失败: {e}")
        
        return self.news["today_reminders"]

    def generate_markdown_news(self) -> str:
        """生成Markdown格式晨报"""
        logger.info("生成晨报...")
        
        news = f"""# ☀️ 悟空晨报 - {self.date_str} {self.weekday}

> 生成时间: {self.time_str}

---

## 📊 昨日概况

"""
        
        # 昨日日报摘要
        if self.news["yesterday_summary"]:
            summary = self.news["yesterday_summary"]
            news += f"昨日({summary['date']})工作已记录，详见 [[{Path(summary['file']).name}|日报]]\n\n"
        else:
            news += "昨日无日报记录\n\n"
        
        # 系统健康
        news += "## 🏥 系统状态\n\n"
        if self.news["system_status"]:
            status = self.news["system_status"]
            status_icon = {"healthy": "✅", "warning": "⚠️", "unhealthy": "❌"}.get(status["status"], "❓")
            issues_text = f"，发现 {status['issues_count']} 个问题" if status["issues_count"] > 0 else ""
            news += f"{status_icon} 悟空健康评分: **{status['score']}/100**{issues_text}\n\n"
        else:
            news += "⚪ 暂无健康数据\n\n"
        
        # 今日提醒
        news += "## 📅 今日提醒\n\n"
        if self.news["today_reminders"]:
            for reminder in self.news["today_reminders"]:
                priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(reminder["priority"], "⚪")
                news += f"{priority_icon} [{reminder['time']}] {reminder['title']}\n"
        else:
            news += "今日暂无日程安排\n\n"
        
        # 待办任务
        news += "## 📋 待办任务\n\n"
        if self.news["pending_tasks"]:
            for i, task in enumerate(self.news["pending_tasks"], 1):
                news += f"{i}. {task}\n"
        else:
            news += "暂无待办任务\n\n"
        
        news += f"""---

*悟空晨报 | 每日 {self.today.strftime('%H:%M')} 自动推送*
"""
        
        return news

    def generate_dingtalk_message(self) -> Dict:
        """生成钉钉消息格式"""
        content = self.generate_markdown_news()
        
        # 转换为钉钉markdown格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"悟空晨报 - {self.date_str}",
                "text": content
            }
        }
        
        return message

    def save_news(self, content: str) -> Path:
        """保存晨报"""
        output_dir = self.obsidian_dir / "Morning"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"晨报-{self.date_str}.md"
        output_file = output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"晨报已保存: {output_file}")
        return output_file

    def send_dingtalk(self, message: Dict) -> bool:
        """发送钉钉消息"""
        if not self.dingtalk_webhook:
            logger.warning("钉钉Webhook未配置，跳过推送")
            return False
        
        try:
            import urllib.request
            import ssl
            
            data = json.dumps(message).encode('utf-8')
            req = urllib.request.Request(
                self.dingtalk_webhook,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # 忽略SSL验证（如果需要）
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, data=data, timeout=10, context=ctx) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('errcode') == 0:
                    logger.info("钉钉推送成功")
                    return True
                else:
                    logger.error(f"钉钉推送失败: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"钉钉推送异常: {e}")
            return False

    def run(self, push: bool = True) -> Path:
        """执行晨报生成"""
        logger.info("=" * 50)
        logger.info(f"悟空晨报生成开始: {self.date_str} {self.weekday}")
        logger.info("=" * 50)
        
        # 收集数据
        self.get_yesterday_summary()
        self.get_health_status()
        self.get_reminders()
        self.get_pending_tasks()
        
        # 生成晨报
        content = self.generate_markdown_news()
        
        # 保存晨报
        output_file = self.save_news(content)
        
        # 推送钉钉
        if push:
            message = self.generate_dingtalk_message()
            self.send_dingtalk(message)
        
        logger.info("=" * 50)
        logger.info(f"晨报生成完成: {output_file}")
        logger.info("=" * 50)
        
        return output_file


def main():
    """主函数"""
    generator = WuKongMorningNews()
    
    # 支持参数
    push = "--no-push" not in sys.argv
    
    output_file = generator.run(push=push)
    
    if push:
        print(f"\n晨报已生成并推送: {output_file}")
    else:
        print(f"\n晨报已生成(未推送): {output_file}")
        print(generator.generate_markdown_news())
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
