#!/usr/bin/env python3
"""
EventBus - 事件传播机制
职责：
1. 监控事件目录
2. 读取新事件并分类
3. 触发对应的响应处理器
4. 记录事件处理结果
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
EVENTS_DIR = os.path.join(SHARED_DIR, "events")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "event_bus.log")
INBOX_DIR = os.path.join(SHARED_DIR, "inbox")

# 事件类型与处理器映射
EVENT_HANDLERS: Dict[str, List[Callable]] = {
    "error.occurred": [],  # 错误事件
    "task.completed": [],  # 任务完成事件
    "task.failed": [],     # 任务失败事件
    "agent.heartbeat": [], # Agent心跳事件
    "system.alert": [],    # 系统告警事件
}

class EventBus:
    def __init__(self):
        self.events_dir = EVENTS_DIR
        self.log_file = LOG_FILE
        self.processed_file = os.path.join(SHARED_DIR, "logs", "processed_events.json")
        self.processed_events = self._load_processed_events()
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    def _load_processed_events(self) -> set:
        """加载已处理事件ID"""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get("processed", []))
        except:
            pass
        return set()
    
    def _save_processed_events(self):
        """保存已处理事件ID"""
        os.makedirs(os.path.dirname(self.processed_file), exist_ok=True)
        with open(self.processed_file, 'w') as f:
            json.dump({"processed": list(self.processed_events)}, f)
    
    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in EVENT_HANDLERS:
            EVENT_HANDLERS[event_type] = []
        EVENT_HANDLERS[event_type].append(handler)
        self.log(f"✅ 注册处理器: {event_type} -> {handler.__name__}")
    
    def scan_events(self) -> List[Dict]:
        """扫描事件目录，返回新事件"""
        new_events = []
        if not os.path.exists(self.events_dir):
            return new_events
        
        for filename in os.listdir(self.events_dir):
            if not filename.endswith('.json'):
                continue
            
            event_id = filename.replace('.json', '')
            if event_id in self.processed_events:
                continue
            
            filepath = os.path.join(self.events_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    event = json.load(f)
                    event['_filename'] = filename
                    event['_id'] = event_id
                    new_events.append(event)
            except Exception as e:
                self.log(f"⚠️ 读取事件失败 {filename}: {e}")
        
        return new_events
    
    def process_event(self, event: Dict):
        """处理单个事件"""
        event_id = event.get('_id', 'unknown')
        event_type = event.get('type', 'unknown')
        
        self.log(f"📨 处理事件: {event_type} ({event_id})")
        
        # 调用对应的处理器
        handlers = EVENT_HANDLERS.get(event_type, [])
        if not handlers:
            self.log(f"  ⚠️ 无处理器: {event_type}")
            return
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.log(f"  ⚠️ 处理器异常 {handler.__name__}: {e}")
        
        # 标记为已处理
        self.processed_events.add(event_id)
        self._save_processed_events()
        self.log(f"✅ 事件已处理: {event_id}")
    
    def run_once(self):
        """执行一次事件扫描和处理"""
        events = self.scan_events()
        if events:
            self.log(f"📋 发现 {len(events)} 个新事件")
        for event in events:
            self.process_event(event)
        return len(events)
    
    def run(self, interval: int = 10):
        """持续运行事件监控"""
        self.log(f"🚀 EventBus 启动 (间隔: {interval}秒)")
        while True:
            try:
                count = self.run_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.log("🛑 EventBus 停止")
                break
            except Exception as e:
                self.log(f"⚠️ 异常: {e}")
                time.sleep(interval)


# 默认处理器
def handle_error(event):
    """错误事件处理器"""
    error_msg = event.get('message', event.get('error', 'unknown'))
    self_log = event.get('source', 'unknown')
    print(f"  🔴 错误: [{self_log}] {error_msg}")
    
    # 可以触发其他响应：通知、记录到ErrorCookbook等

def handle_task_completed(event):
    """任务完成事件处理器"""
    task_id = event.get('task_id', event.get('id', 'unknown'))
    print(f"  ✅ 任务完成: {task_id}")

def handle_task_failed(event):
    """任务失败事件处理器"""
    task_id = event.get('task_id', event.get('id', 'unknown'))
    error = event.get('error', 'unknown')
    print(f"  ❌ 任务失败: {task_id} - {error}")


if __name__ == "__main__":
    bus = EventBus()
    bus.register_handler("error.occurred", handle_error)
    bus.register_handler("task.completed", handle_task_completed)
    bus.register_handler("task.failed", handle_task_failed)
    bus.run(interval=10)
