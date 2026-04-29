#!/usr/bin/env python3
"""
Adaptor 测试脚本 - ClawShell v0.1
=================================

测试自适应机制的核心功能。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adaptor import StateCollector, StrategyAnalyzer, AutoResponder


def test_state_collector():
    """测试状态采集器"""
    print("\n=== 测试状态采集器 ===")
    
    collector = StateCollector()
    
    # 采集系统状态
    system_metrics = collector.collect_system_status()
    print(f"系统指标: {system_metrics}")
    assert "system.cpu_percent" in system_metrics
    assert "system.memory_percent" in system_metrics
    
    # 记录API调用
    collector.record_api_call("test_api", success=True)
    collector.record_api_call("test_api", success=False)
    
    api_metrics = collector.collect_api_status()
    print(f"API指标: {api_metrics}")
    assert "api.test_api.error_rate" in api_metrics
    
    print("✅ 状态采集器测试通过")


def test_strategy_analyzer():
    """测试策略分析器"""
    print("\n=== 测试策略分析器 ===")
    
    analyzer = StrategyAnalyzer()
    
    # 正常状态
    normal_metrics = {
        "system.cpu_percent": 30.0,
        "system.memory_percent": 50.0,
        "api.error_rate": 0.05,
        "business.task_completion_rate": 0.95,
    }
    
    result = analyzer.analyze(normal_metrics)
    print(f"正常状态分析: should_switch={result.should_switch}")
    assert not result.should_switch
    
    # 高API错误率
    high_error_metrics = {
        "system.cpu_percent": 30.0,
        "system.memory_percent": 50.0,
        "api.error_rate": 0.6,
        "business.task_completion_rate": 0.95,
    }
    
    result = analyzer.analyze(high_error_metrics)
    print(f"高错误率分析: should_switch={result.should_switch}, target={result.target_strategy}")
    assert result.should_switch
    assert result.target_strategy == "emergency"
    
    # 高系统资源
    high_resource_metrics = {
        "system.cpu_percent": 90.0,
        "system.memory_percent": 95.0,
        "api.error_rate": 0.05,
        "business.task_completion_rate": 0.95,
    }
    
    result = analyzer.analyze(high_resource_metrics)
    print(f"高资源分析: should_switch={result.should_switch}, target={result.target_strategy}")
    assert result.should_switch
    assert result.target_strategy == "economy"
    
    print("✅ 策略分析器测试通过")


def test_auto_responder():
    """测试自动响应器"""
    print("\n=== 测试自动响应器 ===")
    
    responder = AutoResponder()
    
    # 创建模拟的分析结果
    class MockAnalysisResult:
        def __init__(self, should_switch, target_strategy, reason, issues, confidence):
            self.should_switch = should_switch
            self.target_strategy = target_strategy
            self.reason = reason
            self.issues = issues
            self.confidence = confidence
    
    # 测试策略切换响应
    mock_result = MockAnalysisResult(
        should_switch=True,
        target_strategy="emergency",
        reason="high_error_rate",
        issues=["API error rate high"],
        confidence=0.9,
    )
    
    actions = responder.respond(mock_result)
    print(f"执行动作数: {len(actions)}")
    
    # 测试禁用状态
    responder.disable()
    assert not responder.is_enabled()
    
    responder.enable()
    assert responder.is_enabled()
    
    print("✅ 自动响应器测试通过")


def test_integration():
    """集成测试"""
    print("\n=== 集成测试 ===")
    
    collector = StateCollector()
    analyzer = StrategyAnalyzer()
    responder = AutoResponder()
    
    # 采集状态
    metrics = collector.collect_all()
    print(f"采集指标数: {len(metrics)}")
    
    # 分析状态
    result = analyzer.analyze(metrics)
    print(f"分析结果: should_switch={result.should_switch}")
    
    # 执行响应
    if result.should_switch:
        actions = responder.respond(result)
        print(f"执行动作数: {len(actions)}")
    
    # 获取动作历史
    history = responder.get_action_history()
    print(f"动作历史: {len(history)} 条")
    
    print("✅ 集成测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Adaptor v0.1 测试套件")
    print("=" * 60)
    
    tests = [
        test_state_collector,
        test_strategy_analyzer,
        test_auto_responder,
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
