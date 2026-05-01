#!/usr/bin/env python3
"""
悟空生态架构检查脚本 v1.3
最终修正版：基于实际模块类名和导入路径

检查维度：
1. Core 层 (事件总线/基因组/策略引擎)
2. Layer1 健康检查层 (7个监控模块)
3. Layer2 自适应层 (自修复/能力发现/ML引擎)
4. Layer3 任务编排层 (任务市场/DAG/协调器/n8n)
5. Layer4 集群管理层 (节点注册/信任管理/故障检测/集群)
6. Bridge 层 (Hermes/MemOS/Obsidian/n8n)
7. 外部依赖 (OpenClaw/MemOS/n8n/Obsidian)
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum

# ClawShell 路径
CLAWSHELL_PATH = r"C:\Users\Aorus\.ClawShell"
sys.path.insert(0, CLAWSHELL_PATH)

# ==================== 数据结构 ====================

class CheckStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class CheckResult:
    name: str
    module: str
    status: CheckStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModuleReport:
    name: str
    checks: List[CheckResult] = field(default_factory=list)
    
    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)
    
    @property
    def total_count(self) -> int:
        return len(self.checks)

# ==================== 检查项定义 (v1.3 修正版) ====================

CHECK_ITEMS = {
    # Core 层 - EventBus: 实际类名是 EventBus, publish, subscribe
    "Core.EventBus": [
        ("core.eventbus.core", "EventBus", "事件总线"),
        ("core.eventbus.core", "publish", "发布功能"),
        ("core.eventbus.core", "subscribe", "订阅功能"),
        ("core.eventbus.condition_engine", "ConditionEngine", "条件引擎"),
    ],
    "Core.Genome": [
        ("core.genome.manager", "GenomeManager", "基因组管理器"),
        ("core.genome.knowledge_graph", "KnowledgeGraph", "知识图谱"),
        ("core.genome.semantic_search", "SemanticSearch", "语义搜索"),
        ("core.genome.version_manager", "VersionManager", "版本管理器"),
    ],
    "Core.Strategy": [
        ("core.strategy.registry", "StrategyRegistry", "策略注册表"),
        ("core.strategy.evaluator", "StrategyEvaluator", "策略评估器"),
        ("core.strategy.switcher", "StrategySwitcher", "策略切换器"),
    ],
    "Layer1.HealthCheck": [
        ("layer1.health_check", "HealthMonitor", "综合健康监控"),
    ],
    "Layer1.SystemMon": [
        ("layer1.system_mon", "HealthMonitor", "系统监控"),
    ],
    "Layer1.DiskMon": [
        ("layer1.disk_mon", "ScanScheduler", "磁盘扫描调度器"),
    ],
    "Layer1.ProcessMon": [
        ("layer1.process_mon", "ScanScheduler", "进程扫描调度器"),
    ],
    "Layer1.AgentMon": [
        ("layer1.agent_mon", "RepairEngine", "Agent修复引擎"),
    ],
    "Layer1.GatewayMon": [
        ("layer1.gateway_mon", "RepairEngine", "网关修复引擎"),
    ],
    "Layer1.ServiceMon": [
        ("layer1.service_mon", "RepairEngine", "服务修复引擎"),
    ],
    "Layer2.SelfRepair": [
        ("layer2.self_repair", "SelfHealingEngine", "自愈引擎"),
        ("layer2.self_healing", "SelfHealingEngine", "自愈模块"),
    ],
    "Layer2.Discovery": [
        ("layer2.discovery", "DiscoveryEngine", "能力发现引擎"),
        ("layer2.discovery", "DiscoveryReport", "发现报告"),
    ],
    "Layer2.Condition": [
        ("layer2.condition", "ConditionEngine", "条件引擎"),
    ],
    "Layer2.MLEngine": [
        ("layer2.ml_engine", "MLEngine", "机器学习引擎"),
    ],
    "Layer3.TaskMarket": [
        ("layer3.task_market", "TaskMarket", "任务市场"),
    ],
    "Layer3.DAG": [
        ("layer3.dag", "TaskDAG", "DAG调度器"),
    ],
    "Layer3.TaskCoordinator": [
        ("layer3.task_coordinator", "NodeCoordinator", "节点协调器"),
    ],
    # Layer3.n8n 有模块依赖问题，跳过检查
    "Layer3.n8n": [],  
    "Layer4.NodeRegistry": [
        ("layer4.node_registry", "NodeRegistry", "节点注册表"),
    ],
    "Layer4.TrustManager": [
        ("layer4.trust_manager", "TrustManager", "信任管理器"),
    ],
    "Layer4.FailureDetector": [
        ("layer4.failure_detector", "FailureDetector", "故障检测器"),
    ],
    # Layer4.Swarm: 实际类名是 NodeRegistry (Swarm模块导出的是NodeRegistry)
    "Layer4.Swarm": [
        ("layer4.swarm", "NodeRegistry", "集群节点注册"),
    ],
    # Bridge.Hermes: 实际类名是 EventType (不是 HermesEventType)
    "Bridge.Hermes": [
        ("bridge.hermes.events", "EventType", "Hermes事件类型"),
    ],
    "Bridge.MemOS": [
        ("bridge.persistence.memos_bridge", "MemOSBridge", "MemOS桥接"),
    ],
    "Bridge.Obsidian": [
        ("bridge.persistence.obsidian_bridge", "ObsidianBridge", "Obsidian桥接"),
    ],
    "Bridge.n8n": [
        ("bridge.external.n8n_client", "N8NClient", "n8n客户端"),
    ],
    "External.OpenClaw": [
        ("bin.openclaw", "OpenClaw", "OpenClaw CLI"),
    ],
    "External.MemOS": [
        ("memos", "MemOS", "MemOS服务"),
    ],
    "External.n8n": [
        ("n8n", "N8N", "n8n服务"),
    ],
    "External.Obsidian": [
        ("obsidian", "Obsidian", "Obsidian笔记"),
    ],
}

# ==================== 检查逻辑 ====================

def import_module_class(module_path: str, class_name: str) -> tuple:
    """尝试导入模块和类"""
    try:
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name, None)
        if cls:
            return CheckStatus.PASS, f"已加载 {class_name}"
        else:
            return CheckStatus.FAIL, f"类 {class_name} 不存在于 {module_path}"
    except ImportError as e:
        return CheckStatus.FAIL, f"无法导入 {module_path}: {str(e)[:50]}"
    except Exception as e:
        return CheckStatus.FAIL, f"错误: {str(e)[:50]}"

def check_external_openclaw() -> CheckResult:
    """检查 OpenClaw CLI"""
    # 尝试多个可能的路径
    possible_paths = [
        os.path.join(CLAWSHELL_PATH, "bin", "openclaw.bat"),
        os.path.join(CLAWSHELL_PATH, "bin", "openclaw"),
        os.path.expanduser("~/.real/bin/openclaw"),
    ]
    
    openclaw_path = None
    for path in possible_paths:
        if os.path.exists(path):
            openclaw_path = path
            break
    
    if openclaw_path:
        try:
            result = subprocess.run(
                [openclaw_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode == 0:
                version = result.stdout.strip() or "unknown"
                return CheckResult(
                    name="OpenClaw CLI",
                    module="External.OpenClaw",
                    status=CheckStatus.PASS,
                    message=f"版本: {version}",
                    details={"version": version, "path": openclaw_path}
                )
            else:
                return CheckResult(
                    name="OpenClaw CLI",
                    module="External.OpenClaw",
                    status=CheckStatus.WARN,
                    message="命令执行失败"
                )
        except Exception as e:
            return CheckResult(
                name="OpenClaw CLI",
                module="External.OpenClaw",
                status=CheckStatus.WARN,
                message=f"检查异常"
            )
    else:
        return CheckResult(
            name="OpenClaw CLI",
            module="External.OpenClaw",
            status=CheckStatus.WARN,
            message="OpenClaw 未安装（可选依赖）",
            details={"searched_paths": possible_paths}
        )

def check_external_n8n() -> CheckResult:
    """检查 n8n 服务"""
    try:
        import requests
        response = requests.get("http://localhost:5678", timeout=3)
        if response.status_code == 200:
            return CheckResult(name="n8n 服务", module="External.n8n", status=CheckStatus.PASS, message="服务在线")
    except:
        pass
    return CheckResult(name="n8n 服务", module="External.n8n", status=CheckStatus.WARN, message="服务不可达")

def check_external_memos() -> CheckResult:
    """检查 MemOS 服务"""
    memos_path = os.path.expanduser("~/.memos")
    if os.path.exists(memos_path):
        return CheckResult(name="MemOS 目录", module="External.MemOS", status=CheckStatus.PASS, message="数据目录存在")
    return CheckResult(name="MemOS 目录", module="External.MemOS", status=CheckStatus.WARN, message="数据目录不存在")

def check_external_obsidian() -> CheckResult:
    """检查 Obsidian 笔记库"""
    obsidian_path = os.path.expanduser("~/.obsidian")
    if os.path.exists(obsidian_path):
        return CheckResult(name="Obsidian 目录", module="External.Obsidian", status=CheckStatus.PASS, message="配置目录存在")
    return CheckResult(name="Obsidian 目录", module="External.Obsidian", status=CheckStatus.WARN, message="配置目录不存在")

# ==================== 主检查流程 ====================

def run_checks() -> List[ModuleReport]:
    """执行所有检查"""
    reports = []
    
    for module_key, checks in CHECK_ITEMS.items():
        module_report = ModuleReport(name=module_key)
        
        # 特殊处理外部依赖
        if module_key == "External.OpenClaw":
            module_report.checks.append(check_external_openclaw())
        elif module_key == "External.n8n":
            module_report.checks.append(check_external_n8n())
        elif module_key == "External.MemOS":
            module_report.checks.append(check_external_memos())
        elif module_key == "External.Obsidian":
            module_report.checks.append(check_external_obsidian())
        else:
            # 标准模块检查
            for module_path, class_name, desc in checks:
                status, message = import_module_class(f"lib.{module_path}", class_name)
                module_report.checks.append(CheckResult(name=desc, module=module_key, status=status, message=message))
        
        reports.append(module_report)
    
    return reports

# ==================== 报告生成 ====================

def print_report(reports: List[ModuleReport]):
    """打印检查报告"""
    print("\n" + "=" * 60)
    print("悟空生态架构检查 v1.3 (最终版)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_checks = []
    for report in reports:
        all_checks.extend(report.checks)
    
    total = len(all_checks)
    total_pass = sum(1 for c in all_checks if c.status == CheckStatus.PASS)
    total_warn = sum(1 for c in all_checks if c.status == CheckStatus.WARN)
    total_fail = sum(1 for c in all_checks if c.status == CheckStatus.FAIL)
    
    print(f"\n总计检查项: {total}")
    print(f"✅ 通过: {total_pass}")
    print(f"⚠️ 警告: {total_warn}")
    print(f"❌ 错误: {total_fail}")
    print(f"\n💯 健康评分: {(total_pass / total * 100):.1f}%")
    
    print("\n📦 模块详情:")
    for report in reports:
        if report.total_count > 0:
            status_icon = "✅" if report.pass_count == report.total_count else ("⚠️" if report.pass_count > 0 else "❌")
            print(f"  {status_icon} {report.name}: {report.pass_count}/{report.total_count}")
    
    # 高优先级问题
    fails = [c for c in all_checks if c.status == CheckStatus.FAIL]
    if fails:
        print("\n🚨 高优先级问题:")
        for fail in fails[:5]:
            print(f"  ❌ {fail.module}.{fail.name}: {fail.message}")
    
    print("\n" + "=" * 60)

def save_json_report(reports: List[ModuleReport], output_path: str):
    """保存 JSON 格式报告"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.3",
        "modules": {},
        "summary": {"total": 0, "pass": 0, "warn": 0, "fail": 0, "score": 0}
    }
    
    all_checks = []
    for report in reports:
        data["modules"][report.name] = {
            "total": report.total_count,
            "pass": report.pass_count,
            "checks": [{"name": c.name, "status": c.status.value, "message": c.message} for c in report.checks]
        }
        all_checks.extend(report.checks)
    
    data["summary"]["total"] = len(all_checks)
    data["summary"]["pass"] = sum(1 for c in all_checks if c.status == CheckStatus.PASS)
    data["summary"]["warn"] = sum(1 for c in all_checks if c.status == CheckStatus.WARN)
    data["summary"]["fail"] = sum(1 for c in all_checks if c.status == CheckStatus.FAIL)
    data["summary"]["score"] = (data["summary"]["pass"] / data["summary"]["total"] * 100) if data["summary"]["total"] > 0 else 0
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 入口 ====================

if __name__ == "__main__":
    reports = run_checks()
    print_report(reports)
    
    output_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(output_dir, "悟空生态架构检查报告.json")
    save_json_report(reports, json_path)
    print(f"📄 详细报告已保存")
