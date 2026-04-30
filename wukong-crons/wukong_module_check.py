#!/usr/bin/env python3
"""
悟空ClawShell模块自检器
功能：全面检测ClawShell所有模块的导入状态、功能可用性
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# ClawShell路径配置
CLAWSHELL_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(CLAWSHELL_PATH))

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "module_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 模块测试清单
MODULE_TEST_LIST = {
    "Layer1-自感知": [
        ("lib.layer1.health_check", "HealthMonitor", "健康检查"),
        ("lib.layer1.system_mon", "SystemMonitor", "系统监控"),
        ("lib.layer1.disk_mon", "DiskMonitor", "磁盘监控"),
        ("lib.layer1.process_mon", "ProcessMonitor", "进程监控"),
        ("lib.layer1.agent_mon", "AgentMonitor", "Agent监控"),
        ("lib.layer1.gateway_mon", "GatewayMonitor", "网关监控"),
        ("lib.layer1.service_mon", "ServiceMonitor", "服务监控"),
    ],
    "Layer2-自适应": [
        ("lib.layer2.self_healing", "SelfHealingEngine", "自修复系统"),
        ("lib.layer2.self_repair", "SelfHealingEngine", "自修复引擎"),
        ("lib.layer2.condition", "ConditionEngine", "条件引擎"),
        ("lib.layer2.discovery", "CapabilityDiscovery", "能力发现"),
        ("lib.layer2.sense", "SenseEngine", "感知引擎"),
        ("lib.layer2.responder", "ResponseEngine", "响应引擎"),
        ("lib.layer2.adaptive_controller", "AdaptiveController", "自适应控制器"),
    ],
    "Layer3-自组织": [
        ("lib.layer3.task_market", "TaskMarket", "任务市场"),
        ("lib.layer3.task_market", "TaskMatcher", "任务匹配器"),
        ("lib.layer3.dag", "TaskDAG", "DAG编排"),
        ("lib.layer3.dag", "Task", "DAG任务"),
        ("lib.layer3.coordinator", "NodeCoordinator", "节点协调"),
        ("lib.layer3.context_manager", "ContextManager", "上下文管理"),
        ("lib.layer3.task_registry", "TaskRegistry", "任务注册"),
    ],
    "Layer4-集群": [
        ("lib.layer4.swarm", "NodeRegistry", "节点注册"),
        ("lib.layer4.swarm", "Node", "节点"),
        ("lib.layer4.swarm", "NodeType", "节点类型"),
        ("lib.layer4.swarm", "NodeStatus", "节点状态"),
        ("lib.layer4.trust", "TrustManager", "信任管理"),
        ("lib.layer4.trust", "TrustLevel", "信任级别"),
        ("lib.layer4.trust_manager", "TrustManager", "信任管理器"),
        ("lib.layer4.failure_detector", "FailureDetector", "故障检测"),
    ],
    "Core-核心": [
        ("lib.core.eventbus", "EventBus", "事件总线"),
        ("lib.core.genome", "GenomeManager", "基因组管理"),
        ("lib.core.genome", "Heritage", "知识传承"),
        ("lib.core.strategy", "StrategyRegistry", "策略注册"),
        ("lib.core.strategy", "StrategySwitcher", "策略切换"),
    ],
    "Bridge-桥接": [
        ("lib.bridge.hermes.bridge", "HermesBridge", "Hermes桥接"),
        ("lib.bridge.hermes.scenario_integrator", "ScenarioIntegrator", "场景集成"),
        ("lib.bridge.hermes.classifier", "Classifier", "分类器"),
        ("lib.bridge.hermes.matcher", "Matcher", "匹配器"),
        ("lib.bridge.hermes.publisher", "Publisher", "发布器"),
        ("lib.bridge.hermes.subscriber", "Subscriber", "订阅器"),
    ],
    "Detector-检测": [
        ("lib.detector.dependency_checker", "DependencyChecker", "依赖检查"),
        ("lib.detector.framework_detector", "FrameworkDetector", "框架检测"),
        ("lib.detector.external_detector", "ExternalDetector", "外部检测"),
        ("lib.detector.persistence_detector", "PersistenceDetector", "持久化检测"),
    ],
}


class WuKongModuleChecker:
    """悟空模块检查器"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "total_modules": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": {},
            "summary_by_layer": {}
        }

    def test_module(self, module_path: str, class_name: str, description: str) -> Tuple[str, str]:
        """测试单个模块"""
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name, None)
            
            if cls is None:
                # 类可能在子模块中
                parts = module_path.split('.')
                current = sys.modules.get('.'.join(parts[:2]))
                for part in parts[2:]:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        return "warning", f"模块存在但未找到类 {class_name}"
                
                cls = getattr(current, class_name, None)
            
            if cls:
                return "pass", f"[OK] {cls.__name__}"
            else:
                return "warning", f"模块存在但未找到类 {class_name}"
                
        except ImportError as e:
            return "fail", f"[FAIL] 导入失败: {str(e)[:50]}"
        except Exception as e:
            return "fail", f"[FAIL] {str(e)[:50]}"

    def check_all_modules(self) -> Dict:
        """检查所有模块"""
        logger.info("开始模块检查...")
        
        total = 0
        passed = 0
        failed = 0
        warnings = 0
        
        for layer_name, modules in MODULE_TEST_LIST.items():
            layer_results = []
            layer_passed = 0
            layer_failed = 0
            layer_warnings = 0
            
            logger.info(f"检查 {layer_name}...")
            
            for module_path, class_name, description in modules:
                total += 1
                status, message = self.test_module(module_path, class_name, description)
                
                layer_results.append({
                    "module": module_path,
                    "class": class_name,
                    "description": description,
                    "status": status,
                    "message": message
                })
                
                if status == "pass":
                    passed += 1
                    layer_passed += 1
                elif status == "warning":
                    warnings += 1
                    layer_warnings += 1
                else:
                    failed += 1
                    layer_failed += 1
                
                logger.info(f"  {message}")
            
            self.results["details"][layer_name] = layer_results
            self.results["summary_by_layer"][layer_name] = {
                "total": len(modules),
                "passed": layer_passed,
                "failed": layer_failed,
                "warnings": layer_warnings
            }
        
        self.results["total_modules"] = total
        self.results["passed"] = passed
        self.results["failed"] = failed
        self.results["warnings"] = warnings
        
        return self.results

    def generate_report(self) -> str:
        """生成检查报告"""
        report = f"""# ClawShell模块检查报告

**检查时间**: {self.results['timestamp']}
**总模块数**: {self.results['total_modules']}
**通过**: {self.results['passed']} | **失败**: {self.results['failed']} | **警告**: {self.results['warnings']}

---

## 按层级统计

| 层级 | 总数 | 通过 | 失败 | 警告 | 通过率 |
|------|------|------|------|------|--------|
"""
        
        for layer, summary in self.results["summary_by_layer"].items():
            rate = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
            report += f"| {layer} | {summary['total']} | {summary['passed']} | {summary['failed']} | {summary['warnings']} | {rate:.0f}% |\n"
        
        report += "\n## 详细结果\n\n"
        
        for layer, modules in self.results["details"].items():
            report += f"### {layer}\n\n"
            report += "| 模块 | 类名 | 描述 | 状态 | 详情 |\n"
            report += "|------|------|------|------|------|\n"
            
            for mod in modules:
                status_icon = {"pass": "✅", "warning": "[WARN]️", "fail": "❌"}.get(mod["status"], "❓")
                report += f"| {mod['module']} | {mod['class']} | {mod['description']} | {status_icon} | {mod['message']} |\n"
            
            report += "\n"
        
        # 失败模块汇总
        if self.results["failed"] > 0:
            report += "## 需要修复的模块\n\n"
            for layer, modules in self.results["details"].items():
                failed_modules = [m for m in modules if m["status"] == "fail"]
                if failed_modules:
                    report += f"### {layer}\n"
                    for mod in failed_modules:
                        report += f"- `{mod['module']}` → {mod['message']}\n"
                    report += "\n"
        
        return report

    def save_report(self, content: str) -> Path:
        """保存报告"""
        output_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "module_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"module_check_{timestamp}.md"
        output_file = output_dir / filename
        
        # 同时保存JSON
        json_file = output_dir / f"module_check_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存: {output_file}")
        logger.info(f"JSON已保存: {json_file}")
        
        return output_file

    def run(self) -> Dict:
        """执行检查"""
        logger.info("=" * 50)
        logger.info("ClawShell模块检查开始")
        logger.info("=" * 50)
        
        self.check_all_modules()
        
        logger.info("=" * 50)
        logger.info(f"检查完成: {self.results['passed']}/{self.results['total_modules']} 通过")
        logger.info(f"失败: {self.results['failed']}, 警告: {self.results['warnings']}")
        logger.info("=" * 50)
        
        return self.results


def main():
    """主函数"""
    checker = WuKongModuleChecker()
    results = checker.run()
    
    content = checker.generate_report()
    output_file = checker.save_report(content)
    
    # 输出摘要
    print(f"\n{'=' * 50}")
    print("ClawShell模块检查结果")
    print(f"{'=' * 50}")
    print(f"总模块: {results['total_modules']}")
    print(f"通过: {results['passed']} ✅")
    print(f"失败: {results['failed']} ❌")
    print(f"警告: {results['warnings']} [WARN]️")
    print(f"\n详细报告: {output_file}")
    
    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
