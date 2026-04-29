#!/usr/bin/env python3
"""
Test Library - 测试用例库
功能：
1. 预定义测试用例
2. 测试用例分类
3. 测试数据管理
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# ==================== 配置 ====================

TEST_DATA_DIR = Path.home() / ".openclaw/test_data"
CASE_LIBRARY_FILE = TEST_DATA_DIR / "test_cases.json"

# ==================== 测试用例库 ====================

class TestCaseLibrary:
    def __init__(self):
        self.categories = {}
        self.load_library()
    
    def load_library(self):
        """加载测试用例库"""
        if CASE_LIBRARY_FILE.exists():
            with open(CASE_LIBRARY_FILE, 'r') as f:
                self.categories = json.load(f)
        else:
            self.categories = self._get_default_categories()
    
    def save_library(self):
        """保存测试用例库"""
        TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CASE_LIBRARY_FILE, 'w') as f:
            json.dump(self.categories, f, ensure_ascii=False, indent=2)
    
    def _get_default_categories(self) -> Dict:
        """获取默认分类"""
        return {
            "phase1_knowledge_graph": {
                "name": "Phase 1: 知识图谱",
                "cases": [
                    {
                        "id": "P1-KG-001",
                        "name": "图谱构建器导入测试",
                        "module": "obsidian_graph_builder",
                        "method": "test_import",
                        "description": "验证GraphBuilder类可正常导入"
                    },
                    {
                        "id": "P1-KG-002",
                        "name": "链接发现器导入测试",
                        "module": "obsidian_link_discover",
                        "method": "test_import",
                        "description": "验证LinkDiscover类可正常导入"
                    },
                    {
                        "id": "P1-KG-003",
                        "name": "语义分析器导入测试",
                        "module": "obsidian_semantic_analyzer",
                        "method": "test_import",
                        "description": "验证SemanticAnalyzer类可正常导入"
                    }
                ]
            },
            "phase2_intelligent_qa": {
                "name": "Phase 2: 智能问答",
                "cases": [
                    {
                        "id": "P2-QA-001",
                        "name": "意图解析器导入测试",
                        "module": "qa_intent_parser",
                        "method": "test_import",
                        "description": "验证parse_intent函数可正常导入"
                    },
                    {
                        "id": "P2-QA-002",
                        "name": "语义搜索导入测试",
                        "module": "qa_semantic_search",
                        "method": "test_import",
                        "description": "验证search_knowledge函数可正常导入"
                    },
                    {
                        "id": "P2-QA-003",
                        "name": "答案生成器导入测试",
                        "module": "qa_answer_generator",
                        "method": "test_import",
                        "description": "验证generate_answer函数可正常导入"
                    },
                    {
                        "id": "P2-QA-004",
                        "name": "对话管理器导入测试",
                        "module": "qa_conversation_manager",
                        "method": "test_import",
                        "description": "验证ConversationManager类可正常导入"
                    },
                    {
                        "id": "P2-QA-005",
                        "name": "上下文记忆导入测试",
                        "module": "qa_context_memory",
                        "method": "test_import",
                        "description": "验证ContextMemory类可正常导入"
                    }
                ]
            },
            "integration": {
                "name": "集成测试",
                "cases": [
                    {
                        "id": "INT-001",
                        "name": "QA系统诊断测试",
                        "module": "qa_integrate",
                        "method": "diagnose",
                        "description": "验证QA系统所有模块正常加载"
                    },
                    {
                        "id": "INT-002",
                        "name": "多轮对话测试",
                        "module": "qa_multi_turn",
                        "method": "test_conversation",
                        "description": "验证多轮对话功能正常"
                    }
                ]
            }
        }
    
    def get_cases(self, category: str = None) -> List[Dict]:
        """获取测试用例"""
        if category is None:
            all_cases = []
            for cat_cases in self.categories.values():
                all_cases.extend(cat_cases.get("cases", []))
            return all_cases
        elif category in self.categories:
            return self.categories[category].get("cases", [])
        else:
            return []
    
    def get_case(self, case_id: str) -> Dict:
        """获取单个测试用例"""
        for category in self.categories.values():
            for case in category.get("cases", []):
                if case["id"] == case_id:
                    return case
        return None
    
    def add_case(self, category: str, case: Dict) -> bool:
        """添加测试用例"""
        if category not in self.categories:
            self.categories[category] = {"name": category, "cases": []}
        
        self.categories[category]["cases"].append(case)
        self.save_library()
        return True
    
    def remove_case(self, case_id: str) -> bool:
        """移除测试用例"""
        for category in self.categories.values():
            cases = category.get("cases", [])
            for i, case in enumerate(cases):
                if case["id"] == case_id:
                    cases.pop(i)
                    self.save_library()
                    return True
        return False
    
    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(self.categories.keys())
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = 0
        by_category = {}
        
        for cat_key, category in self.categories.items():
            count = len(category.get("cases", []))
            total += count
            by_category[category["name"]] = count
        
        return {
            "total": total,
            "by_category": by_category
        }

# ==================== 主函数 ====================

def main():
    library = TestCaseLibrary()
    
    if len(sys.argv) < 2:
        # 显示统计
        stats = library.get_statistics()
        print("=" * 60)
        print("      Test Case Library")
        print("=" * 60)
        print(f"\nTotal Cases: {stats['total']}")
        print("\nBy Category:")
        for name, count in stats["by_category"].items():
            print(f"  {name}: {count}")
        print()
        
        # 显示所有用例
        print("Test Cases:")
        for case in library.get_cases():
            print(f"  [{case['id']}] {case['name']}")
            print(f"    {case['description']}")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        for case in library.get_cases():
            print(f"[{case['id']}] {case['name']}")
    
    elif command == "get":
        case_id = sys.argv[2] if len(sys.argv) > 2 else ""
        case = library.get_case(case_id)
        if case:
            print(json.dumps(case, indent=2, ensure_ascii=False))
        else:
            print(f"Case not found: {case_id}")
    
    elif command == "add":
        # 添加用例需要更多参数，简化处理
        print("Use: test_library.py add <category> <case_json>")
    
    elif command == "stats":
        stats = library.get_statistics()
        print(json.dumps(stats, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        print("Usage:")
        print("  test_library.py list")
        print("  test_library.py get <case_id>")
        print("  test_library.py stats")

if __name__ == "__main__":
    main()
