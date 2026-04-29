#!/usr/bin/env python3
"""
Test Reporter - 测试报告生成器
功能：
1. 收集测试结果
2. 生成格式化报告
3. 支持多种格式(json/markdown/html)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# ==================== 配置 ====================

REPORT_DIR = Path.home() / ".openclaw/reports"
ARCHIVE_DIR = REPORT_DIR / "archive"

# ==================== 报告生成器 ====================

class TestReporter:
    def __init__(self):
        self.report_dir = REPORT_DIR
        self.archive_dir = ARCHIVE_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_summary(self, test_results: List[Dict]) -> Dict:
        """生成测试摘要"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_runs": len(test_results),
            "total_cases": 0,
            "total_passed": 0,
            "total_failed": 0,
            "total_errors": 0,
            "pass_rate": 0.0,
            "runs": []
        }
        
        for result in test_results:
            summary["total_cases"] += result.get("total_cases", 0)
            summary["total_passed"] += result.get("passed", 0)
            summary["total_failed"] += result.get("failed", 0)
            summary["total_errors"] += result.get("errors", 0)
            summary["runs"].append({
                "timestamp": result.get("timestamp", ""),
                "suite": result.get("suite", "unknown"),
                "passed": result.get("passed", 0),
                "failed": result.get("failed", 0)
            })
        
        if summary["total_cases"] > 0:
            summary["pass_rate"] = round(
                summary["total_passed"] / summary["total_cases"] * 100, 2
            )
        
        return summary
    
    def generate_markdown(self, summary: Dict, detailed_results: List[Dict] = None) -> str:
        """生成Markdown报告"""
        md = f"""# Test Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Cases | {summary['total_cases']} |
| Passed | {summary['total_passed']} |
| Failed | {summary['total_failed']} |
| Errors | {summary['total_errors']} |
| Pass Rate | {summary['pass_rate']}% |

## Test Runs

| Timestamp | Suite | Passed | Failed |
|-----------|-------|--------|--------|
"""
        
        for run in summary.get("runs", []):
            md += f"| {run['timestamp'][:19]} | {run['suite']} | {run['passed']} | {run['failed']} |\n"
        
        if detailed_results:
            md += "\n## Detailed Results\n"
            for result in detailed_results:
                md += f"\n### {result.get('suite', 'Unknown Suite')}\n\n"
                for case in result.get("cases", []):
                    icon = "✅" if case["result"] == "pass" else "❌"
                    status = "PASS" if case["result"] == "pass" else case["result"].upper()
                    md += f"- {icon} **{case['name']}** - {status}\n"
                    if case.get("message"):
                        md += f"  - {case['message']}\n"
        
        return md
    
    def generate_html(self, summary: Dict, detailed_results: List[Dict] = None) -> str:
        """生成HTML报告"""
        pass_color = "#4CAF50"
        fail_color = "#f44336"
        error_color = "#FF9800"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; }}
        .metric-label {{ color: #666; }}
        .pass {{ color: {pass_color}; }}
        .fail {{ color: {fail_color}; }}
        .error {{ color: {error_color}; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>📊 Test Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <div class="metric">
            <div class="metric-value">{summary['total_cases']}</div>
            <div class="metric-label">Total Cases</div>
        </div>
        <div class="metric">
            <div class="metric-value pass">{summary['total_passed']}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric">
            <div class="metric-value fail">{summary['total_failed']}</div>
            <div class="metric-label">Failed</div>
        </div>
        <div class="metric">
            <div class="metric-value error">{summary['total_errors']}</div>
            <div class="metric-label">Errors</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['pass_rate']}%</div>
            <div class="metric-label">Pass Rate</div>
        </div>
    </div>
    
    <h2>Test Runs</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Suite</th>
            <th>Passed</th>
            <th>Failed</th>
        </tr>
"""
        
        for run in summary.get("runs", []):
            html += f"""        <tr>
            <td>{run['timestamp'][:19]}</td>
            <td>{run['suite']}</td>
            <td class="pass">{run['passed']}</td>
            <td class="fail">{run['failed']}</td>
        </tr>
"""
        
        html += """    </table>
</body>
</html>"""
        
        return html
    
    def save_report(self, summary: Dict, detailed_results: List[Dict] = None, format: str = "markdown"):
        """保存报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "markdown":
            content = self.generate_markdown(summary, detailed_results)
            report_file = self.report_dir / f"test_report_{timestamp}.md"
        elif format == "html":
            content = self.generate_html(summary, detailed_results)
            report_file = self.report_dir / f"test_report_{timestamp}.html"
        elif format == "json":
            content = json.dumps({"summary": summary, "details": detailed_results}, indent=2, ensure_ascii=False)
            report_file = self.report_dir / f"test_report_{timestamp}.json"
        else:
            return None
        
        with open(report_file, 'w') as f:
            f.write(content)
        
        return report_file
    
    def archive_old_reports(self, days: int = 7):
        """归档旧报告"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        for report_file in self.report_dir.glob("test_report_*"):
            if report_file.stat().st_mtime < cutoff:
                archive_file = self.archive_dir / report_file.name
                report_file.rename(archive_file)
                print(f"Archived: {archive_file}")

# ==================== 主函数 ====================

def main():
    reporter = TestReporter()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  test_reporter.py summary <json_file>")
        print("  test_reporter.py generate <result_json> [markdown|html|json]")
        print("  test_reporter.py archive [days]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "summary":
        # 读取测试结果文件
        result_file = sys.argv[2] if len(sys.argv) > 2 else ""
        if not result_file or not os.path.exists(result_file):
            print(f"File not found: {result_file}")
            sys.exit(1)
        
        with open(result_file, 'r') as f:
            results = json.load(f)
        
        if isinstance(results, list):
            summary = reporter.generate_summary(results)
        else:
            summary = reporter.generate_summary([results])
        
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    elif command == "generate":
        result_file = sys.argv[2] if len(sys.argv) > 2 else ""
        format_type = sys.argv[3] if len(sys.argv) > 3 else "markdown"
        
        if not result_file or not os.path.exists(result_file):
            print(f"File not found: {result_file}")
            sys.exit(1)
        
        with open(result_file, 'r') as f:
            results = json.load(f)
        
        if isinstance(results, list):
            summary = reporter.generate_summary(results)
            report_file = reporter.save_report(summary, results, format_type)
        else:
            summary = reporter.generate_summary([results])
            report_file = reporter.save_report(summary, [results], format_type)
        
        print(f"Report saved: {report_file}")
    
    elif command == "archive":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        reporter.archive_old_reports(days)
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
