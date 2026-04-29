#!/usr/bin/env python3
"""
Document Organizer - 文档整理器
功能：
1. 检查文档完整性
2. 更新交叉引用
3. 验证文档结构
"""

import os
import re
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================

VAULT_PATH = Path.home() / "Documents/Obsidian/OpenClaw"
OUTPUT_DIR = VAULT_PATH / "Research/Output"
UPDATE_DIR = VAULT_PATH / "Other/Update"

# ==================== 文档检查 ====================

def check_output_docs():
    """检查输出文档"""
    categories = [
        "系统架构与规范",
        "自动化执行",
        "知识管理",
        "研究与规划"
    ]
    
    results = []
    for cat in categories:
        cat_dir = OUTPUT_DIR / cat
        if not cat_dir.exists():
            results.append({"category": cat, "status": "missing", "files": 0})
            continue
        
        files = list(cat_dir.rglob("*.md"))
        results.append({
            "category": cat,
            "status": "ok",
            "files": len(files),
            "path": str(cat_dir)
        })
    
    return results

def check_update_docs():
    """检查更新文档"""
    results = {
        "main_index": False,
        "system_arch": False,
        "monthly_index": False,
        "update_files": 0
    }
    
    # 主索引
    if (UPDATE_DIR / "README.md").exists():
        results["main_index"] = True
    
    # 系统架构
    if (UPDATE_DIR / "00-SYSTEM_ARCHITECTURE.md").exists():
        results["system_arch"] = True
    
    # 月度索引
    monthly_dir = UPDATE_DIR / "202604"
    if monthly_dir.exists():
        monthly_index = monthly_dir / "README.md"
        if monthly_index.exists():
            results["monthly_index"] = True
        results["update_files"] = len(list(monthly_dir.glob("*.md"))) - 1  # 减去README
    
    return results

def verify_doc_structure(doc_path):
    """验证文档结构"""
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "has_title": bool(re.search(r'^#\s+', content, re.MULTILINE)),
        "has_version": bool(re.search(r'>\s*版本', content)),
        "has_date": bool(re.search(r'>\s*日期', content)),
        "has_sections": content.count('\n## ') >= 3
    }
    
    return checks

def main():
    print("=" * 60)
    print("      Document Organizer")
    print("=" * 60)
    
    # 检查输出文档
    print("\n📁 输出文档检查:")
    docs = check_output_docs()
    for doc in docs:
        icon = "✅" if doc["status"] == "ok" else "❌"
        print(f"   {icon} {doc['category']}: {doc['files']} 个文件")
    
    # 检查更新文档
    print("\n📝 更新文档检查:")
    updates = check_update_docs()
    print(f"   {'✅' if updates['main_index'] else '❌'} 主索引 (README.md)")
    print(f"   {'✅' if updates['system_arch'] else '❌'} 系统架构 (00-SYSTEM_ARCHITECTURE.md)")
    print(f"   {'✅' if updates['monthly_index'] else '❌'} 月度索引 (202604/README.md)")
    print(f"   📄 更新文件: {updates['update_files']} 个")
    
    # 验证系统架构文档
    print("\n🔍 系统架构文档验证:")
    arch_path = UPDATE_DIR / "00-SYSTEM_ARCHITECTURE.md"
    if arch_path.exists():
        checks = verify_doc_structure(arch_path)
        for check, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"   {icon} {check}")
        
        # 文件大小
        size = arch_path.stat().st_size
        print(f"   📊 文档大小: {size / 1024:.1f} KB")
    
    print("\n" + "=" * 60)
    print("      文档检查完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
