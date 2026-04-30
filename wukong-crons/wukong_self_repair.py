#!/usr/bin/env python3
"""
悟空自修复适配器
功能：检测并自动修复悟空常见问题，适配悟空MCP架构
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 跨平台编码配置
import locale
import platform
ENCODING = 'utf-8' if platform.system() != 'Windows' else 'utf-8'

# 设置控制台输出编码
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "self_repair.log", encoding=ENCODING),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 修复动作定义
REPAIR_ACTIONS = {
    # 模块导入问题
    "import_error": {
        "description": "模块导入失败",
        "actions": [
            {
                "name": "重新配置Python路径",
                "command": None,  # 通过代码修复
                "fix_func": "fix_import_path"
            },
            {
                "name": "重装ClawShell-Debug技能",
                "command": "skills reinstall clawshell-debug",
                "fix_func": None
            }
        ]
    },
    # 技能问题
    "skill_missing": {
        "description": "技能缺失",
        "actions": [
            {
                "name": "从本地重新安装技能",
                "command": "skills install local",
                "fix_func": None
            }
        ]
    },
    # 定时任务问题
    "cron_broken": {
        "description": "定时任务失效",
        "actions": [
            {
                "name": "重建定时任务配置",
                "command": None,
                "fix_func": "fix_cron_config"
            }
        ]
    },
    # 配置损坏
    "config_corrupted": {
        "description": "配置文件损坏",
        "actions": [
            {
                "name": "从备份恢复配置",
                "command": None,
                "fix_func": "restore_config"
            }
        ]
    },
    # 内存泄漏
    "memory_leak": {
        "description": "内存使用过高",
        "actions": [
            {
                "name": "清理缓存",
                "command": None,
                "fix_func": "clear_cache"
            },
            {
                "name": "重启悟空会话",
                "command": None,
                "fix_func": "restart_session"
            }
        ]
    },
    # 磁盘空间不足
    "disk_full": {
        "description": "磁盘空间不足",
        "actions": [
            {
                "name": "清理日志文件",
                "command": None,
                "fix_func": "clean_logs"
            },
            {
                "name": "清理缓存",
                "command": None,
                "fix_func": "clear_cache"
            }
        ]
    }
}


class WuKongSelfRepair:
    """悟空自修复系统"""

    def __init__(self):
        self.workspace_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace"
        self.config_dir = Path.home() / ".real" / ".config"
        self.log_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b"
        
        self.issues = []
        self.fixes_applied = []
        self.reports = []

    def detect_issues(self) -> List[Dict]:
        """检测问题"""
        logger.info("开始问题检测...")
        
        self.issues = []
        
        # 1. 检查模块导入
        self._check_module_imports()
        
        # 2. 检查系统资源
        self._check_system_resources()
        
        # 3. 检查定时任务
        self._check_cron_tasks()
        
        # 4. 检查配置文件
        self._check_config_files()
        
        # 5. 检查日志大小
        self._check_log_sizes()
        
        return self.issues

    def _check_module_imports(self):
        """检查模块导入"""
        modules_to_check = [
            ("lib.layer1.health_check", "HealthMonitor"),
            ("lib.core.eventbus", "EventBus"),
            ("lib.layer4.swarm", "NodeRegistry"),
        ]
        
        for module_path, class_name in modules_to_check:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent))
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name, None)
                if cls is None:
                    self.issues.append({
                        "type": "import_error",
                        "component": module_path,
                        "severity": "high",
                        "message": f"模块 {module_path} 导入失败"
                    })
            except Exception as e:
                self.issues.append({
                    "type": "import_error",
                    "component": module_path,
                    "severity": "high",
                    "message": f"模块 {module_path} 导入失败: {str(e)[:50]}"
                })

    def _check_system_resources(self):
        """检查系统资源"""
        try:
            import psutil
            
            # 内存检查
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.issues.append({
                    "type": "memory_leak",
                    "component": "system",
                    "severity": "high",
                    "message": f"内存使用率过高: {memory.percent}%"
                })
            
            # 磁盘检查
            disk = psutil.disk_usage('C:\\')
            if disk.percent > 90:
                self.issues.append({
                    "type": "disk_full",
                    "component": "disk",
                    "severity": "high",
                    "message": f"磁盘使用率过高: {disk.percent}%"
                })
                
        except ImportError:
            logger.warning("psutil未安装，跳过系统资源检查")
        except Exception as e:
            logger.warning(f"系统资源检查失败: {e}")

    def _check_cron_tasks(self):
        """检查定时任务"""
        cron_file = Path.home() / ".real" / "cron_tasks.json"
        
        if not cron_file.exists():
            self.issues.append({
                "type": "cron_broken",
                "component": "cron",
                "severity": "medium",
                "message": "定时任务配置文件不存在"
            })
            return
        
        try:
            with open(cron_file, 'r', encoding='utf-8') as f:
                cron_data = json.load(f)
                tasks = cron_data.get("tasks", [])
                
                # 检查是否有最近执行的任务
                if not tasks:
                    self.issues.append({
                        "type": "cron_broken",
                        "component": "cron",
                        "severity": "medium",
                        "message": "定时任务列表为空"
                    })
        except Exception as e:
            self.issues.append({
                "type": "config_corrupted",
                "component": "cron",
                "severity": "high",
                "message": f"定时任务配置损坏: {str(e)[:50]}"
            })

    def _check_config_files(self):
        """检查配置文件"""
        config_files = [
            Path.home() / ".real" / "config.json",
            self.workspace_dir / "config.json",
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    self.issues.append({
                        "type": "config_corrupted",
                        "component": str(config_file),
                        "severity": "high",
                        "message": f"配置文件 {config_file.name} 损坏"
                    })

    def _check_log_sizes(self):
        """检查日志大小"""
        log_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
        
        if log_dir.exists():
            total_size = 0
            for log_file in log_dir.glob("*.log"):
                total_size += log_file.stat().st_size
            
            # 超过100MB报警
            if total_size > 100 * 1024 * 1024:
                self.issues.append({
                    "type": "disk_full",
                    "component": "logs",
                    "severity": "medium",
                    "message": f"日志文件过大: {total_size / (1024*1024):.1f}MB"
                })

    # ==================== 修复函数 ====================

    def fix_import_path(self) -> Dict:
        """修复导入路径"""
        logger.info("执行: 修复导入路径")
        
        clawshell_path = Path(__file__).parent.parent
        pth_file = clawshell_path / "clawshell.pth"
        
        if not pth_file.exists():
            with open(pth_file, 'w', encoding='utf-8') as f:
                f.write(str(clawshell_path))
            logger.info(f"已创建: {pth_file}")
        
        return {"success": True, "message": "导入路径已修复"}

    def fix_cron_config(self) -> Dict:
        """重建定时任务配置"""
        logger.info("执行: 重建定时任务配置")
        
        cron_file = Path.home() / ".real" / "cron_tasks.json"
        cron_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 默认定时任务配置
        default_config = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "tasks": []
        }
        
        # 读取现有配置
        if cron_file.exists():
            try:
                with open(cron_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    default_config["tasks"] = existing.get("tasks", [])
            except:
                pass
        
        # 保存配置
        with open(cron_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已重建: {cron_file}")
        return {"success": True, "message": "定时任务配置已重建"}

    def restore_config(self, config_path: Path) -> Dict:
        """从备份恢复配置"""
        logger.info(f"执行: 从备份恢复配置 {config_path}")
        
        backup_dir = self.workspace_dir / "backups"
        
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            return {"success": False, "message": "无备份文件"}
        
        # 查找最新的备份
        backups = sorted(backup_dir.glob(f"{config_path.name}.*.bak"), 
                       key=lambda p: p.stat().st_mtime, reverse=True)
        
        if backups:
            latest_backup = backups[0]
            try:
                # 恢复备份
                import shutil
                shutil.copy2(latest_backup, config_path)
                logger.info(f"已从 {latest_backup} 恢复")
                return {"success": True, "message": f"已从 {latest_backup.name} 恢复"}
            except Exception as e:
                return {"success": False, "message": f"恢复失败: {e}"}
        
        return {"success": False, "message": "无有效备份"}

    def clear_cache(self) -> Dict:
        """清理缓存"""
        logger.info("执行: 清理缓存")
        
        cleared_size = 0
        cache_dirs = [
            Path.home() / ".real" / ".cache",
            self.workspace_dir / ".rewind_*",
        ]
        
        for cache_pattern in cache_dirs:
            if "*" in str(cache_pattern):
                for cache_dir in Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" if "*" not in str(cache_pattern) else []:
                    try:
                        import glob
                        for d in glob.glob(str(cache_pattern)):
                            d_path = Path(d)
                            if d_path.exists() and d_path.is_dir():
                                size = sum(f.stat().st_size for f in d_path.rglob("*"))
                                import shutil
                                shutil.rmtree(d_path)
                                cleared_size += size
                                logger.info(f"已清理: {d_path}")
                    except Exception as e:
                        logger.warning(f"清理失败: {e}")
            else:
                cache_dir = Path(cache_pattern)
                if cache_dir.exists():
                    try:
                        size = sum(f.stat().st_size for f in cache_dir.rglob("*"))
                        import shutil
                        shutil.rmtree(cache_dir)
                        cache_dir.mkdir()
                        cleared_size += size
                        logger.info(f"已清理: {cache_dir}")
                    except Exception as e:
                        logger.warning(f"清理失败: {e}")
        
        return {
            "success": True, 
            "message": f"已清理 {cleared_size / (1024*1024):.1f}MB 缓存"
        }

    def clean_logs(self) -> Dict:
        """清理日志"""
        logger.info("执行: 清理日志")
        
        if not LOG_DIR.exists():
            return {"success": True, "message": "日志目录不存在"}
        
        # 保留最近7天的日志
        cutoff = datetime.now().timestamp() - 7 * 24 * 60 * 60
        cleaned_size = 0
        cleaned_count = 0
        
        for log_file in LOG_DIR.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff:
                try:
                    cleaned_size += log_file.stat().st_size
                    log_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"删除日志失败: {e}")
        
        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 个日志文件，共 {cleaned_size / (1024*1024):.1f}MB"
        }

    def restart_session(self) -> Dict:
        """重启会话（标记需要重启）"""
        logger.info("执行: 标记会话需要重启")
        
        # 在配置文件中标记需要重启
        marker_file = self.workspace_dir / "needs_restart.marker"
        with open(marker_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "reason": "memory_leak"
            }, f)
        
        return {
            "success": True,
            "message": "已标记会话需要重启，下次启动时生效"
        }

    def run_repairs(self) -> List[Dict]:
        """执行修复"""
        logger.info("开始执行修复...")
        
        self.fixes_applied = []
        
        for issue in self.issues:
            issue_type = issue["type"]
            if issue_type not in REPAIR_ACTIONS:
                continue
            
            actions = REPAIR_ACTIONS[issue_type]["actions"]
            
            for action in actions:
                fix_func_name = action.get("fix_func")
                
                if fix_func_name and hasattr(self, fix_func_name):
                    try:
                        fix_func = getattr(self, fix_func_name)
                        result = fix_func()
                        
                        self.fixes_applied.append({
                            "issue": issue,
                            "action": action["name"],
                            "result": result
                        })
                        
                        logger.info(f"修复成功: {action['name']} - {result.get('message', '')}")
                        
                    except Exception as e:
                        logger.error(f"修复失败: {action['name']} - {e}")
                        self.fixes_applied.append({
                            "issue": issue,
                            "action": action["name"],
                            "result": {"success": False, "message": str(e)}
                        })
                
                elif action.get("command"):
                    try:
                        # 执行命令
                        result = subprocess.run(
                            action["command"],
                            shell=True,
                            capture_output=True,
                            timeout=60
                        )
                        
                        self.fixes_applied.append({
                            "issue": issue,
                            "action": action["name"],
                            "result": {
                                "success": result.returncode == 0,
                                "message": result.stdout.decode('utf-8', errors='ignore')[:100]
                            }
                        })
                        
                        logger.info(f"命令执行: {action['command']}")
                        
                    except Exception as e:
                        logger.error(f"命令执行失败: {action['command']} - {e}")
        
        return self.fixes_applied

    def generate_report(self) -> str:
        """生成报告"""
        report = f"""# 悟空自修复报告

