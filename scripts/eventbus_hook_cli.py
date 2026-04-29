#!/usr/bin/env python3
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
