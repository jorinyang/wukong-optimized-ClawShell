#!/usr/bin/env python3
# hermes_bridge/subscriber.py
"""
EventBus订阅者

订阅OpenClaw EventBus事件
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Callable, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class EventBusSubscriber:
    """
    EventBus订阅者
    
    职责：
    1. 监听EventBus目录变化
    2. 读取新事件文件
    3. 调用回调处理事件
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.eventbus_path = Path(self.config.get('path', '~/.openclaw/workspace/shared/eventbus')).expanduser()
        self.patterns = self.config.get('patterns', ['*.json'])
        self.callbacks: List[Callable] = []
        self.observer: Optional[Observer] = None
        self.processed_events: set = set()  # 避免重复处理
        self.running = False
    
    def _default_config(self) -> Dict:
        return {
            'path': '~/.openclaw/workspace/shared/eventbus',
            'patterns': ['clawshell.*.json', '*.json'],
            'poll_interval': 1.0,  # 秒
            'batch_size': 10
        }
    
    def subscribe(self, patterns: List[str], callback: Callable):
        """
        订阅事件
        
        参数:
            patterns: 事件类型模式列表，如 ['clawshell.task.*', 'clawshell.error.*']
            callback: 回调函数，接收ClawshellEvent参数
        """
        self.patterns = patterns
        self.callbacks.append(callback)
    
    def unsubscribe_all(self):
        """取消所有订阅"""
        self.callbacks = []
        if self.observer:
            self.observer.stop()
            self.observer = None
    
    def start(self):
        """启动订阅"""
        self.running = True
        self._ensure_directory()
        
        # 使用polling方式监听
        self._start_polling()
    
    def stop(self):
        """停止订阅"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer = None
    
    def _ensure_directory(self):
        """确保目录存在"""
        self.eventbus_path.mkdir(parents=True, exist_ok=True)
    
    def _start_polling(self):
        """轮询方式监听"""
        while self.running:
            try:
                self._check_for_events()
                time.sleep(self.config.get('poll_interval', 1.0))
            except Exception as e:
                print(f"[ERROR] Polling error: {e}")
                time.sleep(5)  # 出错时等待更长时间
    
    def _check_for_events(self):
        """检查新事件"""
        if not self.eventbus_path.exists():
            return
        
        for event_file in self.eventbus_path.glob('*.json'):
            if event_file.name in self.processed_events:
                continue
            
            if self._matches_pattern(event_file.name):
                self._process_event_file(event_file)
    
    def _matches_pattern(self, filename: str) -> bool:
        """检查文件名是否匹配模式"""
        import fnmatch
        
        for pattern in self.patterns:
            # 转换glob模式到fnmatch模式
            fnmatch_pattern = pattern.replace('*', '*').replace('?', '?')
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(filename, fnmatch_pattern):
                return True
        return False
    
    def _process_event_file(self, event_file: Path):
        """处理事件文件"""
        try:
            # 读取事件
            with open(event_file) as f:
                event_data = json.load(f)
            
            # 创建事件对象
            from .events import ClawshellEvent
            event = ClawshellEvent(**event_data)
            
            # 调用回调
            for callback in self.callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[ERROR] Callback error: {e}")
            
            # 标记已处理
            self.processed_events.add(event_file.name)
            
            # 可选：删除或归档已处理的事件
            self._archive_event(event_file)
            
        except Exception as e:
            print(f"[ERROR] Process event error: {e}")
    
    def _archive_event(self, event_file: Path):
        """归档事件文件"""
        archive_dir = self.eventbus_path / 'archive'
        archive_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_name = f"{timestamp}_{event_file.name}"
        event_file.rename(archive_dir / archived_name)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'processed_count': len(self.processed_events),
            'callbacks_count': len(self.callbacks),
            'running': self.running,
            'eventbus_path': str(self.eventbus_path)
        }


class EventBusFileHandler(FileSystemEventHandler):
    """文件变化处理器"""
    
    def __init__(self, subscriber: EventBusSubscriber):
        self.subscriber = subscriber
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if isinstance(event, FileModifiedEvent):
            self.subscriber._process_event_file(Path(event.src_path))


if __name__ == "__main__":
    # 测试代码
    print("=== EventBusSubscriber 测试 ===\n")
    
    subscriber = EventBusSubscriber({
        'path': '/tmp/test_eventbus',
        'poll_interval': 0.5
    })
    
    received_events = []
    
    def test_callback(event):
        received_events.append(event)
        print(f"[RECEIVED] Event: {event.event_type}")
    
    subscriber.subscribe(['clawshell.*'], test_callback)
    
    print(f"订阅者配置: {subscriber.get_stats()}")
    print("\n创建一个测试事件...")
    
    # 创建测试事件
    test_path = Path('/tmp/test_eventbus')
    test_path.mkdir(exist_ok=True)
    
    from .events import ClawshellEvent
    
    test_event = ClawshellEvent(
        event_id="test-001",
        event_type="clawshell.task.execute.P1",
        source="test",
        timestamp=datetime.now().isoformat(),
        payload={"task": "test_task"}
    )
    
    with open(test_path / 'test_event.json', 'w') as f:
        json.dump(test_event.__dict__, f)
    
    print(f"\n已创建测试事件文件")
    print(f"测试事件: {test_event.event_type}")
