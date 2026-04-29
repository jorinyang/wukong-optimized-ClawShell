#!/usr/bin/env python3
"""
OpenClaw Knowledge Graph Builder - .openclaw目录知识图谱构建器
功能：
1. 扫描.openclaw目录结构
2. 分析文件间引用关系
3. 提取关键字和标签
4. 生成知识图谱
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ==================== 配置 ====================

OPENCLAW_DIR = Path.home() / ".openclaw"
GRAPH_OUTPUT = Path.home() / ".openclaw/workspace/openclaw_knowledge_graph.json"

# ==================== 知识图谱构建器 ====================

class OpenClawGraphBuilder:
    def __init__(self):
        self.nodes = {}  # 节点: {id: {type, name, path, tags, content}}
        self.edges = []  # 边: [{source, target, type, label}]
        self.file_types = defaultdict(list)  # 按类型分组文件
    
    def scan_directory(self, root_dir):
        """扫描目录"""
        print(f"扫描目录: {root_dir}")
        
        # 关键目录优先扫描
        key_dirs = ['scripts', 'hooks', 'skills', 'workspace', 'cron', 'inbox', 
                    'error-cookbook', 'shared', 'config', 'identity', 'agents']
        
        # 先扫描关键目录
        for key_dir in key_dirs:
            dir_path = root_dir / key_dir
            if dir_path.exists():
                for path in dir_path.rglob("*"):
                    if path.is_file() and not self._should_skip(path):
                        file_info = self._analyze_file(path)
                        if file_info:
                            self.file_types[file_info['type']].append(file_info)
        
        # 再扫描根目录的关键文件
        for path in root_dir.iterdir():
            if path.is_file() and not self._should_skip(path):
                file_info = self._analyze_file(path)
                if file_info:
                    self.file_types[file_info['type']].append(file_info)
    
    def _should_skip(self, path):
        """判断是否跳过"""
        skip_patterns = [
            '__pycache__', '.git', 'node_modules', '.DS_Store',
            'Thumbs.db', '.pyc', '.pyo'
        ]
        return any(pattern in str(path) for pattern in skip_patterns)
    
    def _analyze_file(self, path):
        """分析文件"""
        try:
            stat = path.stat()
            relative_path = str(path.relative_to(OPENCLAW_DIR))
            
            # 确定文件类型
            file_type = self._get_file_type(path)
            
            # 提取内容
            content = ""
            if path.suffix in ['.py', '.sh', '.json', '.md', '.yaml', '.yml']:
                try:
                    content = path.read_text(encoding='utf-8', errors='ignore')
                except:
                    pass
            
            # 提取标签
            tags = self._extract_tags(content, path)
            
            # 提取引用
            references = self._extract_references(content, path)
            
            node = {
                'id': relative_path,
                'type': file_type,
                'name': path.name,
                'path': relative_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'tags': tags,
                'references': references
            }
            
            self.nodes[relative_path] = node
            return node
            
        except Exception as e:
            print(f"分析失败: {path} - {e}")
            return None
    
    def _get_file_type(self, path):
        """获取文件类型"""
        suffix = path.suffix.lower()
        name = path.name.lower()
        
        if suffix == '.py':
            return 'python'
        elif suffix == '.sh':
            return 'shell'
        elif suffix == '.json':
            return 'config'
        elif suffix in ['.md', '.markdown']:
            return 'document'
        elif suffix in ['.yaml', '.yml']:
            return 'config'
        elif suffix == '.txt':
            return 'text'
        else:
            return 'other'
    
    def _extract_tags(self, content, path):
        """提取标签"""
        tags = set()
        
        # 从文件名提取
        name = path.stem.lower()
        tags.add(name)
        
        # 从内容提取
        if content:
            # 提取 # 标签
            hashtag_pattern = r'#([a-zA-Z_]+)'
            tags.update(re.findall(hashtag_pattern, content.lower()))
            
            # 提取 import 语句
            import_pattern = r'import\s+([a-zA-Z_]+)'
            imports = re.findall(import_pattern, content)
            for imp in imports[:5]:  # 限制数量
                tags.add(imp.lower())
        
        return list(tags)[:20]  # 限制标签数量
    
    def _extract_references(self, content, path):
        """提取引用"""
        refs = []
        
        if not content:
            return refs
        
        # 提取文件路径引用
        path_pattern = r'([~/.][a-zA-Z0-9/_.-]+(?:\.py|\.sh|\.json|\.md))'
        found_paths = re.findall(path_pattern, content)
        for fp in found_paths[:10]:
            if str(OPENCLAW_DIR) in fp or fp.startswith('~'):
                refs.append(fp)
        
        # 提取函数/变量引用
        func_pattern = r'def\s+([a-zA-Z_]+)|([a-zA-Z_]+)\s*='
        found_funcs = re.findall(func_pattern, content)
        for func in found_funcs:
            for f in func:
                if f and not f.startswith('_'):
                    refs.append(f)
        
        return refs[:20]
    
    def build_edges(self):
        """构建引用关系"""
        print("构建引用关系...")
        
        for node_id, node in self.nodes.items():
            for ref in node.get('references', []):
                # 查找引用目标
                target = self._find_reference_target(ref, node_id)
                if target:
                    edge = {
                        'source': node_id,
                        'target': target,
                        'type': 'references',
                        'label': '引用'
                    }
                    self.edges.append(edge)
        
        # 添加类型关系
        for file_type, files in self.file_types.items():
            for i, file1 in enumerate(files):
                for file2 in files[i+1:]:
                    edge = {
                        'source': file1['path'],
                        'target': file2['path'],
                        'type': 'same_type',
                        'label': f'同类型({file_type})'
                    }
                    self.edges.append(edge)
    
    def _find_reference_target(self, ref, source_id):
        """查找引用目标"""
        # 清理引用路径
        ref = ref.replace('~', str(Path.home()))
        
        # 检查是否是openclaw目录内的文件
        if str(OPENCLAW_DIR) in ref:
            try:
                relative = Path(ref).relative_to(OPENCLAW_DIR)
                return str(relative)
            except:
                pass
        
        # 尝试在openclaw目录中查找
        try:
            potential = OPENCLAW_DIR / ref.split('.openclaw/')[-1]
            if potential.exists():
                return str(potential.relative_to(OPENCLAW_DIR))
        except:
            pass
        
        # 查找同名文件
        ref_name = ref.split('/')[-1]
        for node_id in self.nodes:
            if node_id.endswith(ref_name) and node_id != source_id:
                return node_id
        
        return None
    
    def generate_graph(self):
        """生成图谱"""
        graph = {
            'generated': datetime.now().isoformat(),
            'stats': {
                'total_nodes': len(self.nodes),
                'total_edges': len(self.edges),
                'by_type': {k: len(v) for k, v in self.file_types.items()}
            },
            'nodes': self.nodes,
            'edges': self.edges
        }
        
        return graph
    
    def save_graph(self, graph):
        """保存图谱"""
        with open(GRAPH_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        
        print(f"图谱已保存: {GRAPH_OUTPUT}")
    
    def generate_markdown_report(self, graph):
        """生成Markdown报告"""
        report = f"""# .openclaw 目录知识图谱

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 统计概览

