#!/usr/bin/env python3
"""
test_runner_enhanced.py - 增强型自动化测试运行器
功能：单元测试、集成测试、E2E测试、性能基准测试
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
TEST_DIR = os.path.join(SHARED_DIR, "testsuites")
REPORTS_DIR = os.path.join(SHARED_DIR, "reports", "test")

class EnhancedTestRunner:
    """增强型测试运行器"""
    
    def __init__(self):
        os.makedirs(TEST_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "unit_tests": [],
            "integration_tests": [],
            "e2e_tests": [],
            "benchmark": None
        }
    
    def run_all_tests(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("🚀 ClawShell 测试套件")
        print("=" * 60)
        
        # 1. 单元测试
        print("\n📦 运行单元测试...")
        unit_result = self.run_unit_tests()
        self.results["unit_tests"] = unit_result
        print(f"   单元测试: {unit_result['passed']}/{unit_result['total']} 通过")
        
        # 2. 集成测试
        print("\n🔗 运行集成测试...")
        integration_result = self.run_integration_tests()
        self.results["integration_tests"] = integration_result
        print(f"   集成测试: {integration_result['passed']}/{integration_result['total']} 通过")
        
        # 3. E2E测试
        print("\n🎯 运行E2E测试...")
        e2e_result = self.run_e2e_tests()
        self.results["e2e_tests"] = e2e_result
        print(f"   E2E测试: {e2e_result['passed']}/{e2e_result['total']} 通过")
        
        # 4. 性能基准测试
        print("\n⚡ 运行性能基准测试...")
        benchmark_result = self.run_benchmark()
        self.results["benchmark"] = benchmark_result
        print(f"   基准测试: {benchmark_result['status']}")
        
        # 5. 生成报告
        self.generate_report()
        
        return self.results
    
    def run_unit_tests(self) -> dict:
        """运行单元测试"""
        tests = self._discover_unit_tests()
        
        passed = 0
        failed = []
        duration = 0
        
        for test_file in tests:
            start = time.time()
            result = self._run_python_test(test_file)
            duration += time.time() - start
            
            if result["status"] == "passed":
                passed += 1
            else:
                failed.append({
                    "test": test_file,
                    "error": result.get("error", "Unknown")
                })
        
        return {
            "total": len(tests),
            "passed": passed,
            "failed": len(failed),
            "duration": round(duration, 2),
            "failures": failed
        }
    
    def run_integration_tests(self) -> dict:
        """运行集成测试"""
        tests = self._discover_integration_tests()
        
        passed = 0
        failed = []
        duration = 0
        
        for test_file in tests:
            start = time.time()
            result = self._run_integration_test(test_file)
            duration += time.time() - start
            
            if result["status"] == "passed":
                passed += 1
            else:
                failed.append({
                    "test": test_file,
                    "error": result.get("error", "Unknown")
                })
        
        return {
            "total": len(tests),
            "passed": passed,
            "failed": len(failed),
            "duration": round(duration, 2),
            "failures": failed
        }
    
    def run_e2e_tests(self) -> dict:
        """运行端到端测试"""
        tests = self._discover_e2e_tests()
        
        passed = 0
        failed = []
        duration = 0
        
        for test_file in tests:
            start = time.time()
            result = self._run_e2e_test(test_file)
            duration += time.time() - start
            
            if result["status"] == "passed":
                passed += 1
            else:
                failed.append({
                    "test": test_file,
                    "error": result.get("error", "Unknown")
                })
        
        return {
            "total": len(tests),
            "passed": passed,
            "failed": len(failed),
            "duration": round(duration, 2),
            "failures": failed
        }
    
    def run_benchmark(self) -> dict:
        """运行性能基准测试"""
        benchmarks = [
            ("EventBus响应", self._benchmark_eventbus),
            ("ContextManager响应", self._benchmark_context_manager),
            ("TaskScheduler响应", self._benchmark_task_scheduler),
            ("Agent启动时间", self._benchmark_agent_startup),
        ]
        
        results = []
        for name, func in benchmarks:
            start = time.time()
            result = func()
            elapsed = (time.time() - start) * 1000  # ms
            results.append({
                "name": name,
                "duration_ms": round(elapsed, 2),
                "status": "passed" if result else "failed"
            })
        
        all_passed = all(r["status"] == "passed" for r in results)
        
        return {
            "status": "passed" if all_passed else "failed",
            "results": results
        }
    
    def _discover_unit_tests(self) -> list:
        """发现单元测试"""
        unit_dir = os.path.join(TEST_DIR, "unit")
        if not os.path.exists(unit_dir):
            return []
        return [f for f in os.listdir(unit_dir) if f.startswith("test_") and f.endswith(".py")]
    
    def _discover_integration_tests(self) -> list:
        """发现集成测试"""
        integration_dir = os.path.join(TEST_DIR, "integration")
        if not os.path.exists(integration_dir):
            return []
        return [f for f in os.listdir(integration_dir) if f.startswith("test_") and f.endswith(".py")]
    
    def _discover_e2e_tests(self) -> list:
        """发现E2E测试"""
        e2e_dir = os.path.join(TEST_DIR, "e2e")
        if not os.path.exists(e2e_dir):
            return []
        return [f for f in os.listdir(e2e_dir) if f.startswith("test_") and f.endswith(".py")]
    
    def _run_python_test(self, test_file: str) -> dict:
        """运行Python单元测试"""
        test_path = os.path.join(TEST_DIR, "unit", test_file)
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout[:500]
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _run_integration_test(self, test_file: str) -> dict:
        """运行集成测试"""
        test_path = os.path.join(TEST_DIR, "integration", test_file)
        try:
            result = subprocess.run(
                ["python3", test_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout[:500]
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _run_e2e_test(self, test_file: str) -> dict:
        """运行E2E测试"""
        test_path = os.path.join(TEST_DIR, "e2e", test_file)
        try:
            result = subprocess.run(
                ["python3", test_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout[:500]
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "Test timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _benchmark_eventbus(self) -> bool:
        """EventBus响应基准测试"""
        try:
            # 简单测试EventBus处理速度
            script = """
