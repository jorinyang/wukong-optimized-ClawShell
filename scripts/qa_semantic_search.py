#!/usr/bin/env python3
"""
QA Semantic Search - 语义搜索
功能：
1. 基于MemOS的语义搜索
2. 关键词+语义混合检索
3. 结果排序和去重
4. 来源追溯

依赖: MemOS API
"""

import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================

MEMOS_API = "https://memos.memtensor.cn/api/openmem/v1"
MEMOS_API_KEY = "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ"

VAULT_PATH = Path.home() / "Documents/Obsidian/OpenClaw"

# ==================== 搜索 ====================

def search_knowledge(query: str, intent: str = None, limit: int = 5) -> List[Dict]:
    """搜索知识库"""
    results = []
    
    # 1. 搜索Obsidian Vault
    vault_results = search_vault(query, limit)
    results.extend(vault_results)
    
    # 2. 搜索MemOS
    memos_results = search_memos(query, limit)
    results.extend(memos_results)
    
    # 3. 去重和排序
    results = deduplicate_and_rank(results, query)
    
    return results[:limit]

def search_vault(query: str, limit: int = 5) -> List[Dict]:
    """搜索Obsidian Vault"""
    results = []
    keywords = query.split()
    
    # 搜索目录
    search_dirs = ["1_Work", "2_Learn", "3_Research", "4_Life", "Other"]
    
    for dir_name in search_dirs:
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue
        
        for md_file in dir_path.rglob("*.md"):
            content = md_file.read_text(encoding='utf-8', errors='ignore')
            content_lower = content.lower()
            query_lower = query.lower()
            
            # 计算匹配度
            score = 0
            matched_terms = []
            
            # 精确短语匹配
            if query_lower in content_lower:
                score += 10
                matched_terms.append("精确匹配")
            
            # 关键词匹配
            for kw in keywords:
                if kw.lower() in content_lower:
                    score += 2
                    matched_terms.append(kw)
            
            # 标题匹配
            if any(kw.lower() in md_file.stem.lower() for kw in keywords):
                score += 5
                matched_terms.append("标题匹配")
            
            if score > 0:
                # 提取摘要
                summary = extract_summary(content, query, 200)
                
                results.append({
                    "title": md_file.stem,
                    "path": str(md_file.relative_to(VAULT_PATH)),
                    "type": "obsidian",
                    "score": score,
                    "summary": summary,
                    "url": f"obsidian://open?vault=OpenClaw&file={md_file.relative_to(VAULT_PATH)}"
                })
    
    return results

def search_memos(query: str, limit: int = 5) -> List[Dict]:
    """搜索MemOS"""
    results = []
    
    try:
        # 使用MemOS搜索接口
        response = requests.post(
            f"{MEMOS_API}/search",
            headers={
                "Authorization": f"Bearer {MEMOS_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"query": query, "limit": limit},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                items = data.get("data", [])
                for item in items:
                    results.append({
                        "title": item.get("title", "无标题"),
                        "content": item.get("content", "")[:200],
                        "type": "memos",
                        "score": item.get("relevance", 0.5),
                        "source": "MemOS",
                        "id": item.get("id")
                    })
    except Exception as e:
        print(f"⚠️ MemOS搜索失败: {e}")
    
    return results

def extract_summary(content: str, query: str, max_len: int = 200) -> str:
    """提取摘要"""
    # 移除markdown格式
    content = content.replace("#", "").replace("*", "").replace("[[", "").replace("]]", "")
    
    # 找到query的位置
    query_lower = query.lower()
    content_lower = content.lower()
    
    pos = content_lower.find(query_lower.split()[0] if query.split() else "")
    
    if pos == -1:
        pos = 0
    
    # 提取周围内容
    start = max(0, pos - 50)
    end = min(len(content), pos + max_len)
    
    summary = content[start:end].strip()
    
    if start > 0:
        summary = "..." + summary
    if end < len(content):
        summary = summary + "..."
    
    return summary

def deduplicate_and_rank(results: List[Dict], query: str) -> List[Dict]:
    """去重和排序"""
    # 按分数排序
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
    # 简单去重（基于标题）
    seen = set()
    unique_results = []
    
    for r in results:
        title = r.get("title", "")
        if title not in seen:
            seen.add(title)
            unique_results.append(r)
    
    return unique_results

def format_search_results(results: List[Dict], query: str) -> str:
    """格式化搜索结果"""
    if not results:
        return "未找到相关结果"
    
    output = f"**搜索**: {query}\n\n"
    output += f"**找到 {len(results)} 条相关结果**:\n\n"
    
    for i, r in enumerate(results, 1):
        output += f"{i}. **{r['title']}**"
        if r.get("type"):
            output += f" [{r['type']}]"
        output += f"\n"
        output += f"   {r.get('summary', r.get('content', ''))[:150]}...\n"
        if r.get("path"):
            output += f"   📁 {r['path']}\n"
        output += "\n"
    
    return output

# ==================== 测试 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("QA Semantic Search 测试")
    print("=" * 60)
    
    test_queries = [
        "OpenClaw 版本检测",
        "知识图谱",
        "N8N 工作流"
    ]
    
    for query in test_queries:
        print(f"\n搜索: {query}")
        print("-" * 40)
        results = search_knowledge(query)
        print(f"找到 {len(results)} 条结果")
        for r in results[:3]:
            print(f"  - {r['title']} (score: {r['score']})")
