#!/usr/bin/env python3
"""
AlertManager - 告警阈值配置系统
职责：
1. 配置各类监控阈值
2. 检测异常并触发告警
3. 多通道告警通知
4. 告警历史记录
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
ALERT_CONFIG_FILE = os.path.join(SHARED_DIR, "alert_config.json")
ALERT_HISTORY_FILE = os.path.join(SHARED_DIR, "alert_history.json")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "alert_manager.log")

# 默认阈值配置
DEFAULT_THRESHOLDS = {
    "agent": {
        "offline_minutes": 10,        # Agent离线超过10分钟告警
        "max_tasks_per_agent": 5,    # 单Agent最大任务数
        "task_timeout_minutes": 120   # 任务超时2小时告警
    },
    "system": {
        "cpu_percent": 80,           # CPU使用率告警
        "memory_percent": 85,        # 内存使用率告警
        "disk_percent": 90           # 磁盘使用率告警
    },
    "task": {
        "queue_depth": 20,           # 队列深度告警
        "failed_count_1h": 5,        # 1小时内失败任务数告警
        "pending_too_long_minutes": 60  # 任务pending太久
    },
    "event": {
        "error_rate_5m": 3,          # 5分钟内错误数告警
        "heartbeat_miss_count": 3    # 连续心跳丢失次数告警
    }
}

class AlertManager:
    def __init__(self):
        self.config_file = ALERT_CONFIG_FILE
        self.history_file = ALERT_HISTORY_FILE
        self.log_file = LOG_FILE
        self._ensure_files()
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    def _ensure_files(self):
        """确保必要文件存在"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        if not os.path.exists(self.config_file):
            self._save_config({"thresholds": DEFAULT_THRESHOLDS, "enabled": True})
        
        if not os.path.exists(self.history_file):
            self._save_history({"alerts": []})
    
    def _load_config(self) -> Dict:
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def _save_config(self, config: Dict):
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _load_history(self) -> Dict:
        with open(self.history_file, 'r') as f:
            return json.load(f)
    
    def _save_history(self, history: Dict):
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    # ========== 阈值配置 ==========
    
    def get_threshold(self, category: str, key: str) -> any:
        """获取阈值"""
        config = self._load_config()
        return config.get("thresholds", {}).get(category, {}).get(key)
    
    def set_threshold(self, category: str, key: str, value: any) -> bool:
        """设置阈值"""
        try:
            config = self._load_config()
            if "thresholds" not in config:
                config["thresholds"] = {}
            if category not in config["thresholds"]:
                config["thresholds"][category] = {}
            
            config["thresholds"][category][key] = value
            self._save_config(config)
            self.log(f"✅ 阈值已设置: {category}.{key} = {value}")
            return True
        except Exception as e:
            self.log(f"⚠️ 设置阈值失败: {e}")
            return False
    
    def get_all_thresholds(self) -> Dict:
        """获取所有阈值"""
        config = self._load_config()
        return config.get("thresholds", DEFAULT_THRESHOLDS)
    
    # ========== 告警触发 ==========
    
    def check_and_alert(self, category: str, key: str, value: any, message: str = None) -> bool:
        """检查阈值并触发告警"""
        config = self._load_config()
        
        if not config.get("enabled", True):
            return False
        
        threshold = self.get_threshold(category, key)
        if threshold is None:
            return False
        
        # 比较（假设是数值比较）
        triggered = False
        if isinstance(threshold, (int, float)):
            if value >= threshold:
                triggered = True
        elif isinstance(threshold, str):
            if value == threshold:
                triggered = True
        
        if triggered:
            alert_message = message or f"{category}.{key} 超过阈值: {value} >= {threshold}"
            return self.trigger_alert(category, key, value, threshold, alert_message)
        
        return False
    
    def trigger_alert(self, category: str, key: str, value: any, threshold: any, message: str) -> bool:
        """触发告警"""
        alert = {
            "id": f"alert-{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "key": key,
            "value": value,
            "threshold": threshold,
            "message": message,
            "status": "active"
        }
        
        # 记录历史
        history = self._load_history()
        history["alerts"].append(alert)
        
        # 只保留最近100条
        history["alerts"] = history["alerts"][-100:]
        self._save_history(history)
        
        self.log(f"🚨 告警触发: {message}")
        
        # TODO: 发送通知到各通道
        return True
    
    # ========== 预置检查 ==========
    
    def check_agent_offline(self, agent_status: Dict) -> List[Dict]:
        """检查Agent离线"""
        threshold = self.get_threshold("agent", "offline_minutes")
        alerts = []
        
        now = datetime.now()
        
        for agent_id, status in agent_status.get("agents", {}).items():
            last_heartbeat = status.get("last_heartbeat")
            if not last_heartbeat:
                continue
            
            # 解析时间
            try:
                last_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                # 转换为本地时间
                last_time = last_time.replace(tzinfo=None)
                diff_minutes = (now - last_time).total_seconds() / 60
                
                if diff_minutes > threshold:
                    alerts.append({
                        "agent_id": agent_id,
                        "offline_minutes": round(diff_minutes, 1),
                        "threshold": threshold
                    })
            except:
                pass
        
        return alerts
    
    def check_task_timeout(self, tasks: List[Dict]) -> List[Dict]:
        """检查任务超时"""
        threshold = self.get_threshold("agent", "task_timeout_minutes")
        alerts = []
        
        now = datetime.now()
        
        for task in tasks:
            if task.get("status") not in ["claimed", "processing"]:
                continue
            
            claimed_at = task.get("claimed_at")
            if not claimed_at:
                continue
            
            try:
                claimed_time = datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))
                claimed_time = claimed_time.replace(tzinfo=None)
                diff_minutes = (now - claimed_time).total_seconds() / 60
                
                if diff_minutes > threshold:
                    alerts.append({
                        "task_id": task.get("id"),
                        "title": task.get("title"),
                        "executing_minutes": round(diff_minutes, 1),
                        "threshold": threshold
                    })
            except:
                pass
        
        return alerts
    
    def check_queue_depth(self, tasks: List[Dict]) -> bool:
        """检查队列深度"""
        threshold = self.get_threshold("task", "queue_depth")
        pending_count = sum(1 for t in tasks if t.get("status") == "pending")
        
        return self.check_and_alert(
            "task", "queue_depth", pending_count,
            f"队列待处理任务过多: {pending_count} >= {threshold}"
        )
    
    def run_health_check(self, agent_status: Dict, tasks: List[Dict]) -> Dict:
        """运行健康检查"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": []
        }
        
        # 检查Agent离线
        offline_alerts = self.check_agent_offline(agent_status)
        if offline_alerts:
            for alert in offline_alerts:
                self.trigger_alert(
                    "agent", "offline", alert["offline_minutes"],
                    alert["threshold"],
                    f"Agent {alert['agent_id']} 已离线 {alert['offline_minutes']} 分钟"
                )
            results["checks"].append({"type": "agent_offline", "alerts": len(offline_alerts)})
        
        # 检查任务超时
        timeout_alerts = self.check_task_timeout(tasks)
        if timeout_alerts:
            for alert in timeout_alerts:
                self.trigger_alert(
                    "task", "timeout", alert["executing_minutes"],
                    alert["threshold"],
                    f"任务 {alert['task_id']} 执行超时 {alert['executing_minutes']} 分钟"
                )
            results["checks"].append({"type": "task_timeout", "alerts": len(timeout_alerts)})
        
        # 检查队列深度
        self.check_queue_depth(tasks)
        
        return results
    
    # ========== 历史查询 ==========
    
    def get_active_alerts(self) -> List[Dict]:
        """获取活跃告警"""
        history = self._load_history()
        return [a for a in history.get("alerts", []) if a.get("status") == "active"]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近告警"""
        history = self._load_history()
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for alert in history.get("alerts", []):
            try:
                alert_time = datetime.fromisoformat(alert["timestamp"])
                if alert_time > cutoff:
                    recent.append(alert)
            except:
                pass
        
        return recent
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        history = self._load_history()
        
        for alert in history.get("alerts", []):
            if alert.get("id") == alert_id:
                alert["status"] = "resolved"
                alert["resolved_at"] = datetime.now().isoformat()
                self._save_history(history)
                self.log(f"✅ 告警已解决: {alert_id}")
                return True
        
        return False


