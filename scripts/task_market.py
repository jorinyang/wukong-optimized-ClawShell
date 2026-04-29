#!/usr/bin/env python3
"""
TaskMarket - 统一任务队列管理系统
职责：
1. 管理所有任务的生命周期
2. 维护任务状态
3. 支持任务分发和认领
4. 记录任务历史（市场）
5. 提供查询接口
"""

import json
import os
import time
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from enum import Enum

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QUEUE_FILE = os.path.join(SHARED_DIR, "task-queue.json")
MARKET_FILE = os.path.join(SHARED_DIR, "task-market.json")
LOCK_FILE = os.path.join(SHARED_DIR, "task-market.lock")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "task_market.log")

# 任务状态枚举
class TaskStatus(Enum):
    PENDING = "pending"      # 待认领
    CLAIMED = "claimed"     # 已认领
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 取消

class TaskMarket:
    def __init__(self):
        self.queue_file = QUEUE_FILE
        self.market_file = MARKET_FILE
        self.lock_file = LOCK_FILE
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
            self._save_queue({"version": "v2", "queue_id": "main", "last_updated": self._now(), "tasks": []})
        
        if not os.path.exists(self.market_file):
            self._save_market({"version": "v2", "last_updated": self._now(), "tasks": []})
    
    def _now(self):
        return datetime.now().isoformat()
    
    @contextmanager
    def _lock(self, file_path):
        """文件锁上下文管理器"""
        lock_path = file_path + ".lock"
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        
        with open(lock_path, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            except BlockingIOError:
                self.log(f"⚠️ 文件被占用: {file_path}")
                yield
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except:
                    pass
    
    def _load_queue(self) -> Dict:
        with open(self.queue_file, 'r') as f:
            return json.load(f)
    
    def _save_queue(self, queue: Dict):
        with open(self.queue_file, 'w') as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
    
    def _load_market(self) -> Dict:
        with open(self.market_file, 'r') as f:
            return json.load(f)
    
    def _save_market(self, market: Dict):
        with open(self.market_file, 'w') as f:
            json.dump(market, f, indent=2, ensure_ascii=False)
    
    # ========== 核心操作 ==========
    
    def add_task(self, task: Dict) -> str:
        """添加新任务到队列"""
        task_id = task.get("id") or f"task-{int(time.time())}"
        
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            # 检查是否已存在
            existing = [t for t in queue["tasks"] if t.get("id") == task_id]
            if existing:
                self.log(f"⚠️ 任务已存在: {task_id}")
                return task_id
            
            # 添加任务
            new_task = {
                "id": task_id,
                "title": task.get("title", "Untitled"),
                "type": task.get("type", "general"),
                "priority": task.get("priority", "P3"),
                "description": task.get("description", ""),
                "status": TaskStatus.PENDING.value,
                "created_at": self._now(),
                "updated_at": self._now(),
            }
            
            queue["tasks"].append(new_task)
            queue["last_updated"] = self._now()
            self._save_queue(queue)
            
            self.log(f"✅ 任务已添加: {task_id}")
            return task_id
    
    def claim_task(self, task_id: str, agent: str) -> bool:
        """认领任务"""
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            for task in queue["tasks"]:
                if task["id"] == task_id:
                    if task["status"] != TaskStatus.PENDING.value:
                        self.log(f"⚠️ 任务不可认领: {task_id} ({task['status']})")
                        return False
                    
                    task["status"] = TaskStatus.CLAIMED.value
                    task["assigned_to"] = agent
                    task["claimed_at"] = self._now()
                    task["updated_at"] = self._now()
                    
                    queue["last_updated"] = self._now()
                    self._save_queue(queue)
                    
                    self.log(f"🎯 任务已认领: {task_id} -> {agent}")
                    return True
            
            self.log(f"⚠️ 任务不存在: {task_id}")
            return False
    
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """更新任务状态"""
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            for task in queue["tasks"]:
                if task["id"] == task_id:
                    task.update(updates)
                    task["updated_at"] = self._now()
                    task["status"] = updates.get("status", task["status"])
                    
                    queue["last_updated"] = self._now()
                    self._save_queue(queue)
                    
                    self.log(f"🔄 任务已更新: {task_id}")
                    return True
            
            return False
    
    def complete_task(self, task_id: str, result: str = None) -> bool:
        """完成任务"""
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            task_index = None
            task = None
            
            for i, t in enumerate(queue["tasks"]):
                if t["id"] == task_id:
                    task_index = i
                    task = t
                    break
            
            if task is None:
                self.log(f"⚠️ 任务不存在: {task_id}")
                return False
            
            # 移动到市场
            market = self._load_market()
            
            completed_task = task.copy()
            completed_task["status"] = TaskStatus.COMPLETED.value
            completed_task["completed_at"] = self._now()
            completed_task["updated_at"] = self._now()
            if result:
                completed_task["result"] = result
            
            market["tasks"].append(completed_task)
            market["last_updated"] = self._now()
            
            # 从队列移除
            queue["tasks"].pop(task_index)
            queue["last_updated"] = self._now()
            
            self._save_queue(queue)
            self._save_market(market)
            
            self.log(f"✅ 任务已完成: {task_id}")
            return True
    
    def fail_task(self, task_id: str, error: str = None) -> bool:
        """标记任务失败"""
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            task_index = None
            task = None
            
            for i, t in enumerate(queue["tasks"]):
                if t["id"] == task_id:
                    task_index = i
                    task = t
                    break
            
            if task is None:
                self.log(f"⚠️ 任务不存在: {task_id}")
                return False
            
            # 移动到市场
            market = self._load_market()
            
            failed_task = task.copy()
            failed_task["status"] = TaskStatus.FAILED.value
            failed_task["failed_at"] = self._now()
            failed_task["updated_at"] = self._now()
            if error:
                failed_task["error"] = error
            
            market["tasks"].append(failed_task)
            market["last_updated"] = self._now()
            
            # 从队列移除
            queue["tasks"].pop(task_index)
            queue["last_updated"] = self._now()
            
            self._save_queue(queue)
            self._save_market(market)
            
            self.log(f"❌ 任务失败: {task_id}")
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock(self.queue_file):
            queue = self._load_queue()
            
            task_index = None
            
            for i, t in enumerate(queue["tasks"]):
                if t["id"] == task_id:
                    task_index = i
                    break
            
            if task_index is None:
                self.log(f"⚠️ 任务不存在: {task_id}")
                return False
            
            queue["tasks"].pop(task_index)
            queue["last_updated"] = self._now()
            self._save_queue(queue)
            
            self.log(f"🚫 任务已取消: {task_id}")
            return True
    
    # ========== 查询操作 ==========
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        queue = self._load_queue()
        for task in queue["tasks"]:
            if task["id"] == task_id:
                return task
        
        market = self._load_market()
        for task in market["tasks"]:
            if task["id"] == task_id:
                return task
        
        return None
    
    def list_tasks(self, status: str = None, type: str = None, assigned_to: str = None) -> List[Dict]:
        """列出任务"""
        queue = self._load_queue()
        results = []
        
        for task in queue["tasks"]:
            if status and task.get("status") != status:
                continue
            if type and task.get("type") != type:
                continue
            if assigned_to and task.get("assigned_to") != assigned_to:
                continue
            results.append(task)
        
        return results
    
    def get_market(self, status: str = None, type: str = None, limit: int = 20) -> List[Dict]:
        """获取历史任务（市场）"""
        market = self._load_market()
        results = []
        
        for task in market["tasks"]:
            if status and task.get("status") != status:
                continue
            if type and task.get("type") != type:
                continue
            results.append(task)
        
        # 返回最近的
        return results[-limit:]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        queue = self._load_queue()
        market = self._load_market()
        
        queue_by_status = {}
        for t in queue["tasks"]:
            s = t.get("status", "unknown")
            queue_by_status[s] = queue_by_status.get(s, 0) + 1
        
        market_by_status = {}
        for t in market["tasks"]:
            s = t.get("status", "unknown")
            market_by_status[s] = market_by_status.get(s, 0) + 1
        
        return {
            "queue": {
                "total": len(queue["tasks"]),
                "by_status": queue_by_status
            },
            "market": {
                "total": len(market["tasks"]),
                "by_status": market_by_status
            },
            "last_updated": queue.get("last_updated")
        }


# CLI接口
if __name__ == "__main__":
    import sys
    
    tm = TaskMarket()
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "add":
        # add <id> <title> <type> [priority]
        if len(sys.argv) > 4:
            task_id = tm.add_task({
                "id": sys.argv[2],
                "title": sys.argv[3],
                "type": sys.argv[4],
                "priority": sys.argv[5] if len(sys.argv) > 5 else "P3"
            })
            print(f"任务已添加: {task_id}")
        else:
            print("用法: task_market.py add <id> <title> <type> [priority]")
    
    elif action == "claim":
        # claim <task_id> <agent>
        if len(sys.argv) > 3:
            success = tm.claim_task(sys.argv[2], sys.argv[3])
            print(f"认领{'成功' if success else '失败'}")
        else:
            print("用法: task_market.py claim <task_id> <agent>")
    
    elif action == "complete":
        # complete <task_id> [result]
        if len(sys.argv) > 2:
            result = sys.argv[3] if len(sys.argv) > 3 else None
            success = tm.complete_task(sys.argv[2], result)
            print(f"完成{'成功' if success else '失败'}")
        else:
            print("用法: task_market.py complete <task_id> [result]")
    
    elif action == "fail":
        # fail <task_id> [error]
        if len(sys.argv) > 2:
            error = sys.argv[3] if len(sys.argv) > 3 else None
            success = tm.fail_task(sys.argv[2], error)
            print(f"标记失败{'成功' if success else '失败'}")
        else:
            print("用法: task_market.py fail <task_id> [error]")
    
    elif action == "cancel":
        if len(sys.argv) > 2:
            success = tm.cancel_task(sys.argv[2])
            print(f"取消{'成功' if success else '失败'}")
        else:
            print("用法: task_market.py cancel <task_id>")
    
    elif action == "get":
        if len(sys.argv) > 2:
            task = tm.get_task(sys.argv[2])
            if task:
                print(json.dumps(task, indent=2, ensure_ascii=False))
            else:
                print("任务不存在")
        else:
            print("用法: task_market.py get <task_id>")
    
    elif action == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        for task in tm.list_tasks(status=status):
            print(f"[{task['status']}] {task['id']}: {task['title']}")
    
    elif action == "market":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        for task in tm.get_market(status=status, limit=limit):
            print(f"[{task['status']}] {task['id']}: {task['title']}")
    
    elif action == "stats":
        stats = tm.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif action == "status":
        stats = tm.get_stats()
        print(f"队列: {stats['queue']['total']} 个任务")
        print(f"市场: {stats['market']['total']} 个历史任务")
    
    else:
        print(f"未知操作: {action}")
        print("用法: task_market.py <add|claim|complete|fail|cancel|get|list|market|stats>")
