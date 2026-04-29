#!/usr/bin/env python3
"""
Organizer 测试脚本 - ClawShell v0.1
=====================================

测试自组织机制的核心功能。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from organizer import TaskRegistry, TaskMarket, NodeCoordinator, TaskStatus, TaskPriority
from organizer.registry import Task
from organizer.market import NodeCapability
from organizer.coordinator import NodeInfo


def test_task_registry():
    """测试任务注册器"""
    print("\n=== 测试任务注册器 ===")
    
    registry = TaskRegistry()
    
    # 注册任务
    task1 = registry.register(
        name="测试任务1",
        description="这是一个测试任务",
        category="analysis",
        tags=["test", "demo"],
        priority=TaskPriority.NORMAL,
    )
    print(f"✅ 注册任务: {task1.id}")
    
    # 查询任务
    tasks = registry.list_tasks()
    print(f"✅ 查询任务: {len(tasks)}个")
    
    # 更新状态
    registry.update_status(task1.id, TaskStatus.RUNNING)
    print(f"✅ 更新状态: RUNNING")
    
    registry.update_status(task1.id, TaskStatus.COMPLETED, result={"status": "ok"})
    print(f"✅ 完成任务")
    
    # 统计
    stats = registry.get_stats()
    print(f"✅ 统计: {stats}")
    
    print("✅ 任务注册器测试通过")


def test_task_market():
    """测试任务市场"""
    print("\n=== 测试任务市场 ===")
    
    market = TaskMarket()
    
    # 注册节点
    node1 = NodeCapability(
        node_id="agent-1",
        name="分析Agent",
        capabilities=["analysis", "research"],
        categories=["analysis"],
        max_concurrent=2,
    )
    market.register_node(node1)
    print(f"✅ 注册节点: {node1.node_id}")
    
    # 发布任务
    task = market.publish_task(
        name="分析报告",
        description="生成月度分析报告",
        category="analysis",
        required_capabilities=["analysis"],
    )
    print(f"✅ 发布任务: {task.id}")
    
    # 匹配任务
    matched_node = market.match_task(task.id)
    print(f"✅ 匹配节点: {matched_node}")
    
    # 完成任务
    market.complete_task(task.id, result={"status": "ok"})
    print(f"✅ 完成任务")
    
    # 市场统计
    stats = market.get_market_stats()
    print(f"✅ 市场统计: {stats}")
    
    print("✅ 任务市场测试通过")


def test_node_coordinator():
    """测试节点协调器"""
    print("\n=== 测试节点协调器 ===")
    
    coordinator = NodeCoordinator()
    
    # 注册节点
    node1 = NodeInfo(
        node_id="skill-1",
        node_type="skill",
        name="分析技能",
        capabilities=["analysis", "research"],
    )
    coordinator.register_node(node1)
    print(f"✅ 注册节点: {node1.node_id}")
    
    # 心跳
    coordinator.heartbeat("skill-1")
    print(f"✅ 心跳")
    
    # 分发任务
    result = coordinator.dispatch_task(
        task={"id": "task-001", "name": "分析任务"},
        required_capabilities=["analysis"]
    )
    print(f"✅ 分发任务: {result}")
    
    # 节点列表
    nodes = coordinator.list_nodes()
    print(f"✅ 节点列表: {len(nodes)}个")
    
    # 统计
    stats = coordinator.get_coordinator_stats()
    print(f"✅ 协调器统计: {stats}")
    
    print("✅ 节点协调器测试通过")


def test_integration():
    """集成测试"""
    print("\n=== 集成测试 ===")
    
    # 创建组件
    registry = TaskRegistry()
    market = TaskMarket(registry)
    coordinator = NodeCoordinator()
    
    # 注册多个节点
    nodes = [
        NodeCapability("agent-1", "Agent1", ["analysis"], ["analysis"], max_concurrent=2),
        NodeCapability("agent-2", "Agent2", ["coding"], ["coding"], max_concurrent=2),
        NodeCapability("agent-3", "Agent3", ["writing"], ["writing"], max_concurrent=2),
    ]
    for node in nodes:
        market.register_node(node)
        coordinator.register_node(NodeInfo(
            node_id=node.node_id,
            node_type="agent",
            name=node.name,
            capabilities=node.capabilities,
        ))
    
    print(f"✅ 注册了 {len(nodes)} 个节点")
    
    # 发布多个任务
    tasks_data = [
        ("分析报告", "analysis", ["analysis"]),
        ("编写代码", "coding", ["coding"]),
        ("撰写文档", "writing", ["writing"]),
    ]
    
    for name, category, caps in tasks_data:
        task = market.publish_task(
            name=name,
            category=category,
            required_capabilities=caps,
        )
        matched = market.match_task(task.id)
        print(f"  任务'{name}' -> {matched}")
    
    # 验证
    pending = market.get_pending_tasks()
    running = market.get_running_tasks()
    print(f"✅ 待处理: {len(pending)}, 运行中: {len(running)}")
    
    # 统计
    market_stats = market.get_market_stats()
    coord_stats = coordinator.get_coordinator_stats()
    print(f"✅ 市场统计: {market_stats['total_nodes']}节点")
    print(f"✅ 协调器统计: {coord_stats['total_nodes']}节点")
    
    print("✅ 集成测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Organizer v0.1 测试套件")
    print("=" * 60)
    
    tests = [
        test_task_registry,
        test_task_market,
        test_node_coordinator,
        test_integration,
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
