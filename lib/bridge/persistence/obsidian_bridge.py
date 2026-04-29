"""
Obsidian Bridge - Obsidian笔记持久化
====================================

提供Obsidian笔记库的读写接口。
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import re


class ObsidianBridge:
    """Obsidian笔记桥接器"""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or Path(
            os.environ.get('OBSIDIAN_VAULT', '~/Documents/Obsidian').replace('~', str(Path.home()))
        )
    
    def is_available(self) -> bool:
        """检查Obsidian是否可用"""
        return self.vault_path.exists() and self.vault_path.is_dir()
    
    def read_note(self, filename: str) -> Optional[str]:
        """读取笔记"""
        try:
            note_path = self.vault_path / f"{filename}.md"
            if not note_path.exists():
                return None
            with open(note_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"ObsidianBridge read error: {e}")
            return None
    
    def write_note(self, filename: str, content: str) -> bool:
        """写入笔记"""
        try:
            note_path = self.vault_path / f"{filename}.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"ObsidianBridge write error: {e}")
            return False
    
    def list_notes(self, folder: str = "") -> List[str]:
        """列出笔记"""
        try:
            folder_path = self.vault_path / folder if folder else self.vault_path
            if not folder_path.exists():
                return []
            return [f.stem for f in folder_path.glob("*.md")]
        except Exception as e:
            print(f"ObsidianBridge list error: {e}")
            return []
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """搜索笔记"""
        results = []
        try:
            for note_path in self.vault_path.rglob("*.md"):
                try:
                    with open(note_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if query.lower() in content.lower():
                        results.append({
                            'filename': note_path.stem,
                            'path': str(note_path.relative_to(self.vault_path))
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"ObsidianBridge search error: {e}")
        return results
    
    def get_links(self, filename: str) -> List[str]:
        """获取笔记中的链接"""
        content = self.read_note(filename)
        if not content:
            return []
        # 匹配 [[wikilink]] 格式
        return re.findall(r'\[\[([^\]]+)\]\]', content)