import sys
sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/scripts')
from event_bus import EventBus
eb = EventBus()
eb.publish('test.benchmark', {'data': 'test'})
events = eb.get_pending_events()
"""
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _benchmark_context_manager(self) -> bool:
        """ContextManager响应基准测试"""
        try:
            script = """
import sys
sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/scripts')
from context_manager import ContextManager
cm = ContextManager()
cm.collect()
"""
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _benchmark_task_scheduler(self) -> bool:
        """TaskScheduler响应基准测试"""
        try:
            script = """
import sys
sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/scripts')
from task_scheduler import TaskScheduler
ts = TaskScheduler()
ts.check_and_dispatch()
"""
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def _benchmark_agent_startup(self) -> bool:
        """Agent启动时间基准测试"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "--all-agents"],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False
    
    def generate_report(self) -> str:
        """生成测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(REPORTS_DIR, f"test_report_{timestamp}.json")
        
        # 计算汇总
        total_tests = (
            self.results["unit_tests"].get("total", 0) +
            self.results["integration_tests"].get("total", 0) +
            self.results["e2e_tests"].get("total", 0)
        )
        total_passed = (
            self.results["unit_tests"].get("passed", 0) +
            self.results["integration_tests"].get("passed", 0) +
            self.results["e2e_tests"].get("passed", 0)
        )
        
        summary = {
            "timestamp": self.results["timestamp"],
            "total_tests": total_tests,
            "total_passed": total_passed,
            "pass_rate": round(total_passed / total_tests * 100, 1) if total_tests > 0 else 0,
            "benchmark_status": self.results["benchmark"].get("status") if self.results["benchmark"] else "unknown"
        }
        
        self.results["summary"] = summary
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 测试报告已生成: {report_file}")
        return report_file


if __name__ == "__main__":
    runner = EnhancedTestRunner()
    results = runner.run_all_tests()
    
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    print(f"总测试数: {results['summary']['total_tests']}")
    print(f"通过: {results['summary']['total_passed']}")
    print(f"通过率: {results['summary']['pass_rate']}%")
    print(f"基准测试: {results['summary']['benchmark_status']}")
