#!/usr/bin/env python3
"""
ClawShell Cache Manager
智能缓存管理器 - Phase 2
版本: v1.0.0
功能: LRU缓存+预取
"""

import time
import threading
from typing import Any, Dict, Optional, Callable
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 3600  # 默认1小时

class SmartCache:
    """
    智能缓存管理器
    
    功能：
    - LRU淘汰策略
    - TTL过期
    - 预取机制
    - 统计监控
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "prefetch": 0
        }
        self._prefetch_callbacks: Dict[str, Callable] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # 检查TTL
            if time.time() - entry.created_at > entry.ttl:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            # 更新访问时间
            entry.last_accessed = time.time()
            entry.access_count += 1
            self._cache.move_to_end(key)
            
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: float = None):
        """设置缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.default_ttl
            )
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            # LRU淘汰
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
    
    def prefetch(self, keys: list):
        """预取缓存"""
        for key in keys:
            if key not in self._cache:
                if key in self._prefetch_callbacks:
                    value = self._prefetch_callbacks[key]()
                    if value is not None:
                        self.set(key, value)
                        self._stats["prefetch"] += 1
    
    def register_prefetch(self, key: str, callback: Callable):
        """注册预取回调"""
        self._prefetch_callbacks[key] = callback
    
    def invalidate(self, key: str):
        """使缓存失效"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            **self._stats
        }
    
    def auto_prefetch(self, threshold: float = 0.7):
        """自动预取 - 当命中率低于阈值时"""
        stats = self.get_stats()
        if stats["hit_rate"] < threshold:
            # 触发预取
            for key, callback in self._prefetch_callbacks.items():
                if key not in self._cache:
                    value = callback()
                    if value:
                        self.set(key, value)
                        self._stats["prefetch"] += 1

# 全局缓存实例
_global_cache: Optional[SmartCache] = None

def get_cache() -> SmartCache:
    """获取全局缓存"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SmartCache(max_size=1000, default_ttl=3600)
    return _global_cache

if __name__ == "__main__":
    cache = SmartCache(max_size=100, default_ttl=10)
    
    # 测试
    print("=== 智能缓存测试 ===")
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    print(f"get key1: {cache.get('key1')}")
    print(f"get key2: {cache.get('key2')}")
    print(f"get key3: {cache.get('key3')}")
    
    print(f"\nStats: {cache.get_stats()}")
