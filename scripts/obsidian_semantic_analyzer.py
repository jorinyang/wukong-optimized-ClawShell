#!/usr/bin/env python3
"""
Obsidian Semantic Analyzer - 语义分析器
功能：
1. 分析笔记内容的语义
2. 提取主题和概念
3. 构建语义关系
4. 生成分析报告

触发: obsidian_graph_builder.py 调用 或 独立运行
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter
from datetime import datetime

# ==================== 配置 ====================

VAULT_PATH = Path.home() / "Documents/Obsidian/OpenClaw"
OUTPUT_DIR = Path.home() / ".openclaw/reports"
STATE_FILE = Path.home() / ".openclaw/.semantic_analyzer_state.json"

# 扫描范围
SCAN_DIRS = ["1_Work", "2_Learn", "3_Research", "4_Life", "Other"]

# ==================== 状态管理 ====================

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_scan": None, "topics": {}, "concepts": []}

def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ==================== 核心功能 ====================

def analyze_note(content: str, title: str) -> dict:
    """分析单篇笔记"""
    # 提取标题
    headings = re.findall(r'^#{1,6}\s+(.+?)$', content, re.MULTILINE)
    
    # 提取标签
    tags = re.findall(r'#([a-zA-Z0-9_/-]+)', content)
    tags = [t.lower() for t in tags]
    
    # 提取wikilink
    links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
    
    # 清理内容
    text = re.sub(r'[#*`\[\]()]', ' ', content)
    text = re.sub(r'https?://\S+', '', text)
    
    # 提取中文词
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,5}', text)
    
    # 提取英文词
    english_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    
    # 计算词频
    word_freq = Counter(chinese_words + english_words)
    
    # 去除停用词
    stopwords = {
        '的', '了', '和', '与', '在', '是', '我', '你', '他', '她', '它', '这', '那', '有',
        '也', '就', '都', '而', '及', '与', '或', '但', '却', '因为', '所以', '如果',
        'the', 'and', 'is', 'are', 'was', 'were', 'this', 'that', 'for', 'not', 'with',
        'as', 'on', 'at', 'by', 'from', 'or', 'an', 'be', 'has', 'have', 'had', 'will',
        'would', 'could', 'should', 'may', 'can', 'what', 'when', 'where', 'which', 'who'
    }
    for sw in stopwords:
        del word_freq[sw]
    
    return {
        'title': title,
        'headings': headings,
        'tags': tags,
        'links': links,
        'word_freq': dict(word_freq.most_common(20)),
        'word_count': len(text.split()),
        'char_count': len(text)
    }

def scan_vault() -> List[dict]:
    """扫描Vault"""
    notes = []
    
    for dir_name in SCAN_DIRS:
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue
        
        for md_file in dir_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                analysis = analyze_note(content, md_file.stem)
                analysis['path'] = str(md_file.relative_to(VAULT_PATH))
                analysis['dir'] = dir_name
                notes.append(analysis)
            except Exception as e:
                print(f"⚠️ 分析失败: {md_file.name} - {e}")
    
    return notes

def extract_topics(notes: List[dict]) -> Dict[str, List[dict]]:
    """提取主题"""
    topics = {}
    
    for note in notes:
        for tag in note['tags']:
            if tag not in topics:
                topics[tag] = []
            topics[tag].append({
                'title': note['title'],
                'path': note['path'],
                'relevance': note['tags'].count(tag) / max(len(note['tags']), 1)
            })
    
    return topics

def extract_concepts(notes: List[dict], top_n: int = 50) -> List[dict]:
    """提取核心概念"""
    all_words = Counter()
    
    for note in notes:
        for word, freq in note['word_freq'].items():
            if len(word) >= 2:
                all_words[word] += freq
    
    top_concepts = all_words.most_common(top_n)
    
    concepts = []
    for word, freq in top_concepts:
        # 找到包含这个概念的笔记
        related = []
        for note in notes:
            if word in note['word_freq']:
                related.append({
                    'title': note['title'],
                    'path': note['path'],
                    'freq': note['word_freq'].get(word, 0)
                })
        
        concepts.append({
            'concept': word,
            'total_freq': freq,
            'related_notes': len(related),
            'top_related': sorted(related, key=lambda x: x['freq'], reverse=True)[:5]
        })
    
    return concepts

def generate_report(notes: List[dict], topics: Dict, concepts: List[dict]) -> str:
    """生成分析报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    report = f"""# 语义分析报告

**生成时间**: {today}
**分析笔记**: {len(notes)} 篇

---

## 核心指标

| 指标 | 值 |
|------|-----|
| 笔记总数 | {len(notes)} |
| 发现主题 | {len(topics)} 个 |
| 核心概念 | {len(concepts)} 个 |
| 总词数 | {sum(n['word_count'] for n in notes)} |
| 平均长度 | {sum(n['word_count'] for n in notes) // max(len(notes), 1)} 字 |

---

## 热门主题 TOP 20

| 主题 | 笔记数 | 代表笔记 |
|------|--------|---------|
"""
    
    # 按笔记数排序主题
    sorted_topics = sorted(topics.items(), key=lambda x: len(x[1]), reverse=True)
    for tag, related_notes in sorted_topics[:20]:
        top_note = related_notes[0]['title'] if related_notes else '-'
        report += f"| #{tag} | {len(related_notes)} | [[{top_note}]] |\n"
    
    report += f"""

## 核心概念 TOP 30

| 概念 | 频次 | 相关笔记数 |
|------|------|-----------|
"""
    
    for concept in concepts[:30]:
        report += f"| {concept['concept']} | {concept['total_freq']} | {concept['related_notes']} |\n"
    
    report += f"""

## 概念详情 (TOP 10)

"""
    
    for concept in concepts[:10]:
        report += f"""### {concept['concept']} ({concept['total_freq']}次)

相关笔记:
"""
        for note in concept['top_related'][:5]:
            report += f"- [[{note['title']}]] ({note['freq']}次)\n"
        report += "\n"
    
    report += f"""---

## 目录分布

| 目录 | 笔记数 | 占比 |
|------|--------|------|
"""
    
    dir_counts = Counter(n['dir'] for n in notes)
    for dir_name, count in dir_counts.most_common():
        pct = count / max(len(notes), 1) * 100
        report += f"| {dir_name} | {count} | {pct:.1f}% |\n"
    
    report += """

---

*由 OpenClaw 语义分析器自动生成*
"""
    
    return report

