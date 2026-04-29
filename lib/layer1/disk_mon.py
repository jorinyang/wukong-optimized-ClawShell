"""
ScanScheduler - 扫描调度器

后台定时扫描 + 修复协调
"""

from __future__ import annotations
import time
import threading
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ScanConfig:
    """扫描配置"""
    # 扫描间隔（分钟）
    interval_minutes: int = 10
    
    # 冷却时间（分钟）- 修复后不重复扫描
    cooldown_minutes: int = 60
    
    # 是否启用自动修复
    auto_repair: bool = True
    
    # 严重问题是否立即扫描
    immediate_on_p0: bool = True
    
    # 最大连续扫描次数（防止死循环）
    max_consecutive_scans: int = 10
    
    # 是否只报告不修复
    dry_run: bool = False


@dataclass
class ScanResult:
    """扫描结果"""
    scan_id: str
    timestamp: str
    duration_ms: float
    
    # 健康报告摘要
    status: str  # healthy/degraded/critical
    score: float
    
    # 问题和修复
    issues_found: int
    issues_repaired: int
    issues_failed: int
    
    # 详情
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "score": self.score,
            "issues_found": self.issues_found,
            "issues_repaired": self.issues_repaired,
            "issues_failed": self.issues_failed,
            "details": self.details,
        }