# CLI接口
if __name__ == "__main__":
    import sys
    
    am = AlertManager()
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "get":
        # get <category> <key>
        if len(sys.argv) > 2:
            value = am.get_threshold(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
            print(f"{sys.argv[2]}.{sys.argv[3]}: {value}")
        else:
            print("用法: alert_manager.py get <category> <key>")
    
    elif action == "set":
        # set <category> <key> <value>
        if len(sys.argv) > 4:
            value = sys.argv[4]
            # 尝试转换为数字
            try:
                value = int(value)
            except:
                try:
                    value = float(value)
                except:
                    pass
            
            am.set_threshold(sys.argv[2], sys.argv[3], value)
            print(f"已设置: {sys.argv[2]}.{sys.argv[3]} = {value}")
        else:
            print("用法: alert_manager.py set <category> <key> <value>")
    
    elif action == "thresholds":
        thresholds = am.get_all_thresholds()
        print(json.dumps(thresholds, indent=2, ensure_ascii=False))
    
    elif action == "active":
        alerts = am.get_active_alerts()
        print(f"活跃告警: {len(alerts)} 个")
        for a in alerts:
            print(f"  [{a['category']}] {a['message']}")
    
    elif action == "recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        alerts = am.get_recent_alerts(hours)
        print(f"最近 {hours} 小时告警: {len(alerts)} 个")
        for a in alerts[-10:]:
            print(f"  [{a['timestamp']}] {a['message']}")
    
    elif action == "resolve":
        if len(sys.argv) > 2:
            success = am.resolve_alert(sys.argv[2])
            print(f"解决告警{'成功' if success else '失败'}")
        else:
            print("用法: alert_manager.py resolve <alert_id>")
    
    elif action == "check":
        # 模拟检查
        print("运行健康检查...")
        results = am.run_health_check(
            {"agents": {}},
            []
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    elif action == "status":
        thresholds = am.get_all_thresholds()
        active = am.get_active_alerts()
        print(f"告警系统: {'启用' if True else '禁用'}")
        print(f"阈值配置: {len(thresholds)} 项")
        print(f"活跃告警: {len(active)} 个")
    
    else:
        print(f"未知操作: {action}")
        print("用法: alert_manager.py <get|set|thresholds|active|recent|resolve|check|status>")
