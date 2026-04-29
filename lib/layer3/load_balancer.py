#!/usr/bin/env python3
"""
ClawShell Organizer Load Balancer
负载均衡器模块
功能: 智能任务分发与负载均衡
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import random


@dataclass
class Worker:
    """工作节点"""
    id: str
    name: str
    capabilities: List[str]
    load: int = 0
    max_load: int = 100
    status: str = "active"
    last_heartbeat: float = field(default_factory=time.time)


@dataclass
class LoadBalanceResult:
    """负载均衡结果"""
    success: bool
    worker_id: Optional[str] = None
    reason: Optional[str] = None


class LoadBalancer:
    """
    负载均衡器
    
    功能：
    - 多种负载均衡策略
    - 能力匹配
    - 健康检查
    - 动态权重
    """

    STRATEGY_ROUND_ROBIN = "round_robin"
    STRATEGY_LEAST_LOAD = "least_load"
    STRATEGY_WEIGHTED = "weighted"
    STRATEGY_CAPABILITY_MATCH = "capability_match"
    STRATEGY_RANDOM = "random"

    def __init__(self, strategy: str = STRATEGY_LEAST_LOAD):
        self.strategy = strategy
        
        self._workers: Dict[str, Worker] = {}
        self._capability_index: Dict[str, List[str]] = defaultdict(list)  # capability -> worker_ids
        self._round_robin_index: Dict[str, int] = defaultdict(int)  # strategy -> index
        self._lock = threading.Lock()
        
        self._stats = {
            "total_assignments": 0,
            "successful_assignments": 0,
            "failed_assignments": 0,
        }

    def register_worker(
        self,
        worker_id: str,
        name: str,
        capabilities: List[str],
        max_load: int = 100,
        weight: float = 1.0
    ) -> bool:
        """注册工作节点"""
        with self._lock:
            if worker_id in self._workers:
                return False
            
            worker = Worker(
                id=worker_id,
                name=name,
                capabilities=capabilities,
                max_load=max_load
            )
            
            self._workers[worker_id] = worker
            
            # 更新能力索引
            for cap in capabilities:
                self._capability_index[cap].append(worker_id)
            
            return True

    def unregister_worker(self, worker_id: str) -> bool:
        """注销工作节点"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            worker = self._workers[worker_id]
            
            # 从能力索引中移除
            for cap in worker.capabilities:
                if worker_id in self._capability_index[cap]:
                    self._capability_index[cap].remove(worker_id)
            
            del self._workers[worker_id]
            return True

    def update_load(self, worker_id: str, load: int) -> bool:
        """更新工作节点负载"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            self._workers[worker_id].load = max(0, min(load, self._workers[worker_id].max_load))
            return True

    def heartbeat(self, worker_id: str) -> bool:
        """工作节点心跳"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            self._workers[worker_id].last_heartbeat = time.time()
            return True

    def assign_task(
        self,
        task_id: str,
        required_capabilities: Optional[List[str]] = None,
        preferred_worker_id: Optional[str] = None
    ) -> LoadBalanceResult:
        """分配任务"""
        with self._lock:
            self._stats["total_assignments"] += 1
            
            # 如果指定了首选工作节点
            if preferred_worker_id and preferred_worker_id in self._workers:
                worker = self._workers[preferred_worker_id]
                if worker.load < worker.max_load and worker.status == "active":
                    worker.load += 1
                    self._stats["successful_assignments"] += 1
                    return LoadBalanceResult(True, preferred_worker_id)
            
            # 根据策略选择
            if self.strategy == self.STRATEGY_LEAST_LOAD:
                return self._assign_least_load(required_capabilities)
            elif self.strategy == self.STRATEGY_ROUND_ROBIN:
                return self._assign_round_robin(required_capabilities)
            elif self.strategy == self.STRATEGY_WEIGHTED:
                return self._assign_weighted(required_capabilities)
            elif self.strategy == self.STRATEGY_CAPABILITY_MATCH:
                return self._assign_capability_match(required_capabilities)
            elif self.strategy == self.STRATEGY_RANDOM:
                return self._assign_random(required_capabilities)
            else:
                return self._assign_least_load(required_capabilities)

    def _assign_least_load(self, capabilities: Optional[List[str]]) -> LoadBalanceResult:
        """最少负载策略"""
        candidates = self._filter_by_capabilities(capabilities)
        
        if not candidates:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="No available workers")
        
        # 选择负载最低的
        candidates.sort(key=lambda w: w.load / w.max_load if w.max_load > 0 else 1)
        
        worker = candidates[0]
        worker.load += 1
        self._stats["successful_assignments"] += 1
        
        return LoadBalanceResult(True, worker.id)

    def _assign_round_robin(self, capabilities: Optional[List[str]]) -> LoadBalanceResult:
        """轮询策略"""
        candidates = self._filter_by_capabilities(capabilities)
        
        if not candidates:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="No available workers")
        
        # 轮询选择
        start_index = self._round_robin_index[self.STRATEGY_ROUND_ROBIN]
        index = start_index
        
        for i in range(len(candidates)):
            candidate = candidates[(start_index + i) % len(candidates)]
            if candidate.load < candidate.max_load:
                candidate.load += 1
                self._round_robin_index[self.STRATEGY_ROUND_ROBIN] = (index + 1) % len(candidates)
                self._stats["successful_assignments"] += 1
                return LoadBalanceResult(True, candidate.id)
        
        self._stats["failed_assignments"] += 1
        return LoadBalanceResult(False, reason="All workers at capacity")

    def _assign_weighted(self, capabilities: Optional[List[str]]) -> LoadBalanceResult:
        """加权策略"""
        candidates = self._filter_by_capabilities(capabilities)
        
        if not candidates:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="No available workers")
        
        # 计算权重分数
        for worker in candidates:
            worker.score = (worker.max_load - worker.load) / worker.max_load
        
        candidates.sort(key=lambda w: w.score, reverse=True)
        
        candidates[0].load += 1
        self._stats["successful_assignments"] += 1
        
        return LoadBalanceResult(True, candidates[0].id)

    def _assign_capability_match(self, capabilities: Optional[List[str]]) -> LoadBalanceResult:
        """能力匹配策略"""
        if not capabilities:
            return self._assign_least_load(capabilities)
        
        candidates = []
        
        for cap in capabilities:
            for worker_id in self._capability_index.get(cap, []):
                if worker_id in self._workers:
                    worker = self._workers[worker_id]
                    if worker.load < worker.max_load and worker not in candidates:
                        candidates.append(worker)
        
        if not candidates:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="No workers with required capabilities")
        
        # 选择匹配度最高的(负载最低的)
        candidates.sort(key=lambda w: w.load)
        candidates[0].load += 1
        self._stats["successful_assignments"] += 1
        
        return LoadBalanceResult(True, candidates[0].id)

    def _assign_random(self, capabilities: Optional[List[str]]) -> LoadBalanceResult:
        """随机策略"""
        candidates = self._filter_by_capabilities(capabilities)
        
        if not candidates:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="No available workers")
        
        # 过滤可用的
        available = [w for w in candidates if w.load < w.max_load]
        
        if not available:
            self._stats["failed_assignments"] += 1
            return LoadBalanceResult(False, reason="All workers at capacity")
        
        worker = random.choice(available)
        worker.load += 1
        self._stats["successful_assignments"] += 1
        
        return LoadBalanceResult(True, worker.id)

    def _filter_by_capabilities(self, capabilities: Optional[List[str]]) -> List[Worker]:
        """按能力过滤"""
        if not capabilities:
            return [w for w in self._workers.values() 
                   if w.status == "active" and w.load < w.max_load]
        
        result = []
        for cap in capabilities:
            for worker_id in self._capability_index.get(cap, []):
                if worker_id in self._workers:
                    worker = self._workers[worker_id]
                    if worker not in result and worker.status == "active":
                        result.append(worker)
        
        return result

    def release_task(self, worker_id: str) -> bool:
        """释放任务(任务完成后调用)"""
        with self._lock:
            if worker_id not in self._workers:
                return False
            
            self._workers[worker_id].load = max(0, self._workers[worker_id].load - 1)
            return True

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """获取工作节点"""
        return self._workers.get(worker_id)

    def get_all_workers(self) -> List[Worker]:
        """获取所有工作节点"""
        return list(self._workers.values())

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            **self._stats,
            "total_workers": len(self._workers),
            "active_workers": len([w for w in self._workers.values() if w.status == "active"]),
        }
