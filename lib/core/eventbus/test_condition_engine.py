#!/usr/bin/env python3
"""
ClawShell 条件触发引擎 测试
测试阈值、变化、组合、逆向条件触发
"""

import unittest
import time
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eventbus.condition_engine import (
    ConditionEngine,
    ConditionTrigger,
    Condition,
    ConditionType,
    create_threshold_trigger,
    create_change_trigger,
    create_composite_trigger,
    TriggerActions,
    ACTION_REGISTRY
)


class TestConditionEngine(unittest.TestCase):
    """条件触发引擎测试"""

    def setUp(self):
        """设置测试环境"""
        self.engine = ConditionEngine()

    def tearDown(self):
        """清理"""
        self.engine.stop()

    def test_threshold_greater_than(self):
        """测试阈值触发 - 大于"""
        trigger = create_threshold_trigger(
            trigger_id="test_gt",
            name="测试大于",
            metric="test_value",
            comparison=">",
            threshold=100,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 小于阈值 - 不触发
        self.engine.update_metric("test_value", 50)
        self.assertEqual(trigger.triggered_count, 0)

        # 等于阈值 - 不触发
        self.engine.update_metric("test_value", 100)
        self.assertEqual(trigger.triggered_count, 0)

        # 大于阈值 - 触发
        self.engine.update_metric("test_value", 150)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Threshold GT test passed")

    def test_threshold_less_than(self):
        """测试阈值触发 - 小于"""
        trigger = create_threshold_trigger(
            trigger_id="test_lt",
            name="测试小于",
            metric="balance",
            comparison="<",
            threshold=100,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 大于阈值 - 不触发
        self.engine.update_metric("balance", 150)
        self.assertEqual(trigger.triggered_count, 0)

        # 小于阈值 - 触发
        self.engine.update_metric("balance", 50)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Threshold LT test passed")

    def test_cooldown(self):
        """测试冷却时间"""
        trigger = create_threshold_trigger(
            trigger_id="test_cooldown",
            name="测试冷却",
            metric="cpu",
            comparison=">",
            threshold=80,
            action="log_event",
            cooldown=60  # 60秒冷却
        )
        self.engine.add_trigger(trigger)

        # 第一次触发
        self.engine.update_metric("cpu", 90)
        self.assertEqual(trigger.triggered_count, 1)

        # 立即再次更新 - 冷却中，不触发
        self.engine.update_metric("cpu", 95)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Cooldown test passed")

    def test_change_trigger(self):
        """测试变化触发"""
        trigger = create_change_trigger(
            trigger_id="test_change",
            name="测试变化",
            metric="temperature",
            comparison=">",
            threshold=10,  # 变化超过10度触发
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 设置初始值
        self.engine.update_metric("temperature", 25)
        self.assertEqual(trigger.triggered_count, 0)

        # 变化5度 - 不触发
        self.engine.update_metric("temperature", 30)
        self.assertEqual(trigger.triggered_count, 0)

        # 变化15度 - 触发
        self.engine.update_metric("temperature", 45)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Change trigger test passed")

    def test_negation_trigger(self):
        """测试逆向条件（从坏变好）"""
        trigger = ConditionTrigger(
            id="test_negation",
            name="测试逆向",
            condition=Condition(
                type=ConditionType.NEGATION.value,
                target_metric="api_health",
                comparison=">",
                threshold=0.5
            ),
            action_type="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 设置初始为坏 (0.8 > 0.5)
        self.engine.update_metric("api_health", 0.8)
        self.assertEqual(trigger.triggered_count, 0)

        # 仍然坏 - 不触发
        self.engine.update_metric("api_health", 0.7)
        self.assertEqual(trigger.triggered_count, 0)

        # 变好 (0.3 <= 0.5) - 触发
        self.engine.update_metric("api_health", 0.3)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Negation trigger test passed")

    def test_composite_trigger(self):
        """测试组合条件"""
        trigger = create_composite_trigger(
            trigger_id="test_composite",
            name="测试组合",
            expression="cpu > 70 AND memory > 80",
            target_metrics=["cpu", "memory"],
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 都不满足 - 使用批量更新确保同时满足
        self.engine.update_metrics_batch({"cpu": 50, "memory": 60})
        self.assertEqual(trigger.triggered_count, 0)

        # 只满足一个
        self.engine.update_metrics_batch({"cpu": 80, "memory": 60})
        self.assertEqual(trigger.triggered_count, 0)

        # 都满足
        self.engine.update_metrics_batch({"cpu": 80, "memory": 90})
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Composite trigger test passed")

    def test_enable_disable(self):
        """测试启用/禁用"""
        trigger = create_threshold_trigger(
            trigger_id="test_toggle",
            name="测试开关",
            metric="value",
            comparison=">",
            threshold=50,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        # 禁用
        self.engine.disable_trigger("test_toggle")
        self.engine.update_metric("value", 100)
        self.assertEqual(trigger.triggered_count, 0)

        # 启用
        self.engine.enable_trigger("test_toggle")
        self.engine.update_metric("value", 100)
        self.assertEqual(trigger.triggered_count, 1)

        print("✅ Enable/Disable test passed")

    def test_batch_update(self):
        """测试批量更新"""
        trigger1 = create_threshold_trigger(
            trigger_id="test_batch_1",
            name="测试批量1",
            metric="cpu",
            comparison=">",
            threshold=80,
            action="log_event",
            cooldown=0
        )
        trigger2 = create_threshold_trigger(
            trigger_id="test_batch_2",
            name="测试批量2",
            metric="memory",
            comparison=">",
            threshold=90,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger1)
        self.engine.add_trigger(trigger2)

        # 批量更新
        self.engine.update_metrics_batch({
            "cpu": 85,
            "memory": 95
        })

        self.assertEqual(trigger1.triggered_count, 1)
        self.assertEqual(trigger2.triggered_count, 1)

        print("✅ Batch update test passed")

    def test_builtin_triggers_loaded(self):
        """测试内置触发器已加载"""
        self.assertGreater(len(self.engine.triggers), 0)

        # 检查内置触发器
        trigger_ids = [t.id for t in self.engine.triggers.values()]
        self.assertIn("balance_low", trigger_ids)
        self.assertIn("cpu_high", trigger_ids)
        self.assertIn("memory_high", trigger_ids)

        print(f"✅ Builtin triggers loaded: {len(self.engine.triggers)}")

    def test_stats(self):
        """测试统计信息"""
        trigger = create_threshold_trigger(
            trigger_id="test_stats",
            name="测试统计",
            metric="value",
            comparison=">",
            threshold=50,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)

        self.engine.update_metric("value", 100)
        self.engine.update_metric("value", 200)

        stats = self.engine.get_stats()
        self.assertEqual(stats["total_executions"], 2)
        self.assertGreater(stats["active_triggers"], 0)

        print(f"✅ Stats: {stats['total_executions']} executions")

    def test_remove_trigger(self):
        """测试移除触发器"""
        trigger = create_threshold_trigger(
            trigger_id="test_remove",
            name="测试移除",
            metric="value",
            comparison=">",
            threshold=50,
            action="log_event",
            cooldown=0
        )
        self.engine.add_trigger(trigger)
        self.assertIn("test_remove", self.engine.triggers)

        self.engine.remove_trigger("test_remove")
        self.assertNotIn("test_remove", self.engine.triggers)

        print("✅ Remove trigger test passed")


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ClawShell 条件触发引擎 - 测试套件")
    print("=" * 60 + "\n")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestConditionEngine)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
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
