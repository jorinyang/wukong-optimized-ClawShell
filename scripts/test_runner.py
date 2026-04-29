#!/usr/bin/env python3
"""
Test Runner - 自动化测试运行器
功能：
1. 发现和收集测试用例
2. 执行测试
3. 记录结果
4. 生成报告
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable

# ==================== 配置 ====================

TEST_DIR = Path.home() / ".openclaw/scripts"
REPORT_DIR = Path.home() / ".openclaw/reports"
LOG_DIR = Path.home() / ".openclaw/logs"

# ==================== 测试框架 ====================

class TestResult:
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"

class TestCase:
    def __init__(self, name: str, func: Callable, description: str = ""):
        self.name = name
        self.func = func
        self.description = description
        self.result = None
        self.message = ""
        self.traceback = ""
        self.duration = 0
    
    def run(self):
        """执行测试"""
        start = time.time()
        try:
            self.func()
            self.result = TestResult.PASS
            self.message = "通过"
        except AssertionError as e:
            self.result = TestResult.FAIL
            self.message = str(e)
        except Exception as e:
            self.result = TestResult.ERROR
            self.message = str(e)
            self.traceback = traceback.format_exc()
        finally:
            self.duration = time.time() - start

class TestSuite:
    def __init__(self, name: str):
        self.name = name
        self.cases: List[TestCase] = []
        self.setup_func = None
        self.teardown_func = None
    
    def add_test(self, name: str, func: Callable, description: str = ""):
        """添加测试用例"""
        self.cases.append(TestCase(name, func, description))
    
    def set_setup(self, func: Callable):
        """设置前置条件"""
        self.setup_func = func
    
    def set_teardown(self, func: Callable):
        """设置后置清理"""
        self.teardown_func = func
    
    def run(self, verbose: bool = False) -> Dict:
        """运行测试套件"""
        results = {
            "suite": self.name,
            "timestamp": datetime.now().isoformat(),
            "total": len(self.cases),
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "duration": 0,
            "cases": []
        }
        
        start_time = time.time()
        
        # 执行前置条件
        if self.setup_func:
            try:
                self.setup_func()
            except Exception as e:
                results["setup_error"] = str(e)
                return results
        
        # 执行测试用例
        for case in self.cases:
            case.run()
            
            case_result = {
                "name": case.name,
                "description": case.description,
                "result": case.result,
                "message": case.message,
                "duration": round(case.duration, 3)
            }
            
            if case.traceback:
                case_result["traceback"] = case.traceback
            
            results["cases"].append(case_result)
            
            if case.result == TestResult.PASS:
                results["passed"] += 1
            elif case.result == TestResult.FAIL:
                results["failed"] += 1
            elif case.result == TestResult.ERROR:
                results["errors"] += 1
            else:
                results["skipped"] += 1
            
            if verbose and case.result != TestResult.PASS:
                print(f"  ❌ {case.name}: {case.message}")
        
        # 执行后置清理
        if self.teardown_func:
            try:
                self.teardown_func()
            except Exception as e:
                results["teardown_error"] = str(e)
        
        results["duration"] = round(time.time() - start_time, 3)
        return results

class TestRunner:
    def __init__(self):
        self.suites: List[TestSuite] = []
        self.report_dir = REPORT_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def add_suite(self, suite: TestSuite):
        """添加测试套件"""
        self.suites.append(suite)
    
    def run_all(self, verbose: bool = False) -> Dict:
        """运行所有测试"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_suites": len(self.suites),
            "total_cases": 0,
            "total_passed": 0,
            "total_failed": 0,
            "total_errors": 0,
            "total_skipped": 0,
            "total_duration": 0,
            "suites": []
        }
        
        start_time = time.time()
        
        for suite in self.suites:
            result = suite.run(verbose)
            summary["suites"].append(result)
            summary["total_cases"] += result["total"]
            summary["total_passed"] += result["passed"]
            summary["total_failed"] += result["failed"]
            summary["total_errors"] += result["errors"]
            summary["total_skipped"] += result["skipped"]
        
        summary["total_duration"] = round(time.time() - start_time, 3)
        return summary
    
    def save_report(self, summary: Dict, format: str = "json"):
        """保存报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            report_file = self.report_dir / f"test_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
        elif format == "html":
            report_file = self.report_dir / f"test_report_{timestamp}.html"
            with open(report_file, 'w') as f:
                f.write(self._generate_html(summary))
        elif format == "markdown":
            report_file = self.report_dir / f"test_report_{timestamp}.md"
            with open(report_file, 'w') as f:
                f.write(self._generate_markdown(summary))
        
        return report_file
    
    def _generate_html(self, summary: Dict) -> str:
        """生成HTML报告"""
        html = f"""<!DOCTYPE html>
<html>
<head><title>Test Report</title></head>
<body>
<h1>Test Report</h1>
<p>Timestamp: {summary['timestamp']}</p>
<p>Total: {summary['total_cases']} | 
Passed: <span style="color:green">{summary['total_passed']}</span> | 
Failed: <span style="color:red">{summary['total_failed']}</span> | 
Errors: <span style="color:orange">{summary['total_errors']}</span></p>
</body></html>"""
        return html
    
    def _generate_markdown(self, summary: Dict) -> str:
        """生成Markdown报告"""
        md = f"""# Test Report

**Timestamp**: {summary['timestamp']}

## Summary

| Metric | Value |
|--------|-------|
| Total Cases | {summary['total_cases']} |
| Passed | {summary['total_passed']} |
| Failed | {summary['total_failed']} |
| Errors | {summary['total_errors']} |
| Duration | {summary['total_duration']}s |

## Details

