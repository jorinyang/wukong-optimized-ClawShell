"""
HealthMonitor - 健康监控器

全面扫描系统瓶颈，交叉分析根因
"""

from __future__ import annotations
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """问题严重度"""
    P0 = "P0"  # 阻断级
    P1 = "P1"  # 严重级
    P2 = "P2"  # 一般级
    P3 = "P3"  # 优化级


@dataclass
class SystemIssue:
    """系统问题"""
    id: str
    name: str
    description: str
    severity: IssueSeverity
    category: str  # memory/disk/eventbus/agent/coordination
    
    # 诊断信息
    symptoms: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    
    # 修复信息
    repair_action: str = ""
    repair_params: Dict[str, Any] = field(default_factory=dict)
    auto_repairable: bool = False
    
    # 状态
    detected_at: str = ""
    resolved_at: Optional[str] = None
    attempt_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "category": self.category,
            "description": self.description,
            "symptoms": self.symptoms,
            "root_causes": self.root_causes,
            "repair_action": self.repair_action,
            "auto_repairable": self.auto_repairable,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "attempt_count": self.attempt_count,
        }


@dataclass
class HealthReport:
    """健康报告"""
    timestamp: str
    status: HealthStatus
    overall_score: float  # 0-100
    
    # 各维度得分
    scores: Dict[str, float] = field(default_factory=dict)
    
    # 发现的问题
    issues: List[SystemIssue] = field(default_factory=list)
    
    # 统计数据
    stats: Dict[str, Any] = field(default_factory=dict)
    
    # 建议
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status.value,
            "overall_score": self.overall_score,
            "scores": self.scores,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
            "recommendations": self.recommendations,
        }


