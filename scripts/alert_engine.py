#!/usr/bin/env python3
"""
alert_engine.py - 告警规则引擎
功能：基于指标阈值的告警触发和升级
"""

import os
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
ALERT_DIR = os.path.join(SHARED_DIR, "alerts")

class AlertEngine:
    """告警规则引擎"""
    
    # 默认告警规则
    DEFAULT_RULES = [
        {
            "name": "high_cpu",
            "metric": "cpu_percent",
            "threshold": 90,
            "condition": "greater",
            "severity": "warning",
            "duration": 60,  # 持续60秒才告警
            "enabled": True
        },
        {
            "name": "critical_cpu",
            "metric": "cpu_percent",
            "threshold": 95,
            "condition": "greater",
            "severity": "critical",
            "duration": 30,
            "enabled": True
        },
        {
            "name": "high_memory",
            "metric": "memory_percent",
            "threshold": 85,
            "condition": "greater",
            "severity": "warning",
            "duration": 60,
            "enabled": True
        },
        {
            "name": "critical_memory",
            "metric": "memory_percent",
            "threshold": 95,
            "condition": "greater",
            "severity": "critical",
            "duration": 30,
            "enabled": True
        },
        {
            "name": "disk_full",
            "metric": "disk_percent",
            "threshold": 90,
            "condition": "greater",
            "severity": "warning",
            "duration": 0,
            "enabled": True
        },
        {
            "name": "agent_offline",
            "metric": "agent_status",
            "condition": "equals",
            "value": "offline",
            "severity": "critical",
            "duration": 0,
            "enabled": True
        },
        {
            "name": "gateway_down",
            "metric": "gateway_status",
            "condition": "equals",
            "value": "down",
            "severity": "critical",
            "duration": 0,
            "enabled": True
        },
        {
            "name": "high_task_queue",
            "metric": "pending_tasks",
            "threshold": 50,
            "condition": "greater",
            "severity": "warning",
            "duration": 300,
            "enabled": True
        }
    ]
    
    def __init__(self, rules_file: str = None):
        os.makedirs(ALERT_DIR, exist_ok=True)
        self.rules = self.DEFAULT_RULES.copy()
        self.alert_history = []
        self.active_alerts = {}
        
        if rules_file and os.path.exists(rules_file):
            self.load_rules(rules_file)
    
    def evaluate(self, metrics: dict) -> list:
        """评估指标是否触发告警"""
        triggered = []
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            metric_value = self._get_metric_value(metrics, rule["metric"])
            if metric_value is None:
                continue
            
            if self._check_condition(metric_value, rule):
                alert = self._create_alert(rule, metric_value)
                triggered.append(alert)
        
        return triggered
    
    def _get_metric_value(self, metrics: dict, metric_name: str):
        """获取指标值"""
        return metrics.get(metric_name)
    
    def _check_condition(self, value, rule: dict) -> bool:
        """检查条件是否满足"""
        condition = rule.get("condition")
        
        if condition == "greater":
            threshold = rule.get("threshold")
            return value > threshold
        elif condition == "less":
            threshold = rule.get("threshold")
            return value < threshold
        elif condition == "equals":
            expected = rule.get("value")
            return value == expected
        elif condition == "not_equals":
            expected = rule.get("value")
            return value != expected
        
        return False
    
    def _create_alert(self, rule: dict, metric_value) -> dict:
        """创建告警"""
        alert_id = f"{rule['name']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        alert = {
            "id": alert_id,
            "name": rule["name"],
            "severity": rule["severity"],
            "metric": rule["metric"],
            "value": metric_value,
            "threshold": rule.get("threshold") or rule.get("value"),
            "triggered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        return alert
    
    def process_alerts(self, alerts: list) -> dict:
        """处理告警"""
        processed = {
            "new": [],
            "escalated": [],
            "resolved": []
        }
        
        for alert in alerts:
            alert_id = alert["id"]
            
            if alert_id not in self.active_alerts:
                # 新告警
                self.active_alerts[alert_id] = alert
                processed["new"].append(alert)
                self.alert_history.append(alert)
            else:
                # 已存在的告警，检查是否升级
                existing = self.active_alerts[alert_id]
                if self._should_escalate(existing, alert):
                    alert["escalated_from"] = existing["severity"]
                    self.active_alerts[alert_id] = alert
                    processed["escalated"].append(alert)
        
        # 检查已解决的告警
        resolved = self.check_resolved()
        processed["resolved"] = resolved
        
        # 保存告警状态
        self._save_alert_state()
        
        return processed
    
    def _should_escalate(self, existing: dict, new: dict) -> bool:
        """检查是否需要升级"""
        severity_levels = {"info": 0, "warning": 1, "critical": 2}
        
        old_level = severity_levels.get(existing["severity"], 0)
        new_level = severity_levels.get(new["severity"], 0)
        
        return new_level > old_level
    
    def check_resolved(self) -> list:
        """检查已解决的告警"""
        resolved = []
        current_metrics = self.collect_metrics()
        current_alerts = list(self.active_alerts.keys())
        
        for alert_id in current_alerts:
            alert = self.active_alerts[alert_id]
            rule = self._find_rule(alert["name"])
            
            if rule:
                metric_value = self._get_metric_value(current_metrics, rule["metric"])
                if metric_value is not None and not self._check_condition(metric_value, rule):
                    # 告警已解决
                    alert["resolved_at"] = datetime.now().isoformat()
                    alert["status"] = "resolved"
                    resolved.append(alert)
                    del self.active_alerts[alert_id]
        
        return resolved
    
    def _find_rule(self, rule_name: str) -> dict:
        """查找规则"""
        for rule in self.rules:
            if rule["name"] == rule_name:
                return rule
        return None
    
    def collect_metrics(self) -> dict:
        """收集当前指标"""
        metrics = {}
        
        # CPU
        metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
        
        # 内存
        mem = psutil.virtual_memory()
        metrics["memory_percent"] = mem.percent
        metrics["memory_available_mb"] = mem.available / (1024 * 1024)
        
        # 磁盘
        disk = psutil.disk_usage('/')
        metrics["disk_percent"] = disk.percent
        metrics["disk_free_gb"] = disk.free / (1024 * 1024 * 1024)
        
        # Gateway状态
        metrics["gateway_status"] = self._check_gateway_status()
        
        # Agent状态
        metrics["agent_status"] = self._check_agent_status()
        
        # 任务队列
        metrics["pending_tasks"] = self._check_pending_tasks()
        
        return metrics
    
    def _check_gateway_status(self) -> str:
        """检查Gateway状态"""
        try:
            result = subprocess.run(
                ["openclaw", "gateway", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "up" if "running" in result.stdout.lower() else "down"
        except:
            return "unknown"
    
    def _check_agent_status(self) -> str:
        """检查Agent状态"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "--all-agents"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return "online"
            return "offline"
        except:
            return "unknown"
    
    def _check_pending_tasks(self) -> int:
        """检查待处理任务数"""
        queue_file = os.path.join(SHARED_DIR, "task-queue.json")
        if not os.path.exists(queue_file):
            return 0
        
        try:
            with open(queue_file, 'r') as f:
                data = json.load(f)
            return len([t for t in data.get("tasks", []) if t.get("status") == "pending"])
        except:
            return 0
    
    def get_active_alerts(self) -> list:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_summary(self) -> dict:
        """获取告警摘要"""
        summary = {
            "total": len(self.alert_history),
            "active": len(self.active_alerts),
            "by_severity": {
                "critical": 0,
                "warning": 0,
                "info": 0
            }
        }
        
        for alert in self.active_alerts.values():
            severity = alert.get("severity", "info")
            if severity in summary["by_severity"]:
                summary["by_severity"][severity] += 1
        
        return summary
    
    def load_rules(self, rules_file: str):
        """加载规则"""
        with open(rules_file, 'r') as f:
            self.rules = json.load(f)
    
    def save_rules(self, rules_file: str):
        """保存规则"""
        with open(rules_file, 'w') as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)
    
    def _save_alert_state(self):
        """保存告警状态"""
        state_file = os.path.join(ALERT_DIR, "alert_state.json")
        state = {
            "active_alerts": self.active_alerts,
            "saved_at": datetime.now().isoformat()
        }
        with open(state_file, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def add_rule(self, rule: dict):
        """添加规则"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self.rules):
            if rule["name"] == rule_name:
                self.rules.pop(i)
                return True
        return False


if __name__ == "__main__":
    engine = AlertEngine()
    
    print("=" * 50)
    print("告警规则引擎测试")
    print("=" * 50)
    
    # 收集指标
    print("\n📊 收集系统指标...")
    metrics = engine.collect_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # 评估告警
    print("\n🔔 评估告警...")
    alerts = engine.evaluate(metrics)
    print(f"  触发告警数: {len(alerts)}")
    
    # 处理告警
    if alerts:
        print("\n⚠️ 处理告警...")
        processed = engine.process_alerts(alerts)
        print(f"  新告警: {len(processed['new'])}")
        print(f"  升级: {len(processed['escalated'])}")
        print(f"  已解决: {len(processed['resolved'])}")
    
    # 告警摘要
    summary = engine.get_alert_summary()
    print(f"\n📈 告警摘要:")
    print(f"  总告警数: {summary['total']}")
    print(f"  活跃告警: {summary['active']}")
    print(f"  严重: {summary['by_severity']['critical']}")
    print(f"  警告: {summary['by_severity']['warning']}")
    
    print("\n✅ 告警引擎测试完成")