def main():
    """主函数"""
    print(f"[Semantic Analyzer] 语义分析器启动... {datetime.now().strftime('%H:%M:%S')}")
    
    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载状态
    state = load_state()
    
    # 扫描笔记
    print(f"📂 扫描Vault...")
    notes = scan_vault()
    print(f"   分析 {len(notes)} 篇笔记")
    
    # 提取主题
    print(f"📊 提取主题...")
    topics = extract_topics(notes)
    print(f"   发现 {len(topics)} 个主题")
    
    # 提取概念
    print(f"🧠 提取概念...")
    concepts = extract_concepts(notes, top_n=100)
    print(f"   提取 {len(concepts)} 个核心概念")
    
    # 生成报告
    print(f"📝 生成报告...")
    report = generate_report(notes, topics, concepts)
    
    today = datetime.now().strftime("%Y%m%d")
    report_file = OUTPUT_DIR / f"semantic_{today}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   已保存: {report_file.name}")
    
    # 保存数据
    data_file = OUTPUT_DIR / f"semantic_{today}.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'notes_count': len(notes),
            'topics_count': len(topics),
            'concepts_count': len(concepts),
            'topics': {k: len(v) for k, v in topics.items()},
            'top_concepts': concepts[:50]
        }, f, ensure_ascii=False, indent=2)
    
    # 更新状态
    state['last_scan'] = datetime.now().isoformat()
    state['topics'] = {k: len(v) for k, v in topics.items()}
    state['concepts'] = concepts[:100]
    save_state(state)
    
    print(f"\n============================================================")
    print(f"                      语义分析完成")
    print(f"============================================================")
    print(f"📂 笔记: {len(notes)} 篇")
    print(f"📊 主题: {len(topics)} 个")
    print(f"🧠 概念: {len(concepts)} 个")
    print(f"============================================================")
    
    return notes, topics, concepts

if __name__ == "__main__":
    main()
