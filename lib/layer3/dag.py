#!/usr/bin/env python3
"""
ClawShell 任务DAG (Task Dependency DAG)
版本: v0.2.1-C
功能: 任务依赖管理、拓扑排序、并行执行组
"""

import os
import json
import time
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
from pathlib import Path

# ============ 配置 ============

DAG_STATE_PATH = Path("~/.openclaw/.dag_state.json").expanduser()


# ============ 数据结构 ============

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    BLOCKED = "blocked"  # 等待依赖
    READY = "ready"     # 可以执行
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务"""
    id: str
    name: str
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID列表
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # 优先级，数字越大优先级越高
    metadata: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "priority": self.priority,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": str(self.result) if self.result else None,
            "error": self.error
        }


@dataclass
class DAGReport:
    """DAG报告"""
    tasks: Dict[str, Task]
    ready_tasks: List[str]  # 可以执行的任务
    completed_tasks: List[str]
    blocked_tasks: List[str]
    parallel_groups: List[List[str]]  # 可并行执行的任务组
    execution_order: List[str]  # 拓扑排序顺序
    
    def to_dict(self) -> Dict:
        return {
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
            "ready_tasks": self.ready_tasks,
            "completed_tasks": self.completed_tasks,
            "blocked_tasks": self.blocked_tasks,
            "parallel_groups": self.parallel_groups,
            "execution_order": self.execution_order
        }


# ============ DAG验证器 ============

class DAGValidator:
    """DAG验证器"""
    
    @staticmethod
    def validate(tasks: Dict[str, Task]) -> tuple[bool, Optional[str]]:
        """
        验证DAG是否有环
        返回: (is_valid, error_message)
        """
        # 构建邻接表
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        
        for task_id in tasks:
            in_degree[task_id] = 0
        
        for task_id, task in tasks.items():
            for dep in task.dependencies:
                if dep not in tasks:
                    return False, f"Task {task_id} depends on non-existent task {dep}"
                adj[dep].append(task_id)
                in_degree[task_id] += 1
        
        # Kahn算法检测环
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        visited = 0
        
        while queue:
            node = queue.popleft()
            visited += 1
            
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if visited != len(tasks):
            return False, "Cycle detected in task dependencies"
        
        return True, None


# ============ DAG调度器 ============

class TaskDAG:
    """任务依赖DAG"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._executor: Optional[Callable] = None
        self._load_state()
    
    def _load_state(self):
        """加载状态"""
        if DAG_STATE_PATH.exists():
            try:
                with open(DAG_STATE_PATH) as f:
                    state = json.load(f)
                    for task_data in state.get("tasks", {}).values():
                        task = Task(**task_data)
                        # 转换状态枚举
                        task.status = TaskStatus(task_data["status"])
                        self.tasks[task.id] = task
            except:
                pass
    
    def _save_state(self):
        """保存状态"""
        state = {
            "last_update": time.time(),
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()}
        }
        with open(DAG_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    def add_task(self, task_id: str, name: str, dependencies: Optional[List[str]] = None, 
                 priority: int = 0, metadata: Optional[Dict] = None) -> bool:
        """添加任务"""
        if task_id in self.tasks:
            return False
        
        task = Task(
            id=task_id,
            name=name,
            dependencies=dependencies or [],
            priority=priority,
            metadata=metadata or {}
        )
        
        # 验证DAG
        self.tasks[task_id] = task
        is_valid, error = DAGValidator.validate(self.tasks)
        
        if not is_valid:
            del self.tasks[task_id]
            raise ValueError(f"Invalid DAG: {error}")
        
        self._save_state()
        self._update_task_statuses()
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id not in self.tasks:
            return False
        
        # 移除对该任务的依赖
        for task in self.tasks.values():
            if task_id in task.dependencies:
                task.dependencies.remove(task_id)
        
        del self.tasks[task_id]
        self._save_state()
        self._update_task_statuses()
        return True
    
    def get_dependencies(self, task_id: str) -> List[str]:
        """获取任务的依赖"""
        if task_id not in self.tasks:
            return []
        return self.tasks[task_id].dependencies
    
    def get_dependents(self, task_id: str) -> List[str]:
        """获取依赖该任务的任务"""
        dependents = []
        for task in self.tasks.values():
            if task_id in task.dependencies:
                dependents.append(task.id)
        return dependents
    
    def _update_task_statuses(self):
        """更新所有任务状态"""
        completed = {tid for tid, t in self.tasks.items() if t.status == TaskStatus.COMPLETED}
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                continue
            
            # 检查依赖是否都已完成
            deps_completed = all(dep in completed for dep in task.dependencies)
            
            if task.dependencies and not deps_completed:
                task.status = TaskStatus.BLOCKED
            elif task.status == TaskStatus.BLOCKED and deps_completed:
                task.status = TaskStatus.READY
    
    def get_execution_order(self) -> List[str]:
        """
        获取拓扑排序执行顺序（Kahn算法）
        返回按依赖顺序排列的任务ID列表
        """
        # 构建图
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        
        for task_id in self.tasks:
            in_degree[task_id] = 0
        
        for task_id, task in self.tasks.items():
            for dep in task.dependencies:
                adj[dep].append(task_id)
                in_degree[task_id] += 1
        
        # 按优先级初始化的队列
        zero_degree = [(tid, self.tasks[tid].priority) for tid, deg in in_degree.items() if deg == 0]
        zero_degree.sort(key=lambda x: -x[1])  # 高优先级在前
        
        queue = deque([tid for tid, _ in zero_degree])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    # 按优先级插入
                    priority = self.tasks[neighbor].priority
                    inserted = False
                    for i, (tid, p) in enumerate(queue):
                        if p < priority:
                            queue.insert(i, (neighbor, priority))
                            inserted = True
                            break
                    if not inserted:
                        queue.append((neighbor, priority))
        
        return result
    
    def get_parallel_groups(self) -> List[List[str]]:
        """
        获取可并行执行的任务组
        每组内的任务可以并行执行，组间有依赖关系
        """
        groups = []
        remaining = set(self.tasks.keys())
        completed = set()
        
        while remaining:
            # 找出所有依赖都已完成但还未执行的任务
            ready = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    completed.add(task_id)
                    continue
                
                # 检查依赖是否都已完成
                deps_done = all(dep in completed or dep in ready 
                              for dep in task.dependencies)
                if deps_done:
                    ready.append(task_id)
            
            if not ready:
                # 有环或死锁
                break
            
            # 按优先级排序
            ready.sort(key=lambda x: -self.tasks[x].priority)
            groups.append(ready)
            
            # 标记为完成（实际执行时应该是运行完成后才标记）
            for tid in ready:
                completed.add(tid)
                remaining.discard(tid)
        
        return groups
    
    def mark_running(self, task_id: str) -> bool:
        """标记任务开始运行"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.READY:
            return False
        
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._save_state()
        return True
    
    def mark_completed(self, task_id: str, result: Any = None) -> bool:
        """标记任务完成"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        
        # 更新依赖该任务的任务状态
        self._update_task_statuses()
        self._save_state()
        return True
    
    def mark_failed(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.completed_at = time.time()
        task.error = error
        
        # 标记依赖该任务的任务为阻塞（可选：也可传播失败）
        # 这里采用传播失败策略
        self._propagate_failure(task_id)
        self._save_state()
        return True
    
    def _propagate_failure(self, failed_task_id: str):
        """传播失败状态"""
        dependents = self.get_dependents(failed_task_id)
        queue = deque(dependents)
        
        while queue:
            task_id = queue.popleft()
            task = self.tasks[task_id]
            
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.status = TaskStatus.FAILED
                task.error = f"Dependency {failed_task_id} failed"
                
                # 继续传播
                for dep_id in self.get_dependents(task_id):
                    queue.append(dep_id)
    
    def get_report(self) -> DAGReport:
        """获取DAG报告"""
        ready = [tid for tid, t in self.tasks.items() if t.status == TaskStatus.READY]
        completed = [tid for tid, t in self.tasks.items() if t.status == TaskStatus.COMPLETED]
        blocked = [tid for tid, t in self.tasks.items() if t.status == TaskStatus.BLOCKED]
        
        return DAGReport(
            tasks=self.tasks,
            ready_tasks=ready,
            completed_tasks=completed,
            blocked_tasks=blocked,
            parallel_groups=self.get_parallel_groups(),
            execution_order=self.get_execution_order()
        )
    
    def visualize(self) -> str:
        """生成DOT格式可视化"""
        lines = ["digraph DAG {", "  rankdir=TB;"]
        
        # 节点定义
        for task_id, task in self.tasks.items():
            color = {
                TaskStatus.PENDING: "#E0E0E0",
                TaskStatus.BLOCKED: "#FFB74D",
                TaskStatus.READY: "#81C784",
                TaskStatus.RUNNING: "#64B5F6",
                TaskStatus.COMPLETED: "#4CAF50",
                TaskStatus.FAILED: "#F44336",
                TaskStatus.CANCELLED: "#9E9E9E",
            }.get(task.status, "#E0E0E0")
            
            label = f'{task_id}\\n{task.name}'
            lines.append(f'  {task_id} [label="{label}", fillcolor="{color}", style=filled];')
        
        # 边定义
        for task_id, task in self.tasks.items():
            for dep in task.dependencies:
                lines.append(f"  {dep} -> {task_id};")
        
        lines.append("}")
        return "\n".join(lines)


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 任务DAG")
    parser.add_argument("--visualize", action="store_true", help="生成可视化")
    parser.add_argument("--report", action="store_true", help="显示报告")
    parser.add_argument("--order", action="store_true", help="显示执行顺序")
    parser.add_argument("--groups", action="store_true", help="显示并行组")
    args = parser.parse_args()
    
    dag = TaskDAG()
    
    if args.visualize:
        dot = dag.visualize()
        print(dot)
    
    elif args.order:
        order = dag.get_execution_order()
        print("执行顺序:")
        for i, tid in enumerate(order):
            print(f"  {i+1}. {tid}: {dag.tasks[tid].name}")
    
    elif args.groups:
        groups = dag.get_parallel_groups()
        print(f"并行执行组 ({len(groups)} 组):")
        for i, group in enumerate(groups):
            print(f"  组 {i+1}: {', '.join(group)}")
    
    elif args.report:
        report = dag.get_report()
        print("=" * 60)
        print("ClawShell 任务DAG 报告")
        print("=" * 60)
        print(f"总任务数: {len(report.tasks)}")
        print(f"就绪任务: {len(report.ready_tasks)}")
        print(f"已完成: {len(report.completed_tasks)}")
        print(f"阻塞: {len(report.blocked_tasks)}")
        print()
        
        if report.ready_tasks:
            print("就绪任务:")
            for tid in report.ready_tasks:
                print(f"  - {tid}: {report.tasks[tid].name}")
        
        if report.blocked_tasks:
            print("\n阻塞任务:")
            for tid in report.blocked_tasks:
                deps = report.tasks[tid].dependencies
                print(f"  - {tid}: {report.tasks[tid].name} (等待 {deps})")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
