#!/usr/bin/env python3
"""
Report Template Engine - 报告模板引擎
功能：
1. 管理报告模板
2. 变量替换
3. 自定义模板
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

TEMPLATE_DIR = Path.home() / ".openclaw/templates"
TEMPLATE_CONFIG = TEMPLATE_DIR / "templates.json"

# ==================== 模板引擎 ====================

class ReportTemplateEngine:
    def __init__(self):
        self.template_dir = TEMPLATE_DIR
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.templates = self.load_templates()
    
    def load_templates(self) -> Dict:
        """加载模板配置"""
        if TEMPLATE_CONFIG.exists():
            with open(TEMPLATE_CONFIG, 'r') as f:
                return json.load(f)
        
        return self._get_default_templates()
    
    def save_templates(self):
        """保存模板配置"""
        with open(TEMPLATE_CONFIG, 'w') as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)
    
    def _get_default_templates(self) -> Dict:
        """获取默认模板"""
        return {
            "daily": {
                "name": "日报模板",
                "file": "daily_template.md",
                "description": "每日工作汇报模板",
                "variables": ["{date}", "{tasks_completed}", "{tasks_in_progress}", "{notes}"]
            },
            "weekly": {
                "name": "周报模板",
                "file": "weekly_template.md",
                "description": "每周工作汇报模板",
                "variables": ["{week_number}", "{start_date}", "{end_date}", "{summary}", "{next_week_plan}"]
            },
            "monthly": {
                "name": "月报模板",
                "file": "monthly_template.md",
                "description": "每月工作汇报模板",
                "variables": ["{month}", "{year}", "{summary}", "{achievements}", "{next_month_plan}"]
            },
            "project": {
                "name": "项目报告模板",
                "file": "project_template.md",
                "description": "项目进度报告模板",
                "variables": ["{project_name}", "{progress}", "{issues}", "{next_steps}"]
            }
        }
    
    def render(self, template_name: str, variables: Dict) -> str:
        """渲染模板"""
        if template_name not in self.templates:
            return f"模板不存在: {template_name}"
        
        template_file = self.template_dir / self.templates[template_name]["file"]
        
        if not template_file.exists():
            return f"模板文件不存在: {template_file}"
        
        content = template_file.read_text()
        
        # 替换变量
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            content = content.replace(placeholder, str(value))
        
        # 处理未替换的变量
        import re
        remaining = re.findall(r'\{[^}]+\}', content)
        if remaining:
            content += f"\n\n<!-- 未替换的变量: {', '.join(set(remaining))} -->\n"
        
        return content
    
    def create_template(self, name: str, content: str, description: str = "") -> bool:
        """创建模板"""
        if name in self.templates:
            return False
        
        filename = f"{name}_template.md"
        template_file = self.template_dir / filename
        
        with open(template_file, 'w') as f:
            f.write(content)
        
        # 提取变量
        import re
        variables = re.findall(r'\{([^}]+)\}', content)
        
        self.templates[name] = {
            "name": description or name,
            "file": filename,
            "description": description,
            "variables": list(set(variables))
        }
        
        self.save_templates()
        
        return True
    
    def delete_template(self, name: str) -> bool:
        """删除模板"""
        if name not in self.templates:
            return False
        
        template_info = self.templates[name]
        template_file = self.template_dir / template_info["file"]
        
        if template_file.exists():
            template_file.unlink()
        
        del self.templates[name]
        self.save_templates()
        
        return True
    
    def list_templates(self) -> List[Dict]:
        """列出所有模板"""
        templates = []
        
        for name, info in self.templates.items():
            templates.append({
                "name": name,
                "display_name": info["name"],
                "description": info.get("description", ""),
                "variables": info.get("variables", [])
            })
        
        return templates
    
    def get_template_info(self, name: str) -> Optional[Dict]:
        """获取模板信息"""
        if name not in self.templates:
            return None
        
        return self.templates[name]

# ==================== 主函数 ====================

def main():
    engine = ReportTemplateEngine()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  report_template.py list")
        print("  report_template.py info <name>")
        print("  report_template.py render <name> <var1=val1> ...")
        print("  report_template.py create <name> <description>")
        print("  report_template.py delete <name>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        templates = engine.list_templates()
        print(f"可用模板 ({len(templates)}个):\n")
        for t in templates:
            print(f"[{t['name']}] {t['display_name']}")
            print(f"  描述: {t['description']}")
            print(f"  变量: {', '.join(t['variables']) or '无'}")
            print()
    
    elif command == "info":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        info = engine.get_template_info(name)
        
        if info:
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print(f"模板不存在: {name}")
    
    elif command == "render":
        if len(sys.argv) < 3:
            print("用法: report_template.py render <name> <var1=val1> ...")
            sys.exit(1)
        
        name = sys.argv[2]
        variables = {}
        
        for arg in sys.argv[3:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                variables[key] = value
        
        result = engine.render(name, variables)
        print(result)
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("用法: report_template.py create <name> <description>")
            sys.exit(1)
        
        name = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        
        # 创建示例模板内容
        content = f"""# {{name}}报告

**日期**: {{{{date}}}}

---

## 内容

{{{{content}}}}

---

*由系统自动生成*
"""
        
        if engine.create_template(name, content, description):
            print(f"模板已创建: {name}")
        else:
            print(f"模板已存在: {name}")
    
    elif command == "delete":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        
        if engine.delete_template(name):
            print(f"模板已删除: {name}")
        else:
            print(f"模板不存在: {name}")
    
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()
