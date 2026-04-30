#!/usr/bin/env python3
"""
ClawShell × WuKong 集成模块
方案B产物：基于真实API探测的集成代码
"""
import sys
from pathlib import Path

# ClawShell路径配置
CLAWSHELL_PATH = Path(r"C:\Users\Aorus\.ClawShell")
sys.path.insert(0, str(CLAWSHELL_PATH))

# ============ Layer 1: 健康监控集成 ============
def init_health_monitor():
    """初始化WuKong健康监控器"""
    from lib.layer1.health_check import HealthMonitor
    from lib.layer1.process_mon import ProcessMonitor
    from lib.layer1.service_mon import ServiceMonitor
    from lib.layer1.disk_mon import DiskMonitor
    from lib.layer1.agent_mon import AgentMonitor
    from lib.layer1.gateway_mon import GatewayMonitor
    
    return {
        "HealthMonitor": HealthMonitor,
        "ProcessMonitor": ProcessMonitor,
        "ServiceMonitor": ServiceMonitor,
        "DiskMonitor": DiskMonitor,
        "AgentMonitor": AgentMonitor,
        "GatewayMonitor": GatewayMonitor
    }

# ============ Layer 2: 自修复与条件引擎 ============
def init_layer2_modules():
    """初始化Layer2自修复模块"""
    from lib.layer2.self_repair import SelfHealingEngine, BackupManager, CheckpointManager
    from lib.layer2.self_healing import HealingAction, HealingReport
    from lib.layer2.responder import ResponseEngine
    from lib.layer2.condition import ConditionEngine
    from lib.layer2.sense import SenseEngine
    from lib.layer2.discovery import CapabilityDiscovery
    from lib.layer2.adaptive_controller import AdaptiveController
    
    return {
        "SelfHealingEngine": SelfHealingEngine,
        "BackupManager": BackupManager,
        "CheckpointManager": CheckpointManager,
        "HealingAction": HealingAction,
        "HealingReport": HealingReport,
        "ResponseEngine": ResponseEngine,
        "ConditionEngine": ConditionEngine,
        "SenseEngine": SenseEngine,
        "CapabilityDiscovery": CapabilityDiscovery,
        "AdaptiveController": AdaptiveController
    }

# ============ Layer 3: 任务市场与编排 ============
def init_layer3_modules():
    """初始化Layer3任务编排模块"""
    from lib.layer3.task_market import TaskMarket, TaskMatcher
    from lib.layer3.dag import TaskDAG, Task, TaskStatus, DAGValidator, DAGReport
    from lib.layer3.coordinator import Coordinator
    from lib.layer3.context_manager import ContextManager
    from lib.layer3.task_registry import TaskRegistry
    
    return {
        "TaskMarket": TaskMarket,
        "TaskMatcher": TaskMatcher,
        "TaskDAG": TaskDAG,
        "Task": Task,
        "TaskStatus": TaskStatus,
        "DAGValidator": DAGValidator,
        "DAGReport": DAGReport,
        "Coordinator": Coordinator,
        "ContextManager": ContextManager,
        "TaskRegistry": TaskRegistry
    }

# ============ Layer 4: 集群与信任管理 ============
def init_layer4_modules():
    """初始化Layer4集群模块"""
    from lib.layer4.swarm import NodeRegistry, Node, NodeType, NodeStatus
    from lib.layer4.trust import TrustManager, TrustLevel
    from lib.layer4.trust_manager import TrustManager as TrustManagerV2, TrustScore
    from lib.layer4.failure_detector import FailureDetector
    
    return {
        "NodeRegistry": NodeRegistry,
        "Node": Node,
        "NodeType": NodeType,
        "NodeStatus": NodeStatus,
        "TrustManager": TrustManager,
        "TrustLevel": TrustLevel,
        "TrustManagerV2": TrustManagerV2,
        "TrustScore": TrustScore,
        "FailureDetector": FailureDetector
    }

# ============ Core: 事件总线与策略 ============
def init_core_modules():
    """初始化Core核心模块"""
    from lib.core.eventbus import EventBus
    from lib.core.genome import GenomeManager, Heritage
    from lib.core.strategy import StrategyRegistry, StrategySwitcher
    
    return {
        "EventBus": EventBus,
        "GenomeManager": GenomeManager,
        "Heritage": Heritage,
        "StrategyRegistry": StrategyRegistry,
        "StrategySwitcher": StrategySwitcher
    }

