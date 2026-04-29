#!/usr/bin/env python3
"""
Obsidian知识图谱引擎
自动分析笔记关联并生成JSON Canvas可视化
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Vault路径
VAULT_PATH = Path("/Users/yangyang/Documents/Obsidian/OpenClaw")
GRAPH_DIR = VAULT_PATH / "Graphs"

class KnowledgeGraphEngine:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.notes_index = {}  # filename -> note_info
        
    def scan_vault(self):
        """扫描Vault构建笔记索引"""
        print("=== 扫描Vault ===")
        
        for md_file in VAULT_PATH.rglob("*.md"):
            # 跳过特殊文件
            if any(x in str(md_file) for x in ["_templates", "CATEGORIES", ".obsidian"]):
                continue
            
            note_info = self.parse_note(md_file)
            if note_info:
                self.notes_index[note_info['path']] = note_info
        
        print(f"索引笔记: {len(self.notes_index)} 篇")
    
    def parse_note(self, filepath: Path) -> dict:
        """解析单个笔记"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return None
        
        # 提取frontmatter
        frontmatter = {}
        body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body = parts[2]
                
                # 简单解析YAML
                for line in frontmatter_str.split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        frontmatter[key.strip()] = val.strip()
        
        # 提取wikilinks
        wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', body)
        
        # 提取标题
        title = frontmatter.get('title', filepath.stem)
        
        # 确定分类
        category = self.detect_category(filepath, frontmatter, body)
        
        return {
            'path': filepath,
            'name': filepath.name,
            'title': title,
            'category': category,
            'wikilinks': wikilinks,
            'tags': frontmatter.get('tags', '').split(','),
            'modified': filepath.stat().st_mtime
        }
    
    def detect_category(self, filepath: Path, frontmatter: dict, body: str) -> str:
        """检测笔记分类"""
        # 从路径判断
        path_parts = filepath.parts
        for cat in ['Work', 'Learn', 'Research', 'Life', 'Other']:
            if cat in path_parts:
                return cat
        
        # 从frontmatter判断
        if 'category' in frontmatter:
            return frontmatter['category']
        
        return 'Other'
    
    def generate_id(self) -> str:
        """生成16位十六进制ID"""
        import random
        return ''.join(random.choice('0123456789abcdef') for _ in range(16))
    
    def build_graph(self):
        """构建知识图谱"""
        print("=== 构建知识图谱 ===")
        
        node_id_map = {}  # path -> node_id
        
        # 创建节点
        for path, note in self.notes_index.items():
            node_id = self.generate_id()
            node_id_map[path] = node_id
            
            # 确定颜色
            color_map = {
                'Work': '1',      # 红
                'Learn': '2',     # 橙
                'Research': '3',  # 黄
                'Life': '4',     # 绿
                'Other': '6'     # 紫
            }
            
            node = {
                'id': node_id,
                'type': 'text',
                'x': 0,
                'y': 0,
                'width': 300,
                'height': 150,
                'color': color_map.get(note['category'], '6'),
                'text': f"# {note['title']}\n\n类型: {note['category']}\n链接: {len(note['wikilinks'])}个"
            }
            self.nodes.append(node)
        
        # 创建边
        for path, note in self.notes_index.items():
            source_id = node_id_map.get(path)
            if not source_id:
                continue
            
            for link_target in note['wikilinks']:
                # 查找目标笔记
                target_path = self.find_note_by_name(link_target)
                if target_path and target_path in node_id_map:
                    target_id = node_id_map[target_path]
                    
                    edge = {
                        'id': self.generate_id(),
                        'fromNode': source_id,
                        'fromSide': 'right',
                        'toNode': target_id,
                        'toSide': 'left',
                        'toEnd': 'arrow'
                    }
                    self.edges.append(edge)
        
        print(f"节点: {len(self.nodes)}, 边: {len(self.edges)}")
    
    def find_note_by_name(self, name: str) -> str:
        """根据名称查找笔记路径"""
        # 支持模糊匹配
        for path in self.notes_index:
            path_str = str(path)
            if path_str.endswith(f"/{name}.md") or path_str.endswith(f"/{name}"):
                return path
        return None
    
    def layout_graph(self):
        """图谱布局"""
        print("=== 图谱布局 ===")
        
        # 按分类分组布局
        category_positions = {
            'Work': {'x': 0, 'y': 0},
            'Learn': {'x': 400, 'y': 0},
            'Research': {'x': 800, 'y': 0},
            'Life': {'x': 1200, 'y': 0},
            'Other': {'x': 1600, 'y': 0}
        }
        
        category_counters = defaultdict(int)
        
        for node in self.nodes:
            # 找到节点的分类
            note_info = None
            node_title = node['text'].split('\n')[0].replace('# ', '')
            for path, info in self.notes_index.items():
                if str(path).endswith(node_title):
                    note_info = info
                    break
            
            if not note_info:
                continue
            
            cat = note_info['category']
            pos = category_positions.get(cat, {'x': 2000, 'y': 0})
            counter = category_counters[cat]
            
            # 网格布局
            col = counter % 3
            row = counter // 3
            
            node['x'] = pos['x'] + col * 320
            node['y'] = pos['y'] + row * 200
            
            category_counters[cat] += 1
    
    def export_canvas(self, output_path: str = None):
        """导出为JSON Canvas"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = GRAPH_DIR / f"knowledge_graph_{timestamp}.canvas"
        
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        
        canvas = {
            'nodes': self.nodes,
            'edges': self.edges
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(canvas, f, ensure_ascii=False, indent=2)
        
        print(f"图谱已导出: {output_path}")
        return str(output_path)
    
    def generate_category_graphs(self):
        """生成分类子图"""
        print("=== 生成分类子图 ===")
        
        for category in ['Work', 'Learn', 'Research', 'Life', 'Other']:
            self.nodes = []
            self.edges = []
            
            # 只包含该分类的节点
            cat_nodes = {}
            for path, note in self.notes_index.items():
                if note['category'] == category:
                    node_id = self.generate_id()
                    cat_nodes[path] = node_id
                    
                    node = {
                        'id': node_id,
                        'type': 'text',
                        'x': 0,
                        'y': 0,
                        'width': 280,
                        'height': 120,
                        'text': f"# {note['title']}\n\n链接: {len(note['wikilinks'])}个"
                    }
                    self.nodes.append(node)
            
            # 只包含该分类内的边
            for path, note in self.notes_index.items():
                if note['category'] != category:
                    continue
                    
                source_id = cat_nodes.get(path)
                if not source_id:
                    continue
                
                for link_target in note['wikilinks']:
                    target_path = self.find_note_by_name(link_target)
                    if target_path in cat_nodes:
                        edge = {
                            'id': self.generate_id(),
                            'fromNode': source_id,
                            'fromSide': 'right',
                            'toNode': cat_nodes[target_path],
                            'toSide': 'left',
                            'toEnd': 'arrow'
                        }
                        self.edges.append(edge)
            
            if self.nodes:
                self.layout_graph_simple(category)
                output_path = GRAPH_DIR / f"{category.lower()}_graph.canvas"
                self.export_to_file(output_path)
    
    def layout_graph_simple(self, category: str):
        """简单网格布局"""
        cols = 3
        for i, node in enumerate(self.nodes):
            col = i % cols
            row = i // cols
            node['x'] = col * 300
            node['y'] = row * 180
    
    def export_to_file(self, output_path: Path):
        """导出到文件"""
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        
        canvas = {
            'nodes': self.nodes,
            'edges': self.edges
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(canvas, f, ensure_ascii=False, indent=2)
        
        print(f"  {category}图谱: {output_path.name}")
    
    def run(self, full: bool = True):
        """运行图谱引擎"""
        self.scan_vault()
        self.build_graph()
        
        if full:
            self.layout_graph()
            self.export_canvas()
            self.generate_category_graphs()
        else:
            # 只生成分类图
            self.generate_category_graphs()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Obsidian知识图谱引擎")
    parser.add_argument("--quick", action="store_true", help="快速模式，只生成分类图")
    parser.add_argument("--full", action="store_true", help="完整模式，生成全局图")
    
    args = parser.parse_args()
    
    engine = KnowledgeGraphEngine()
    engine.run(full=args.full or not args.quick)


if __name__ == "__main__":
    main()
