#!/usr/bin/env python3
"""
execution_bridge.py - OpenClaw到Hermes的桥接
功能：
1. 监听OpenClaw执行结果
2. 将关键信息发送到Hermes inbox
3. 触发Hermes深度分析
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
HERMES_INBOX = os.path.expanduser("~/.hermes/inbox/openclaw_feed")
BRIDGE_LOG = os.path.join(SHARED_DIR, "logs", "execution_bridge.log")

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    os.makedirs(os.path.dirname(BRIDGE_LOG), exist_ok=True)
    with open(BRIDGE_LOG, "a") as f:
        f.write(log_line + "\n")

def send_to_hermes(event_type: str, data: dict):
    """发送事件到Hermes inbox"""
    os.makedirs(HERMES_INBOX, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{event_type}_{timestamp}.json"
    filepath = os.path.join(HERMES_INBOX, filename)
    
    payload = {
        "source": "openclaw",
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        log(f"✅ 发送Hermes: {event_type} -> {filename}")
        return True
    except Exception as e:
        log(f"❌ 发送失败: {e}")
        return False

def bridge_task_completed(task_id: str, result: dict):
    """桥接任务完成事件"""
    send_to_hermes("task_completed", {
        "task_id": task_id,
        "result": result
    })

def bridge_task_failed(task_id: str, error: str):
    """桥接任务失败事件"""
    send_to_hermes("task_failed", {
        "task_id": task_id,
        "error": error
    })

def bridge_system_status():
    """桥接系统状态（定时）"""
    # 读取当前状态
    context_file = os.path.join(SHARED_DIR, "context_manager.json")
    try:
        with open(context_file, 'r') as f:
            context = json.load(f)
        send_to_hermes("system_status", context)
    except Exception as e:
        log(f"⚠️ 读取上下文失败: {e}")

def bridge_error_occurred(error_msg: str, source: str):
    """桥接错误事件"""
    send_to_hermes("error_occurred", {
        "error": error_msg,
        "source": source
    })

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: execution_bridge.py <event_type> [data_json]")
        print("  event_type: task_completed|task_failed|system_status|error_occurred")
        sys.exit(1)
    
    event_type = sys.argv[1]
    
    if len(sys.argv) > 2:
        data = json.loads(sys.argv[2])
    else:
        data = {}
    
    if event_type == "task_completed":
        bridge_task_completed(data.get("task_id", "unknown"), data.get("result", {}))
    elif event_type == "task_failed":
        bridge_task_failed(data.get("task_id", "unknown"), data.get("error", ""))
    elif event_type == "system_status":
        bridge_system_status()
    elif event_type == "error_occurred":
        bridge_error_occurred(data.get("error", ""), data.get("source", ""))
    else:
        log(f"❌ 未知事件类型: {event_type}")
        sys.exit(1)
