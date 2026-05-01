#!/usr/bin/env python3
"""
ClawShell Obsidian 同步模块
版本: v0.2.2-C
功能: Obsidian 文档归档、笔记同步
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

# ============ 配置 ============

OBSIDIAN_CONFIG_PATH = Path("~/.real/.obsidian_config.json").expanduser()
OBSIDIAN_STATE_PATH = Path("~/.real/.obsidian_sync_state.json").expanduser()

# 默认 Obsidian 路径
DEFAULT_OBSIDIAN_PATH = Path("~/Documents/Obsidian/OpenClaw").expanduser()


# ============ 数据结构 ============

@dataclass
class Note:
    """笔记"""
    path: Path
    title: str
    content: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: Optional[float] = None
    modified_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "path": str(self.path),
            "title": self.title,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }


@dataclass
class ArchiveResult:
    """归档结果"""
    success: bool
    archived_count: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)


# ============ Obsidian 同步 ============

class ObsidianSync:
    """Obsidian 同步"""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or DEFAULT_OBSIDIAN_PATH
        self.state = self._load_state()
        self._ensure_directories()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if OBSIDIAN_STATE_PATH.exists():
            try:
                with open(OBSIDIAN_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": 0,
            "last_archive_id": None,
            "archived_count": 0,
            "synced_files": {}  # path -> last_modified
        }
    
    def _save_state(self):
        """保存状态"""
        with open(OBSIDIAN_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _ensure_directories(self):
        """确保目录存在"""
        if not self.vault_path.exists():
            print(f"Warning: Vault path does not exist: {self.vault_path}")
            return
        
        # 确保必要的子目录存在
        for subdir in ["Research/Output", "Other/Update", "1_Work/Output"]:
            path = self.vault_path / subdir
            path.mkdir(parents=True, exist_ok=True)
    
    def _extract_frontmatter(self, content: str) -> tuple[Dict, str]:
        """提取 YAML frontmatter"""
        lines = content.split('\n')
        
        if not lines or lines[0].strip() != '---':
            return {}, content
        
        # 找到结束标记
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break
        
        if end_idx is None:
            return {}, content
        
        # 解析 frontmatter
        frontmatter = {}
        for line in lines[1:end_idx]:
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
        
        # 返回去除 frontmatter 的内容
        return frontmatter, '\n'.join(lines[end_idx + 1:])
    
    def _generate_frontmatter(self, metadata: Dict) -> str:
        """生成 YAML frontmatter"""
        if not metadata:
            return ""
        
        lines = ["---"]
        for key, value in metadata.items():
            if isinstance(value, list):
                lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---\n")
        
        return '\n'.join(lines)
    
    # ---- 文件操作 ----
    
    def read_note(self, relative_path: str) -> Optional[Note]:
        """读取笔记"""
        path = self.vault_path / relative_path
        
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding='utf-8')
            frontmatter, body = self._extract_frontmatter(content)
            
            # 提取标题（第一个 # 标题）
            title = ""
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            stat = path.stat()
            
            return Note(
                path=path,
                title=title or path.stem,
                content=body.strip(),
                tags=frontmatter.get('tags', '').strip('[]').split(','),
                created_at=stat.st_ctime,
                modified_at=stat.st_mtime,
                metadata=frontmatter
            )
        except Exception as e:
            print(f"Read note failed: {e}")
            return None
    
    def write_note(self, relative_path: str, note: Note) -> bool:
        """写入笔记"""
        path = self.vault_path / relative_path
        
        try:
            # 确保父目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 构建内容
            frontmatter = note.metadata.copy()
            if note.tags:
                frontmatter['tags'] = note.tags
            
            content = self._generate_frontmatter(frontmatter)
            content += f"# {note.title}\n\n{note.content}"
            
            path.write_text(content, encoding='utf-8')
            
            # 更新状态
            self.state["synced_files"][str(relative_path)] = time.time()
            self._save_state()
            
            return True
        except Exception as e:
            print(f"Write note failed: {e}")
            return False
    
    def archive_note(self, source_path: Path, category: str = "archive") -> bool:
        """
        归档笔记
        
        Args:
            source_path: 源文件路径
            category: 归档类别 (archive/output/research)
        """
        if not source_path.exists():
            return False
        
        try:
            # 确定目标路径
            if category == "archive":
                dest_dir = self.vault_path / "9_Archive" / datetime.now().strftime("%Y%m")
            elif category == "output":
                dest_dir = self.vault_path / "Research/Output" / datetime.now().strftime("%Y%m%d")
            else:
                dest_dir = self.vault_path / "Research" / category
            
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / source_path.name
            
            # 如果目标已存在，添加时间戳
            if dest_path.exists():
                stem = dest_path.stem
                suffix = dest_path.suffix
                dest_path = dest_dir / f"{stem}_{int(time.time())}{suffix}"
            
            # 复制文件
            shutil.copy2(source_path, dest_path)
            
            # 更新状态
            self.state["last_archive_id"] = str(dest_path)
            self.state["archived_count"] += 1
            self._save_state()
            
            return True
        except Exception as e:
            print(f"Archive failed: {e}")
            return False
    
    def sync_directory(self, relative_dir: str, pattern: str = "*.md") -> ArchiveResult:
        """
        同步目录
        
        Args:
            relative_dir: 相对于 vault 的目录
            pattern: 文件匹配模式
        """
        source_dir = self.vault_path / relative_dir
        
        if not source_dir.exists():
            return ArchiveResult(success=False, errors=[f"Directory not found: {source_dir}"])
        
        result = ArchiveResult(success=True)
        
        try:
            for file_path in source_dir.glob(pattern):
                if file_path.is_file():
                    # 检查是否已同步
                    file_key = str(file_path.relative_to(self.vault_path))
                    last_sync = self.state.get("synced_files", {}).get(file_key, 0)
                    
                    if file_path.stat().st_mtime > last_sync:
                        # 文件有更新，需要同步
                        note = self.read_note(str(file_path.relative_to(self.vault_path)))
                        if note:
                            # 写入到 Research/Output
                            dest_relative = f"Research/Output/{datetime.now().strftime('%Y%m%d')}/{file_path.name}"
                            if self.write_note(dest_relative, note):
                                result.archived_count += 1
                            else:
                                result.failed_count += 1
                        else:
                            result.failed_count += 1
                    else:
                        # 无需同步，检查路径是否存在
                        dest_path = self.vault_path / "Research/Output" / datetime.now().strftime("%Y%m%d") / file_path.name
                        if not dest_path.exists():
                            result.failed_count += 1
            
            self.state["last_sync"] = time.time()
            self._save_state()
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            "vault_path": str(self.vault_path),
            "last_sync": self.state.get("last_sync", 0),
            "last_archive_id": self.state.get("last_archive_id"),
            "archived_count": self.state.get("archived_count", 0),
            "synced_files_count": len(self.state.get("synced_files", {})),
            "vault_exists": self.vault_path.exists()
        }
    
    # ---- 知识沉淀 ----
    
    def save_research_output(self, title: str, content: str, category: str = "general", 
                           tags: Optional[List[str]] = None) -> bool:
        """
        保存研究输出到 Obsidian
        
        Args:
            title: 文档标题
            content: 文档内容
            category: 分类 (general/clawshell/system)
            tags: 标签
        """
        # 生成文件名
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_title[:50]}.md"
        
        # 确定路径
        if category == "clawshell":
            dest_dir = self.vault_path / "Research/Output/ClawShell"
        elif category == "system":
            dest_dir = self.vault_path / "Research/Output/系统架构与规范"
        else:
            dest_dir = self.vault_path / "Research/Output/General"
        
        note = Note(
            path=dest_dir / filename,
            title=title,
            content=content,
            tags=tags or [],
            metadata={
                "created": datetime.now().isoformat(),
                "category": category,
                "source": "ClawShell"
            }
        )
        
        return self.write_note(str(note.path.relative_to(self.vault_path)), note)


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell Obsidian同步")
    parser.add_argument("--path", type=str, help="Vault路径")
    parser.add_argument("--read", type=str, help="读取笔记")
    parser.add_argument("--archive", type=str, help="归档文件")
    parser.add_argument("--sync", type=str, help="同步目录")
    parser.add_argument("--status", action="store_true", help="同步状态")
    parser.add_argument("--save", nargs=3, metavar=("TITLE", "CONTENT", "CATEGORY"), help="保存研究输出")
    args = parser.parse_args()
    
    vault_path = Path(args.path) if args.path else None
    obsidian = ObsidianSync(vault_path)
    
    if args.read:
        note = obsidian.read_note(args.read)
        if note:
            print(f"标题: {note.title}")
            print(f"标签: {note.tags}")
            print(f"---\n{note.content[:500]}...")
        else:
            print(f"❌ 笔记不存在: {args.read}")
    
    elif args.archive:
        success = obsidian.archive_note(Path(args.archive))
        print(f"{'✅' if success else '❌'} 归档 {'成功' if success else '失败'}")
    
    elif args.sync:
        result = obsidian.sync_directory(args.sync)
        print(f"同步完成:")
        print(f"  成功: {result.archived_count}")
        print(f"  失败: {result.failed_count}")
        if result.errors:
            print(f"  错误: {result.errors}")
    
    elif args.status:
        status = obsidian.get_sync_status()
        print("=" * 60)
        print("Obsidian 同步状态")
        print("=" * 60)
        print(f"Vault: {status['vault_path']}")
        print(f"存在: {'是' if status['vault_exists'] else '否'}")
        print(f"最后同步: {time.ctime(status['last_sync']) if status['last_sync'] else '从未'}")
        print(f"已归档: {status['archived_count']} 个文件")
        print(f"已同步文件: {status['synced_files_count']} 个")
    
    elif args.save:
        title, content, category = args.save
        success = obsidian.save_research_output(title, content, category)
        print(f"{'✅' if success else '❌'} 保存 {'成功' if success else '失败'}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
