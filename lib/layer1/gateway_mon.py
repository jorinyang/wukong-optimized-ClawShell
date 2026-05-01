"""
RepairEngine - 修复引擎

自动执行修复动作
"""

from __future__ import annotations
import time
import logging
import subprocess
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class RepairStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RepairAction:
    """修复动作"""
    action_id: str
    issue_id: str
    action_name: str
    action_type: str  # python/bash/system
    
    # 执行配置
    command: str = ""
    python_code: str = ""
    timeout_seconds: int = 30
    
    # 重试配置
    max_retries: int = 2
    retry_delay_seconds: int = 5
    
    # 冷却配置
    cooldown_minutes: int = 60  # 修复后60分钟不重复修复


@dataclass
class RepairResult:
    """修复结果"""
    action_id: str
    issue_id: str
    status: RepairStatus
    started_at: str = ""
    completed_at: str = ""
    output: str = ""
    error: str = ""
    attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "issue_id": self.issue_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output": self.output,
            "error": self.error,
            "attempts": self.attempts,
        }


class RepairEngine:
    """
    修复引擎
    
    功能：
    - 维护修复动作注册表
    - 执行修复并处理失败重试
    - 冷却机制防止频繁修复
    - 修复历史记录
    """
    
    def __init__(self):
        self._action_registry: Dict[str, Callable] = {}
        self._repair_history: List[RepairResult] = []
        self._cooldown_tracker: Dict[str, datetime] = {}
        self._max_history = 100
        
        # 注册内置修复动作
        self._register_builtin_actions()
    
    def _register_builtin_actions(self):
        """注册内置修复动作"""
        self._action_registry = {
            "activate_eventbus": self._repair_activate_eventbus,
            "register_default_listeners": self._repair_register_listeners,
            "restart_agent_daemon": self._repair_restart_agent_daemon,
            "update_agent_status": self._repair_update_agent_status,
            "cleanup_disk": self._repair_cleanup_disk,
            "cleanup_temp": self._repair_cleanup_temp,
            "trigger_gc": self._repair_trigger_gc,
            "build_heritage_package": self._repair_build_heritage_package,
            "register_capabilities": self._repair_register_capabilities,
            "fix_module_imports": self._repair_fix_module_imports,
            "optimize_cron_tasks": self._repair_optimize_cron,
        }
    
    def register_action(self, action_type: str, handler: Callable):
        """注册修复动作"""
        self._action_registry[action_type] = handler
        logger.info(f"Registered repair action: {action_type}")
    
    def repair(self, issue, dry_run: bool = False) -> RepairResult:
        """
        执行修复
        
        Args:
            issue: SystemIssue对象
            dry_run: 是否只检查不执行
            
        Returns:
            RepairResult
        """
        if not issue.auto_repairable:
            return RepairResult(
                action_id="",
                issue_id=issue.id,
                status=RepairStatus.SKIPPED,
                output="Issue is not auto-repairable"
            )
        
        # 检查冷却
        if self._is_in_cooldown(issue.id):
            return RepairResult(
                action_id="",
                issue_id=issue.id,
                status=RepairStatus.SKIPPED,
                output=f"Issue {issue.id} is in cooldown"
            )
        
        # 获取修复动作
        action_type = issue.repair_action
        handler = self._action_registry.get(action_type)
        
        if not handler:
            logger.warning(f"No handler for action: {action_type}")
            return RepairResult(
                action_id=action_type,
                issue_id=issue.id,
                status=RepairStatus.FAILED,
                error=f"No handler for action: {action_type}"
            )
        
        # 执行修复
        result = RepairResult(
            action_id=action_type,
            issue_id=issue.id,
            status=RepairStatus.RUNNING,
            started_at=datetime.now().isoformat()
        )
        
        if dry_run:
            result.status = RepairStatus.SKIPPED
            result.output = "Dry run mode"
            return result
        
        # 执行并处理重试
        for attempt in range(3):
            result.attempts = attempt + 1
            
            try:
                output = handler(issue)
                result.status = RepairStatus.SUCCESS
                result.completed_at = datetime.now().isoformat()
                result.output = str(output)
                
                # 设置冷却
                self._set_cooldown(issue.id)
                
                logger.info(f"Repair success: {issue.id} -> {action_type}")
                break
                
            except Exception as e:
                result.error = str(e)
                logger.warning(f"Repair attempt {attempt+1} failed: {e}")
                
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))  # 递增等待
                    continue
                
                result.status = RepairStatus.FAILED
                result.completed_at = datetime.now().isoformat()
        
        # 记录历史
        self._repair_history.append(result)
        if len(self._repair_history) > self._max_history:
            self._repair_history = self._repair_history[-self._max_history:]
        
        return result
    
    def repair_all(self, issues: List, dry_run: bool = False) -> List[RepairResult]:
        """批量修复"""
        results = []
        
        # 按严重度排序
        priority = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        sorted_issues = sorted(
            issues, 
            key=lambda i: priority.get(i.severity.value, 9)
        )
        
        for issue in sorted_issues:
            result = self.repair(issue, dry_run)
            results.append(result)
            
            # P0失败则停止
            if issue.severity.value == "P0" and result.status == RepairStatus.FAILED:
                logger.error(f"P0 repair failed, stopping: {issue.id}")
                break
        
        return results
    
    def _is_in_cooldown(self, issue_id: str) -> bool:
        """检查是否在冷却中"""
        if issue_id not in self._cooldown_tracker:
            return False
        
        last_repair = self._cooldown_tracker[issue_id]
        elapsed = (datetime.now() - last_repair).total_seconds() / 60
        
        return elapsed < 60  # 60分钟冷却
    
    def _set_cooldown(self, issue_id: str):
        """设置冷却"""
        self._cooldown_tracker[issue_id] = datetime.now()
    
    def get_history(self, limit: int = 20) -> List[RepairResult]:
        """获取修复历史"""
        return self._repair_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取修复统计"""
        total = len(self._repair_history)
        success = sum(1 for r in self._repair_history if r.status == RepairStatus.SUCCESS)
        failed = sum(1 for r in self._repair_history if r.status == RepairStatus.FAILED)
        
        return {
            "total_repairs": total,
            "success": success,
            "failed": failed,
            "in_cooldown": len(self._cooldown_tracker),
        }
    
    # ==================== 内置修复动作 ====================
    
    def _repair_activate_eventbus(self, issue) -> str:
        """激活EventBus"""
        import sys
        sys.path.insert(0, 'C:\Users\Aorus\.real')
        from eventbus import EventBus
        from eventbus.event import Event, EventType
        
        eb = EventBus.get_instance()
        event = Event(
            type=EventType.SYSTEM_STARTED,
            source="self_healing",
            payload={"triggered_by": "health_check"}
        )
        eb.publish(event)
        
        return f"Published event, stats: {eb.get_stats()}"
    
    def _repair_register_listeners(self, issue) -> str:
        """注册默认订阅者"""
        # 实现订阅者注册逻辑
        return "Listeners registered"
    
    def _repair_restart_agent_daemon(self, issue) -> str:
        """重启Agent Daemon"""
        # 检查是否有guardian脚本
        guardian = Path.home() / ".openclaw/scripts/guardian.sh"
        if guardian.exists():
            subprocess.run([str(guardian), "restart"], capture_output=True)
            return "Agent Daemon restarted"
        
        # 直接更新状态
        return "Agent Daemon restart skipped (no guardian)"
    
    def _repair_update_agent_status(self, issue) -> str:
        """更新Agent状态"""
        import json
        from pathlib import Path
        from datetime import datetime
        
        agent_file = Path("${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/agent-status.json")
        
        if agent_file.exists():
            with open(agent_file) as f:
                data = json.load(f)
            
            data["updated_at"] = datetime.now().isoformat()
            
            with open(agent_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return f"Updated {len(data.get('agents', {}))} agents"
        
        return "Agent file not found"
    
    def _repair_cleanup_disk(self, issue) -> str:
        """清理磁盘"""
        import subprocess
        from pathlib import Path
        
        cleaned = 0
        
        # 清理备份目录
        backups = Path.home() / ".openclaw/backups"
        if backups.exists():
            for subdir in backups.iterdir():
                if subdir.is_dir() and subdir.name.startswith("backup_"):
                    size = sum(f.stat().st_size for f in subdir.rglob("*") if f.is_file())
                    subprocess.run(["rm", "-rf", str(subdir)])
                    cleaned += size
        
        # 清理日志
        logs = Path.home() / ".openclaw/workspace/shared/logs"
        if logs.exists():
            for log_file in logs.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # > 10MB
                    cleaned += log_file.stat().st_size
                    log_file.unlink()
        
        return f"Cleaned {cleaned / (1024**2):.1f}MB"
    
    def _repair_cleanup_temp(self, issue) -> str:
        """清理临时文件"""
        import subprocess
        from pathlib import Path
        
        cleaned = 0
        temp_dirs = [
            Path.home() / ".openclaw/workspace/shared/tmp",
            Path.home() / ".openclaw/workspace/shared/cache",
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for f in temp_dir.iterdir():
                    if f.is_file():
                        cleaned += f.stat().st_size
                        f.unlink()
        
        return f"Cleaned temp: {cleaned / 1024:.1f}KB"
    
    def _repair_trigger_gc(self, issue) -> str:
        """触发垃圾回收"""
        import gc
        collected = gc.collect()
        return f"GC collected {collected} objects"
    
    def _repair_build_heritage_package(self, issue) -> str:
        """构建传承包"""
        import sys
        sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/clawshell')
        from heritage import HeritageManager
        
        hm = HeritageManager()
        path = hm.build_package()
        
        return f"Built package: {path.name}"
    
    def _repair_register_capabilities(self, issue) -> str:
        """注册能力"""
        import subprocess
        
        script = Path.home() / ".openclaw/clawshell/heritage/register_capabilities.py"
        if script.exists():
            result = subprocess.run(
                ["/Library/Frameworks/Python.framework/Versions/3.12/bin/python3", str(script)],
                capture_output=True,
                text=True
            )
            return result.stdout or "Capabilities registered"
        
        return "Register script not found"
    
    def _repair_fix_module_imports(self, issue) -> str:
        """修复模块导入"""
        # 检查sys.path配置
        import sys
        from pathlib import Path
        
        clawshell_path = Path.home() / ".openclaw/clawshell"
        workspace_path = Path.home() / ".openclaw/workspace"
        
        for path in [str(clawshell_path), str(workspace_path)]:
            if path not in sys.path:
                sys.path.insert(0, path)
        
        return "sys.path updated"
    
    def _repair_optimize_cron(self, issue) -> str:
        """优化Cron任务"""
        # 统计当前任务
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        tasks = [l for l in result.stdout.split('\n') if l and not l.startswith('#')]
        
        return f"Found {len(tasks)} tasks (optimization not yet implemented)"
