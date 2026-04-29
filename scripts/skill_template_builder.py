#!/usr/bin/env python3
"""
Skill Template Builder - 技能模板构建器
功能：
1. 监听hermes_insights/applied中的技能模板
2. 验证模板完整性
3. 生成可执行的技能文件
4. 注册新技能
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 配置
OPENCLAW_DIR = Path.home() / ".openclaw"
SKILLS_DIR = OPENCLAW_DIR / "workspace" / "skills"
TEMPLATE_DIR = OPENCLAW_DIR / "shared" / "hermes_insights" / "applied"
TEMPLATE_BACKUP = OPENCLAW_DIR / "shared" / "hermes_insights" / "skill_templates"
LOG_FILE = OPENCLAW_DIR / "logs" / "skill_builder.log"


class SkillTemplateBuilder:
    """技能模板构建器"""
    
    def __init__(self):
        TEMPLATE_BACKUP.mkdir(parents=True, exist_ok=True)
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _log(self, msg: str):
        """写日志"""
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {msg}\n")
    
    def poll_templates(self) -> int:
        """轮询并处理技能模板"""
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        processed = 0
        
        for template_file in TEMPLATE_DIR.glob("skill_template_*.json"):
            try:
                if self._validate_and_build(template_file):
                    processed += 1
            except Exception as e:
                self._log(f"Error: {template_file.name}: {e}")
        
        return processed
    
    def _validate_and_build(self, template_path: Path) -> bool:
        """验证并构建技能"""
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        # 验证必要字段
        if not self._validate_template(template):
            self._log(f"Invalid template: {template_path.name}")
            return False
        
        # 生成技能文件
        skill_name = template.get("template", {}).get("name")
        skill_path = SKILLS_DIR / skill_name
        
        self._create_skill(skill_path, template)
        self._log(f"Created skill: {skill_name}")
        
        # 移动模板到备份
        shutil.move(str(template_path), str(TEMPLATE_BACKUP / template_path.name))
        
        return True
    
    def _validate_template(self, template: Dict) -> bool:
        """验证模板完整性"""
        required_fields = ["stream_type", "template"]
        for field in required_fields:
            if field not in template:
                return False
        
        template_data = template.get("template", {})
        required_template_fields = ["name", "description", "trigger_conditions", "actions"]
        for field in required_template_fields:
            if field not in template_data:
                return False
        
        return True
    
    def _create_skill(self, skill_path: Path, template: Dict):
        """创建技能文件"""
        skill_path.mkdir(parents=True, exist_ok=True)
        template_data = template.get("template", {})
        
        # 创建SKILL.md
        skill_md = self._generate_skill_md(template_data)
        with open(skill_path / "SKILL.md", 'w') as f:
            f.write(skill_md)
        
        # 创建主脚本
        main_script = self._generate_main_script(template_data)
        script_name = template_data.get("name", "skill").replace("-", "_")
        with open(skill_path / f"{script_name}.py", 'w') as f:
            f.write(main_script)
        
        # 设置执行权限
        os.chmod(skill_path / f"{script_name}.py", 0o755)
    
    def _generate_skill_md(self, template: Dict) -> str:
        """生成SKILL.md内容"""
        trigger_lines = []
        for tc in template.get("trigger_conditions", []):
            trigger_lines.append(f"- {tc}")
        
        actions_lines = []
        for action in template.get("actions", []):
            action_str = f"- type: {action.get('type')}"
            if 'target' in action:
                action_str += f", target: {action.get('target')}"
            if 'pattern' in action:
                action_str += f", pattern: {action.get('pattern')}"
            actions_lines.append(action_str)
        
        trigger_text = "\n".join(trigger_lines) if trigger_lines else "- 无"
        actions_text = "\n".join(actions_lines) if actions_lines else "- 无"
        
        md_content = f"""# {template['name']}

> 自动生成的技能模板
> 创建时间: {datetime.now().isoformat()}

## 描述

{template.get('description', '')}

## 触发条件

{trigger_text}

## 执行动作

{actions_text}

## 输出格式

{template.get('output_format', 'text')}

---

*此技能由Hermes自动生成*
"""
        return md_content
    
    def _generate_main_script(self, template: Dict) -> str:
        """生成主脚本"""
        skill_name = template.get("name", "skill")
        script_name = skill_name.replace("-", "_")
        
        script_content = f'''#!/usr/bin/env python3
"""
{skill_name} - 自动生成的技能脚本
由Hermes自动生成
创建时间: {datetime.now().isoformat()}
"""

import sys
import json
from datetime import datetime
from pathlib import Path

SKILL_NAME = "{skill_name}"
SKILL_VERSION = "1.0.0"


def main():
    """主执行函数"""
    print(f"[{{SKILL_NAME}}] v{{SKILL_VERSION}}")
    print(f"执行时间: {{datetime.now().isoformat()}}")
    
    # TODO: 实现技能逻辑
    print("技能执行中...")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
        return script_content


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Template Builder")
    parser.add_argument("--dry-run", action="store_true", help="仅显示待处理模板")
    args = parser.parse_args()
    
    builder = SkillTemplateBuilder()
    
    if args.dry_run:
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        templates = list(TEMPLATE_DIR.glob("skill_template_*.json"))
        print(f"待处理模板: {len(templates)}")
        for f in templates:
            print(f"  - {f.name}")
    else:
        processed = builder.poll_templates()
        print(f"处理完成: {processed}个模板")


if __name__ == "__main__":
    main()
