#!/usr/bin/env python3
"""
alert_notifier.py - 多渠道告警通知
功能：Discord/钉钉/微信/邮件通知
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
CONFIG_DIR = os.path.join(SHARED_DIR, "notifications")

class AlertNotifier:
    """多渠道告警通知器"""
    
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载通知配置"""
        config_file = os.path.join(CONFIG_DIR, "channels.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # 默认配置
        return {
            "discord": {
                "enabled": True,
                "webhook": os.getenv("DISCORD_WEBHOOK", "")
            },
            "dingtalk": {
                "enabled": False,
                "webhook": os.getenv("DINGTALK_WEBHOOK", "")
            },
            "wechat": {
                "enabled": False,
                "webhook": os.getenv("WECHAT_WEBHOOK", "")
            },
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "from_addr": "",
                "to_addrs": []
            }
        }
    
    def save_config(self):
        """保存通知配置"""
        config_file = os.path.join(CONFIG_DIR, "channels.json")
        with open(config_file, 'w') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def notify(self, alert: dict, channels: list = None):
        """发送通知"""
        if channels is None:
            channels = self._get_default_channels()
        
        results = {}
        for channel in channels:
            if channel == "discord":
                results["discord"] = self._notify_discord(alert)
            elif channel == "dingtalk":
                results["dingtalk"] = self._notify_dingtalk(alert)
            elif channel == "wechat":
                results["wechat"] = self._notify_wechat(alert)
            elif channel == "email":
                results["email"] = self._notify_email(alert)
        
        return results
    
    def notify_batch(self, alerts: list, channels: list = None):
        """批量发送通知"""
        if channels is None:
            channels = self._get_default_channels()
        
        results = {}
        for channel in channels:
            results[channel] = self._notify_batch(channel, alerts)
        
        return results
    
    def _get_default_channels(self) -> list:
        """获取默认通知渠道"""
        default = []
        if self.config.get("discord", {}).get("enabled"):
            default.append("discord")
        if self.config.get("dingtalk", {}).get("enabled"):
            default.append("dingtalk")
        if self.config.get("wechat", {}).get("enabled"):
            default.append("wechat")
        if self.config.get("email", {}).get("enabled"):
            default.append("email")
        return default
    
    def _notify_discord(self, alert: dict) -> bool:
        """发送Discord通知"""
        webhook = self.config.get("discord", {}).get("webhook")
        if not webhook:
            print("Discord webhook未配置")
            return False
        
        # 颜色映射
        colors = {
            "info": 0x3498db,
            "warning": 0xf39c12,
            "critical": 0xe74c3c
        }
        
        color = colors.get(alert.get("severity", "info"), 0x3498db)
        
        # 构建消息
        payload = {
            "embeds": [{
                "title": f"🚨 告警: {alert.get('name', 'Unknown')}",
                "color": color,
                "fields": [
                    {"name": "严重程度", "value": alert.get("severity", "unknown"), "inline": True},
                    {"name": "指标", "value": str(alert.get("metric", "")), "inline": True},
                    {"name": "当前值", "value": str(alert.get("value", "")), "inline": True},
                    {"name": "阈值", "value": str(alert.get("threshold", "")), "inline": True},
                    {"name": "触发时间", "value": alert.get("triggered_at", ""), "inline": False}
                ],
                "footer": {"text": "ClawShell Alert System"}
            }]
        }
        
        try:
            response = requests.post(webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Discord通知失败: {e}")
            return False
    
    def _notify_dingtalk(self, alert: dict) -> bool:
        """发送钉钉通知"""
        webhook = self.config.get("dingtalk", {}).get("webhook")
        if not webhook:
            print("钉钉webhook未配置")
            return False
        
        # 消息类型
        msg_type = "markdown"
        
        # 构建消息
        content = f"## 🚨 ClawShell告警\n\n"
        content += f"**告警名称**: {alert.get('name', 'Unknown')}\n\n"
        content += f"**严重程度**: {alert.get('severity', 'unknown')}\n\n"
        content += f"**指标**: {alert.get('metric', '')}\n\n"
        content += f"**当前值**: {alert.get('value', '')}\n\n"
        content += f"**阈值**: {alert.get('threshold', '')}\n\n"
        content += f"**触发时间**: {alert.get('triggered_at', '')}\n"
        
        payload = {
            "msgtype": msg_type,
            "markdown": {
                "title": f"告警: {alert.get('name', 'Unknown')}",
                "text": content
            }
        }
        
        try:
            response = requests.post(webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"钉钉通知失败: {e}")
            return False
    
    def _notify_wechat(self, alert: dict) -> bool:
        """发送微信通知"""
        webhook = self.config.get("wechat", {}).get("webhook")
        if not webhook:
            print("微信webhook未配置")
            return False
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"🚨 ClawShell告警\n\n告警: {alert.get('name')}\n严重程度: {alert.get('severity')}\n指标: {alert.get('metric')}\n值: {alert.get('value')}"
            }
        }
        
        try:
            response = requests.post(webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"微信通知失败: {e}")
            return False
    
    def _notify_email(self, alert: dict) -> bool:
        """发送邮件通知"""
        email_config = self.config.get("email", {})
        if not email_config.get("enabled"):
            print("邮件通知未启用")
            return False
        
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            msg = MIMEText(f"""
ClawShell 告警通知
==================

告警名称: {alert.get('name')}
严重程度: {alert.get('severity')}
指标: {alert.get('metric')}
当前值: {alert.get('value')}
阈值: {alert.get('threshold')}
触发时间: {alert.get('triggered_at')}

---
此邮件由ClawShell告警系统自动发送
""", "plain", "utf-8")
            
            msg["Subject"] = f"[{alert.get('severity', 'ALERT').upper()}] ClawShell告警: {alert.get('name')}"
            msg["From"] = email_config.get("from_addr", "")
            msg["To"] = ", ".join(email_config.get("to_addrs", []))
            
            server = smtplib.SMTP(email_config.get("smtp_server", ""), email_config.get("smtp_port", 587))
            server.starttls()
            server.login(email_config.get("from_addr", ""), email_config.get("password", ""))
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"邮件通知失败: {e}")
            return False
    
    def _notify_batch(self, channel: str, alerts: list) -> bool:
        """批量发送通知"""
        if not alerts:
            return True
        
        # 汇总告警
        summary = {
            "total": len(alerts),
            "critical": len([a for a in alerts if a.get("severity") == "critical"]),
            "warning": len([a for a in alerts if a.get("severity") == "warning"])
        }
        
        # 构建汇总告警
        summary_alert = {
            "name": "alert_summary",
            "severity": "critical" if summary["critical"] > 0 else "warning",
            "metric": "alert_count",
            "value": summary["total"],
            "triggered_at": datetime.now().isoformat(),
            "details": summary
        }
        
        if channel == "discord":
            return self._notify_discord(summary_alert)
        elif channel == "dingtalk":
            return self._notify_dingtalk(summary_alert)
        elif channel == "wechat":
            return self._notify_wechat(summary_alert)
        elif channel == "email":
            return self._notify_email(summary_alert)
        
        return False
    
    def enable_channel(self, channel: str):
        """启用渠道"""
        if channel in self.config:
            self.config[channel]["enabled"] = True
            self.save_config()
    
    def disable_channel(self, channel: str):
        """禁用渠道"""
        if channel in self.config:
            self.config[channel]["enabled"] = False
            self.save_config()
    
    def set_webhook(self, channel: str, webhook: str):
        """设置webhook"""
        if channel in self.config:
            self.config[channel]["webhook"] = webhook
            self.save_config()


if __name__ == "__main__":
    notifier = AlertNotifier()
    
    print("=" * 50)
    print("多渠道通知测试")
    print("=" * 50)
    
    # 测试告警
    test_alert = {
        "name": "high_cpu",
        "severity": "warning",
        "metric": "cpu_percent",
        "value": 92.5,
        "threshold": 90,
        "triggered_at": datetime.now().isoformat()
    }
    
    # 发送通知
    print("\n📤 发送Discord通知...")
    result = notifier.notify(test_alert, channels=["discord"])
    print(f"结果: {result}")
    
    # 查看配置
    print("\n📋 当前配置:")
    print(json.dumps(notifier.config, indent=2))
    
    print("\n✅ 通知测试完成")
