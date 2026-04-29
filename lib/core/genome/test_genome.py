#!/usr/bin/env python3
"""
GenomeStore 测试脚本 - ClawShell v0.1
=====================================

测试基因组管理器、传承协议的核心功能。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from genome import (
    GenomeManager,
    HeritageProtocol,
    Genome,
    AgentType,
    HeritageRecord,
)
from genome.schema import KnowledgeEntry, ErrorPattern, SkillState


def test_genome_creation():
    """测试基因组创建"""
    print("\n=== 测试基因组创建 ===")
    
    genome = Genome(agent_type=AgentType.OPENCLAW)
    
    assert genome.agent_type == AgentType.OPENCLAW
    assert genome.version == "0.1.0"
    assert genome.knowledge == []
    
    print(f"✅ 基因组创建成功")
    print(f"   Agent类型: {genome.agent_type.value}")
    print(f"   版本: {genome.version}")


def test_genome_add_knowledge():
    """测试添加知识"""
    print("\n=== 测试添加知识 ===")
    
    genome = Genome(agent_type=AgentType.OPENCLAW)
    
    genome.add_knowledge(
        key="user_name",
        value="月夜",
        category="user",
        source="conversation",
        confidence=0.95,
    )
    
    assert len(genome.knowledge) == 1
    assert genome.get_knowledge("user_name") == "月夜"
    
    print(f"✅ 知识添加成功")
    print(f"   知识数量: {len(genome.knowledge)}")
    print(f"   获取测试: {genome.get_knowledge('user_name')}")


def test_genome_add_error_pattern():
    """测试添加错误模式"""
    print("\n=== 测试添加错误模式 ===")
    
    genome = Genome(agent_type=AgentType.OPENCLAW)
    
    genome.add_error_pattern(
        error_type="APIError",
        description="API调用失败",
        solution="切换到备用API",
        tags=["api", "error"],
    )
    
    assert len(genome.error_patterns) == 1
    assert genome.find_error_solution("APIError") == "切换到备用API"
    
    print(f"✅ 错误模式添加成功")
    print(f"   模式数量: {len(genome.error_patterns)}")
    print(f"   解决方案查询: {genome.find_error_solution('APIError')}")


def test_genome_serialization():
    """测试基因组序列化"""
    print("\n=== 测试基因组序列化 ===")
    
    genome = Genome(agent_type=AgentType.HERMES)
    genome.add_knowledge("test_key", "test_value")
    
    # 转换为YAML
    yaml_str = genome.to_yaml()
    assert "test_key" in yaml_str
    
    # 从YAML恢复
    genome2 = Genome.from_yaml(yaml_str)
    assert genome2.get_knowledge("test_key") == "test_value"
    
    print(f"✅ 基因组序列化成功")
    print(f"   YAML长度: {len(yaml_str)} 字符")


def test_genome_manager_save_load():
    """测试基因组管理器保存和加载"""
    print("\n=== 测试基因组管理器保存加载 ===")
    
    manager = GenomeManager()
    
    # 创建并保存
    genome = Genome(agent_type=AgentType.OPENCLAW)
    genome.add_knowledge("test", "value")
    genome.add_knowledge("user", "月夜")
    
    success = manager.save_genome(genome)
    assert success
    
    # 加载
    loaded = manager.load_genome(AgentType.OPENCLAW)
    assert loaded.get_knowledge("test") == "value"
    assert loaded.get_knowledge("user") == "月夜"
    
    print(f"✅ 基因组保存加载成功")


def test_heritage_protocol():
    """测试传承协议"""
    print("\n=== 测试传承协议 ===")
    
    manager = GenomeManager()
    protocol = HeritageProtocol(manager)
    
    # 初始化
    genome = protocol.initialize(AgentType.OPENCLAW)
    initial_version = genome.version
    
    # 执行传承
    record = protocol.heritage(
        agent_type=AgentType.OPENCLAW,
        heritage_type="restart",
        notes="Test heritage",
    )
    
    assert record.from_version == initial_version
    assert record.heritage_type == "restart"
    
    print(f"✅ 传承协议执行成功")
    print(f"   {record.from_version} -> {record.to_version}")
    print(f"   类型: {record.heritage_type}")


def test_genome_stats():
    """测试基因组统计"""
    print("\n=== 测试基因组统计 ===")
    
    manager = GenomeManager()
    
    # 添加一些数据
    genome = manager.load_genome(AgentType.OPENCLAW)
    genome.add_knowledge("k1", "v1")
    genome.add_knowledge("k2", "v2")
    genome.add_error_pattern("e1", "d1", "s1")
    manager.save_genome(genome)
    
    # 获取统计
    stats = manager.get_stats(AgentType.OPENCLAW)
    
    assert stats["knowledge_count"] >= 2
    assert stats["error_patterns_count"] >= 1
    
    print(f"✅ 基因组统计正常")
    print(f"   知识条目: {stats['knowledge_count']}")
    print(f"   错误模式: {stats['error_patterns_count']}")
    print(f"   版本: {stats['version']}")


def test_heritage_history():
    """测试传承历史"""
    print("\n=== 测试传承历史 ===")
    
    manager = GenomeManager()
    protocol = HeritageProtocol(manager)
    
    # 执行多次传承
    for i in range(3):
        protocol.heritage(AgentType.OPENCLAW, heritage_type="restart")
    
    # 获取历史
    history = protocol.get_heritage_history(AgentType.OPENCLAW, limit=5)
    
    assert len(history) >= 3
    
    print(f"✅ 传承历史正常")
    print(f"   历史记录数: {len(history)}")


def test_genome_health_check():
    """测试健康检查"""
    print("\n=== 测试健康检查 ===")
    
    manager = GenomeManager()
    protocol = HeritageProtocol(manager)
    
    health = protocol.check_genome_health(AgentType.OPENCLAW)
    
    assert "healthy" in health
    assert "issues" in health
    
    print(f"✅ 健康检查完成")
    print(f"   健康状态: {'✅' if health['healthy'] else '⚠️'}")
    print(f"   问题数: {len(health['issues'])}")
    if health['issues']:
        for issue in health['issues']:
            print(f"     - {issue}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("GenomeStore v0.1 测试套件")
    print("=" * 60)
    
    tests = [
        test_genome_creation,
        test_genome_add_knowledge,
        test_genome_add_error_pattern,
        test_genome_serialization,
        test_genome_manager_save_load,
        test_heritage_protocol,
        test_genome_stats,
        test_heritage_history,
        test_genome_health_check,
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