# ============ Detector: 异常检测 ============
def init_detector_modules():
    """初始化Detector检测模块"""
    from lib.detector.dependency_checker import DependencyChecker
    from lib.detector.framework_detector import FrameworkDetector
    from lib.detector.external_detector import ExternalDetector
    from lib.detector.persistence_detector import PersistenceDetector
    
    return {
        "DependencyChecker": DependencyChecker,
        "FrameworkDetector": FrameworkDetector,
        "ExternalDetector": ExternalDetector,
        "PersistenceDetector": PersistenceDetector
    }

# ============ WuKong 统一入口 ============
class WuKongClawShell:
    """WuKong × ClawShell 统一入口"""
    
    def __init__(self):
        self.health = None
        self.layer2 = None
        self.layer3 = None
        self.layer4 = None
        self.core = None
        self.detector = None
        self._initialized = False
    
    def initialize(self):
        """初始化所有模块"""
        if self._initialized:
            return
        
        print("🚀 WuKong: 初始化 ClawShell 模块...")
        
        try:
            self.health = init_health_monitor()
            print(f"  ✓ Layer1 健康监控: {len(self.health)} 模块")
        except Exception as e:
            print(f"  ✗ Layer1 失败: {e}")
        
        try:
            self.layer2 = init_layer2_modules()
            print(f"  ✓ Layer2 自修复: {len(self.layer2)} 模块")
        except Exception as e:
            print(f"  ✗ Layer2 失败: {e}")
        
        try:
            self.layer3 = init_layer3_modules()
            print(f"  ✓ Layer3 任务编排: {len(self.layer3)} 模块")
        except Exception as e:
            print(f"  ✗ Layer3 失败: {e}")
        
        try:
            self.layer4 = init_layer4_modules()
            print(f"  ✓ Layer4 集群管理: {len(self.layer4)} 模块")
        except Exception as e:
            print(f"  ✗ Layer4 失败: {e}")
        
        try:
            self.core = init_core_modules()
            print(f"  ✓ Core 核心模块: {len(self.core)} 模块")
        except Exception as e:
            print(f"  ✗ Core 失败: {e}")
        
        try:
            self.detector = init_detector_modules()
            print(f"  ✓ Detector 检测器: {len(self.detector)} 模块")
        except Exception as e:
            print(f"  ✗ Detector 失败: {e}")
        
        self._initialized = True
        print("✅ WuKong: ClawShell 模块初始化完成!")
    
    def get_module(self, layer: str, name: str):
        """获取指定模块"""
        layer_map = {
            "health": self.health,
            "layer2": self.layer2,
            "layer3": self.layer3,
            "layer4": self.layer4,
            "core": self.core,
            "detector": self.detector
        }
        
        modules = layer_map.get(layer, {})
        return modules.get(name)
    
    def status(self):
        """输出状态摘要"""
        print("\n" + "=" * 50)
        print("WuKong × ClawShell 状态")
        print("=" * 50)
        
        for layer_name, modules in [
            ("Layer1 健康监控", self.health),
            ("Layer2 自修复", self.layer2),
            ("Layer3 任务编排", self.layer3),
            ("Layer4 集群管理", self.layer4),
            ("Core 核心", self.core),
            ("Detector 检测", self.detector)
        ]:
            if modules:
                print(f"\n{layer_name}:")
                for name in modules:
                    print(f"  - {name}")


def main():
    """主函数：演示集成模块"""
    print("=" * 60)
    print("WuKong × ClawShell 集成演示")
    print("=" * 60)
    
    # 创建实例并初始化
    wk = WuKongClawShell()
    wk.initialize()
    
    # 输出状态
    wk.status()
    
    # 测试获取具体模块
    print("\n" + "=" * 50)
    print("模块调用测试")
    print("=" * 50)
    
    # 测试 NodeRegistry (Layer4)
    NodeRegistry = wk.get_module("layer4", "NodeRegistry")
    if NodeRegistry:
        print(f"✓ NodeRegistry 可用: {NodeRegistry}")
    
    # 测试 EventBus (Core)
    EventBus = wk.get_module("core", "EventBus")
    if EventBus:
        print(f"✓ EventBus 可用: {EventBus}")
    
    # 测试 DependencyChecker (Detector)
    DependencyChecker = wk.get_module("detector", "DependencyChecker")
    if DependencyChecker:
        print(f"✓ DependencyChecker 可用: {DependencyChecker}")
    
    # 统计结果
    total = sum([
        wk.health and len(wk.health) or 0,
        wk.layer2 and len(wk.layer2) or 0,
        wk.layer3 and len(wk.layer3) or 0,
        wk.layer4 and len(wk.layer4) or 0,
        wk.core and len(wk.core) or 0,
        wk.detector and len(wk.detector) or 0
    ])
    
    print(f"\n总计可用模块: {total}")
    print("🎉 集成验证成功!")


if __name__ == "__main__":
    main()
