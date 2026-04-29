#!/usr/bin/env python3
"""
Test CI - 持续集成脚本
功能：
1. 集成到CI/CD流水线
2. 自动触发测试
3. 门禁检查
4. 通知
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# ==================== 配置 ====================

SCRIPT_DIR = Path.home() / ".openclaw/scripts"
REPORT_DIR = Path.home() / ".openclaw/reports"
GATE_THRESHOLD = 80.0  # 通过率门禁阈值(%)

# ==================== CI管理器 ====================

class CITestManager:
    def __init__(self):
        self.gate_threshold = GATE_THRESHOLD
        self.notify_script = SCRIPT_DIR / "notify.py"
    
    def run_tests(self, verbose: bool = False) -> Tuple[bool, Dict]:
        """运行测试"""
        test_script = SCRIPT_DIR / "test_runner.py"
        
        cmd = [sys.executable, str(test_script)]
        if verbose:
            cmd.append("--verbose")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(SCRIPT_DIR)
        )
        
        try:
            # 查找最新报告
            reports = sorted(REPORT_DIR.glob("test_report_*.json"))
            if reports:
                with open(reports[-1], 'r') as f:
                    report = json.load(f)
                    summary = report.get("summary", report)
            else:
                summary = {"error": "No report found"}
        except:
            summary = {"error": "Failed to parse report"}
        
        passed = result.returncode == 0
        return passed, summary
    
    def check_gate(self, summary: Dict) -> Tuple[bool, str]:
        """检查门禁"""
        if "error" in summary:
            return False, f"Test error: {summary.get('error')}"
        
        pass_rate = summary.get("pass_rate", 0)
        
        if pass_rate >= self.gate_threshold:
            return True, f"Gate passed: {pass_rate}% >= {self.gate_threshold}%"
        else:
            return False, f"Gate failed: {pass_rate}% < {self.gate_threshold}%"
    
    def run_full_ci(self) -> Dict:
        """运行完整CI流程"""
        print("=" * 60)
        print("      CI Test Pipeline")
        print("=" * 60)
        print()
        
        # 1. 运行测试
        print("📦 Running tests...")
        test_passed, summary = self.run_tests(verbose=True)
        print()
        
        # 2. 门禁检查
        print("🚪 Checking gate...")
        gate_passed, gate_message = self.check_gate(summary)
        print(f"  {gate_message}")
        print()
        
        # 3. 结果汇总
        result = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": test_passed,
            "gate_passed": gate_passed,
            "gate_message": gate_message,
            "summary": summary,
            "overall_passed": test_passed and gate_passed
        }
        
        # 4. 打印结果
        print("=" * 60)
        print("      CI Result")
        print("=" * 60)
        print(f"Tests: {'✅ PASSED' if test_passed else '❌ FAILED'}")
        print(f"Gate:  {'✅ PASSED' if gate_passed else '❌ FAILED'}")
        print(f"Overall: {'✅ PASSED' if result['overall_passed'] else '❌ FAILED'}")
        print()
        
        if "total_cases" in summary:
            print(f"Total: {summary['total_cases']} | Passed: {summary['total_passed']} | Failed: {summary['total_failed']} | Errors: {summary['total_errors']}")
            print(f"Pass Rate: {summary['pass_rate']}%")
        
        return result
    
    def notify_result(self, result: Dict):
        """通知结果"""
        status = "✅ PASSED" if result["overall_passed"] else "❌ FAILED"
        
        message = f"""CI Test {status}

Time: {result['timestamp']}
Tests: {'Passed' if result['tests_passed'] else 'Failed'}
Gate: {result['gate_message']}
"""
        
        # 这里可以集成通知脚本
        print("\n📤 Notification:")
        print(message)

# ==================== 主函数 ====================

def main():
    manager = CITestManager()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # 仅检查门禁
        print(f"Gate threshold: {manager.gate_threshold}%")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "--run":
        # 运行完整CI
        result = manager.run_full_ci()
        manager.notify_result(result)
        sys.exit(0 if result["overall_passed"] else 1)
    
    else:
        print("Usage:")
        print("  test_ci.py --check    # Check gate threshold")
        print("  test_ci.py --run      # Run full CI pipeline")
        sys.exit(1)

if __name__ == "__main__":
    main()
