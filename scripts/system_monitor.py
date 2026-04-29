#!/usr/bin/env python3
"""
System Monitor - 系统监控脚本
功能：
1. 监控CPU/内存/磁盘
2. 监控进程状态
3. 监控服务健康
4. 告警触发
"""

import os
import sys
import json
import time
import psutil
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

LOG_DIR = Path.home() / ".openclaw/logs"
STATE_DIR = Path.home() / ".openclaw/workspace"

# 告警阈值
CPU_THRESHOLD = 80.0  # %
MEMORY_THRESHOLD = 85.0  # %
DISK_THRESHOLD = 90.0  # %

# ==================== 监控模块 ====================

class SystemMonitor:
    def __init__(self):
        self.alerts = []
        self.hostname = socket.gethostname()
    
    def get_cpu_usage(self) -> Dict:
        """获取CPU使用率"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        result = {
            "percent": cpu_percent,
            "count": cpu_count,
            "status": "warning" if cpu_percent > CPU_THRESHOLD else "normal"
        }
        
        if result["status"] == "warning":
            self.alerts.append({
                "type": "cpu",
                "level": "warning",
                "message": f"CPU使用率 {cpu_percent}% 超过阈值 {CPU_THRESHOLD}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    
    def get_memory_usage(self) -> Dict:
        """获取内存使用率"""
        mem = psutil.virtual_memory()
        
        result = {
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent,
            "used": mem.used,
            "status": "warning" if mem.percent > MEMORY_THRESHOLD else "normal"
        }
        
        if result["status"] == "warning":
            self.alerts.append({
                "type": "memory",
                "level": "warning",
                "message": f"内存使用率 {mem.percent}% 超过阈值 {MEMORY_THRESHOLD}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    
    def get_disk_usage(self, path: str = "/") -> Dict:
        """获取磁盘使用率"""
        disk = psutil.disk_usage(path)
        
        result = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "path": path,
            "status": "warning" if disk.percent > DISK_THRESHOLD else "normal"
        }
        
        if result["status"] == "warning":
            self.alerts.append({
                "type": "disk",
                "level": "warning",
                "message": f"磁盘使用率 {disk.percent}% 超过阈值 {DISK_THRESHOLD}%",
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    
    def get_process_list(self, limit: int = 10) -> List[Dict]:
        """获取进程列表（按CPU使用率排序）"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_percent": proc.info['cpu_percent'],
                    "memory_percent": proc.info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按CPU使用率排序
        processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        
        return processes[:limit]
    
    def check_service(self, service_name: str) -> Dict:
        """检查服务状态"""
        result = {
            "service": service_name,
            "running": False,
            "status": "unknown"
        }
        
        for proc in psutil.process_iter(['name']):
            try:
                if service_name.lower() in proc.info['name'].lower():
                    result["running"] = True
                    result["status"] = "running"
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not result["running"]:
            result["status"] = "stopped"
            self.alerts.append({
                "type": "service",
                "level": "error",
                "message": f"服务 {service_name} 已停止",
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    
    def get_network_status(self) -> Dict:
        """获取网络状态"""
        net_io = psutil.net_io_counters()
        
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout
        }
    
    def monitor_all(self) -> Dict:
        """执行全面监控"""
        self.alerts = []  # 重置告警
        
        return {
            "timestamp": datetime.now().isoformat(),
            "hostname": self.hostname,
            "cpu": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "network": self.get_network_status(),
            "top_processes": self.get_process_list(5),
            "alerts": self.alerts,
            "alert_count": len(self.alerts)
        }
    
    def save_state(self, state: Dict):
        """保存监控状态"""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = STATE_DIR / "system_monitor.json"
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def load_state(self) -> Optional[Dict]:
        """加载上次监控状态"""
        state_file = STATE_DIR / "system_monitor.json"
        
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        
        return None

# ==================== 主函数 ====================

def main():
    monitor = SystemMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "cpu":
            result = monitor.get_cpu_usage()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "memory":
            result = monitor.get_memory_usage()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "disk":
            result = monitor.get_disk_usage()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "process":
            result = monitor.get_process_list()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "service":
            service = sys.argv[2] if len(sys.argv) > 2 else "openclaw"
            result = monitor.check_service(service)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "network":
            result = monitor.get_network_status()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "all":
            result = monitor.monitor_all()
            monitor.save_state(result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "alerts":
            monitor.monitor_all()
            print(json.dumps(monitor.alerts, indent=2, ensure_ascii=False))
        
        else:
            print(f"Unknown command: {command}")
            print("Usage:")
            print("  system_monitor.py cpu|memory|disk|process|service|network|all|alerts")
    
    else:
        # 默认执行全面监控
        result = monitor.monitor_all()
        monitor.save_state(result)
        
        print(f"监控时间: {result['timestamp']}")
        print(f"主机: {result['hostname']}")
        print(f"\nCPU: {result['cpu']['percent']}% ({result['cpu']['status']})")
        print(f"内存: {result['memory']['percent']}% ({result['memory']['status']})")
        print(f"磁盘: {result['disk']['percent']}% ({result['disk']['status']})")
        print(f"\n告警数: {result['alert_count']}")
        
        if result['alerts']:
            print("\n告警详情:")
            for alert in result['alerts']:
                print(f"  [{alert['level']}] {alert['message']}")

if __name__ == "__main__":
    main()