"""
        for suite in summary["suites"]:
            md += f"""### {suite['suite']}

| Test | Result | Duration |
|------|--------|----------|
"""
            for case in suite["cases"]:
                icon = "✅" if case["result"] == "pass" else "❌"
                md += f"| {case['name']} | {icon} {case['result']} | {case['duration']}s |\n"
        
        return md

# ==================== 内置测试用例 ====================

def create_phase1_tests():
    """创建Phase 1知识图谱测试"""
    suite = TestSuite("Phase 1: 知识图谱")
    
    # 确保脚本目录在path中
    sys.path.insert(0, str(TEST_DIR))
    
    def test_graph_builder_import():
        """测试图谱构建器导入"""
        import obsidian_graph_builder as gb
        assert hasattr(gb, 'scan_vault'), "scan_vault函数不存在"
    
    def test_link_discover_import():
        """测试链接发现器导入"""
        import obsidian_link_discover as ld
        assert hasattr(ld, 'scan_all_notes'), "scan_all_notes函数不存在"
    
    def test_semantic_analyzer_import():
        """测试语义分析器导入"""
        import obsidian_semantic_analyzer as sa
        assert hasattr(sa, 'analyze_note'), "analyze_note函数不存在"
    
    def test_graph_builder_function():
        """测试图谱构建器函数"""
        import obsidian_graph_builder as gb
        # 测试load_state函数存在
        assert callable(getattr(gb, 'load_state', None)), "load_state不是可调用函数"
    
    def test_link_discover_function():
        """测试链接发现器函数"""
        import obsidian_link_discover as ld
        # 测试load_state函数存在
        assert callable(getattr(ld, 'load_state', None)), "load_state不是可调用函数"
    
    def test_semantic_analyzer_function():
        """测试语义分析器函数"""
        import obsidian_semantic_analyzer as sa
        # 测试load_state函数存在
        assert callable(getattr(sa, 'load_state', None)), "load_state不是可调用函数"
    
    suite.add_test("graph_builder_import", test_graph_builder_import, "图谱构建器导入")
    suite.add_test("link_discover_import", test_link_discover_import, "链接发现器导入")
    suite.add_test("semantic_analyzer_import", test_semantic_analyzer_import, "语义分析器导入")
    suite.add_test("graph_builder_function", test_graph_builder_function, "图谱构建器函数")
    suite.add_test("link_discover_function", test_link_discover_function, "链接发现器函数")
    suite.add_test("semantic_analyzer_function", test_semantic_analyzer_function, "语义分析器函数")
    
    return suite

def create_phase2_tests():
    """创建Phase 2智能问答测试"""
    suite = TestSuite("Phase 2: 智能问答")
    
    # 确保脚本目录在path中
    sys.path.insert(0, str(TEST_DIR))
    
    def test_intent_parser_import():
        """测试意图解析器导入"""
        from qa_intent_parser import parse_intent
        assert parse_intent is not None
    
    def test_semantic_search_import():
        """测试语义搜索导入"""
        from qa_semantic_search import search_knowledge
        assert search_knowledge is not None
    
    def test_answer_generator_import():
        """测试答案生成器导入"""
        from qa_answer_generator import generate_answer
        assert generate_answer is not None
    
    def test_conversation_manager_import():
        """测试对话管理器导入"""
        from qa_conversation_manager import ConversationManager
        assert ConversationManager is not None
    
    def test_context_memory_import():
        """测试上下文记忆导入"""
        from qa_context_memory import ContextMemory
        assert ContextMemory is not None
    
    def test_multi_turn_import():
        """测试多轮对话导入"""
        from qa_multi_turn import MultiTurnHandler
        assert MultiTurnHandler is not None
    
    def test_integrate_import():
        """测试集成模块导入"""
        from qa_integrate import QAIntegrator
        assert QAIntegrator is not None
    
    suite.add_test("intent_parser_import", test_intent_parser_import, "意图解析器导入")
    suite.add_test("semantic_search_import", test_semantic_search_import, "语义搜索导入")
    suite.add_test("answer_generator_import", test_answer_generator_import, "答案生成器导入")
    suite.add_test("conversation_manager_import", test_conversation_manager_import, "对话管理器导入")
    suite.add_test("context_memory_import", test_context_memory_import, "上下文记忆导入")
    suite.add_test("multi_turn_import", test_multi_turn_import, "多轮对话导入")
    suite.add_test("integrate_import", test_integrate_import, "集成模块导入")
    
    return suite

# ==================== 主函数 ====================

def main():
    # 确保脚本目录在path中
    sys.path.insert(0, str(TEST_DIR))
    
    runner = TestRunner()
    
    # 添加测试套件
    runner.add_suite(create_phase1_tests())
    runner.add_suite(create_phase2_tests())
    
    # 解析参数
    if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        verbose = True
    else:
        verbose = False
    
    # 运行测试
    print("=" * 60)
    print("      Phase 1 & Phase 2 Automated Tests")
    print("=" * 60)
    print()
    
    summary = runner.run_all(verbose)
    
    # 打印摘要
    print()
    print("=" * 60)
    print("      Test Summary")
    print("=" * 60)
    print(f"Total: {summary['total_cases']}")
    print(f"Passed: {summary['total_passed']}")
    print(f"Failed: {summary['total_failed']}")
    print(f"Errors: {summary['total_errors']}")
    print(f"Duration: {summary['total_duration']}s")
    print()
    
    # 保存报告
    report_file = runner.save_report(summary, "markdown")
    print(f"Report saved: {report_file}")
    
    # 返回退出码
    sys.exit(0 if summary['total_failed'] == 0 and summary['total_errors'] == 0 else 1)

if __name__ == "__main__":
    main()
