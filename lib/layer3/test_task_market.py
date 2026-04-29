#!/usr/bin/env python3
"""
ClawShell TaskMarket 测试
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from organizer.task_market import (
    TaskMarket,
    TaskMatcher,
    Task,
    TaskStatus,
    TaskPriority,
    create_task
)
from swarm.node_registry import NodeRegistry, NodeType, NodeStatus


class TestTaskMatcher(unittest.TestCase):
    """任务匹配器测试"""

    def setUp(self):
        """设置测试环境"""
        self.node_registry = NodeRegistry()
        self.matcher = TaskMatcher(self.node_registry)

        # 添加测试节点
        self.node1_id = self.node_registry.register(
            name="执行节点1",
            node_type=NodeType.OPENCLAW,
            endpoint="http://localhost:8001",
            capabilities=["python", "shell"]
        )
        self.node2_id = self.node_registry.register(
            name="执行节点2",
            node_type=NodeType.N8N,
            endpoint="http://localhost:5678",
            capabilities=["workflow", "automation"]
        )
        self.node3_id = self.node_registry.register(
            name="执行节点3",
            node_type=NodeType.HERMES,
            endpoint="http://localhost:30000",
            capabilities=["analysis", "python"]
        )

    def test_match_with_capabilities(self):
        """测试基于能力的匹配"""
        task = create_task(
            name="Python任务",
            required_capabilities=["python"]
        )
        node = self.matcher.match(task)
        self.assertIsNotNone(node)
        self.assertIn("python", node.capabilities)
        print(f"✅ Matched: {node.name}")

    def test_match_top_k(self):
        """测试Top-K匹配"""
        task = create_task(required_capabilities=["python"])
        nodes = self.matcher.match_top_k(task, k=3)
        self.assertGreater(len(nodes), 0)
        print(f"✅ Top-3: {[n.name for n in nodes]}")

    def test_match_filters_offline(self):
        """测试过滤离线节点"""
        self.node_registry.update_status(self.node1_id, NodeStatus.OFFLINE)
        task = create_task(required_capabilities=["python"])
        matched = self.matcher.match(task)
        self.assertIsNotNone(matched)
        self.assertNotEqual(matched.id, self.node1_id)
        print(f"✅ Filtered offline: {matched.name}")


class TestTaskMarket(unittest.TestCase):
    """任务市场测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.node_registry = NodeRegistry()
        self.market = TaskMarket(
            self.node_registry,
            persistence_path=self.temp_dir
        )

        # 添加测试节点
        self.executor1_id = self.node_registry.register(
            name="执行器1",
            node_type=NodeType.OPENCLAW,
            capabilities=["python", "shell"]
        )
        self.executor2_id = self.node_registry.register(
            name="执行器2",
            node_type=NodeType.OPENCLAW,
            capabilities=["python", "analysis"]
        )

    def test_publish_task(self):
        """测试发布任务"""
        task = create_task(name="测试任务")
        task_id = self.market.publish_task(task)
        self.assertIsNotNone(task_id)
        retrieved = self.market.get_task(task_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.status, TaskStatus.MATCHED.value)
        print(f"✅ Task published and matched: {task_id}")

    def test_complete_flow(self):
        """测试完成流程"""
        task = create_task(name="完成测试")
        task_id = self.market.publish_task(task)
        self.market.start_task(task_id)
        result = {"output": "success"}
        self.market.complete_task(task_id, result=result)
        retrieved = self.market.get_task(task_id)
        self.assertEqual(retrieved.status, TaskStatus.COMPLETED.value)
        self.assertEqual(retrieved.result, result)
        print("✅ Complete flow passed")

    def test_failed_flow(self):
        """测试失败流程"""
        task = create_task(name="失败测试")
        task_id = self.market.publish_task(task)
        self.market.complete_task(task_id, error="Test error")
        retrieved = self.market.get_task(task_id)
        self.assertEqual(retrieved.status, TaskStatus.FAILED.value)
        print("✅ Failed flow passed")

    def test_retry(self):
        """测试重试"""
        task = create_task(name="重试测试", max_retries=3)
        task_id = self.market.publish_task(task)
        self.market.complete_task(task_id, error="Temp error")
        success = self.market.retry_task(task_id)
        self.assertTrue(success)
        retrieved = self.market.get_task(task_id)
        self.assertEqual(retrieved.retry_count, 1)
        print("✅ Retry passed")

    def test_stats(self):
        """测试统计"""
        task = create_task(name="统计测试")
        self.market.publish_task(task)
        stats = self.market.get_stats()
        self.assertGreater(stats["total_tasks"], 0)
        print(f"✅ Stats: {stats}")


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ClawShell TaskMarket - 测试套件")
    print("=" * 60 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestTaskMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskMarket))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print("\n❌ 部分测试失败!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
