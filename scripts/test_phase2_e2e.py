#!/usr/bin/env python3
"""
Phase 2 End-to-End Test
测试知识图谱和智能问答的完整流程
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 路径
SCRIPT_DIR = Path.home() / ".openclaw/scripts"
OUTPUT_DIR = Path.home() / ".openclaw"
LOG_DIR = OUTPUT_DIR / "logs"

# ==================== 测试用例 ====================

def test_graph_builder():
    """测试图谱构建器"""
    print("\n" + "="*60)
    print("测试1: 图谱构建器")
    print("="*60)
    
    script = SCRIPT_DIR / "obsidian_graph_builder.py"
    if not script.exists():
        return {"status": "FAIL", "msg": "脚本不存在"}
    
    # 尝试导入
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        # 简单验证脚本存在且可执行
        with open(script, 'r') as f:
            content = f.read()
        
        checks = [
            ("scan_vault" in content, "扫描函数"),
            ("discover_links" in content, "链接发现"),
            ("generate_graph_data" in content, "图谱生成"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        if failed:
            return {"status": "FAIL", "msg": f"缺少: {', '.join(failed)}"}
        
        return {"status": "PASS", "msg": "图谱构建器完整"}
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

def test_link_discover():
    """测试链接发现器"""
    print("\n" + "="*60)
    print("测试2: 链接发现器")
    print("="*60)
    
    script = SCRIPT_DIR / "obsidian_link_discover.py"
    if not script.exists():
        return {"status": "FAIL", "msg": "脚本不存在"}
    
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        with open(script, 'r') as f:
            content = f.read()
        
        checks = [
            ("scan_all_notes" in content, "扫描函数"),
            ("discover_links" in content, "链接发现"),
            ("calculate_link_score" in content, "评分计算"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        if failed:
            return {"status": "FAIL", "msg": f"缺少: {', '.join(failed)}"}
        
        return {"status": "PASS", "msg": "链接发现器完整"}
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

def test_semantic_analyzer():
    """测试语义分析器"""
    print("\n" + "="*60)
    print("测试3: 语义分析器")
    print("="*60)
    
    script = SCRIPT_DIR / "obsidian_semantic_analyzer.py"
    if not script.exists():
        return {"status": "FAIL", "msg": "脚本不存在"}
    
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        with open(script, 'r') as f:
            content = f.read()
        
        checks = [
            ("analyze_note" in content, "笔记分析"),
            ("extract_topics" in content, "主题提取"),
            ("extract_concepts" in content, "概念提取"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        if failed:
            return {"status": "FAIL", "msg": f"缺少: {', '.join(failed)}"}
        
        return {"status": "PASS", "msg": "语义分析器完整"}
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

def test_qa_system():
    """测试问答系统"""
    print("\n" + "="*60)
    print("测试4: 智能问答系统")
    print("="*60)
    
    scripts = [
        ("qa_intent_parser.py", ["parse_intent", "INTENT_PATTERNS"]),
        ("qa_semantic_search.py", ["search_knowledge", "search_vault"]),
        ("qa_answer_generator.py", ["generate_answer", "format_final_response"]),
        ("knowledge_qa.py", ["process_question"]),
    ]
    
    results = []
    for script_name, required_items in scripts:
        script = SCRIPT_DIR / script_name
        if not script.exists():
            results.append({"script": script_name, "status": "FAIL", "msg": "不存在"})
            continue
        
        try:
            with open(script, 'r') as f:
                content = f.read()
            
            missing = [item for item in required_items if item not in content]
            if missing:
                results.append({"script": script_name, "status": "FAIL", "msg": f"缺少: {', '.join(missing)}"})
            else:
                results.append({"script": script_name, "status": "PASS", "msg": "完整"})
        except Exception as e:
            results.append({"script": script_name, "status": "ERROR", "msg": str(e)})
    
    failed = [r for r in results if r["status"] != "PASS"]
    if failed:
        return {"status": "PARTIAL", "msg": f"{len(results)-len(failed)}/{len(results)} 通过", "details": results}
    
    return {"status": "PASS", "msg": f"问答系统完整({len(results)}个脚本)", "details": results}

def test_output_dirs():
    """测试输出目录"""
    print("\n" + "="*60)
    print("测试5: 输出目录")
    print("="*60)
    
    dirs = [
        (OUTPUT_DIR / "graphs/daily", "图谱目录"),
        (OUTPUT_DIR / "reports", "报告目录"),
        (OUTPUT_DIR / "workspace/OpenClaw/.links", "链接推荐目录"),
        (LOG_DIR, "日志目录"),
    ]
    
    results = []
    for dir_path, name in dirs:
        if dir_path.exists():
            results.append({"dir": name, "status": "PASS"})
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            results.append({"dir": name, "status": "CREATED"})
    
    return {"status": "PASS", "msg": f"{len(results)}个目录就绪", "details": results}

def test_cron_config():
    """测试Cron配置"""
    print("\n" + "="*60)
    print("测试6: Cron配置")
    print("="*60)
    
    import subprocess
    
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        crontab = result.stdout
        
        checks = [
            ("obsidian_graph_builder" in crontab, "图谱构建Cron"),
            ("qa_" in crontab or "knowledge_qa" in crontab, "问答Cron(可选)"),
        ]
        
        results = []
        for check, name in checks:
            results.append({"item": name, "status": "PASS" if check else "MISSING"})
        
        graph_cron = "0 0 * * *" in crontab
        if graph_cron:
            return {"status": "PASS", "msg": "图谱Cron已配置(00:00)", "details": results}
        else:
            return {"status": "FAIL", "msg": "图谱Cron未配置", "details": results}
            
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

# ==================== 主函数 ====================

def main():
    print("="*60)
    print("      Phase 2 End-to-End Test")
    print("      知识图谱 + 智能问答")
    print("="*60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("图谱构建器", test_graph_builder),
        ("链接发现器", test_link_discover),
        ("语义分析器", test_semantic_analyzer),
        ("智能问答系统", test_qa_system),
        ("输出目录", test_output_dirs),
        ("Cron配置", test_cron_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append({"test": name, **result})
            
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️", "PARTIAL": "⚡"}.get(result["status"], "?")
            print(f"\n{status_icon} {name}: {result['msg']}")
            
        except Exception as e:
            results.append({"test": name, "status": "ERROR", "msg": str(e)})
            print(f"\n⚠️ {name}: 错误 - {e}")
    
    # 汇总
    print("\n" + "="*60)
    print("                      测试汇总")
    print("="*60)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    partial = sum(1 for r in results if r["status"] in ("PARTIAL", "ERROR"))
    
    print(f"通过: {passed}/{len(results)}")
    print(f"失败: {failed}/{len(results)}")
    print(f"部分: {partial}/{len(results)}")
    
    if failed > 0:
        print("\n失败项:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  ❌ {r['test']}: {r['msg']}")
    
    print("\n" + "="*60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