class HealthMonitor:
    """
    健康监控器
    
    功能：
    - 全面扫描系统各维度
    - 交叉分析问题根因
    - 生成修复建议
    """
    
    def __init__(self):
        self._checkers: Dict[str, Callable] = {}
        self._last_report: Optional[HealthReport] = None
        self._active_issues: Dict[str, SystemIssue] = {}
        
        # 注册检查器
        self._register_checkers()
    
    def _register_checkers(self):
        """注册所有检查器"""
        self._checkers = {
            "eventbus": self._check_eventbus,
            "agents": self._check_agents,
            "memory": self._check_memory,
            "disk": self._check_disk,
            "collaboration": self._check_collaboration,
            "coordination": self._check_coordination,
            "heritage": self._check_heritage,
            "cron": self._check_cron,
            "processes": self._check_processes,
        }
    
    def scan(self) -> HealthReport:
        """
        执行全面扫描
        
        Returns:
            健康报告
        """
        report = HealthReport(
            timestamp=datetime.now().isoformat(),
            status=HealthStatus.HEALTHY,
            overall_score=100.0,
            scores={},
            issues=[],
            stats={},
            recommendations=[]
        )
        
        all_issues = []
        
        # 执行所有检查器
        for name, checker in self._checkers.items():
            try:
                score, issues = checker()
                report.scores[name] = score
                
                if issues:
                    all_issues.extend(issues)
                    for issue in issues:
                        self._active_issues[issue.id] = issue
                        
            except Exception as e:
                logger.error(f"Checker {name} failed: {e}")
                report.scores[name] = 0
                report.stats[f"{name}_error"] = str(e)
        
        report.issues = all_issues
        
        # 计算总体得分
        if report.scores:
            report.overall_score = sum(report.scores.values()) / len(report.scores)
        
        # 确定健康状态
        if report.overall_score >= 80:
            report.status = HealthStatus.HEALTHY
        elif report.overall_score >= 50:
            report.status = HealthStatus.DEGRADED
        else:
            report.status = HealthStatus.CRITICAL
        
        # 生成建议
        report.recommendations = self._generate_recommendations(report)
        
        # 统计
        report.stats = {
            "total_checkers": len(self._checkers),
            "active_issues": len(self._active_issues),
            "p0_count": sum(1 for i in all_issues if i.severity == IssueSeverity.P0),
            "p1_count": sum(1 for i in all_issues if i.severity == IssueSeverity.P1),
        }
        
        self._last_report = report
        return report
    
    def _check_eventbus(self) -> tuple:
        """检查EventBus"""
        score = 100
        issues = []
        
        try:
            import sys
            sys.path.insert(0, '/Users/yangyang/.openclaw/clawshell')
            from eventbus import EventBus
            
            eb = EventBus.get_instance()
            stats = eb.get_stats()
            
            event_count = stats.get('total_events', 0)
            listener_count = stats.get('total_listeners', 0)
            
            if event_count == 0:
                score -= 30
                issues.append(SystemIssue(
                    id="eventbus_no_events",
                    name="EventBus无事件流转",
                    description="EventBus存在但无事件流转，协作链路可能断裂",
                    severity=IssueSeverity.P1,
                    category="eventbus",
                    symptoms=["EventBus.total_events = 0"],
                    root_causes=["事件发布机制未激活", "订阅者未注册"],
                    repair_action="activate_eventbus",
                    auto_repairable=True
                ))
            
            if listener_count == 0:
                score -= 20
                issues.append(SystemIssue(
                    id="eventbus_no_listeners",
                    name="EventBus无订阅者",
                    description="EventBus无订阅者，无法进行事件驱动协作",
                    severity=IssueSeverity.P2,
                    category="eventbus",
                    symptoms=["EventBus.total_listeners = 0"],
                    root_causes=["订阅机制未配置"],
                    repair_action="register_default_listeners",
                    auto_repairable=True
                ))
            
        except Exception as e:
            score = 0
            issues.append(SystemIssue(
                id="eventbus_error",
                name="EventBus错误",
                description=f"EventBus检查失败: {e}",
                severity=IssueSeverity.P0,
                category="eventbus",
                symptoms=[str(e)],
                root_causes=["模块导入失败"],
                repair_action="restart_eventbus",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_agents(self) -> tuple:
        """检查Agent状态"""
        score = 100
        issues = []
        
        try:
            import json
            agent_file = Path("/Users/yangyang/.openclaw/workspace/shared/agent-status.json")
            
            if not agent_file.exists():
                score -= 50
                issues.append(SystemIssue(
                    id="agents_file_missing",
                    name="Agent状态文件缺失",
                    description="agent-status.json不存在",
                    severity=IssueSeverity.P0,
                    category="agent",
                    repair_action="recreate_agent_status",
                    auto_repairable=True
                ))
            else:
                with open(agent_file) as f:
                    data = json.load(f)
                
                agents = data.get("agents", {})
                online_count = sum(1 for a in agents.values() if a.get("status") == "online")
                total_count = len(agents)
                
                if online_count == 0 and total_count > 0:
                    score -= 60
                    issues.append(SystemIssue(
                        id="all_agents_offline",
                        name="所有Agent离线",
                        description=f"{total_count}个Agent全部离线",
                        severity=IssueSeverity.P0,
                        category="agent",
                        symptoms=[f"online: {online_count}/{total_count}"],
                        root_causes=["Agent Daemon心跳失效", "进程异常退出"],
                        repair_action="restart_agent_daemon",
                        auto_repairable=True
                    ))
                elif online_count < total_count * 0.5:
                    score -= 30
                    issues.append(SystemIssue(
                        id="agents_partially_offline",
                        name="部分Agent离线",
                        description=f"仅{online_count}/{total_count}个Agent在线",
                        severity=IssueSeverity.P1,
                        category="agent",
                        repair_action="restart_offline_agents",
                        auto_repairable=True
                    ))
                
                # 检查状态更新时间
                updated_at = data.get("updated_at", "")
                if updated_at:
                    last_update = datetime.fromisoformat(updated_at)
                    age_minutes = (datetime.now() - last_update).total_seconds() / 60
                    if age_minutes > 30:
                        score -= 20
                        issues.append(SystemIssue(
                            id="agent_status_stale",
                            name="Agent状态过期",
                            description=f"最后更新于{age_minutes:.0f}分钟前",
                            severity=IssueSeverity.P2,
                            category="agent",
                            symptoms=[f"age: {age_minutes:.0f} minutes"],
                            repair_action="update_agent_status",
                            auto_repairable=True
                        ))
                        
        except Exception as e:
            score = 0
            issues.append(SystemIssue(
                id="agents_error",
                name="Agent检查错误",
                description=str(e),
                severity=IssueSeverity.P0,
                category="agent",
                repair_action="recover_agent_system",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_memory(self) -> tuple:
        """检查内存"""
        score = 100
        issues = []
        
        try:
            import subprocess
            result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                free_pages = 0
                for line in lines:
                    if "Pages free:" in line:
                        free_pages = int(line.split(":")[1].strip().rstrip('.'))
                        break
                
                # 估算内存压力 (macOS page size = 4096)
                total_mem_gb = 32  # 固定32GB
                free_mem_gb = (free_pages * 4096) / (1024**3)
                
                if free_mem_gb < 1:  # < 1GB可用
                    score -= 40
                    issues.append(SystemIssue(
                        id="memory_low",
                        name="内存不足",
                        description=f"可用内存仅{free_mem_gb:.1f}GB",
                        severity=IssueSeverity.P1,
                        category="memory",
                        symptoms=[f"free: {free_mem_gb:.1f}GB"],
                        repair_action="trigger_gc",
                        auto_repairable=True
                    ))
                    
        except Exception as e:
            score = 50  # 无法确定，保守处理
            issues.append(SystemIssue(
                id="memory_check_error",
                name="内存检查失败",
                description=str(e),
                severity=IssueSeverity.P2,
                category="memory",
                repair_action="manual_check",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_disk(self) -> tuple:
        """检查磁盘空间"""
        score = 100
        issues = []
        
        try:
            import subprocess
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('\n')[-1].split()
                available = parts[3]
                capacity = parts[1]
                used_pct = parts[4]
                
                # 解析使用率
                pct = int(used_pct.rstrip('%'))
                
                if pct > 90:
                    score -= 50
                    issues.append(SystemIssue(
                        id="disk_almost_full",
                        name="磁盘空间不足",
                        description=f"磁盘使用率{pct}%",
                        severity=IssueSeverity.P0,
                        category="disk",
                        symptoms=[f"used: {used_pct}"],
                        root_causes=["日志文件未清理", "备份过多"],
                        repair_action="cleanup_disk",
                        auto_repairable=True
                    ))
                elif pct > 80:
                    score -= 20
                    issues.append(SystemIssue(
                        id="disk_high_usage",
                        name="磁盘使用率高",
                        description=f"磁盘使用率{pct}%",
                        severity=IssueSeverity.P1,
                        category="disk",
                        symptoms=[f"used: {used_pct}"],
                        repair_action="cleanup_temp",
                        auto_repairable=True
                    ))
                
        except Exception as e:
            score = 50
            issues.append(SystemIssue(
                id="disk_check_error",
                name="磁盘检查失败",
                description=str(e),
                severity=IssueSeverity.P2,
                category="disk",
                repair_action="manual_check",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_collaboration(self) -> tuple:
        """检查协作链路"""
        score = 100
        issues = []
        
        # 检查ClawShell各模块可用性
        try:
            import sys
            sys.path.insert(0, '/Users/yangyang/.openclaw/clawshell')
            
            modules = [
                ("TaskMarket", "organizer", "TaskMarket"),
                ("GenomeBridge", "genome_bridge", "GenomeBridge"),
                ("ContextManager", "context_manager", "ContextManager"),
                ("ErrorHandler", "error_handler", "ErrorHandler"),
            ]
            
            failed = []
            for name, module, cls_name in modules:
                try:
                    mod = __import__(module, fromlist=[cls_name])
                    cls = getattr(mod, cls_name)
                    obj = cls()
                except Exception as e:
                    failed.append(f"{name}: {str(e)[:30]}")
            
            if failed:
                score -= len(failed) * 15
                issues.append(SystemIssue(
                    id="collaboration_modules_failed",
                    name="协作模块部分失效",
                    description=f"失败模块: {', '.join(failed)}",
                    severity=IssueSeverity.P1,
                    category="coordination",
                    symptoms=failed,
                    root_causes=["模块导入错误", "依赖缺失"],
                    repair_action="fix_module_imports",
                    auto_repairable=False
                ))
                
        except Exception as e:
            score = 50
            issues.append(SystemIssue(
                id="collaboration_check_error",
                name="协作链路检查失败",
                description=str(e),
                severity=IssueSeverity.P2,
                category="coordination",
                repair_action="manual_recovery",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_coordination(self) -> tuple:
        """检查协调机制"""
        score = 100
        issues = []
        
        # 检查N8N配置
        n8n_config = Path("/Users/yangyang/.openclaw/config/n8n.yaml")
        if not n8n_config.exists():
            score -= 10
            issues.append(SystemIssue(
                id="n8n_config_missing",
                name="N8N配置缺失",
                description="n8n.yaml不存在，自动化工作流未配置",
                severity=IssueSeverity.P3,
                category="coordination",
                repair_action="create_n8n_config",
                auto_repairable=True
            ))
        
        return score, issues
    
    def _check_heritage(self) -> tuple:
        """检查传承系统"""
        score = 100
        issues = []
        
        try:
            import sys
            sys.path.insert(0, '/Users/yangyang/.openclaw/clawshell')
            from heritage import HeritageManager
            
            hm = HeritageManager()
            status = hm.get_status()
            
            if status['total_capabilities'] == 0:
                score -= 30
                issues.append(SystemIssue(
                    id="heritage_no_capabilities",
                    name="传承能力未注册",
                    description="Heritage注册表为空",
                    severity=IssueSeverity.P2,
                    category="heritage",
                    repair_action="register_capabilities",
                    auto_repairable=True
                ))
            
            # 检查最新包
            latest = hm.get_latest_package()
            if not latest:
                score -= 20
                issues.append(SystemIssue(
                    id="heritage_no_package",
                    name="无传承包",
                    description="未找到最新传承包",
                    severity=IssueSeverity.P3,
                    category="heritage",
                    repair_action="build_heritage_package",
                    auto_repairable=True
                ))
                
        except Exception as e:
            score = 50
            issues.append(SystemIssue(
                id="heritage_check_error",
                name="传承系统检查失败",
                description=str(e),
                severity=IssueSeverity.P2,
                category="heritage",
                repair_action="manual_check",
                auto_repairable=False
            ))
        
        return score, issues
    
    def _check_cron(self) -> tuple:
        """检查Cron任务"""
        score = 100
        issues = []
        
        try:
            import subprocess
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                tasks = [l for l in result.stdout.split('\n') if l and not l.startswith('#')]
                task_count = len(tasks)
                
                if task_count > 20:
                    score -= 20
                    issues.append(SystemIssue(
                        id="cron_too_many_tasks",
                        name="Cron任务过多",
                        description=f"共{task_count}个活动任务",
                        severity=IssueSeverity.P2,
                        category="cron",
                        symptoms=[f"tasks: {task_count}"],
                        root_causes=["任务未整合"],
                        repair_action="optimize_cron_tasks",
                        auto_repairable=True
                    ))
                    
        except Exception as e:
            score = 80  # Cron检查失败不影响核心功能
        
        return score, issues
    
    def _check_processes(self) -> tuple:
        """检查关键进程"""
        score = 100
        issues = []
        
        try:
            import subprocess
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # 检查OpenClaw进程
                openclaw_procs = [l for l in result.stdout.split('\n') if 'openclaw' in l.lower()]
                
                if not openclaw_procs:
                    score = 0
                    issues.append(SystemIssue(
                        id="openclaw_not_running",
                        name="OpenClaw未运行",
                        description="未找到OpenClaw进程",
                        severity=IssueSeverity.P0,
                        category="processes",
                        repair_action="restart_openclaw",
                        auto_repairable=True
                    ))
                else:
                    # 检查CPU使用率过高的进程
                    for proc in openclaw_procs[:5]:
                        parts = proc.split()
                        if len(parts) > 3:
                            try:
                                cpu = float(parts[2])
                                if cpu > 80:
                                    score -= 10
                                    issues.append(SystemIssue(
                                        id="process_high_cpu",
                                        name="进程CPU过高",
                                        description=f"PID {parts[1]} CPU使用率{cpu}%",
                                        severity=IssueSeverity.P2,
                                        category="processes",
                                        symptoms=[f"cpu: {cpu}%"],
                                        repair_action="investigate_process",
                                        auto_repairable=False
                                    ))
                            except:
                                pass
                                
        except Exception as e:
            score = 50
        
        return score, issues
    
    def _generate_recommendations(self, report: HealthReport) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 按严重度排序处理
        p0_issues = [i for i in report.issues if i.severity == IssueSeverity.P0]
        p1_issues = [i for i in report.issues if i.severity == IssueSeverity.P1]
        
        if p0_issues:
            recommendations.append(f"🔴 立即处理 {len(p0_issues)} 个P0问题")
            for issue in p0_issues:
                recommendations.append(f"   - {issue.name}: {issue.repair_action}")
        
        if p1_issues:
            recommendations.append(f"🟠 尽快处理 {len(p1_issues)} 个P1问题")
            for issue in p1_issues:
                recommendations.append(f"   - {issue.name}")
        
        if not recommendations:
            recommendations.append("✅ 系统健康，无需特殊处理")
        
        return recommendations
    
    def get_active_issues(self) -> List[SystemIssue]:
        """获取当前活跃问题"""
        return list(self._active_issues.values())
    
    def get_last_report(self) -> Optional[HealthReport]:
        """获取上次报告"""
        return self._last_report