**执行时间**: {datetime.now().isoformat()}
**检测问题数**: {len(self.issues)}
**修复执行数**: {len(self.fixes_applied)}

---

## 检测到的问题

"""
        
        if self.issues:
            for issue in self.issues:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue["severity"], "⚪")
                report += f"- {severity_icon} [{issue['severity']}] {issue['component']}: {issue['message']}\n"
        else:
            report += "- ✅ 无问题检测到\n"
        
        report += "\n## 修复执行记录\n\n"
        
        if self.fixes_applied:
            for fix in self.fixes_applied:
                success = fix["result"].get("success", False)
                icon = "✅" if success else "❌"
                report += f"- {icon} **{fix['action']}**"
                if fix["result"].get("message"):
                    report += f": {fix['result']['message']}"
                report += "\n"
        else:
            report += "- 无修复执行\n"
        
        # 统计
        success_count = sum(1 for f in self.fixes_applied if f["result"].get("success"))
        report += f"\n**修复成功率**: {success_count}/{len(self.fixes_applied)}\n"
        
        return report

    def save_report(self, content: str) -> Path:
        """保存报告"""
        output_dir = self.workspace_dir / "repair_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"self_repair_{timestamp}.md"
        output_file = output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 同时保存JSON
        json_file = output_dir / f"self_repair_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "issues": self.issues,
                "fixes_applied": self.fixes_applied
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存: {output_file}")
        return output_file

    def run(self) -> Dict:
        """执行完整自修复流程"""
        logger.info("=" * 50)
        logger.info("悟空自修复开始")
        logger.info("=" * 50)
        
        # 1. 检测问题
        self.detect_issues()
        logger.info(f"检测到 {len(self.issues)} 个问题")
        
        # 2. 执行修复
        if self.issues:
            self.run_repairs()
            logger.info(f"执行了 {len(self.fixes_applied)} 项修复")
        
        # 3. 生成报告
        content = self.generate_report()
        report_path = self.save_report(content)
        
        logger.info("=" * 50)
        logger.info(f"自修复完成: {report_path}")
        logger.info("=" * 50)
        
        return {
            "issues_found": len(self.issues),
            "fixes_applied": len(self.fixes_applied),
            "report_path": str(report_path)
        }


def main():
    """主函数"""
    repair = WuKongSelfRepair()
    result = repair.run()
    
    print(f"\n{'=' * 50}")
    print("自修复执行完成")
    print(f"{'=' * 50}")
    print(f"检测问题: {result['issues_found']}")
    print(f"执行修复: {result['fixes_applied']}")
    print(f"详细报告: {result['report_path']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
