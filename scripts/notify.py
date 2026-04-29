#!/usr/bin/env python3
"""
Notifier - 多渠道通知脚本
功能：
1. 钉钉通知
2. 邮件通知
3. 控制台输出
4. 日志记录
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

LOG_DIR = Path.home() / ".openclaw/logs"
CONFIG_FILE = Path.home() / ".openclaw/workspace/notify_config.json"

# ==================== 通知客户端 ====================

class Notifier:
    def __init__(self):
        self.config = self.load_config()
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> Dict:
        """加载配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        
        return self._get_default_config()
    
    def save_config(self):
        """保存配置"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "dingtalk": {
                "enabled": True,
                "webhook": os.environ.get("DINGTALK_WEBHOOK", ""),
                "secret": os.environ.get("DINGTALK_SECRET", "")
            },
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "to": []
            },
            "console": {
                "enabled": True,
                "color": True
            },
            "log": {
                "enabled": True,
                "file": str(LOG_DIR / "notifications.json")
            }
        }
    
    def send(self, message: str, level: str = "info", title: str = None) -> bool:
        """发送通知"""
        if title is None:
            title = f"系统通知"
        
        # 构建通知内容
        content = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
        
        results = []
        
        # 发送到各渠道
        if self.config.get("console", {}).get("enabled", True):
            results.append(self._send_console(content))
        
        if self.config.get("dingtalk", {}).get("enabled", False):
            results.append(self._send_dingtalk(content))
        
        if self.config.get("email", {}).get("enabled", False):
            results.append(self._send_email(content))
        
        if self.config.get("log", {}).get("enabled", True):
            results.append(self._log_notification(content))
        
        # 返回是否至少有一个成功
        return any(results)
    
    def _send_console(self, content: Dict) -> bool:
        """发送到控制台"""
        colors = {
            "info": "\033[94m",      # 蓝色
            "warning": "\033[93m",   # 黄色
            "error": "\033[91m",     # 红色
            "critical": "\033[91m",  # 红色
            "reset": "\033[0m"
        }
        
        color = colors.get(content["level"], colors["info"])
        reset = colors["reset"]
        
        print(f"{color}[{content['level'].upper()}] {content['title']}{reset}")
        print(f"  {content['message']}")
        print(f"  时间: {content['timestamp']}")
        
        return True
    
    def _send_dingtalk(self, content: Dict) -> bool:
        """发送钉钉通知"""
        webhook = self.config.get("dingtalk", {}).get("webhook", "")
        
        if not webhook:
            print("钉钉webhook未配置")
            return False
        
        try:
            # 钉钉消息格式
            msg = {
                "msgtype": "markdown",
                "markdown": {
                    "title": content["title"],
                    "text": f"### {content['title']}\n\n{content['message']}\n\n> 时间: {content['timestamp']}\n> 级别: {content['level']}"
                }
            }
            
            response = requests.post(webhook, json=msg, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                print(f"钉钉通知发送成功")
                return True
            else:
                print(f"钉钉通知发送失败: {result}")
                return False
        
        except Exception as e:
            print(f"钉钉通知发送异常: {e}")
            return False
    
    def _send_email(self, content: Dict) -> bool:
        """发送邮件通知"""
        email_config = self.config.get("email", {})
        
        if not email_config.get("enabled"):
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = email_config.get("username")
            msg['To'] = ", ".join(email_config.get("to", []))
            msg['Subject'] = f"[{content['level'].upper()}] {content['title']}"
            
            body = f"{content['message']}\n\n时间: {content['timestamp']}"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config.get("smtp_server"), email_config.get("smtp_port"))
            server.starttls()
            server.login(email_config.get("username"), email_config.get("password"))
            server.send_message(msg)
            server.quit()
            
            print(f"邮件通知发送成功")
            return True
        
        except Exception as e:
            print(f"邮件通知发送失败: {e}")
            return False
    
    def _log_notification(self, content: Dict) -> bool:
        """记录到日志"""
        try:
            log_file = Path(self.config.get("log", {}).get("file", str(LOG_DIR / "notifications.json")))
            
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            
            logs.append(content)
            
            # 只保留最近100条
            logs = logs[-100:]
            
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            print(f"日志记录失败: {e}")
            return False
    
    def send_alert(self, alert: Dict) -> bool:
        """发送告警通知"""
        title = f"告警: {alert.get('message', '未知告警')}"
        level = alert.get('level', 'warning')
        message = alert.get('message', '')
        
        if 'value' in alert:
            message += f"\n当前值: {alert['value']}"
        if 'threshold' in alert:
            message += f"\n阈值: {alert['threshold']}"
        
        return self.send(message, level, title)

# ==================== 主函数 ====================

def main():
    notifier = Notifier()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  notify.py send <message> [level] [title]")
        print("  notify.py alert <alert_json>")
        print("  notify.py config show|set")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "send":
        message = sys.argv[2] if len(sys.argv) > 2 else "测试消息"
        level = sys.argv[3] if len(sys.argv) > 3 else "info"
        title = sys.argv[4] if len(sys.argv) > 4 else None
        
        if notifier.send(message, level, title):
            print("发送成功")
        else:
            print("发送失败")
    
    elif command == "alert":
        alert_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
        alert = json.loads(alert_json)
        
        if notifier.send_alert(alert):
            print("告警发送成功")
        else:
            print("告警发送失败")
    
    elif command == "config":
        if len(sys.argv) < 3:
            print(json.dumps(notifier.config, indent=2, ensure_ascii=False))
        else:
            subcommand = sys.argv[2]
            if subcommand == "show":
                print(json.dumps(notifier.config, indent=2, ensure_ascii=False))
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
