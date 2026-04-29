#!/usr/bin/env python3
"""
Obsidian Graph Builder - 知识图谱构建器
功能：
1. 扫描Obsidian Vault新笔记
2. 分析语义关联
3. 发现潜在wikilink
4. 生成图谱数据
5. 输出关联报告

触发: 每日00:00 Cron
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ==================== 配置 ====================

VAULT_PATH = Path.home() / "Documents/Obsidian/OpenClaw"
GRAPH_DIR = Path.home() / ".openclaw/graphs"
REPORT_DIR = Path.home() / ".openclaw/reports"
LOG_DIR = Path.home() / ".openclaw/logs"
STATE_FILE = Path.home() / ".openclaw/.graph_builder_state.json"

# 扫描范围（一级目录）
SCAN_DIRS = ["1_Work", "2_Learn", "3_Research", "4_Life", "Other"]

# 忽略文件
IGNORE_FILES = ["README.md", "SUMMARY.md", "INDEX.md"]

# ==================== 状态管理 ====================

def load_state() -> dict:
    """加载状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_scan": None, "processed_files": []}

def save_state(state: dict):
    """保存状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ==================== 核心功能 ====================

def scan_vault() -> List[Path]:
    """扫描Vault中的markdown文件"""
    files = []
    today = datetime.now().date()
    
    for dir_name in SCAN_DIRS:
        dir_path = VAULT_PATH / dir_name
        if not dir_path.exists():
            continue
        
        for md_file in dir_path.rglob("*.md"):
            if md_file.name in IGNORE_FILES:
                continue
            
            # 检查修改时间（今天或昨天）
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime).date()
            if mtime >= today - timedelta(days=1):
                files.append(md_file)
    
    return files

def extract_links(content: str) -> Set[str]:
    """提取wikilink"""
    # [[link]] 格式
    wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)
    return set(wikilinks)

def extract_tags(content: str) -> Set[str]:
    """提取标签"""
    tags = re.findall(r'#([a-zA-Z0-9_/-]+)', content)
    return set(tags)

def extract_headings(content: str) -> List[str]:
    """提取标题"""
    headings = re.findall(r'^#{1,6}\s+(.+?)$', content, re.MULTILINE)
    return headings

def calculate_similarity(text1: str, text2: str) -> float:
    """简单相似度计算（基于共同词汇）"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union)

def discover_links(files: List[Path]) -> List[Dict]:
    """发现潜在关联"""
    links = []
    
    # 加载所有文件内容建立索引
    file_index = {}
    for f in files:
        try:
            content = f.read_text(encoding='utf-8')
            file_index[str(f)] = {
                'content': content,
                'title': f.stem,
                'path': str(f),
                'wikilinks': extract_links(content),
                'tags': extract_tags(content),
                'headings': extract_headings(content)[:5]  # 只取前5个标题
            }
        except Exception as e:
            print(f"  ⚠️ 读取失败: {f.name} - {e}")
    
    # 发现关联
    for path1, data1 in file_index.items():
        for path2, data2 in file_index.items():
            if path1 >= path2:
                continue
            
            score = 0.0
            reasons = []
            
            # 1. 直接wikilink
            if data2['title'] in data1['wikilinks'] or data1['title'] in data2['wikilinks']:
                score += 0.5
                reasons.append("直接wikilink")
            
            # 2. 共同标签
            common_tags = data1['tags'] & data2['tags']
            if common_tags:
                score += 0.3 * len(common_tags)
                reasons.append(f"共同标签: {', '.join(list(common_tags)[:3])}")
            
            # 3. 共同标题词
            title_words1 = set(' '.join(data1['headings']).lower().split())
            title_words2 = set(' '.join(data2['headings']).lower().split())
            common_title_words = title_words1 & title_words2 - {'的', '了', '和', '与', '在', '是', '我', '你', '他'}
            if common_title_words:
                score += 0.2 * len(common_title_words)
                reasons.append(f"标题相似: {', '.join(list(common_title_words)[:3])}")
            
            if score > 0.1:
                links.append({
                    'source': data1['title'],
                    'target': data2['title'],
                    'score': round(score, 3),
                    'reasons': reasons,
                    'source_path': path1,
                    'target_path': path2
                })
    
    return sorted(links, key=lambda x: x['score'], reverse=True)

