#!/usr/bin/env python3
"""
TaskDependency - 任务依赖自动触发系统
职责：
1. 解析任务依赖关系 (depends_on)
2. 监控依赖任务完成状态
3. 自动触发满足条件的下游任务
4. 防止循环依赖
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Set, Optional
from pathlib import Path

# 路径配置
WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QUEUE_FILE = os.path.join(SHARED_DIR, "task-queue.json")
MARKET_FILE = os.path.join(SHARED_DIR, "task-market.json")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "task_dependency.log")

class TaskDependency:
    def __init__(self):
        self.queue_file = QUEUE_FILE
        self.market_file = MARKET_FILE
        self.log_file = LOG_FILE
        self._ensure_files()
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    def _ensure_files(self):
        """确保必要文件存在"""
        os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.market_file), exist_ok=True)
        
        if not os.path.exists(self.queue_file):
            with open(self.queue_file, 'w') as f:
                json.dump({"version": "v2", "tasks": []}, f)
        
        if not os.path.exists(self.market_file):
            with open(self.market_file, 'w') as f:
                json.dump({"version": "v2", "tasks": []}, f)
    
    def _load_queue(self) -> Dict:
        with open(self.queue_file, 'r') as f:
            return json.load(f)
    
    def _save_queue(self, queue: Dict):
        with open(self.queue_file, 'w') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
    
    def _load_market(self) -> Dict:
        with open(self.market_file, 'r') as f:
            return json.load(f)
    
    def _load_all_tasks(self) -> List[Dict]:
        """加载所有任务（队列+市场）"""
        queue = self._load_queue()
        market = self._load_market()
        return queue.get("tasks", []) + market.get("tasks", [])
    
    def detect_cycle(self, task_id: str, depends_on: List[str]) -> bool:
        """检测循环依赖"""
        visited = set()
        stack = set(depends_on)
        
        while stack:
            current = stack.pop()
            
            if current == task_id:
                return True  # 发现循环
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # 查找这个任务的依赖
            for task in self._load_all_tasks():
                if task.get("id") == current:
                    deps = task.get("depends_on", [])
                    stack.update(deps)
        
        return False
    
    def add_dependency(self, task_id: str, depends_on: List[str]) -> bool:
        """添加任务依赖"""
        # 检测循环依赖
        if self.detect_cycle(task_id, depends_on):
            self.log(f"⚠️ 检测到循环依赖: {task_id} -> {depends_on}")
            return False
        
        # 更新任务
        queue = self._load_queue()
        
        for task in queue.get("tasks", []):
            if task.get("id") == task_id:
                task["depends_on"] = depends_on
                self._save_queue(queue)
                self.log(f"🔗 设置依赖: {task_id} -> {depends_on}")
                return True
        
        self.log(f"⚠️ 任务不存在: {task_id}")
        return False
    
    def check_dependencies(self, task_id: str) -> Dict:
        """检查任务依赖状态"""
        queue = self._load_queue()
        market = self._load_market()
        
        all_tasks = queue.get("tasks", []) + market.get("tasks", [])
        
        task = None
        for t in all_tasks:
            if t.get("id") == task_id:
                task = t
                break
        
        if not task:
            return {"exists": False}
        
        depends_on = task.get("depends_on", [])
        
        if not depends_on:
            return {
                "exists": True,
                "can_run": True,
                "dependencies": []
            }
        
        results = []
        all_satisfied = True
        
        for dep_id in depends_on:
            # 在队列中查找
            in_queue = any(t.get("id") == dep_id for t in queue.get("tasks", []))
            
            # 在市场中查找（已完成的任务）
            in_market = None
            for t in market.get("tasks", []):
                if t.get("id") == dep_id:
                    in_market = t
                    break
            
            if in_market and in_market.get("status") == "completed":
                results.append({"id": dep_id, "status": "completed"})
            elif in_queue:
                results.append({"id": dep_id, "status": "pending"})
                all_satisfied = False
            else:
                results.append({"id": dep_id, "status": "not_found"})
                all_satisfied = False
        
        return {
            "exists": True,
            "can_run": all_satisfied,
            "dependencies": results
        }
    
    def process_dependencies(self) -> List[str]:
        """处理所有任务的依赖，自动触发可运行的任务"""
        triggered = []
        queue = self._load_queue()
        
        for task in queue.get("tasks", []):
            if task.get("status") not in ["pending"]:
                continue
            
            dep_check = self.check_dependencies(task.get("id"))
            
            if dep_check.get("can_run") and dep_check.get("dependencies"):
                # 有依赖但都满足了，标记为可运行
                self.log(f"✅ 任务可运行: {task.get('id')}")
        
        return triggered
    
    def auto_trigger(self) -> Dict:
        """自动触发满足条件的后续任务"""
        results = {
            "triggered": [],
            "checked": 0
        }
        
        queue = self._load_queue()
        
        for task in queue.get("tasks", []):
            if task.get("status") not in ["pending"]:
                continue
            
            dep_check = self.check_dependencies(task.get("id"))
            results["checked"] += 1
            
            if not dep_check.get("exists"):
                continue
            
            depends_on = task.get("depends_on", [])
            if not depends_on:
                continue
            
            if dep_check.get("can_run"):
                # 依赖都满足了，可以触发
                results["triggered"].append({
                    "task_id": task.get("id"),
                    "title": task.get("title"),
                    "message": f"依赖任务已完成，{task.get('title')} 可以开始执行"
                })
                self.log(f"🚀 自动触发: {task.get('id')}")
        
        return results
    
    def get_dependency_tree(self, task_id: str, depth: int = 0, max_depth: int = 5) -> Dict:
        """获取任务依赖树"""
        if depth > max_depth:
            return {"id": task_id, "truncated": True}
        
        all_tasks = self._load_all_tasks()
        task = None
        for t in all_tasks:
            if t.get("id") == task_id:
                task = t
                break
        
        if not task:
            return {"id": task_id, "status": "not_found"}
        
        node = {
            "id": task_id,
            "title": task.get("title"),
            "status": task.get("status"),
            "depends_on": []
        }
        
        for dep_id in task.get("depends_on", []):
            node["depends_on"].append(
                self.get_dependency_tree(dep_id, depth + 1, max_depth)
            )
        
        return node
    
    def validate_all(self) -> Dict:
        """验证所有任务的依赖关系"""
        issues = []
        queue = self._load_queue()
        
        for task in queue.get("tasks", []):
            task_id = task.get("id")
            depends_on = task.get("depends_on", [])
            
            if not depends_on:
                continue
            
            # 检测循环
            if self.detect_cycle(task_id, depends_on):
                issues.append({
                    "type": "cycle",
                    "task_id": task_id,
                    "depends_on": depends_on
                })
            
            # 检查依赖是否存在
            all_tasks = self._load_all_tasks()
            for dep_id in depends_on:
                exists = any(t.get("id") == dep_id for t in all_tasks)
                if not exists:
                    issues.append({
                        "type": "missing",
                        "task_id": task_id,
                        "missing_dep": dep_id
                    })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


# CLI接口
if __name__ == "__main__":
    import sys
    
    td = TaskDependency()
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "add":
        # add <task_id> <dep1,dep2>
        if len(sys.argv) > 2:
            task_id = sys.argv[2]
            deps = sys.argv[3].split(",") if len(sys.argv) > 3 else []
            success = td.add_dependency(task_id, deps)
            print(f"设置依赖{'成功' if success else '失败'}")
        else:
            print("用法: task_dependency.py add <task_id> <dep1,dep2>")
    
    elif action == "check":
        if len(sys.argv) > 2:
            result = td.check_dependencies(sys.argv[2])
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("用法: task_dependency.py check <task_id>")
    
    elif action == "trigger":
        results = td.auto_trigger()
        print(f"检查了 {results['checked']} 个任务")
        print(f"触发了 {len(results['triggered'])} 个任务")
        for t in results["triggered"]:
            print(f"  - {t['task_id']}: {t['message']}")
    
    elif action == "tree":
        if len(sys.argv) > 2:
            tree = td.get_dependency_tree(sys.argv[2])
            print(json.dumps(tree, indent=2, ensure_ascii=False))
        else:
            print("用法: task_dependency.py tree <task_id>")
    
    elif action == "validate":
        result = td.validate_all()
        if result["valid"]:
            print("✅ 所有依赖关系有效")
        else:
            print(f"⚠️ 发现 {len(result['issues'])} 个问题:")
            for issue in result["issues"]:
                print(f"  - {issue}")
    
    elif action == "status":
        queue = td._load_queue()
        with_deps = sum(1 for t in queue.get("tasks", []) if t.get("depends_on"))
        print(f"队列任务: {len(queue.get('tasks', []))} 个")
        print(f"带依赖任务: {with_deps} 个")
    
    else:
        print(f"未知操作: {action}")
        print("用法: task_dependency.py <add|check|trigger|tree|validate|status>")
