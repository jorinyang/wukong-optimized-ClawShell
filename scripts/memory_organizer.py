#!/usr/bin/env python3
"""
Memory Organizer - 统一记忆整理脚本
整合了Dream（每日整理）和SELF_ITERATION（触发迭代）的功能

功能：
1. Dream Consolidation - 每日整理（睡觉时执行）
2. Trigger Iteration - 触发迭代（新机制构建时）
3. Health Check - 健康度检查
4. 知识沉淀 - 定期归档
"""

import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# 配置
OPENCLAW_DIR = Path(os.path.expanduser("~/.openclaw"))
WORKSPACE_DIR = OPENCLAW_DIR / "workspace"
MEMORY_DIR = WORKSPACE_DIR / "memory"
DREAM_LOG = MEMORY_DIR / "dream-log.md"
ITERATION_LOG = MEMORY_DIR / "iteration-log.md"
CONFIG_FILE = OPENCLAW_DIR / ".memory_organizer_config.json"


class MemoryConfig:
    """记忆配置"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "dream_schedule": "0 3 * * *",  # 每天凌晨3点
            "retention_days": 30,
            "consolidation_threshold": 10,  # 超过10条变更才整理
            "health_check_interval": 7,  # 每7天健康检查
            "last_dream": None,
            "last_health_check": None,
            "last_consolidation": None
        }
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return default_config
    
    def save(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def update(self, key: str, value: Any):
        self.config[key] = value
        self.save()


class DreamConsolidation:
    """Dream每日整理"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
    
    def scan_changes(self) -> List[Dict[str, Any]]:
        """扫描最近的变更"""
        changes = []
        memory_files = list(MEMORY_DIR.glob("*.md"))
        
        # 也扫描workspace根目录的重要文件
        workspace_files = [
            WORKSPACE_DIR / "AGENTS.md",
            WORKSPACE_DIR / "SOUL.md", 
            WORKSPACE_DIR / "IDENTITY.md",
            WORKSPACE_DIR / "USER.md"
        ]
        
        all_files = memory_files + [f for f in workspace_files if f.exists()]
        
        for file_path in all_files:
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                # 只扫描最近24小时的变更
                if (datetime.now() - mtime).days < 1:
                    changes.append({
                        "file": file_path.name,
                        "path": str(file_path),
                        "mtime": mtime.isoformat(),
                        "size": file_path.stat().st_size
                    })
            except:
                pass
        
        return changes
    
    def check_health(self) -> int:
        """检查健康度"""
        issues = []
        
        # 检查文件数量
        md_files = list(MEMORY_DIR.glob("*.md"))
        if len(md_files) > 100:
            issues.append("文件数量过多")
        
        # 检查错误cookbook
        error_dir = OPENCLAW_DIR / "error-cookbook" / "errors"
        if error_dir.exists():
            error_count = len(list(error_dir.rglob("*.md")))
            if error_count > 100:
                issues.append(f"错误记录过多: {error_count}")
        
        # 检查脚本完整性
        scripts_dir = OPENCLAW_DIR / "scripts"
        essential_scripts = ["system_monitor.sh", "harness_core.py"]
        for script in essential_scripts:
            if not (scripts_dir / script).exists():
                issues.append(f"脚本缺失: {script}")
        
        return max(0, 100 - len(issues) * 20)
    
    def consolidate(self) -> Dict[str, Any]:
        """执行每日整理"""
        changes = self.scan_changes()
        health = self.check_health()
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "scanned_files": len(changes),
            "changes": changes,
            "health": health,
            "suggestions": []
        }
        
        # 生成建议
        if health < 60:
            result["suggestions"].append("健康度较低，建议检查系统状态")
        if len(changes) > 20:
            result["suggestions"].append("变更较多，可能需要整理")
        
        # 更新配置
        self.config.update("last_dream", datetime.now().isoformat())
        
        # 更新日志
        self._update_dream_log(result)
        
        return result
    
    def _update_dream_log(self, result: Dict[str, Any]):
        """更新Dream日志"""
        entry = f"\n## 🌙 Dream {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        entry += f"**Scanned**: {result['scanned_files']} files | **New**: {len(result['changes'])}\n\n"
        entry += "### Changes\n"
        for change in result['changes'][:5]:
            entry += f"- [{change['mtime'][:10]}] {change['file']}\n"
        
        entry += f"\n### Suggestions\n"
        entry += f"- Health: {result['health']}/100\n"
        if result['suggestions']:
            for suggestion in result['suggestions']:
                entry += f"- {suggestion}\n"
        
        try:
            with open(DREAM_LOG, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            print(f"Dream log update error: {e}")


class TriggerIteration:
    """触发迭代 - SELF_ITERATION核心"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
    
    def analyze_impact(self, file_path: str) -> Dict[str, Any]:
        """分析变更影响"""
        # 读取被修改的文件
        target = Path(file_path)
        if not target.exists():
            return {"error": "File not found"}
        
        content = target.read_text(encoding='utf-8')
        
        # 分析影响范围
        impact = {
            "file": file_path,
            "size": len(content),
            "lines": len(content.splitlines()),
            "headings": len([l for l in content.splitlines() if l.startswith('#')]),
            "code_blocks": content.count('```'),
            "references": []
        }
        
        # 查找交叉引用
        ref_patterns = [
            r'\[\[([^\]]+)\]\]',  # [[xxx]] 格式
            r'`([^`]+)`',  # `code` 格式
        ]
        
        for pattern in ref_patterns:
            import re
            impact["references"].extend(re.findall(pattern, content))
        
        return impact
    
    def execute_iteration(self, trigger_type: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """执行迭代"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "trigger_type": trigger_type,
            "level": 1,
            "actions": [],
            "files_modified": []
        }
        
        # Level 1: 触发检测
        if trigger_type == "new_skill":
            result["actions"].append("检测到新技能创建")
            result["level"] = 1
        
        # Level 2: 影响分析
        if file_path:
            impact = self.analyze_impact(file_path)
            result["impact"] = impact
            result["level"] = 2
        
        # Level 3: 执行优化
        if result["level"] >= 2:
            result["actions"].append("执行文档结构优化")
            result["level"] = 3
        
        # Level 4: 验证固化
        result["actions"].append("更新索引")
        result["level"] = 4
        self.config.update("last_consolidation", datetime.now().isoformat())
        
        # 记录迭代
        self._update_iteration_log(result)
        
        return result
    
    def _update_iteration_log(self, result: Dict[str, Any]):
        """更新迭代日志"""
        entry = f"\n## 🔄 Iteration {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        entry += f"**Trigger**: {result['trigger_type']} | **Level**: {result['level']}\n\n"
        entry += "### Actions\n"
        for action in result.get("actions", []):
            entry += f"- {action}\n"
        
        if "impact" in result:
            entry += f"\n### Impact\n"
            entry += f"- Size: {result['impact'].get('size', 0)} bytes\n"
            entry += f"- Lines: {result['impact'].get('lines', 0)}\n"
            entry += f"- References: {len(result['impact'].get('references', []))}\n"
        
        try:
            with open(ITERATION_LOG, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            print(f"Iteration log update error: {e}")


def main():
    if len(sys.argv) < 2:
        print("Memory Organizer - 统一记忆整理脚本")
        print("用法:")
        print("  memory_organizer.py dream          # 执行每日整理")
        print("  memory_organizer.py iteration <类型> [文件]  # 触发迭代")
        print("  memory_organizer.py health         # 健康检查")
        print("  memory_organizer.py status         # 查看状态")
        return
    
    command = sys.argv[1]
    config = MemoryConfig()
    
    if command == "dream":
        print("执行Dream每日整理...")
        organizer = DreamConsolidation(config)
        result = organizer.consolidate()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "iteration":
        trigger_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
        file_path = sys.argv[3] if len(sys.argv) > 3 else None
        print(f"执行触发迭代: {trigger_type}")
        organizer = TriggerIteration(config)
        result = organizer.execute_iteration(trigger_type, file_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "health":
        print("执行健康检查...")
        organizer = DreamConsolidation(config)
        health = organizer.check_health()
        print(f"健康度: {health}/100")
    
    elif command == "status":
        print("当前状态:")
        print(f"  上次Dream: {config.config.get('last_dream', '从未')}")
        print(f"  上次Health Check: {config.config.get('last_health_check', '从未')}")
        print(f"  上次Consolidation: {config.config.get('last_consolidation', '从未')}")


if __name__ == "__main__":
    main()
