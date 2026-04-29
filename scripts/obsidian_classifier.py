#!/usr/bin/env python3
"""
Obsidian知识库自动分类+标签引擎
根据内容特征自动分类笔记到对应目录，并提取标签
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime

# 分类关键词配置
CLASSIFICATION_RULES = {
    "Work": {
        "keywords": [
            # 工作/客户相关
            "客户", "项目", "方案", "合同", "报价", "交付",
            "客户名称", "甲方", "乙方", "商务", "谈判",
            "工作", "任务", "报告", "总结", "计划", "会议",
            "同事", "领导", "团队", "部门", "公司",
            "阳光集团", "企业", "数字化", "转型"
        ],
        "patterns": [
            r"客户[^\s]*",
            r"项目[^\s]*",
            r"工作[^\s]*",
            r"方案[^\s]*",
        ]
    },
    "Learn": {
        "keywords": [
            # 系统化知识/规律性学习
            "学习", "教程", "课程", "培训", "理论",
            "概念", "原理", "方法论", "框架", "模型",
            "知识点", "概念", "定义", "理论", "基础",
            "AI", "大模型", "Agent", "VibeCoding", "悟空",
            "编程", "开发", "语言", "框架", "库"
        ],
        "patterns": [
            r"学习[^\s]*",
            r"教程[^\s]*",
            r"课程[^\s]*",
            r"培训[^\s]*",
        ]
    },
    "Research": {
        "keywords": [
            # 主动探索研究
            "研究", "探索", "实验", "测试", "尝试",
            "OpenClaw", "Hermes", "Harness", "Agent集群",
            "协议", "架构", "设计", "分析", "调研",
            "技术", "实现", "源码", "代码", "开发",
            "配置", "安装", "调试", "优化"
        ],
        "patterns": [
            r"研究[^\s]*",
            r"探索[^\s]*",
            r"测试[^\s]*",
            r"实验[^\s]*",
        ]
    },
    "Life": {
        "keywords": [
            # 爱好/娱乐/财务/家庭
            "生活", "日常", "家庭", "孩子", "女儿",
            "爱好", "娱乐", "休闲", "电影", "音乐",
            "财务", "理财", "支出", "收入", "账单",
            "旅行", "运动", "健身", "饮食", "购物",
            "小米", "Su7", "汽车", "手机"
        ],
        "patterns": [
            r"生活[^\s]*",
            r"家庭[^\s]*",
            r"财务[^\s]*",
            r"爱好[^\s]*",
        ]
    }
}

# 标签提取规则
TAG_RULES = {
    "Agents": {
        "keywords": [
            "agent", "agents", "multi-agent", "集群", "协作", "分工",
            "coordinator", "executor", "worker", "manager"
        ],
        "patterns": []
    },
    "Claude Code": {
        "keywords": [
            "claude code", "claude-code", "codex", "cursor", "copilot",
            "@code", "ide plugin"
        ],
        "patterns": []
    },
    "LLM": {
        "keywords": [
            "llm", "language model", "大模型", "语言模型", "GPT", "Claude",
            "Gemini", "Kimi", "Minimax", "Qwen", "deepseek", "embedding",
            "RAG", "向量", "token", "上下文"
        ],
        "patterns": []
    },
    "Tools": {
        "keywords": [
            "tool", "tools", "mcp", "browser", "shell", "exec",
            "function call", "api", "接口"
        ],
        "patterns": []
    },
    "Skills": {
        "keywords": [
            "skill", "skills", "skill.md", "agent skill", "capability",
            "技能", "工具箱"
        ],
        "patterns": []
    },
    "Knowledge": {
        "keywords": [
            "knowledge", "knowledge base", "知识库", "知识图谱", "graph",
            "wiki", "文档", "笔记", "note"
        ],
        "patterns": []
    },
    "OpenClaw": {
        "keywords": [
            "openclaw", "open-claw", "clawdbot", "gateway", "plugin",
            "extension", "channel", "session", "agent"
        ],
        "patterns": []
    },
    "Harness": {
        "keywords": [
            "harness", "engineering", "cli-anything", "opencli",
            "agent harness", "测试框架", "自动化测试"
        ],
        "patterns": []
    },
    "OPC": {
        "keywords": [
            "opc", "opt", "optimization", "optimise", "性能优化",
            "效率", "performance", "效率优化"
        ],
        "patterns": []
    }
}

# 优先级：Work > Learn > Research > Life > Other
PRIORITY = ["Work", "Learn", "Research", "Life"]

def classify_content(content: str) -> tuple[str, dict]:
    """
    根据内容分类笔记
    返回: (分类, 匹配详情)
    """
    scores = {}
    details = {}
    
    for category, rules in CLASSIFICATION_RULES.items():
        score = 0
        matches = []
        
        # 关键词匹配
        for keyword in rules["keywords"]:
            if keyword.lower() in content.lower():
                score += 1
                matches.append(f"keyword:{keyword}")
        
        # 正则匹配
        for pattern in rules.get("patterns", []):
            if re.search(pattern, content):
                score += 2  # 正则权重更高
                matches.append(f"pattern:{pattern}")
        
        if score > 0:
            scores[category] = score
            details[category] = matches
    
    # 按优先级选择最高分类
    for cat in PRIORITY:
        if cat in scores:
            return cat, details[cat]
    
    return "Other", {}


def extract_tags(content: str) -> list:
    """
    根据内容提取标签
    返回: 匹配的标签列表
    """
    tags = []
    
    for tag, rules in TAG_RULES.items():
        matched = False
        
        # 关键词匹配
        for keyword in rules.get("keywords", []):
            if keyword.lower() in content.lower():
                matched = True
                break
        
        # 正则匹配
        if not matched:
            for pattern in rules.get("patterns", []):
                if re.search(pattern, content, re.IGNORECASE):
                    matched = True
                    break
        
        if matched:
            tags.append(tag)
    
    return tags


def classify_file(filepath: str, dry_run: bool = False) -> dict:
    """
    分类单个文件
    """
    vault_path = Path("/Users/yangyang/Documents/Obsidian/OpenClaw")
    file_path = Path(filepath)
    
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}
    
    # 提取YAML frontmatter和正文
    frontmatter = ""
    body = content
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
    
    # 合并frontmatter和body进行分类
    full_content = frontmatter + body
    category, matches = classify_content(full_content)
    
    # 提取标签
    tags = extract_tags(full_content)
    
    # 确定目标路径
    type_subdir = detect_type(file_path.name, body)
    
    # 计划/待办/日程 → 归入 Other（直接归入 Other/Plan, Other/Schedule, Other/Todo）
    if type_subdir is None:
        category = "Other"
        # detect_type 返回 None 时，需要根据文件名判断具体子目录
        name_lower = file_path.name.lower()
        if "plan" in name_lower or "计划" in name_lower:
            type_subdir = "Plan"
        elif "todo" in name_lower or "待办" in name_lower:
            type_subdir = "Todo"
        elif "schedule" in name_lower or "日程" in name_lower:
            type_subdir = "Schedule"
        else:
            type_subdir = "Plan"  # 默认归入 Plan
    
    target_dir = vault_path / category / type_subdir
    target_path = target_dir / file_path.name
    
    result = {
        "file": str(file_path),
        "category": category,
        "type": type_subdir,
        "tags": tags,
        "target": str(target_path),
        "matches": matches,
        "action": "move" if not dry_run else "would_move"
    }
    
    if not dry_run:
        # 移动文件
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(target_path))
            result["status"] = "success"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
    else:
        result["status"] = "dry_run"
    
    return result


def detect_type(filename: str, content: str) -> str:
    """
    检测笔记类型（新：Knowledge/Tools/Input/Output）
    计划/待办/日程 → 返回 None，交给调用方处理归入 Other
    """
    name_lower = filename.lower()
    content_lower = content.lower()
    
    # 计划/待办/日程 → 返回 None，调用方会将其归入 Other
    if "plan" in name_lower or "计划" in name_lower:
        return None
    if "todo" in name_lower or "待办" in name_lower:
        return None
    if "schedule" in name_lower or "日程" in name_lower:
        return None
    
    # 从内容检测
    if "计划" in content_lower or "目标" in content_lower:
        return None
    if "待办" in content_lower or "任务清单" in content_lower:
        return None
    if "日程" in content_lower or "会议" in content_lower:
        return None
    
    # 二级分类：Knowledge/Tools/Input/Output
    if "知识" in content_lower or "概念" in content_lower or "原理" in content_lower:
        return "Knowledge"
    if "工具" in content_lower or "方法" in content_lower or "脚本" in content_lower:
        return "Tools"
    if "素材" in content_lower or "原始" in content_lower or "原文" in content_lower or "input" in name_lower:
        return "Input"
    if "output" in name_lower or "成果" in content_lower or "总结" in content_lower or "产出" in content_lower:
        return "Output"
    
    # 默认归类逻辑
    # 文章类（公众号文章、博客）默认 Knowledge
    if "article" in name_lower or "post" in name_lower or "文章" in content_lower:
        return "Knowledge"
    # 教程/课程类默认 Knowledge
    if "tutorial" in name_lower or "教程" in content_lower or "课程" in content_lower:
        return "Knowledge"
    
    return "Knowledge"  # 默认


def classify_directory(dir_path: str, dry_run: bool = False) -> list:
    """
    分类目录下的所有markdown文件
    """
    results = []
    dir_path = Path(dir_path)
    
    for md_file in dir_path.rglob("*.md"):
        # 跳过目录和模板
        if "_templates" in str(md_file) or "CATEGORIES" in md_file.name:
            continue
        
        result = classify_file(str(md_file), dry_run=dry_run)
        results.append(result)
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Obsidian知识库自动分类引擎")
    parser.add_argument("path", help="文件或目录路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("--status", action="store_true", help="显示分类状态")
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"错误: 路径不存在 - {path}")
        return
    
    if args.status:
        # 显示分类统计
        print("=== 分类统计 ===")
        vault = Path("/Users/yangyang/Documents/Obsidian/OpenClaw")
        for cat in ["Work", "Learn", "Research", "Life", "Other"]:
            cat_path = vault / cat
            if cat_path.exists():
                count = len(list(cat_path.rglob("*.md")))
                print(f"{cat}: {count} 篇")
        return
    
    if path.is_file():
        result = classify_file(str(path), dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        results = classify_directory(str(path), dry_run=args.dry_run)
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
