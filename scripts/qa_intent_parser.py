#!/usr/bin/env python3
"""
QA Intent Parser - 问答意图解析器
功能：
1. 解析用户问题
2. 识别意图类型
3. 提取关键实体
4. 生成检索query

触发: Webhook实时调用
"""

import re
import json
from typing import Dict, List, Optional
from datetime import datetime

# ==================== 意图类型 ====================

INTENT_PATTERNS = {
    "知识查询": [
        r"什么是", r"是什么", r"哪个是", r"请问",
        r"我想了解", r"想知道", r"查一下", r"找一下"
    ],
    "操作指引": [
        r"怎么", r"如何", r"怎样", r"要怎么做",
        r"步骤", r"方法", r"教程", r"指南"
    ],
    "原因解释": [
        r"为什么", r"为啥", r"什么原因",
        r"为什么回", r"怎么会"
    ],
    "对比分析": [
        r"区别", r"比较", r"对比", r"差异",
        r"哪个好", r"有什么不同"
    ],
    "状态查询": [
        r"状态", r"进度", r"情况", r"怎么样了",
        r"完成了吗", r"进行到哪了"
    ],
    "计划咨询": [
        r"计划", r"安排", r"打算", r"目标",
        r"什么时候", r"哪天"
    ],
    "推荐请求": [
        r"推荐", r"建议", r"有什么好",
        r"介绍一下", r"分享"
    ]
}

# ==================== 实体提取 ====================

ENTITY_PATTERNS = {
    "技术栈": r"(Python|JavaScript|Go|Rust|Node|Python3|Shell|Bash)",
    "工具": r"(Obsidian|OpenClaw|N8N|Hermes|MemOS|VSCode)",
    "时间": r"(\d+年|\d+月|\d+日|\d+点|\d+时|今天|明天|昨天|本周|本月)",
    "人物": r"@(\w+)",
    "项目": r"项目[名称]?[:：]?(\w+)"
}

# ==================== 意图解析 ====================

def parse_intent(question: str) -> Dict:
    """解析用户意图"""
    question = question.strip()
    scores = {}
    
    # 计算各意图得分
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, question):
                score += 1
        scores[intent] = score
    
    # 找出最高分意图
    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        primary_intent = "一般查询"
    else:
        primary_intent = max(scores, key=scores.get)
    
    # 提取实体
    entities = extract_entities(question)
    
    # 生成检索query
    search_query = generate_search_query(question, primary_intent, entities)
    
    return {
        "question": question,
        "primary_intent": primary_intent,
        "intent_scores": scores,
        "entities": entities,
        "search_query": search_query,
        "timestamp": datetime.now().isoformat()
    }

def extract_entities(question: str) -> Dict[str, List[str]]:
    """提取实体"""
    entities = {}
    
    for entity_type, pattern in ENTITY_PATTERNS.items():
        matches = re.findall(pattern, question, re.IGNORECASE)
        if matches:
            entities[entity_type] = list(set(matches))
    
    return entities

def generate_search_query(question: str, intent: str, entities: Dict) -> str:
    """生成检索query"""
    # 移除问号和语气词
    query = question
    query = re.sub(r'[？?。!！]', '', query)
    query = re.sub(r'请问|我想知道|查一下', '', query)
    query = query.strip()
    
    # 添加实体关键词
    if entities:
        entity_keywords = []
        for entity_list in entities.values():
            entity_keywords.extend(entity_list)
        if entity_keywords:
            query = query + ' ' + ' '.join(entity_keywords[:3])
    
    return query

def format_intent_report(parsed: Dict) -> str:
    """格式化意图报告"""
    report = f"""**问题**: {parsed['question']}

**识别意图**: {parsed['primary_intent']}

**意图得分**:
"""
    for intent, score in sorted(parsed['intent_scores'].items(), key=lambda x: x[1], reverse=True):
        if score > 0:
            report += f"- {intent}: {score}\n"
    
    if parsed['entities']:
        report += f"\n**提取实体**:\n"
        for entity_type, values in parsed['entities'].items():
            report += f"- {entity_type}: {', '.join(values)}\n"
    
    report += f"\n**检索query**: {parsed['search_query']}"
    
    return report

# ==================== 测试 ====================

if __name__ == "__main__":
    test_questions = [
        "什么是OpenClaw的版本感知系统？",
        "Python怎么连接MemOS？",
        "为什么我的N8N服务会中断？",
        "OpenClaw和N8N有什么区别？",
        "知识图谱的计划是什么？"
    ]
    
    print("=" * 60)
    print("QA Intent Parser 测试")
    print("=" * 60)
    
    for q in test_questions:
        result = parse_intent(q)
        print(f"\n问题: {q}")
        print(f"意图: {result['primary_intent']}")
        print(f"检索: {result['search_query']}")
        print("-" * 40)