| 指标 | 数值 |
|------|------|
| 总节点数 | {graph['stats']['total_nodes']} |
| 总边数 | {graph['stats']['total_edges']} |

### 按类型分布

| 类型 | 数量 |
|------|------|
"""
        
        for file_type, count in sorted(graph['stats']['by_type'].items(), key=lambda x: -x[1]):
            report += f"| {file_type} | {count} |\n"
        
        report += "\n---\n\n## 主要模块\n\n"
        
        # 按目录分组
        modules = defaultdict(list)
        for node_id in graph['nodes']:
            parts = node_id.split('/')
            if len(parts) > 1:
                modules[parts[0]].append(node_id)
            else:
                modules['root'].append(node_id)
        
        for module, files in sorted(modules.items()):
            report += f"### {module}/\n\n"
            for f in sorted(files)[:15]:
                node = graph['nodes'][f]
                tags = ', '.join(node.get('tags', [])[:5])
                report += f"- `{f}` - {tags}\n"
            if len(files) > 15:
                report += f"- ... 还有 {len(files) - 15} 个文件\n"
            report += "\n"
        
        report += f"""---

## 引用关系

共 {graph['stats']['total_edges']} 条引用关系

"""
        
        return report
    
    def run(self):
        """运行构建"""
        print("=" * 60)
        print("      OpenClaw 知识图谱构建器")
        print("=" * 60)
        print()
        
        # 扫描
        self.scan_directory(OPENCLAW_DIR)
        print(f"扫描完成: {len(self.nodes)} 个文件")
        
        # 构建关系
        self.build_edges()
        print(f"关系构建完成: {len(self.edges)} 条边")
        
        # 生成图谱
        graph = self.generate_graph()
        
        # 保存
        self.save_graph(graph)
        
        # 生成报告
        report = self.generate_markdown_report(graph)
        report_file = Path.home() / ".openclaw/workspace/openclaw_graph_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"报告已生成: {report_file}")
        
        return graph

# ==================== 主函数 ====================

if __name__ == "__main__":
    builder = OpenClawGraphBuilder()
    graph = builder.run()
    
    print()
    print("=" * 60)
    print("      构建完成")
    print("=" * 60)
    print(f"节点: {graph['stats']['total_nodes']}")
    print(f"边: {graph['stats']['total_edges']}")
