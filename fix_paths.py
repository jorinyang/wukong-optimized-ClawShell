#!/usr/bin/env python3
"""
ClawShell 路径修复脚本
将所有 ~/.real 引用映射到 ~/.real/
适配悟空的目录结构
"""

import os
import re
from pathlib import Path

# 路径映射规则
# ~/.real/ -> ~/.real/ (悟空主目录)
PATH_MAPPINGS = {
    "~/.real/": "~/.real/",
    "~/.real": "~/.real",
}

# Mac 特定路径 (需要移除或修改)
MAC_SPECIFIC_PATHS = [
    "C:\Users\Aorus\.real",
    "C:\Users\Aorus\.real",
]

def should_skip_file(filepath: str) -> bool:
    """检查文件是否应该跳过"""
    skip_patterns = ['.git', '__pycache__', '.pyc', '.venv', 'node_modules']
    return any(p in filepath for p in skip_patterns)

def fix_content(content: str) -> tuple[bool, str]:
    """修复文件内容中的路径"""
    original = content
    modified = False
    
    # 替换 ~/.real -> ~/.real
    for old, new in PATH_MAPPINGS.items():
        if old in content:
            content = content.replace(old, new)
            modified = True
    
    # 处理 Mac 特定路径 - 改为注释或移除
    for mac_path in MAC_SPECIFIC_PATHS:
        if mac_path in content:
            # 替换为合理的 Unix 路径或移除
            content = content.replace(mac_path, str(Path.home() / ".real"))
            modified = True
    
    return modified, content

def process_file(filepath: Path) -> bool:
    """处理单个文件"""
    if should_skip_file(str(filepath)):
        return False
    
    # 只处理文本文件
    text_extensions = {'.py', '.sh', '.yaml', '.yml', '.json', '.md', '.txt', '.toml'}
    if filepath.suffix not in text_extensions:
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return False
    
    modified, new_content = fix_content(content)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    
    return False

def scan_and_fix(root_dir: Path) -> list[tuple[Path, str]]:
    """扫描并修复目录中的所有文件"""
    fixed_files = []
    
    for filepath in root_dir.rglob('*'):
        if filepath.is_file() and not should_skip_file(str(filepath)):
            if process_file(filepath):
                fixed_files.append((filepath, "路径已修复"))
    
    return fixed_files

def main():
    clawshell_dir = Path.home() / ".ClawShell"
    
    if not clawshell_dir.exists():
        print(f"错误: ClawShell目录不存在: {clawshell_dir}")
        return
    
    print(f"开始扫描: {clawshell_dir}")
    print("=" * 60)
    
    fixed = scan_and_fix(clawshell_dir)
    
    print(f"\n修复完成! 共修复 {len(fixed)} 个文件:\n")
    for filepath, status in fixed:
        print(f"  ✅ {filepath.relative_to(clawshell_dir)}")

if __name__ == "__main__":
    main()
