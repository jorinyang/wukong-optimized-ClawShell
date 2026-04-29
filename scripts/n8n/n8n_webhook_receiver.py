#!/usr/bin/env python3
"""
N8N Webhook Receiver - N1验证脚本
功能：接收N8N的HTTP请求，执行简单操作并返回结果
验证N8N调用OpenClaw接口的可行性
"""

import json
import sys
from datetime import datetime

def handle_request(data):
    """处理N8N请求"""
    action = data.get("action", "ping")
    
    if action == "ping":
        return {
            "status": "success",
            "message": "pong",
            "timestamp": datetime.now().isoformat(),
            "from": "OpenClaw-N8N-Integration"
        }
    
    elif action == "add_task":
        # 模拟添加任务到队列
        task = data.get("task", {})
        return {
            "status": "success",
            "message": "Task added",
            "task_id": f"n8n-task-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "task": task
        }
    
    elif action == "check_status":
        # 检查系统状态
        return {
            "status": "success",
            "openclaw": "online",
            "n8n": "online",
            "timestamp": datetime.now().isoformat()
        }
    
    elif action == "dispatch_task":
        # 模拟任务分发
        task_type = data.get("task_type", "unknown")
        task_desc = data.get("description", "")
        
        # 简单路由逻辑
        routing = {
            "analyze": "lab",
            "develop": "dev", 
            "write": "doc",
            "publish": "pub",
            "archive": "lib",
            "analyze_data": "dat"
        }
        
        target_agent = routing.get(task_type, "lab")
        
        return {
            "status": "success",
            "dispatched_to": target_agent,
            "task_type": task_type,
            "task_desc": task_desc,
            "timestamp": datetime.now().isoformat()
        }
    
    else:
        return {
            "status": "error",
            "message": f"Unknown action: {action}"
        }

def main():
    """主函数"""
    # 读取输入（从stdin或文件）
    try:
        input_data = sys.stdin.read()
        if input_data.strip():
            data = json.loads(input_data)
        else:
            data = {}
    except:
        data = {}
    
    # 处理请求
    result = handle_request(data)
    
    # 输出JSON结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
