#!/usr/bin/env python3
"""
Obsidian链接自动构建器
每日扫描新增/修改的笔记，自动建立wikilinks关联
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
import argparse

# Vault路径
VAULT_PATH = Path("${OBSIDIAN_VAULT:-$HOME/Documents/Obsidian}/OpenClaw")
LINKS_DIR = VAULT_PATH / ".links"

class LinkBuilder:
    def __init__(self):
        self.notes_index = {}  # path -> note_info
        self.new_links = []  # [(source, target, reason)]
        
    def scan_vault(self):
        """扫描Vault构建笔记索引"""
        print("=== 扫描Vault ===")
        
        for md_file in VAULT_PATH.rglob("*.md"):
            # 跳过特殊文件
            if any(x in str(md_file) for x in ["_templates", "CATEGORIES", ".obsidian", "Graphs", ".links"]):
                continue
            
            note_info = self.parse_note(md_file)
            if note_info:
                self.notes_index[md_file] = note_info
        
        print(f"索引笔记: {len(self.notes_index)} 篇")
    
    def parse_note(self, filepath: Path) -> dict:
        """解析单个笔记"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return None
        
        # 提取frontmatter
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2]
        
        # 提取关键词（标题、标签、内容中的重要词汇）
        keywords = self.extract_keywords(filepath.stem, body)
        
        # 提取已有链接
        existing_links = re.findall(r'\[\[([^\]]+)\]\]', body)
        
        return {
            'path': filepath,
            'stem': filepath.stem,
            'title': self.extract_title(body) or filepath.stem,
            'keywords': keywords,
            'existing_links': set(existing_links),
            'content_lower': body.lower(),
            'mtime': filepath.stat().st_mtime
        }
    
    def extract_title(self, content: str) -> str:
        """提取标题"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            if line.startswith('## '):
                return line[3:].strip()
        return None
    
    def extract_keywords(self, filename: str, content: str) -> Set[str]:
        """提取关键词"""
        keywords = set()
        
        # 添加文件名
        keywords.add(filename.lower())
        
        # 添加标题词
        title = self.extract_title(content)
        if title:
            for word in re.split(r'[#\s\-_]', title):
                if len(word) > 2:
                    keywords.add(word.lower())
        
        # 添加标签
        tags = re.findall(r'#([a-zA-Z0-9_\-]+)', content)
        keywords.update(t.lower() for t in tags)
        
        # 添加重要概念词（长度>3的连续中文词或英文词）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{3,}', content)
        keywords.update(w.lower() for w in chinese_words)
        
        english_words = re.findall(r'[a-zA-Z]{4,}', content.lower())
        keywords.update(english_words)
        
        return keywords
    
    def find_today_changes(self) -> List[Path]:
        """查找今日新增/修改的笔记"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        changes = []
        
        for md_file in VAULT_PATH.rglob("*.md"):
            if any(x in str(md_file) for x in ["_templates", "CATEGORIES", ".obsidian", "Graphs", ".links"]):
                continue
            
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime >= today:
                changes.append(md_file)
        
        return changes
    
    def find_related_notes(self, note_info: dict) -> List[Tuple[Path, str]]:
        """找出与当前笔记相关的其他笔记"""
        related = []
        current_keywords = note_info['keywords']
        current_stem = note_info['stem']
        
        for filepath, info in self.notes_index.items():
            if filepath == note_info['path']:
                continue
            
            # 跳过已有关联的笔记
            if current_stem in info['existing_links']:
                continue
            
            # 计算关联度
            other_keywords = info['keywords']
            common = current_keywords & other_keywords
            
            if len(common) >= 2:  # 至少2个共同关键词
                # 优先匹配标题相似的
                title_match = any(w in info['title'].lower() for w in current_keywords if len(w) > 3)
                
                related.append((filepath, f"共同关键词: {', '.join(list(common)[:5])}"))
        
        # 按关联度排序
        related.sort(key=lambda x: len(x[1]), reverse=True)
        return related[:5]  # 最多返回5个关联
    
    def build_links(self) -> Dict:
        """构建所有需要的链接"""
        print("\n=== 构建链接 ===")
        
        changes = self.find_today_changes()
        print(f"今日变更: {len(changes)} 篇")
        
        if not changes:
            return {"new_links": [], "changed_files": []}
        
        results = {
            "new_links": [],
            "changed_files": [str(p) for p in changes]
        }
        
        for filepath in changes:
            if filepath not in self.notes_index:
                note_info = self.parse_note(filepath)
                if note_info:
                    self.notes_index[filepath] = note_info
            else:
                note_info = self.notes_index[filepath]
            
            related = self.find_related_notes(note_info)
            
            for target_path, reason in related:
                target_stem = target_path.stem
                
                # 检查是否已存在链接
                if target_stem not in note_info['existing_links']:
                    results["new_links"].append({
                        "source": str(filepath),
                        "target": str(target_path),
                        "source_stem": filepath.stem,
                        "target_stem": target_stem,
                        "reason": reason
                    })
                    
                    print(f"  📎 {filepath.stem} → {target_stem}")
                    print(f"     原因: {reason}")
        
        return results
    
    def apply_links(self, links: List[Dict]) -> int:
        """将链接写入笔记"""
        print("\n=== 应用链接 ===")
        applied = 0
        
        # 按文件分组链接
        links_by_file = {}
        for link in links:
            source = link['source']
            if source not in links_by_file:
                links_by_file[source] = []
            links_by_file[source].append(link)
        
        for source_path, file_links in links_by_file.items():
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original = content
                
                for link in file_links:
                    target_stem = link['target_stem']
                    
                    # 检查是否已存在链接
                    if f"[[{target_stem}]]" in content:
                        continue
                    
                    # 在合适的位置插入链接（在段落末尾或特定标记处）
                    # 这里简单地在文件末尾添加
                    new_link = f"\n\n<!-- auto-link: {target_stem} -->\n[[{target_stem}]]"
                    content += new_link
                    applied += 1
                    print(f"  ✅ 添加链接: [[{target_stem}]] → {source_path}")
                
                if content != original:
                    with open(source_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
            except Exception as e:
                print(f"  ❌ 错误: {source_path} - {e}")
        
        return applied
    
    def save_report(self, results: Dict):
        """保存链接报告"""
        LINKS_DIR.mkdir(exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        report_file = LINKS_DIR / f"links_{date_str}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 报告已保存: {report_file}")
    
    def run(self, dry_run: bool = True, apply: bool = False):
        """运行链接构建"""
        print(f"=== Obsidian链接构建器 ===")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Vault: {VAULT_PATH}")
        print(f"模式: {'干运行' if dry_run else '实际执行'}")
        
        # 扫描
        self.scan_vault()
        
        # 构建链接
        results = self.build_links()
        
        # 应用或保存
        if apply and not dry_run:
            applied = self.apply_links(results.get("new_links", []))
            results["applied"] = applied
            print(f"\n已应用 {applied} 个链接")
        
        # 保存报告
        self.save_report(results)
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Obsidian链接自动构建器')
    parser.add_argument('--dry-run', action='store_true', default=True, help='干运行模式')
    parser.add_argument('--apply', action='store_true', help='实际应用链接')
    parser.add_argument('--force', action='store_true', help='强制处理所有文件（不只是今日变更）')
    args = parser.parse_args()
    
    builder = LinkBuilder()
    
    if args.force:
        # 强制模式：处理所有文件
        builder.scan_vault()
        results = builder.build_links()
    else:
        # 正常模式：只处理今日变更
        results = builder.run(dry_run=args.apply)
    
    if args.apply:
        applied = builder.apply_links(results.get("new_links", []))
        print(f"\n已应用 {applied} 个链接")
    
    return results


if __name__ == "__main__":
    main()
