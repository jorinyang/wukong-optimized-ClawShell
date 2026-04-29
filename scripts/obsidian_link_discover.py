#!/usr/bin/env python3
"""
Obsidian Link Discover - 链接发现器
功能：
1. 扫描Vault中所有笔记
2. 发现未建立链接但可能相关的笔记
3. 生成推荐链接
4. 可选自动应用

触发: obsidian_graph_builder.py 调用 或 独立运行
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# ==================== 配置 ====================

VAULT_PATH = Path.home() / "Documents/Obsidian/OpenClaw"
OUTPUT_DIR = Path.home() / ".openclaw/workspace/OpenClaw/.links"
STATE_FILE = Path.home() / ".openclaw/.link_discover_state.json"

# 扫描范围
SCAN_DIRS = ["1_Work", "2_Learn", "3_Research", "4_Life", "Other"]

# 忽略文件
IGNORE_FILES = ["README.md", "SUMMARY.md", "INDEX.md"]

# 链接阈值
MIN_SCORE = 0.3

# ==================== 状态管理 ====================

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_scan": None, "existing_links": {}, "recommendations": []}

def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ==================== 核心功能 ====================

def scan_all_notes() -> Dict[str, dict]:
    """扫描所有笔记"""
    notes = {}
    
    for dir_name in SCAN_DIRS:
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue
        
        for md_file in dir_path.rglob("*.md"):
            if md_file.name in IGNORE_FILES:
                continue
            
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                
                # 提取现有链接
                existing_links = extract_links(content)
                
                # 提取关键词
                keywords = extract_keywords(content, md_file.stem)
                
                # 提取标题
                headings = extract_headings(content)
                
                notes[str(md_file)] = {
                    'title': md_file.stem,
                    'path': str(md_file.relative_to(VAULT_PATH)),
                    'dir': dir_name,
                    'content': content,
                    'existing_links': existing_links,
                    'keywords': keywords,
                    'headings': headings
                }
            except Exception as e:
                print(f"⚠️ 读取失败: {md_file.name} - {e}")
    
    return notes

def extract_links(content: str) -> Set[str]:
    """提取wikilink"""
    wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
    return set(wikilinks)

def extract_keywords(content: str, title: str) -> Set[str]:
    """提取关键词"""
    keywords = set()
    
    # 标题词
    keywords.update(title.replace('-', ' ').replace('_', ' ').split())
    
    # 去除markdown
    text = re.sub(r'[#*`\[\]()]', ' ', content)
    text = re.sub(r'https?://\S+', '', text)
    
    # 提取中文词
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,5}', text)
    keywords.update(chinese_words)
    
    # 提取英文词
    english_words = re.findall(r'[a-zA-Z]{3,}', text)
    keywords.update(w.lower() for w in english_words)
    
    # 过滤停用词
    stopwords = {'的', '了', '和', '与', '在', '是', '我', '你', '他', '她', '它', '这', '那', '有', '了', '也', '就', '都', '而', '及', '与', '或', 'the', 'and', 'is', 'are', 'was', 'were', 'this', 'that', 'for', 'not', 'with', 'as', 'on', 'at', 'by'}
    keywords = keywords - stopwords
    
    return keywords

def extract_headings(content: str) -> List[str]:
    """提取标题"""
    headings = re.findall(r'^#{1,6}\s+(.+?)$', content, re.MULTILINE)
    return headings[:10]

def calculate_link_score(note1: dict, note2: dict) -> float:
    """计算链接可能性得分"""
    score = 0.0
    reasons = []
    
    # 关键词重叠
    common_keywords = note1['keywords'] & note2['keywords']
    if common_keywords:
        score += min(0.5, len(common_keywords) * 0.1)
        if len(common_keywords) >= 2:
            reasons.append(f"共同关键词: {', '.join(list(common_keywords)[:5])}")
    
    # 标题相似
    title1_words = set(note1['title'].replace('-', ' ').replace('_', ' ').lower().split())
    title2_words = set(note2['title'].replace('-', ' ').replace('_', ' ').lower().split())
    common_title = title1_words & title2_words
    if common_title and len(common_title) >= 1:
        score += 0.3
        reasons.append(f"标题相似: {', '.join(common_title)}")
    
    # 同一目录
    if note1['dir'] == note2['dir'] and note1['dir'] not in ['Other']:
        score += 0.2
    
    # 检查是否已存在链接
    if note2['title'] in note1['existing_links'] or note1['title'] in note2['existing_links']:
        return 0.0, []  # 已存在链接
    
    return score, reasons

def discover_links(notes: Dict[str, dict]) -> List[Dict]:
    """发现推荐链接"""
    recommendations = []
    
    note_list = list(notes.items())
    for i, (path1, note1) in enumerate(note_list):
        for path2, note2 in note_list[i+1:]:
            score, reasons = calculate_link_score(note1, note2)
            
            if score >= MIN_SCORE:
                recommendations.append({
                    'source': note1['title'],
                    'source_path': note1['path'],
                    'target': note2['title'],
                    'target_path': note2['path'],
                    'score': round(score, 3),
                    'reasons': reasons,
                    'wikilink': f"[[{note2['title']}]]"
                })
    
    return sorted(recommendations, key=lambda x: x['score'], reverse=True)

def generate_apply_script(recommendations: List[Dict], dry_run: bool = True) -> str:
    """生成应用脚本"""
    script = "#!/bin/bash\n"
    script += "# Obsidian Link Auto-Apply Script\n"
    script += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    script += "# Mode: DRY-RUN (use --apply to actually apply)\n\n" if dry_run else "\n"
    
    for rec in recommendations[:50]:  # 最多50条
        script += f"# Score: {rec['score']} | {rec['source']} → {rec['target']}\n"
        script += f"# Reasons: {'; '.join(rec['reasons'])}\n"
        script += f"# [[{rec['source']}]] → [[{rec['target']}]]\n\n"
    
    if dry_run:
        script += "\n# Use --apply to actually apply these changes\n"
    
    return script

def main(apply: bool = False, dry_run_only: bool = True):
    """主函数"""
    print(f"[Link Discover] 链接发现器启动... {datetime.now().strftime('%H:%M:%S')}")
    
    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载状态
    state = load_state()
    
    # 扫描笔记
    print(f"📂 扫描Vault笔记...")
    notes = scan_all_notes()
    print(f"   发现 {len(notes)} 篇笔记")
    
    # 发现链接
    print(f"🔗 发现推荐链接...")
    recommendations = discover_links(notes)
    print(f"   发现 {len(recommendations)} 条推荐链接")
    
    # 保存推荐
    today = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"links_{today}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_notes': len(notes),
            'recommendations': recommendations
        }, f, ensure_ascii=False, indent=2)
    print(f"   已保存: {output_file.name}")
    
    # 生成脚本
    script = generate_apply_script(recommendations, dry_run=dry_run_only)
    script_file = OUTPUT_DIR / f"apply_links_{today}.sh"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"   脚本已保存: {script_file.name}")
    
    # 更新状态
    state['last_scan'] = datetime.now().isoformat()
    state['recommendations'] = recommendations[:100]  # 只保存前100条
    save_state(state)
    
    # 显示TOP推荐
    if recommendations:
        print(f"\n📋 TOP 10 推荐链接:")
        for i, rec in enumerate(recommendations[:10], 1):
            print(f"   {i}. {rec['source']} → {rec['target']} (score: {rec['score']})")
    
    print(f"\n============================================================")
    print(f"                      链接发现完成")
    print(f"============================================================")
    print(f"📂 笔记: {len(notes)} 篇")
    print(f"🔗 推荐: {len(recommendations)} 条")
    print(f"============================================================")
    
    return recommendations

if __name__ == "__main__":
    import sys
    
    dry_run = "--apply" not in sys.argv
    apply = "--apply" in sys.argv
    
    main(apply=apply, dry_run_only=dry_run)
