#!/usr/bin/env python3
"""
ClawShell Agent 能力验证脚本

新 Agent 运行此脚本验证是否成功继承系统能力。
"""

import sys
import os

# 添加路径
sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}')
sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/clawshell')

def verify_agent_capabilities():
    """验证 Agent 能力继承"""
    
    print("🧪 ClawShell Agent 能力验证")
    print("=" * 50)
    
    checks = []
    
    # 1. 核心模块导入
    print("\n1️⃣ 核心模块导入测试")
    try:
        from clawshell.core import ClawShell
        print("   ✅ ClawShell")
    except Exception as e:
        print(f"   ❌ ClawShell: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from eventbus import EventBus, Event, EventType
        print("   ✅ EventBus")
    except Exception as e:
        print(f"   ❌ EventBus: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from organizer import TaskRegistry, TaskMarket
        print("   ✅ Organizer")
    except Exception as e:
        print(f"   ❌ Organizer: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from genome import GenomeManager, AgentType
        print("   ✅ GenomeStore")
    except Exception as e:
        print(f"   ❌ GenomeStore: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from context_manager import ContextManager
        print("   ✅ ContextManager")
    except Exception as e:
        print(f"   ❌ ContextManager: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from error_handler import ErrorHandler, ErrorSeverity
        print("   ✅ ErrorHandler")
    except Exception as e:
        print(f"   ❌ ErrorHandler: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    try:
        from n8n_integration import N8NIntegration
        print("   ✅ N8N Integration")
    except Exception as e:
        print(f"   ❌ N8N Integration: {e}")
        checks.append(False)
    else:
        checks.append(True)
    
    # 2. 系统初始化
    print("\n2️⃣ 系统初始化测试")
    try:
        shell = ClawShell()
        result = shell.initialize()
        if result:
            print("   ✅ ClawShell 初始化成功")
            checks.append(True)
        else:
            print("   ❌ ClawShell 初始化失败")
            checks.append(False)
    except Exception as e:
        print(f"   ❌ 初始化错误: {e}")
        checks.append(False)
    
    # 3. 功能测试
    print("\n3️⃣ 功能测试")
    
    # EventBus 测试
    try:
        bus = EventBus.get_instance()
        from eventbus import Event
        event = Event(
            type=EventType.TASK_COMPLETED,
            source="test",
            payload={"test": True}
        )
        event_id = bus.publish(event)
        print(f"   ✅ EventBus 发布事件: {event_id[:8]}...")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ EventBus 测试失败: {e}")
        checks.append(False)
    
    # Organizer 测试
    try:
        registry = TaskRegistry()
        market = TaskMarket(registry)
        task = market.submit("verify_task", category="test")
        print(f"   ✅ Organizer 提交任务: {task.id[:8]}...")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ Organizer 测试失败: {e}")
        checks.append(False)
    
    # GenomeStore 测试
    try:
        manager = GenomeManager()
        genome = manager.load_genome(AgentType.OPENCLAW)
        print(f"   ✅ GenomeStore 加载: {genome.agent_type.value}")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ GenomeStore 测试失败: {e}")
        checks.append(False)
    
    # ContextManager 测试
    try:
        cm = ContextManager.get_instance()
        ctx = cm.create_context("verify_ctx", "test")
        ctx.set("key", "value")
        assert ctx.get("key") == "value"
        cm.destroy_context("verify_ctx")
        print("   ✅ ContextManager 上下文管理")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ ContextManager 测试失败: {e}")
        checks.append(False)
    
    # ErrorHandler 测试
    try:
        eh = ErrorHandler.get_instance()
        try:
            raise ValueError("Test error")
        except Exception as e:
            record = eh.handle_error(e, ErrorSeverity.ERROR, "test")
            assert record.error_type == "ValueError"
        print("   ✅ ErrorHandler 错误处理")
        checks.append(True)
    except Exception as e:
        print(f"   ❌ ErrorHandler 测试失败: {e}")
        checks.append(False)
    
    # 4. 结果汇总
    print("\n" + "=" * 50)
    passed = sum(checks)
    total = len(checks)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"📊 验证结果: {passed}/{total} ({percentage:.1f}%)")
    
    if percentage == 100:
        print("🎉 恭喜！所有能力已继承，可以开始执行任务！")
        print("\n📚 下一步:")
        print("  1. 阅读传承文档: ~/.openclaw/workspace/CLAWSHELL_ONBOARDING.md")
        print("  2. 注册到系统: coordinator.register('your_id', 'your_type')")
        print("  3. 开始执行任务: market.fetch_next('your_id')")
        return True
    elif percentage >= 80:
        print("⚠️ 大部分能力已继承，但有部分功能需要检查")
        return True
    else:
        print("❌ 能力继承不完整，请检查环境配置")
        print("\n🔧 故障排除:")
        print("  1. 确认 sys.path 包含 ${CLAWSHELL_HOME:-$HOME/.clawshell}")
        print("  2. 确认所有模块文件存在")
        print("  3. 检查 Python 版本 (需要 3.8+)")
        return False

if __name__ == "__main__":
    success = verify_agent_capabilities()
    sys.exit(0 if success else 1)
