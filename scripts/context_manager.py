#!/usr/bin/env python3
"""
ContextManager - 多Agent共享上下文管理器
职责：
1. 管理Agent间的共享状态
2. 提供读写接口
3. 处理并发写入冲突
4. 支持上下文快照和恢复
"""

import json
import os
import time
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
CONTEXT_FILE = os.path.join(SHARED_DIR, "context.json")
CONTEXT_LOCK = os.path.join(SHARED_DIR, "context.lock")
CONTEXT_HISTORY = os.path.join(SHARED_DIR, "context_history.json")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "context_manager.log")

# 默认上下文TTL（秒）
DEFAULT_TTL = 3600  # 1小时

class ContextManager:
    def __init__(self):
        self.context_file = CONTEXT_FILE
        self.lock_file = CONTEXT_LOCK
        self.history_file = CONTEXT_HISTORY
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
        os.makedirs(os.path.dirname(self.context_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        if not os.path.exists(self.context_file):
            self._save_context({"version": "1.0", "data": {}, "metadata": {}})
    
    def _load_context(self) -> Dict:
        """加载上下文（加锁）"""
        with open(self.context_file, 'r') as f:
            return json.load(f)
    
    def _save_context(self, context: Dict):
        """保存上下文（加锁）"""
        with open(self.context_file, 'w') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
    
    @contextmanager
    def _lock(self):
        """文件锁上下文管理器"""
        lock_file = self.lock_file
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        
        with open(lock_file, 'w') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
            except BlockingIOError:
                self.log("⚠️ 上下文被其他进程占用")
                yield  # 降级处理
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except:
                    pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """读取上下文值"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                
                if key not in data:
                    return default
                
                entry = data[key]
                
                # 检查TTL
                if "expires_at" in entry:
                    if time.time() > entry["expires_at"]:
                        self.log(f"⏰ 上下文已过期: {key}")
                        del data[key]
                        self._save_context(context)
                        return default
                
                return entry.get("value", default)
        except Exception as e:
            self.log(f"⚠️ 读取上下文失败 {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = None, owner: str = None):
        """写入上下文值"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                
                entry = {
                    "value": value,
                    "updated_at": datetime.now().isoformat(),
                    "updated_by": owner or "unknown"
                }
                
                if ttl:
                    entry["expires_at"] = time.time() + ttl
                
                data[key] = entry
                context["data"] = data
                context["metadata"]["last_updated"] = datetime.now().isoformat()
                
                self._save_context(context)
                self.log(f"✅ 设置上下文: {key}")
                return True
        except Exception as e:
            self.log(f"⚠️ 写入上下文失败 {key}: {e}")
            return False
    
    def delete(self, key: str):
        """删除上下文值"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                
                if key in data:
                    del data[key]
                    context["data"] = data
                    self._save_context(context)
                    self.log(f"🗑️ 删除上下文: {key}")
                    return True
                return False
        except Exception as e:
            self.log(f"⚠️ 删除上下文失败 {key}: {e}")
            return False
    
    def keys(self, pattern: str = None) -> List[str]:
        """列出所有上下文键"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                keys = list(data.keys())
                
                if pattern:
                    import fnmatch
                    keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
                
                return keys
        except Exception as e:
            self.log(f"⚠️ 列出上下文失败: {e}")
            return []
    
    def snapshot(self, name: str = None) -> bool:
        """创建上下文快照"""
        try:
            if not name:
                name = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            with self._lock():
                context = self._load_context()
                
                history = []
                if os.path.exists(self.history_file):
                    with open(self.history_file, 'r') as f:
                        history = json.load(f)
                
                history.append({
                    "name": name,
                    "timestamp": datetime.now().isoformat(),
                    "data": context.get("data", {})
                })
                
                # 只保留最近10个快照
                history = history[-10:]
                
                with open(self.history_file, 'w') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                
                self.log(f"📸 快照已创建: {name}")
                return True
        except Exception as e:
            self.log(f"⚠️ 创建快照失败: {e}")
            return False
    
    def restore(self, name: str = None) -> bool:
        """恢复上下文快照"""
        try:
            with self._lock():
                if not os.path.exists(self.history_file):
                    self.log("⚠️ 无历史快照")
                    return False
                
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                
                if not history:
                    self.log("⚠️ 无历史快照")
                    return False
                
                if name:
                    snapshot = next((h for h in history if h["name"] == name), None)
                else:
                    snapshot = history[-1]  # 恢复最新
                
                if not snapshot:
                    self.log(f"⚠️ 快照不存在: {name}")
                    return False
                
                context = self._load_context()
                context["data"] = snapshot["data"]
                context["metadata"]["last_restored"] = datetime.now().isoformat()
                context["metadata"]["restored_from"] = snapshot["name"]
                
                self._save_context(context)
                self.log(f"♻️ 已恢复快照: {snapshot['name']}")
                return True
        except Exception as e:
            self.log(f"⚠️ 恢复快照失败: {e}")
            return False
    
    def clear_expired(self):
        """清理过期上下文"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                now = time.time()
                
                expired_keys = [
                    k for k, v in data.items()
                    if "expires_at" in v and now > v["expires_at"]
                ]
                
                for key in expired_keys:
                    del data[key]
                
                if expired_keys:
                    context["data"] = data
                    self._save_context(context)
                    self.log(f"🧹 清理了 {len(expired_keys)} 个过期上下文")
                
                return len(expired_keys)
        except Exception as e:
            self.log(f"⚠️ 清理过期上下文失败: {e}")
            return 0
    
    def status(self) -> Dict:
        """获取状态"""
        try:
            with self._lock():
                context = self._load_context()
                data = context.get("data", {})
                
                return {
                    "total_keys": len(data),
                    "keys": list(data.keys()),
                    "last_updated": context.get("metadata", {}).get("last_updated"),
                    "history_count": 0
                }
        except Exception as e:
            self.log(f"⚠️ 获取状态失败: {e}")
            return {"error": str(e)}


# CLI接口
if __name__ == "__main__":
    import sys
    
    cm = ContextManager()
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "get":
        key = sys.argv[2] if len(sys.argv) > 2 else None
        if key:
            value = cm.get(key)
            print(json.dumps(value, indent=2, ensure_ascii=False))
        else:
            print("用法: context_manager.py get <key>")
    
    elif action == "set":
        if len(sys.argv) > 3:
            key = sys.argv[2]
            value = json.loads(sys.argv[3])
            cm.set(key, value)
        else:
            print("用法: context_manager.py set <key> <value>")
    
    elif action == "delete":
        key = sys.argv[2] if len(sys.argv) > 2 else None
        if key:
            cm.delete(key)
        else:
            print("用法: context_manager.py delete <key>")
    
    elif action == "keys":
        pattern = sys.argv[2] if len(sys.argv) > 2 else None
        for key in cm.keys(pattern):
            print(key)
    
    elif action == "snapshot":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        cm.snapshot(name)
    
    elif action == "restore":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        cm.restore(name)
    
    elif action == "clear-expired":
        cm.clear_expired()
    
    elif action == "status":
        status = cm.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    else:
        print(f"未知操作: {action}")
        print("用法: context_manager.py <get|set|delete|keys|snapshot|restore|clear-expired|status>")
