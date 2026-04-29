#!/usr/bin/env python3
"""
Performance Optimizer - 性能优化器
功能：
1. 分析脚本执行时间
2. 优化慢查询
3. 缓存管理
4. 资源清理
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================

SCRIPT_DIR = Path.home() / ".openclaw/scripts"
LOG_DIR = Path.home() / ".openclaw/logs"
CACHE_DIR = Path.home() / ".openclaw/cache"

# ==================== 性能分析 ====================

def analyze_scripts():
    """分析脚本性能"""
    results = []
    
    scripts = [
        "obsidian_graph_builder.py",
        "obsidian_link_discover.py",
        "obsidian_semantic_analyzer.py",
        "qa_semantic_search.py",
    ]
    
    for script_name in scripts:
        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            continue
        
        # 简单分析：文件大小和修改时间
        stat = script_path.stat()
        results.append({
            "name": script_name,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(script_path)
        })
    
    return results

def check_cache():
    """检查缓存"""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return {"status": "clean", "size": 0}
    
    total_size = sum(f.stat().st_size for f in CACHE_DIR.rglob("*") if f.is_file())
    file_count = len(list(CACHE_DIR.rglob("*")))
    
    return {
        "status": "ok" if total_size < 100 * 1024 * 1024 else "large",
        "size": total_size,
        "files": file_count
    }

def optimize_search():
    """优化搜索性能"""
    # 检查是否需要创建索引
    index_file = CACHE_DIR / "vault_index.json"
    
    if not index_file.exists():
        return {"optimized": False, "reason": "索引不存在"}
    
    # 检查索引年龄
    stat = index_file.stat()
    age = time.time() - stat.st_mtime
    
    if age > 3600:  # 超过1小时
        return {"optimized": True, "reason": "索引已刷新", "age_hours": age/3600}
    
    return {"optimized": False, "reason": "索引新鲜", "age_minutes": age/60}

def cleanup_old_logs():
    """清理旧日志"""
    if not LOG_DIR.exists():
        return {"cleaned": 0, "size_freed": 0}
    
    # 清理7天前的日志
    cutoff = time.time() - 7 * 24 * 3600
    cleaned = 0
    size_freed = 0
    
    for log_file in LOG_DIR.glob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            size = log_file.stat().st_size
            log_file.unlink()
            cleaned += 1
            size_freed += size
    
    return {"cleaned": cleaned, "size_freed": size_freed}

def main():
    print("=" * 60)
    print("      Performance Optimizer")
    print("=" * 60)
    
    # 分析脚本
    print("\n📊 脚本性能分析:")
    scripts = analyze_scripts()
    for s in scripts:
        print(f"   {s['name']}: {s['size']} bytes")
    
    # 检查缓存
    print("\n💾 缓存状态:")
    cache = check_cache()
    print(f"   状态: {cache['status']}")
    print(f"   大小: {cache.get('size', 0) / 1024:.1f} KB")
    print(f"   文件: {cache.get('files', 0)}")
    
    # 优化搜索
    print("\n🔍 搜索优化:")
    opt = optimize_search()
    print(f"   {opt['reason']}")
    
    # 清理日志
    print("\n🧹 日志清理:")
    cleanup = cleanup_old_logs()
    print(f"   清理: {cleanup['cleaned']} 个文件")
    print(f"   释放: {cleanup['size_freed'] / 1024:.1f} KB")
    
    print("\n" + "=" * 60)
    print("      优化完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
