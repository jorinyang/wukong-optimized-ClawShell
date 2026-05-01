#!/usr/bin/env python3
"""
Update Indexer - 自动更新Obsidian更新索引 v3.0
功能：
1. 扫描更新目录
2. 更新主索引 README.md
3. 更新月度索引
4. 同步更新系统架构文档 (00-SYSTEM_ARCHITECTURE.md)

用法：
    python3 ~/.real/scripts/update_indexer.py
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================

OBSIDIAN_UPDATE_DIR = Path.home() / "Documents/Obsidian/OpenClaw/Other/Update"
MAIN_INDEX = OBSIDIAN_UPDATE_DIR / "README.md"
SYSTEM_ARCH = OBSIDIAN_UPDATE_DIR / "00-SYSTEM_ARCHITECTURE.md"
MONTHLY_DIR = OBSIDIAN_UPDATE_DIR / "202604"

# ==================== 解析器 ====================

def parse_update_file(file_path):
    """解析更新文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取版本号 (文件名格式: yyyymmdd-xxx.md)
        filename = file_path.stem
        version_match = re.match(r'^(\d{8})', filename)
        version = version_match.group(1) if version_match else ""
        
        # 提取日期
        date_match = re.search(r'> 日期: (\d{4}-\d{2}-\d{2})', content)
        date = date_match.group(1) if date_match else ""
        
        # 提取类型
        type_match = re.search(r'> 类型: (.+)', content)
        update_type = type_match.group(1).strip() if type_match else "未知"
        
        # 提取摘要
        summary_match = re.search(r'## 变更摘要\s+(.+?)(?:\n##|\n\n|\n---)', content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""
        
        return {
            'version': version,
            'date': date,
            'type': update_type,
            'summary': summary,
            'file': file_path.name,
            'path': str(file_path.relative_to(OBSIDIAN_UPDATE_DIR))
        }
    except Exception as e:
        print(f"⚠️ 解析失败: {file_path.name} - {e}")
        return None

def get_type_icon(update_type):
    """获取类型图标"""
    icons = {
        '技能学习': '🧠',
        '插件安装与配置': '🔌',
        '优化方案': '⚡',
        '机制构建': '🏗️',
        '系统配置': '⚙️',
        'Bug修复': '🐛'
    }
    return icons.get(update_type, '📝')

def scan_updates():
    """扫描所有更新文件"""
    updates = []
    
    if not MONTHLY_DIR.exists():
        print(f"⚠️ 目录不存在: {MONTHLY_DIR}")
        return updates
    
    for file in MONTHLY_DIR.glob("*.md"):
        if file.name != "README.md":
            update = parse_update_file(file)
            if update:
                updates.append(update)
    
    return sorted(updates, key=lambda x: x['date'] or '', reverse=True)

def rebuild_main_index(updates):
    """重建主索引"""
    # 生成表格行
    table_rows = []
    for u in updates:
        icon = get_type_icon(u['type'])
        link = f"[{u['version']}](./{u['path']})"
        summary = u['summary'][:45] + ('...' if len(u['summary']) > 45 else '')
        table_rows.append(f"| {link} | {u['date']} | {icon} | {summary} |")
    
    table_content = '\n'.join(table_rows)
    
    # 读取模板
    if not MAIN_INDEX.exists():
        print(f"❌ 主索引不存在: {MAIN_INDEX}")
        return
    
    with open(MAIN_INDEX, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 找到表格位置并替换
    lines = template.split('\n')
    new_lines = []
    skip_old_table = False
    table_replaced = False
    
    for line in lines:
        if '| 版本 | 日期 | 类别 | 摘要 |' in line:
            new_lines.append(line)
            new_lines.append("|------|------|------|------|")
            new_lines.append(table_content)
            skip_old_table = True
            table_replaced = True
            continue
        
        if skip_old_table:
            if line.startswith('|') and '---' not in line and line.strip() not in ('', '|'):
                continue
            skip_old_table = False
        
        new_lines.append(line)
    
    if not table_replaced:
        print("⚠️ 未找到表格位置，跳过替换")
    
    with open(MAIN_INDEX, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ 主索引已更新: {len(updates)} 条记录")

def update_monthly_index(updates):
    """更新月度索引"""
    monthly_index = MONTHLY_DIR / "README.md"
    
    # 按日期分组
    by_date = {}
    for u in updates:
        date = u['date'][:10] if u['date'] else '未知'
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(u)
    
    # 生成月度索引内容
    content = ["# 2026年4月更新\n", "> 月度更新索引\n", "---\n"]
    
    for date in sorted(by_date.keys(), reverse=True):
        content.append(f"\n## 📅 {date} 更新\n")
        content.append("| 版本 | 类型 | 摘要 |")
        content.append("|------|------|------|")
        
        for u in by_date[date]:
            icon = get_type_icon(u['type'])
            link = f"[{u['version']}](./{u['file']})"
            summary = u['summary'][:35] + ('...' if len(u['summary']) > 35 else '')
            content.append(f"| {link} | {icon} | {summary} |")
    
    content.append(f"\n---\n*月度索引最后更新: {datetime.now().strftime('%Y-%m-%d')}*\n")
    
    with open(monthly_index, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    
    print(f"✅ 月度索引已更新")

def update_system_architecture(updates):
    """更新系统架构文档"""
    if not SYSTEM_ARCH.exists():
        print(f"⚠️ 系统架构文档不存在: {SYSTEM_ARCH}")
        return
    
    # 读取当前文档
    with open(SYSTEM_ARCH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成新的版本历史表格
    new_versions = []
    for u in updates[:10]:  # 只取最新的10条
        icon = get_type_icon(u['type'])
        new_versions.append(f"| {u['version']} | {u['date']} | {icon} | {u['summary'][:40]}... |")
    
    version_table = '\n'.join(new_versions)
    
    new_history_section = f"""
## 十一、更新历史

| 版本 | 日期 | 类型 | 变更 |
|------|------|------|------|
{version_table}
"""
    
    # 更新最后更新时间
    content = re.sub(
        r'\*\*最后更新:.*\*\*',
        f'**最后更新: {datetime.now().strftime("%Y-%m-%d %H:%M")}**',
        content
    )
    
    # 找到最后一个 ## 十一、更新历史 的位置并替换之后的内容
    last_section_pos = content.rfind('## 十一、更新历史')
    
    if last_section_pos != -1:
        # 找到下一个 ## 章节（如果存在）
        next_section_pos = content.find('\n## ', last_section_pos + 1)
        
        if next_section_pos == -1:
            # 没有下一个章节，替换从 last_section_pos 到末尾的所有内容
            content = content[:last_section_pos] + new_history_section
        else:
            # 替换两个章节之间的内容
            content = content[:last_section_pos] + new_history_section + content[next_section_pos:]
        
        print(f"✅ 系统架构文档已同步更新")
    else:
        # 如果没找到，在文档末尾添加
        content += new_history_section
        print(f"✅ 系统架构文档已添加新章节")
    
    # 写回
    with open(SYSTEM_ARCH, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print(f"[Update Indexer v3.0] 扫描更新目录...")
    print(f"目录: {MONTHLY_DIR}")
    
    # 确保目录存在
    OBSIDIAN_UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    
    # 扫描更新
    updates = scan_updates()
    print(f"找到 {len(updates)} 条更新记录")
    
    if updates:
        rebuild_main_index(updates)
        update_monthly_index(updates)
        update_system_architecture(updates)
        
        print(f"\n📊 更新统计:")
        for u in updates[:5]:
            print(f"   {u['version']} | {u['date']} | {u['type']}")
        if len(updates) > 5:
            print(f"   ... 还有 {len(updates) - 5} 条")
    
    print("\n[Update Indexer] 完成")

if __name__ == "__main__":
    main()