def generate_graph_data(files: List[Path], links: List[Dict]) -> dict:
    """生成图谱数据"""
    nodes = []
    for f in files:
        nodes.append({
            'id': f.stem,
            'title': f.stem,
            'path': str(f.relative_to(VAULT_PATH)),
            'dir': f.parent.name,
            'type': 'file'
        })
    
    edges = []
    for link in links:
        edges.append({
            'source': link['source'],
            'target': link['target'],
            'score': link['score'],
            'reasons': link['reasons']
        })
    
    return {
        'timestamp': datetime.now().isoformat(),
        'node_count': len(nodes),
        'edge_count': len(edges),
        'nodes': nodes,
        'edges': edges
    }

def generate_report(files: List[Path], links: List[Dict], graph_data: dict) -> str:
    """生成报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    report = f"""# 知识图谱报告

**生成时间**: {today}
**扫描文件**: {len(files)} 个
**发现关联**: {len(links)} 条

---

## 图谱概览

| 指标 | 值 |
|------|-----|
| 节点数 | {graph_data['node_count']} |
| 边数 | {graph_data['edge_count']} |
| 平均关联 | {len(links)/max(len(files),1):.2f} |

---

## 高置信度关联 (TOP 10)

| 来源 | 目标 | 置信度 | 原因 |
|------|------|--------|------|
"""
    
    for link in links[:10]:
        report += f"| {link['source']} | {link['target']} | {link['score']:.2f} | {', '.join(link['reasons'][:2])} |\n"
    
    report += f"""

---

## 新增文件

"""
    
    for f in files[:20]:
        report += f"- [[{f.stem}]] ({f.parent.name})\n"
    
    report += """

---

*由 OpenClaw 知识图谱构建器自动生成*
"""
    
    return report

def main():
    print(f"[Graph Builder] 知识图谱构建器启动... {datetime.now().strftime('%H:%M:%S')}")
    
    # 确保目录存在
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载状态
    state = load_state()
    
    # 扫描文件
    print(f"📂 扫描Vault...")
    files = scan_vault()
    print(f"   发现 {len(files)} 个新/近期文件")
    
    if not files:
        print("⚠️ 没有发现需要处理的文件")
        # 仍然生成空图谱
        files = list(VAULT_PATH.rglob("*.md"))[:100]  # 取最近100个
    
    # 发现关联
    print(f"🔗 发现关联...")
    links = discover_links(files)
    print(f"   发现 {len(links)} 条潜在关联")
    
    # 生成图谱数据
    print(f"📊 生成图谱数据...")
    graph_data = generate_graph_data(files, links)
    
    # 保存图谱JSON
    today = datetime.now().strftime("%Y%m%d")
    graph_file = GRAPH_DIR / "daily" / f"{today}.json"
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    with open(graph_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)
    print(f"   已保存: {graph_file.name}")
    
    # 生成报告
    print(f"📝 生成报告...")
    report = generate_report(files, links, graph_data)
    report_file = REPORT_DIR / f"graph_{today}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   已保存: {report_file.name}")
    
    # 更新状态
    state['last_scan'] = datetime.now().isoformat()
    state['processed_files'] = [str(f) for f in files]
    save_state(state)
    
    print(f"\n============================================================")
    print(f"                      图谱构建完成")
    print(f"============================================================")
    print(f"📂 文件: {len(files)} 个")
    print(f"🔗 关联: {len(links)} 条")
    print(f"📊 节点: {graph_data['node_count']}")
    print(f"📈 边数: {graph_data['edge_count']}")
    print(f"============================================================")
    
    return graph_data

if __name__ == "__main__":
    main()
