#!/usr/bin/env python3
"""
Strategy Library 测试脚本 - ClawShell v0.1
==========================================

测试策略库的核心功能。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies import (
    Strategy,
    StrategyType,
    SwitchCondition,
    StrategySwitcher,
    StrategyRegistry,
)


def test_strategy_creation():
    """测试策略创建"""
    print("\n=== 测试策略创建 ===")
    
    strategy = Strategy(
        name="test",
        type=StrategyType.DEFAULT,
        description="测试策略",
    )
    
    assert strategy.name == "test"
    assert strategy.type == StrategyType.DEFAULT
    assert strategy.enabled == True
    
    print(f"✅ 策略创建成功")
    print(f"   名称: {strategy.name}")
    print(f"   类型: {strategy.type.value}")


def test_strategy_serialization():
    """测试策略序列化"""
    print("\n=== 测试策略序列化 ===")
    
    strategy = Strategy(
        name="test",
        type=StrategyType.DEFAULT,
    )
    
    # 转换为YAML
    yaml_str = strategy.to_yaml()
    assert "test" in yaml_str
    
    # 从YAML恢复
    strategy2 = Strategy.from_yaml(yaml_str)
    assert strategy2.name == "test"
    
    print(f"✅ 策略序列化成功")
    print(f"   YAML长度: {len(yaml_str)} 字符")


def test_switch_condition():
    """测试切换条件"""
    print("\n=== 测试切换条件 ===")
    
    condition = SwitchCondition(
        name="high_error_rate",
        condition="api_error_rate > 0.3",
        target_strategy="emergency",
        priority=10,
    )
    
    # 测试评估
    metrics1 = {"api_error_rate": 0.5}
    assert condition.evaluate(metrics1) == True
    
    metrics2 = {"api_error_rate": 0.1}
    assert condition.evaluate(metrics2) == False
    
    print(f"✅ 切换条件评估成功")
    print(f"   0.5 > 0.3: {condition.evaluate(metrics1)}")
    print(f"   0.1 > 0.3: {condition.evaluate(metrics2)}")


def test_strategy_switcher():
    """测试策略切换器"""
    print("\n=== 测试策略切换器 ===")
    
    switcher = StrategySwitcher()
    
    # 获取当前策略
    current = switcher.get_current_strategy()
    print(f"   当前策略: {current.name}")
    
    # 手动切换
    success = switcher.switch_to("emergency", reason="测试切换")
    assert success
    
    current = switcher.get_current_strategy()
    assert current.name == "emergency"
    
    # 切换回default
    switcher.switch_to("default")
    
    print(f"✅ 策略切换成功")


def test_evaluate_and_switch():
    """测试条件评估切换"""
    print("\n=== 测试条件评估切换 ===")
    
    switcher = StrategySwitcher()
    
    # 添加条件
    condition = SwitchCondition(
        name="test_condition",
        condition="error_rate > 0.5",
        target_strategy="emergency",
        priority=10,
    )
    switcher.add_condition(condition)
    
    # 评估（不满足条件）
    result = switcher.evaluate_and_switch({"error_rate": 0.1})
    assert result is None
    print(f"   错误率0.1: 保持{switcher.get_current_strategy().name}")
    
    # 评估（满足条件）
    result = switcher.evaluate_and_switch({"error_rate": 0.6})
    assert result == "emergency"
    print(f"   错误率0.6: 切换到{result}")
    
    # 恢复
    switcher.switch_to("default")
    
    print(f"✅ 条件评估切换成功")


def test_switch_callback():
    """测试切换回调"""
    print("\n=== 测试切换回调 ===")
    
    switcher = StrategySwitcher()
    
    callback_executed = []
    
    def callback(from_strategy, to_strategy):
        callback_executed.append((from_strategy, to_strategy))
    
    switcher.on_switch(callback)
    switcher.switch_to("emergency")
    
    assert len(callback_executed) == 1
    assert callback_executed[0] == ("default", "emergency")
    
    # 恢复
    switcher.switch_to("default")
    
    print(f"✅ 切换回调成功执行")


def test_strategy_registry():
    """测试策略注册器"""
    print("\n=== 测试策略注册器 ===")
    
    registry = StrategyRegistry()
    
    # 列出所有策略
    strategies = registry.list_strategies()
    print(f"   已注册策略数: {len(strategies)}")
    
    for s in strategies:
        print(f"     - {s.name} ({s.type.value})")
    
    # 获取指定策略
    default = registry.get("default")
    assert default is not None
    print(f"✅ 策略注册器正常")
    
    # 测试禁用/启用
    registry.disable("economy")
    economy = registry.get("economy")
    assert economy.enabled == False
    
    registry.enable("economy")
    economy = registry.get("economy")
    assert economy.enabled == True
    
    print(f"✅ 策略启用/禁用成功")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Strategy Library v0.1 测试套件")
    print("=" * 60)
    
    tests = [
        test_strategy_creation,
        test_strategy_serialization,
        test_switch_condition,
        test_strategy_switcher,
        test_evaluate_and_switch,
        test_switch_callback,
        test_strategy_registry,
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