class ScanScheduler:
    """
    扫描调度器
    
    功能：
    - 后台定时扫描
    - 冷却机制（修复后1小时不重复）
    - 扫描历史记录
    - SubAgent集成
    """
    
    def __init__(
        self,
        config: ScanConfig = None,
        health_monitor = None,
        repair_engine = None
    ):
        self.config = config or ScanConfig()
        self.health_monitor = health_monitor
        self.repair_engine = repair_engine
        
        self._running = False
        self._scan_thread: Optional[threading.Thread] = None
        self._last_scan: Optional[ScanResult] = None
        self._last_repair_time: Optional[datetime] = None
        self._consecutive_scans = 0
        self._scan_history: List[ScanResult] = []
        self._max_history = 100
        
        # 扫描锁
        self._scan_lock = threading.Lock()
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            daemon=True,
            name="SelfHealingScheduler"
        )
        self._scan_thread.start()
        logger.info(f"Self-healing scheduler started (interval: {self.config.interval_minutes}min)")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._scan_thread:
            self._scan_thread.join(timeout=10)
        logger.info("Self-healing scheduler stopped")
    
    def _scan_loop(self):
        """扫描循环"""
        while self._running:
            try:
                # 检查冷却
                if self._should_skip_scan():
                    logger.debug("Skipping scan due to cooldown")
                    time.sleep(60)  # 1分钟后重新检查
                    continue
                
                # 执行扫描
                result = self.scan()
                
                # 如果发现问题且需要修复
                if (result.issues_found > 0 and 
                    self.config.auto_repair and 
                    not self.config.dry_run):
                    self._consecutive_scans = 0
                elif result.issues_repaired > 0:
                    # 有修复，更新冷却时间
                    self._last_repair_time = datetime.now()
                    self._consecutive_scans = 0
                else:
                    self._consecutive_scans += 1
                
                # 检查连续扫描次数
                if self._consecutive_scans >= self.config.max_consecutive_scans:
                    logger.warning(f"Max consecutive scans reached ({self._consecutive_scans}), cooling down")
                    self._last_repair_time = datetime.now()
                    self._consecutive_scans = 0
                
            except Exception as e:
                logger.error(f"Scan loop error: {e}")
            
            # 等待下一个扫描周期
            time.sleep(self.config.interval_minutes * 60)
    
    def _should_skip_scan(self) -> bool:
        """检查是否应跳过扫描"""
        # 如果有修复，更新冷却
        if self._last_repair_time:
            elapsed = (datetime.now() - self._last_repair_time).total_seconds() / 60
            if elapsed < self.config.cooldown_minutes:
                return True
        
        return False
    
    def scan(self, force: bool = False) -> ScanResult:
        """
        执行一次扫描
        
        Args:
            force: 是否强制扫描（跳过冷却）
            
        Returns:
            ScanResult
        """
        if not force and not self._scan_lock.acquire(blocking=False):
            logger.warning("Scan already in progress")
            return self._last_scan
        
        start_time = time.time()
        
        try:
            scan_id = f"scan_{int(start_time * 1000)}"
            logger.info(f"Starting scan: {scan_id}")
            
            # 1. 健康检查
            health_report = self.health_monitor.scan() if self.health_monitor else None
            
            # 2. 生成结果
            result = ScanResult(
                scan_id=scan_id,
                timestamp=datetime.now().isoformat(),
                duration_ms=0,
                status=health_report.status.value if health_report else "unknown",
                score=health_report.overall_score if health_report else 0,
                issues_found=len(health_report.issues) if health_report else 0,
                issues_repaired=0,
                issues_failed=0,
                details={}
            )
            
            # 3. 自动修复
            if (self.config.auto_repair and 
                not self.config.dry_run and 
                health_report and 
                health_report.issues):
                
                repair_results = self.repair_engine.repair_all(health_report.issues)
                
                result.issues_repaired = sum(
                    1 for r in repair_results 
                    if r.status.value == "success"
                )
                result.issues_failed = sum(
                    1 for r in repair_results 
                    if r.status.value == "failed"
                )
                
                result.details["repairs"] = [r.to_dict() for r in repair_results]
            
            # 4. 记录历史
            self._last_scan = result
            self._scan_history.append(result)
            if len(self._scan_history) > self._max_history:
                self._scan_history = self._scan_history[-self._max_history:]
            
            result.duration_ms = (time.time() - start_time) * 1000
            
            # 5. 发布事件
            self._publish_scan_event(result)
            
            logger.info(
                f"Scan complete: {result.status} "
                f"(score: {result.score:.1f}, "
                f"found: {result.issues_found}, "
                f"repaired: {result.issues_repaired})"
            )
            
            return result
            
        finally:
            self._scan_lock.release()
    
    def scan_once(self) -> ScanResult:
        """执行一次扫描（公共接口）"""
        return self.scan(force=True)
    
    def _publish_scan_event(self, result: ScanResult):
        """发布扫描结果事件"""
        try:
            import sys
            sys.path.insert(0, '${CLAWSHELL_HOME:-$HOME/.clawshell}/clawshell')
            from eventbus import EventBus
            from eventbus.event import Event, EventType
            
            eb = EventBus.get_instance()
            event = Event(
                type=EventType.SYSTEM_STATUS,
                source="self_healing",
                payload={
                    "scan_id": result.scan_id,
                    "status": result.status,
                    "score": result.score,
                    "issues_found": result.issues_found,
                    "issues_repaired": result.issues_repaired,
                }
            )
            eb.publish(event)
        except Exception as e:
            logger.warning(f"Failed to publish scan event: {e}")
    
    def get_last_scan(self) -> Optional[ScanResult]:
        """获取上次扫描结果"""
        return self._last_scan
    
    def get_history(self, limit: int = 10) -> List[ScanResult]:
        """获取扫描历史"""
        return self._scan_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_scans = len(self._scan_history)
        
        if total_scans == 0:
            return {"total_scans": 0}
        
        avg_score = sum(s.score for s in self._scan_history) / total_scans
        total_repaired = sum(s.issues_repaired for s in self._scan_history)
        total_failed = sum(s.issues_failed for s in self._scan_history)
        
        return {
            "total_scans": total_scans,
            "avg_score": avg_score,
            "total_repaired": total_repaired,
            "total_failed": total_failed,
            "last_scan": self._last_scan.timestamp if self._last_scan else None,
            "cooldown_remaining_minutes": self._get_cooldown_remaining(),
            "consecutive_scans": self._consecutive_scans,
        }
    
    def _get_cooldown_remaining(self) -> float:
        """获取剩余冷却时间"""
        if not self._last_repair_time:
            return 0
        
        elapsed = (datetime.now() - self._last_repair_time).total_seconds() / 60
        remaining = self.config.cooldown_minutes - elapsed
        return max(0, remaining)
    
    def save_state(self, path: Path):
        """保存状态"""
        try:
            state = {
                "config": {
                    "interval_minutes": self.config.interval_minutes,
                    "cooldown_minutes": self.config.cooldown_minutes,
                    "auto_repair": self.config.auto_repair,
                },
                "last_scan": self._last_scan.to_dict() if self._last_scan else None,
                "last_repair_time": self._last_repair_time.isoformat() if self._last_repair_time else None,
                "consecutive_scans": self._consecutive_scans,
            }
            
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"State saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self, path: Path):
        """加载状态"""
        try:
            if not path.exists():
                return
            
            with open(path) as f:
                state = json.load(f)
            
            if "config" in state:
                self.config.interval_minutes = state["config"].get("interval_minutes", 10)
                self.config.cooldown_minutes = state["config"].get("cooldown_minutes", 60)
                self.config.auto_repair = state["config"].get("auto_repair", True)
            
            if "last_repair_time" in state and state["last_repair_time"]:
                self._last_repair_time = datetime.fromisoformat(state["last_repair_time"])
            
            self._consecutive_scans = state.get("consecutive_scans", 0)
            
            logger.info(f"State loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
