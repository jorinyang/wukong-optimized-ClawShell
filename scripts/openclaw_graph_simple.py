#!/usr/bin/env python3
"""
OpenClaw Knowledge Graph - 简化版知识图谱
分析.openclaw目录下脚本和配置文件的引用关系
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

OPENCLAW_DIR = Path.home() / ".openclaw"

def scan_scripts():
    """扫描关键脚本"""
    scripts = {}
    
    # scripts目录
    scripts_dir = OPENCLAW_DIR / "scripts"
    if scripts_dir.exists():
        for f in scripts_dir.glob("*.py"):
            scripts[f.name] = {
                'path': str(f.relative_to(OPENCLAW_DIR)),
                'type': 'python',
                'imports': [],
                'references': []
            }
        for f in scripts_dir.glob("*.sh"):
            scripts[f.name] = {
                'path': str(f.relative_to(OPENCLAW_DIR)),
                'type': 'shell',
                'calls': [],
                'references': []
            }
    
    return scripts

def analyze_references(scripts):
    """分析引用关系"""
    scripts_dir = OPENCLAW_DIR / "scripts"
    
    for name, info in scripts.items():
        if info['type'] == 'python':
            filepath = scripts_dir / name
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                
                # 提取import
                for imp in re.findall(r'^import\s+([a-zA-Z_]+)', content, re.MULTILINE):
                    info['imports'].append(imp)
                
                # 提取from import
                for imp in re.findall(r'^from\s+([a-zA-Z_.]+)\s+import', content, re.MULTILINE):
                    info['imports'].append(imp)
                
                # 提取脚本调用
                for call in re.findall(r'(?:python3?\s+)?([a-zA-Z_]+)\.py', content):
                    info['references'].append(call + '.py')
                
                # 提取配置文件引用
                for ref in re.findall(r'([a-zA-Z_]+\.json|[a-zA-Z_]+\.md)', content):
                    info['references'].append(ref)
                    
            except:
                pass
        else:
            filepath = scripts_dir / name
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                
                # 提取shell调用
                for call in re.findall(r'(?:python3?\s+|bash\s+)?([a-zA-Z_]+)\.sh', content):
                    info['calls'].append(call + '.sh')
                for call in re.findall(r'(?:python3?\s+)?([a-zA-Z_]+)\.py', content):
                    info['references'].append(call + '.py')
                    
            except:
                pass
    
    return scripts

def build_graph(scripts):
    """构建知识图谱"""
    nodes = []
    edges = []
    
    # 创建节点
    for name, info in scripts.items():
        node = {
            'id': name,
            'path': info['path'],
            'type': info['type'],
            'imports': info.get('imports', []),
            'references': info.get('references', []) + info.get('calls', [])
        }
        nodes.append(node)
        
        # 创建边
        for ref in node['references']:
            edges.append({
                'source': name,
                'target': ref,
                'type': 'references'
            })
    
    return {'nodes': nodes, 'edges': edges}

def generate_markdown(graph):
    """生成Markdown报告"""
    
    md = """# .openclaw 目录知识图谱

**生成时间**: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """

---

## 图谱概览

"""
    
    # 统计
    total_scripts = len(graph['nodes'])
    total_refs = len(graph['edges'])
    
    md += f"""| 指标 | 数值 |
|------|------|
| 总脚本数 | {total_scripts} |
| 总引用关系 | {total_refs} |

---

## 节点列表

### Python脚本

| 脚本 | 导入模块 | 引用文件 |
|------|----------|----------|
"""
    
    for node in sorted(graph['nodes'], key=lambda x: x['id']):
        if node['type'] == 'python':
            imports = ', '.join(node['imports'][:5]) if node['imports'] else '-'
            refs = ', '.join(node['references'][:5]) if node['references'] else '-'
            md += f"| `{node['id']}` | {imports} | {refs} |\n"
    
    md += """
### Shell脚本

| 脚本 | 引用脚本 | 引用文件 |
|------|----------|----------|
"""
    
    for node in sorted(graph['nodes'], key=lambda x: x['id']):
        if node['type'] == 'shell':
            calls = ', '.join(node['references'][:5]) if node['references'] else '-'
            md += f"| `{node['id']}` | {calls} | - |\n"
    
    md += """
---

## 引用关系

"""
    
    # 按引用者分组
    by_source = defaultdict(list)
    for edge in graph['edges']:
        by_source[edge['source']].append(edge['target'])
    
    for source in sorted(by_source.keys()):
        targets = by_source[source]
        md += f"### {source}\n"
        for target in targets:
            md += f"- → `{target}`\n"
        md += "\n"
    
    md += """---

## 核心依赖链

"""
    
    # 找出被引用最多的脚本
    ref_count = defaultdict(int)
    for edge in graph['edges']:
        ref_count[edge['target']] += 1
    
    top_refs = sorted(ref_count.items(), key=lambda x: -x[1])[:10]
    
    md += "| 脚本 | 被引用次数 |\n|------|------------|\n"
    for name, count in top_refs:
        md += f"| `{name}` | {count} |\n"
    
    md += """

---

*本文档由系统自动生成*

"""
    return md

def main():
    print("=" * 60)
    print("      OpenClaw 知识图谱构建器 (简化版)")
    print("=" * 60)
    print()
    
    # 扫描
    print("扫描脚本...")
    scripts = scan_scripts()
    print(f"找到 {len(scripts)} 个脚本")
    
    # 分析
    print("分析引用关系...")
    scripts = analyze_references(scripts)
    
    # 构建
    print("构建图谱...")
    graph = build_graph(scripts)
    
    # 保存JSON
    output_json = OPENCLAW_DIR / "workspace" / "openclaw_graph.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"图谱已保存: {output_json}")
    
    # 生成Markdown
    md = generate_markdown(graph)
    output_md = OPENCLAW_DIR / "workspace" / "openclaw_graph.md"
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"报告已生成: {output_md}")
    
    print()
    print("=" * 60)
    print(f"完成! 节点: {len(graph['nodes'])}, 边: {len(graph['edges'])}")
    print("=" * 60)

if __name__ == "__main__":
    main()
