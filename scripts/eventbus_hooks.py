#!/usr/bin/env python3
"""
EventBus OpenClaw集成脚本 - ClawShell v0.1
==========================================

将EventBus集成到OpenClaw的消息流中。
当OpenClaw处理消息时，自动发布事件到EventBus。

功能：
- 消息接收事件
- 任务开始/完成事件
- 错误发生事件
- 策略切换事件
"""

import sys
import os
import logging
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from eventbus import EventBus, Event, EventType, Publisher, Subscriber
from eventbus.schema import EventType as EventTypeEnum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenClawEventBus:
    """
    OpenClaw EventBus集成类
    =========================
    
    提供与OpenClaw工作流程的事件集成。
    """
    
    def __init__(self):
        self.eventbus = EventBus()
        self.publisher = Publisher(source="openclaw")
        self.subscriber = Subscriber(self.eventbus)
        
        # 注册默认处理器
        self._register_handlers()
        
        logger.info("OpenClaw EventBus initialized")
    
    def _register_handlers(self):
        """注册默认事件处理器"""
        # 可以在这里添加默认的事件响应逻辑
        
        # 例如：错误事件自动记录到Genome
        @self.subscriber.on(EventTypeEnum.ERROR_OCCURRED)
        def handle_error(event):
            self._on_error(event)
    
    def _on_error(self, event):
        """错误事件处理"""
        logger.warning(f"Error event: {event.payload}")
    
    def publish_message_received(self, message_id: str, source: str, content: str):
        """发布消息接收事件"""
        self.publisher.publish(
            EventTypeEnum.CUSTOM,
            {
                "event_name": "message_received",
                "message_id": message_id,
                "source": source,
                "content_length": len(content),
            },
            tags=["message", "openclaw"],
        )
    
    def publish_task_started(self, task_id: str, task_type: str):
        """发布任务开始事件"""
        self.publisher.task_started(task_id=task_id, task_type=task_type)
    
    def publish_task_completed(self, task_id: str, task_type: str, result: dict = None):
        """发布任务完成事件"""
        self.publisher.task_completed(
            task_id=task_id,
            task_type=task_type,
            result=result or {}
        )
    
    def publish_task_failed(self, task_id: str, task_type: str, error: str):
        """发布任务失败事件"""
        self.publisher.task_failed(
            task_id=task_id,
            task_type=task_type,
            error=error
        )
    
    def publish_error(self, error_type: str, message: str, severity: str = "medium"):
        """发布错误事件"""
        self.publisher.error_occurred(
            error_type=error_type,
            message=message,
            severity=severity
        )
    
    def get_stats(self):
        """获取事件统计"""
        return self.eventbus.get_stats()


def create_standalone_script():
    """创建独立使用的钩子脚本"""
    return '''#!/usr/bin/env python3
"""
EventBus钩子 - 可被OpenClaw调用的独立脚本
==========================================

使用方法：
  python eventbus_hooks.py --action publish --type task_completed --task-id 123
  
Actions:
  publish     - 发布事件
  stats       - 获取统计
  history     - 获取历史
  
Types:
  task_scheduled
  task_started
  task_completed
  task_failed
  error_occurred
  insight_generated
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eventbus import EventBus, Event, EventType, Publisher
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="EventBus Hook")
    parser.add_argument("--action", required=True, choices=["publish", "stats", "history"])
    parser.add_argument("--type", help="Event type")
    parser.add_argument("--source", default="cli", help="Event source")
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--task-type", help="Task type")
    parser.add_argument("--error-type", help="Error type")
    parser.add_argument("--message", help="Error message")
    parser.add_argument("--limit", type=int, default=100, help="History limit")
    
    args = parser.parse_args()
    
    if args.action == "publish":
        pub = Publisher(source=args.source)
        
        if args.type == "task_completed":
            pub.task_completed(task_id=args.task_id or "unknown", task_type=args.task_type or "general")
        elif args.type == "task_failed":
            pub.task_failed(task_id=args.task_id or "unknown", task_type=args.task_type or "general", error=args.message or "unknown")
        elif args.type == "error_occurred":
            pub.error_occurred(error_type=args.error_type or "UnknownError", message=args.message or "unknown")
        else:
            print(f"Unknown event type: {args.type}")
            sys.exit(1)
        
        print(f"Published: {args.type}")
    
    elif args.action == "stats":
        bus = EventBus()
        stats = bus.get_stats()
        print(f"Total events: {stats['total_events']}")
        print(f"Subscribers: {stats['subscribers_count']}")
        print(f"Event types: {stats['event_types']}")
    
    elif args.action == "history":
        bus = EventBus()
        history = bus.get_history(limit=args.limit)
        print(f"Recent {len(history)} events:")
        for e in history[-10:]:
            print(f"  [{e.timestamp}] {e.type.value if e.type else 'unknown'}: {e.source}")

if __name__ == "__main__":
    main()
'''


if __name__ == "__main__":
    print("=" * 60)
    print("EventBus OpenClaw集成")
    print("=" * 60)
    
    # 创建集成实例
    integration = OpenClawEventBus()
    
    # 测试发布一些事件
    print("\n--- 测试事件发布 ---")
    
    integration.publish_task_started(task_id="test-001", task_type="test")
    print("✅ 发布任务开始事件")
    
    integration.publish_task_completed(task_id="test-001", task_type="test", result={"status": "ok"})
    print("✅ 发布任务完成事件")
    
    integration.publish_error(error_type="TestError", message="This is a test error", severity="low")
    print("✅ 发布错误事件")
    
    # 获取统计
    print("\n--- 事件统计 ---")
    stats = integration.get_stats()
    print(f"总事件数: {stats['total_events']}")
    print(f"事件类型: {stats['event_types']}")
    
    # 生成独立脚本
    script_path = Path(__file__).parent / "eventbus_hook_cli.py"
    with open(script_path, 'w') as f:
        f.write(create_standalone_script())
    script_path.chmod(0o755)
    print(f"\n✅ 已生成CLI钩子脚本: {script_path}")
    
    print("\n" + "=" * 60)
    print("集成完成")
    print("=" * 60)
