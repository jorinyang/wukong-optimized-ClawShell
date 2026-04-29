#!/usr/bin/env python3
"""
QA Answer Generator - 答案生成器
功能：
1. 基于搜索结果生成答案
2. 多源汇总
3. 引用追溯
4. 格式优化

依赖: qa_semantic_search.py
"""

import json
from typing import Dict, List, Optional
from datetime import datetime

# ==================== 答案生成 ====================

def generate_answer(question: str, intent: str, search_results: List[Dict]) -> Dict:
    """生成答案"""
    if not search_results:
        return {
            "answer": f"抱歉，我在知识库中未找到与「{question}」相关的内容。",
            "sources": [],
            "confidence": 0.0,
            "needs_more_info": True
        }
    
    # 根据意图选择不同的生成策略
    if intent == "知识查询":
        return generate_knowledge_answer(question, search_results)
    elif intent == "操作指引":
        return generate_guide_answer(question, search_results)
    elif intent == "原因解释":
        return generate_explanation_answer(question, search_results)
    elif intent == "对比分析":
        return generate_comparison_answer(question, search_results)
    else:
        return generate_general_answer(question, search_results)

def generate_knowledge_answer(question: str, results: List[Dict]) -> Dict:
    """生成知识查询答案"""
    top_result = results[0]
    
    answer = f"关于「{question}」，我在知识库中找到以下内容：\n\n"
    answer += f"**{top_result['title']}**\n\n"
    answer += f"{top_result.get('summary', top_result.get('content', ''))}\n\n"
    
    if len(results) > 1:
        answer += "**相关补充**:\n"
        for r in results[1:3]:
            answer += f"- [[{r['title']}]]"
            if r.get('path'):
                answer += f" ({r['path']})"
            answer += "\n"
    
    sources = [format_source(r) for r in results[:3]]
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": min(0.95, top_result.get('score', 0.5) / 10 + 0.5),
        "needs_more_info": False
    }

def generate_guide_answer(question: str, results: List[Dict]) -> Dict:
    """生成操作指引答案"""
    answer = f"关于「{question}」，以下是操作步骤：\n\n"
    
    for i, r in enumerate(results[:3], 1):
        answer += f"### 方案 {i}: {r['title']}\n\n"
        answer += f"{r.get('summary', r.get('content', ''))}\n\n"
        if r.get('path'):
            answer += f"📁 详细文档: {r['path']}\n\n"
    
    sources = [format_source(r) for r in results[:3]]
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": 0.85,
        "needs_more_info": False
    }

def generate_explanation_answer(question: str, results: List[Dict]) -> Dict:
    """生成原因解释答案"""
    answer = f"关于「{question}」，可能的原因包括：\n\n"
    
    for r in results[:3]:
        answer += f"**{r['title']}**\n"
        answer += f"{r.get('summary', r.get('content', ''))[:200]}...\n\n"
    
    sources = [format_source(r) for r in results[:3]]
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": 0.80,
        "needs_more_info": True
    }

def generate_comparison_answer(question: str, results: List[Dict]) -> Dict:
    """生成对比分析答案"""
    answer = f"关于「{question}」，以下是对比分析：\n\n"
    
    # 尝试构建对比表格
    if len(results) >= 2:
        answer += "| 方面 | "
        for r in results[:2]:
            answer += f"{r['title']} | "
        answer += "\n|-------|"
        for _ in results[:2]:
            answer += "-------|"
        answer += "\n"
        
        for r in results[:2]:
            content = r.get('summary', r.get('content', ''))[:100]
            answer += f"| {content}..."
    
    sources = [format_source(r) for r in results[:3]]
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": 0.75,
        "needs_more_info": True
    }

def generate_general_answer(question: str, results: List[Dict]) -> Dict:
    """生成一般答案"""
    answer = f"关于「{question}」，找到以下相关结果：\n\n"
    
    for i, r in enumerate(results[:5], 1):
        answer += f"{i}. **[[{r['title']}]]**"
        if r.get('path'):
            answer += f"\n   📁 {r['path']}"
        if r.get('summary'):
            answer += f"\n   {r['summary'][:100]}..."
        answer += "\n\n"
    
    sources = [format_source(r) for r in results[:5]]
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": 0.70,
        "needs_more_info": False
    }

def format_source(r: Dict) -> Dict:
    """格式化来源信息"""
    return {
        "title": r.get("title", ""),
        "type": r.get("type", "unknown"),
        "path": r.get("path", r.get("source", "")),
        "url": r.get("url", "")
    }

def format_final_response(qa_result: Dict, question: str) -> str:
    """格式化最终回复"""
    answer = qa_result["answer"]
    sources = qa_result["sources"]
    confidence = qa_result["confidence"]
    
    response = f"{answer}\n"
    
    if sources:
        response += "\n---\n**参考资料**:\n"
        for s in sources[:3]:
            if s["type"] == "obsidian":
                response += f"📄 [[{s['title']}]] ({s['path']})\n"
            else:
                response += f"💾 {s['title']} ({s['type']})\n"
    
    response += f"\n---\n*🤖 置信度: {confidence:.0%} | {datetime.now().strftime('%H:%M')}*"
    
    return response

# ==================== 测试 ====================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = [
        {
            "title": "OpenClaw版本感知系统",
            "path": "版本感知系统/OPENCLAW_VERSION_SENSE_SYSTEM.md",
            "type": "obsidian",
            "score": 8.5,
            "summary": "版本感知系统用于检测OpenClaw及其依赖的版本变化，包括..."
        },
        {
            "title": "版本检测脚本",
            "path": "scripts/openclaw_version_monitor.py",
            "type": "obsidian",
            "score": 6.0,
            "summary": "openclaw_version_monitor.py 负责检测7项依赖版本..."
        }
    ]
    
    print("=" * 60)
    print("QA Answer Generator 测试")
    print("=" * 60)
    
    question = "什么是版本感知系统？"
    result = generate_answer(question, "知识查询", test_results)
    
    print(f"\n问题: {question}")
    print(f"\n答案:\n{result['answer']}")
    print(f"\n置信度: {result['confidence']:.0%}")
    print(f"来源数: {len(result['sources'])}")
