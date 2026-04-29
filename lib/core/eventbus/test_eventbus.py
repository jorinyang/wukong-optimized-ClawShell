#!/usr/bin/env python3
"""
EventBus 测试脚本 - ClawShell v0.1
===================================

测试事件总线的核心功能。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eventbus import EventBus, Event, EventType, Publisher, Subscriber
from datetime import datetime


def test_event_creation():
    """测试事件创建"""
    print("\n=== 测试事件创建 ===")
    
    event = Event(
        type=EventType.TASK_COMPLETED,
        source="test",
        payload={"task_id": "123", "result": "ok"},
    )
    
    assert event.id is not None
    assert event.type == EventType.TASK_COMPLETED
    assert event.source == "test"
    assert event.timestamp is not None
    
    print(f"✅ 事件创建成功: {event.id}")
    print(f"   类型: {event.type.value}")
    print(f"   来源: {event.source}")
    print(f"   时间: {event.timestamp}")


def test_event_to_dict():
    """测试事件序列化"""
    print("\n=== 测试事件序列化 ===")
    
    event = Event(
        type=EventType.ERROR_OCCURRED,
        source="test",
        payload={"error": "test error"},
        tags=["test", "error"],
    )
    
    data = event.to_dict()
    assert data["type"] == "error.occurred"
    assert data["source"] == "test"
    assert data["payload"]["error"] == "test error"
    assert "test" in data["tags"]
    
    print(f"✅ 事件序列化成功")
    print(f"   JSON: {data}")


def test_eventbus_subscribe_publish():
    """测试订阅和发布"""
    print("\n=== 测试订阅和发布 ===")
    
    bus = EventBus()
    
    received = []
    
    def handler(event):
        received.append(event)
        print(f"   收到事件: {event.type.value}")
    
    # 订阅
    bus.subscribe(EventType.TASK_COMPLETED, handler)
    print("✅ 订阅成功")
    
    # 发布
    event = Event(type=EventType.TASK_COMPLETED, source="test")
    bus.publish(event)
    print("✅ 发布成功")
    
    # 验证
    assert len(received) == 1
    assert received[0].id == event.id
    print(f"✅ 事件传递成功")


def test_publisher():
    """测试发布者"""
    print("\n=== 测试发布者 ===")
    
    pub = Publisher(source="test_publisher")
    
    # 发布任务完成事件
    event = pub.task_completed(
        task_id="test-123",
        result={"status": "ok", "duration": 1.5}
    )
    
    assert event.type == EventType.TASK_COMPLETED
    assert event.source == "test_publisher"
    assert event.payload["task_id"] == "test-123"
    
    print(f"✅ Publisher 任务完成事件发布成功")
    
    # 发布错误事件
    event2 = pub.error_occurred(
        error_type="APIError",
        message="timeout",
        severity="high"
    )
    
    assert event2.type == EventType.ERROR_OCCURRED
    assert event2.payload["error_type"] == "APIError"
    
    print(f"✅ Publisher 错误事件发布成功")


def test_subscriber_decorator():
    """测试订阅者装饰器"""
    print("\n=== 测试订阅者装饰器 ===")
    
    sub = Subscriber()
    received = []
    
    @sub.on(EventType.TASK_COMPLETED)
    def handle_task(event):
        received.append(event)
    
    @sub.on(EventType.ERROR_OCCURRED, tags=["critical"])
    def handle_critical(event):
        received.append(event)
    
    # 启动订阅
    sub.start()
    print("✅ 订阅启动成功")
    
    # 发布测试事件
    from eventbus.core import get_eventbus
    bus = get_eventbus()
    
    event1 = Event(type=EventType.TASK_COMPLETED, source="test")
    event2 = Event(type=EventType.ERROR_OCCURRED, source="test", tags=["critical"])
    event3 = Event(type=EventType.ERROR_OCCURRED, source="test", tags=["normal"])
    
    bus.publish(event1)
    bus.publish(event2)
    bus.publish(event3)
    
    # 验证
    assert len(received) == 2  # event1 和 event2，event3 被过滤
    print(f"✅ 装饰器订阅成功，收到 {len(received)} 个事件")


def test_event_history():
    """测试事件历史"""
    print("\n=== 测试事件历史 ===")
    
    bus = EventBus()
    
    # 发布多个事件
    for i in range(5):
        bus.publish(Event(type=EventType.TASK_COMPLETED, source="test"))
    
    # 获取历史
    history = bus.get_history(limit=10)
    assert len(history) == 5
    
    # 按类型过滤
    history = bus.get_history(event_type=EventType.TASK_COMPLETED)
    assert len(history) == 5
    
    # 按来源过滤
    history = bus.get_history(source="nonexistent")
    assert len(history) == 0
    
    print(f"✅ 事件历史功能正常，共 {len(history)} 条记录")


def test_event_stats():
    """测试事件统计"""
    print("\n=== 测试事件统计 ===")
    
    bus = EventBus()
    
    # 发布各类事件
    for _ in range(3):
        bus.publish(Event(type=EventType.TASK_COMPLETED, source="test"))
    for _ in range(2):
        bus.publish(Event(type=EventType.ERROR_OCCURRED, source="test"))
    
    stats = bus.get_stats()
    
    assert stats["total_events"] == 5
    assert "task.completed" in stats["event_types"]
    assert stats["event_types"]["task.completed"] == 3
    
    print(f"✅ 事件统计正常")
    print(f"   总事件数: {stats['total_events']}")
    print(f"   类型分布: {stats['event_types']}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("EventBus v0.1 测试套件")
    print("=" * 60)
    
    tests = [
        test_event_creation,
        test_event_to_dict,
        test_eventbus_subscribe_publish,
        test_publisher,
        test_subscriber_decorator,
        test_event_history,
        test_event_stats,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {test.__name__}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
