#!/usr/bin/env python3
"""
OpenClaw 自适应执行器 v1.0
功能：
1. 根据影响分析报告执行适配操作
2. 支持目录迁移、配置更新、技能同步
3. 生成回滚预案
4. 验证执行结果
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# ==================== 配置 ====================

BACKUP_DIR = "~/.real/backups"
ADAPTER_STATE_FILE = "~/.real/.adapter_state.json"
LOG_FILE = "~/.real/logs/adaptive_executor.log"

# ==================== 数据类 ====================

@dataclass
class AdaptationAction:
    """适配操作"""
    id: str
    type: str  # directory, config, skill, dependency
    target: str
    action: str  # migrate, update, sync, rollback
    command: Optional[str]
    rollback_command: Optional[str]
    status: str  # pending, executing, completed, failed, rolled_back
    executed_at: Optional[str]
    error: Optional[str]

@dataclass
class AdaptationResult:
    """执行结果"""
    timestamp: str
    total_actions: int
    success_count: int
    failed_count: int
    rolled_back_count: int
    actions: List[Dict]
    summary: str

# ==================== 适配器 ====================

class DirectoryAdapter:
    """目录适配器"""
    
    def __init__(self):
        self.source_dir = "~/.real"
        self.backup_dir = os.path.expanduser(BACKUP_DIR)
    
    def migrate_skills(self, old_path: str, new_path: str) -> AdaptationAction:
        """迁移skills目录"""
        action_id = f"migrate_skills_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        old = os.path.expanduser(old_path)
        new = os.path.expanduser(new_path)
        
        # 备份
        backup_path = os.path.join(self.backup_dir, f"skills_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        def migrate_cmd():
            os.makedirs(os.path.dirname(new), exist_ok=True)
            shutil.copytree(old, backup_path, dirs_exist_ok=True)
            shutil.move(old, new)
        
        def rollback_cmd():
            if os.path.exists(backup_path):
                shutil.move(backup_path, old)
        
        return AdaptationAction(
            id=action_id,
            type="directory",
            target=f"{old_path} → {new_path}",
            action="migrate",
            command="; ".join([f"cp -r {old} {backup_path}", f"mv {old} {new}"]) if os.path.exists(old) else None,
            rollback_command=f"mv {backup_path} {old}" if os.path.exists(backup_path) else None,
            status="pending",
            executed_at=None,
            error=None
        )
    
    def create_directory(self, path: str) -> AdaptationAction:
        """创建目录"""
        action_id = f"create_dir_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        expanded = os.path.expanduser(path)
        
        def create_cmd():
            os.makedirs(expanded, exist_ok=True)
        
        return AdaptationAction(
            id=action_id,
            type="directory",
            target=path,
            action="create",
            command=f"mkdir -p {path}",
            rollback_command=f"rmdir {path}" if os.path.exists(expanded) else None,
            status="pending",
            executed_at=None,
            error=None
        )


class ConfigAdapter:
    """配置适配器"""
    
    def __init__(self):
        self.config_file = "~/.real/openclaw.json"
        self.backup_dir = os.path.expanduser(BACKUP_DIR)
    
    def update_config(self, key: str, new_value: Any, config_path: str = None) -> AdaptationAction:
        """更新配置项"""
        action_id = f"update_config_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        config_file = os.path.expanduser(config_path or self.config_file)
        
        def update_cmd():
            with open(config_file) as f:
                config = json.load(f)
            
            # 备份
            backup_file = os.path.join(self.backup_dir, f"config_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
            with open(backup_file, "w") as f:
                json.dump(config, f, indent=2)
            
            # 更新
            keys = key.split(".")
            current = config
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = new_value
            
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
        
        def rollback_cmd():
            # 找到最新的备份文件并恢复
            backups = sorted([f for f in os.listdir(self.backup_dir) if f.startswith("config_")])
            if backups:
                latest = os.path.join(self.backup_dir, backups[-1])
                shutil.copy(latest, config_file)
        
        return AdaptationAction(
            id=action_id,
            type="config",
            target=f"{config_file}: {key}",
            action="update",
            command=f"python3 -c '...'  # 复杂操作使用脚本",
            rollback_command="恢复备份配置",
            status="pending",
            executed_at=None,
            error=None
        )


class SkillAdapter:
    """技能适配器"""
    
    def sync_skills(self) -> AdaptationAction:
        """同步技能"""
        action_id = f"sync_skills_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        def sync_cmd():
            # 触发技能同步
            subprocess.run([
                "python3", 
                "~/.real/scripts/skill_sync.py"
            ], capture_output=True)
        
        return AdaptationAction(
            id=action_id,
            type="skill",
            target="skills/",
            action="sync",
            command="python3 ~/.real/scripts/skill_sync.py",
            rollback_command=None,
            status="pending",
            executed_at=None,
            error=None
        )


class DependencyAdapter:
    """依赖适配器"""
    
    def check_dependency(self, dep_name: str) -> AdaptationAction:
        """检查依赖状态"""
        action_id = f"check_dep_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return AdaptationAction(
            id=action_id,
            type="dependency",
            target=dep_name,
            action="check",
            command=f"python3 ~/.real/scripts/openclaw_version_monitor.py",
            rollback_command=None,
            status="pending",
            executed_at=None,
            error=None
        )

# ==================== 执行器 ====================

class AdaptiveExecutor:
    """自适应执行器"""
    
    def __init__(self):
        self.dir_adapter = DirectoryAdapter()
        self.config_adapter = ConfigAdapter()
        self.skill_adapter = SkillAdapter()
        self.dep_adapter = DependencyAdapter()
        self.state_file = os.path.expanduser(ADAPTER_STATE_FILE)
        self.backup_dir = os.path.expanduser(BACKUP_DIR)
        
        # 确保目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def generate_actions_from_impact_report(self, impact_report_path: str = None) -> List[AdaptationAction]:
        """从影响报告生成适配动作"""
        if impact_report_path is None:
            impact_report_path = "~/.real/.impact_report.json"
        
        actions = []
        report_path = os.path.expanduser(impact_report_path)
        
        if not os.path.exists(report_path):
            print(f"[WARN] 影响报告不存在: {report_path}")
            return actions
        
        with open(report_path) as f:
            report = json.load(f)
        
        # 根据变更生成动作
        for change in report.get("changes", []):
            change_type = change.get("type", "")
            risk = change.get("risk_level", "")
            
            # 高风险变更需要适配
            if risk in ["HIGH", "CRITICAL"]:
                if change_type == "ARCHITECTURE":
                    # 目录变更
                    areas = change.get("affected_areas", [])
                    if "skills" in areas:
                        actions.append(
                            self.dir_adapter.migrate_skills(
                                "~/.real/skills",
                                "~/.real/workspace/skills"
                            )
                        )
                elif change_type == "INTERFACE":
                    # 接口变更 - 检查技能
                    actions.append(self.skill_adapter.sync_skills())
        
        # 检查受影响的依赖
        for dep in report.get("affected_dependencies", []):
            dep_name = dep.get("dependency", "")
            if dep.get("overall_risk") in ["HIGH", "CRITICAL"]:
                actions.append(self.dep_adapter.check_dependency(dep_name))
        
        return actions
    
    def execute_action(self, action: AdaptationAction) -> AdaptationAction:
        """执行单个动作"""
        action.status = "executing"
        action.executed_at = datetime.now().isoformat()
        
        if not action.command:
            action.status = "skipped"
            return action
        
        try:
            # 执行命令
            result = subprocess.run(
                action.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                action.status = "completed"
            else:
                action.status = "failed"
                action.error = result.stderr[:500] if result.stderr else "Unknown error"
        
        except subprocess.TimeoutExpired:
            action.status = "failed"
            action.error = "Execution timeout"
        except Exception as e:
            action.status = "failed"
            action.error = str(e)
        
        return action
    
    def rollback_action(self, action: AdaptationAction) -> AdaptationAction:
        """回滚动作"""
        if not action.rollback_command:
            action.status = "rolled_back"
            return action
        
        try:
            result = subprocess.run(
                action.rollback_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                action.status = "rolled_back"
            else:
                action.error = f"Rollback failed: {result.stderr}"
        
        except Exception as e:
            action.error = f"Rollback error: {str(e)}"
        
        return action
    
    def execute_all(self, actions: List[AdaptationAction], dry_run: bool = False) -> AdaptationResult:
        """执行所有动作"""
        timestamp = datetime.now().isoformat()
        success_count = 0
        failed_count = 0
        rolled_back_count = 0
        
        results = []
        
        for action in actions:
            print(f"\n[{'DRY-RUN' if dry_run else 'EXEC'}] {action.id}: {action.type} - {action.action}")
            print(f"  Target: {action.target}")
            
            if dry_run:
                results.append(asdict(action))
                continue
            
            # 执行
            executed = self.execute_action(action)
            results.append(asdict(executed))
            
            if executed.status == "completed":
                success_count += 1
            elif executed.status == "failed":
                failed_count += 1
                # 尝试回滚
                print(f"  ⚠️ Failed: {executed.error}")
                print(f"  Attempting rollback...")
                rolled = self.rollback_action(executed)
                results[-1] = asdict(rolled)
                if rolled.status == "rolled_back":
                    rolled_back_count += 1
        
        # 生成总结
        summary = f"执行完成: {success_count}成功, {failed_count}失败, {rolled_back_count}已回滚"
        
        return AdaptationResult(
            timestamp=timestamp,
            total_actions=len(actions),
            success_count=success_count,
            failed_count=failed_count,
            rolled_back_count=rolled_back_count,
            actions=results,
            summary=summary
        )
    
    def save_state(self, result: AdaptationResult):
        """保存执行状态"""
        with open(self.state_file, "w") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
    
    def generate_backup_manifest(self) -> str:
        """生成备份清单"""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "backup_dir": self.backup_dir,
            "files": []
        }
        
        if os.path.exists(self.backup_dir):
            for root, dirs, files in os.walk(self.backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    manifest["files"].append(file_path)
        
        return json.dumps(manifest, indent=2)

# ==================== 主函数 ====================

def main():
    """主函数"""
    print(f"[Adaptive Executor] 启动... {datetime.now().isoformat()}")
    
    executor = AdaptiveExecutor()
    
    # 解析参数
    dry_run = "--dry-run" in sys.argv
    report_path = None
    
    for arg in sys.argv[1:]:
        if arg.endswith(".json") and os.path.exists(os.path.expanduser(arg)):
            report_path = arg
    
    # 生成动作
    print("\n📋 从影响报告生成适配动作...")
    actions = executor.generate_actions_from_impact_report(report_path)
    
    if not actions:
        print("未生成任何动作（可能无需适配）")
        return 0
    
    print(f"生成 {len(actions)} 个动作:")
    for action in actions:
        print(f"  - [{action.type}] {action.target}: {action.action}")
    
    # 执行
    print("\n🚀 开始执行...")
    result = executor.execute_all(actions, dry_run=dry_run)
    
    # 输出结果
    print("\n" + "="*60)
    print("执行结果".center(50))
    print("="*60)
    print(f"\n{result.summary}")
    print(f"总动作: {result.total_actions}")
    print(f"成功: {result.success_count}")
    print(f"失败: {result.failed_count}")
    print(f"已回滚: {result.rolled_back_count}")
    
    # 保存状态
    executor.save_state(result)
    print(f"\n✅ 状态已保存到 {executor.state_file}")
    
    # 生成备份清单
    manifest = executor.generate_backup_manifest()
    manifest_file = os.path.join(executor.backup_dir, "manifest.json")
    with open(manifest_file, "w") as f:
        f.write(manifest)
    print(f"✅ 备份清单已生成: {manifest_file}")
    
    return 0 if result.failed_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
