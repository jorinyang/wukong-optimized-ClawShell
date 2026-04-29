#!/usr/bin/env python3
"""
hermes_insight_bridge.py - Hermes到OpenClaw的桥接
功能：
1. 监听Hermes洞察输出
2. 将洞察同步到OpenClaw知识库
3. 更新系统状态
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
HERMES_INSIGHTS = os.path.expanduser("~/.hermes/insights")
OPENCLAW_INSIGHTS = os.path.join(SHARED_DIR, "hermes_insights")
BRIDGE_LOG = os.path.join(SHARED_DIR, "logs", "hermes_insight_bridge.log")

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    os.makedirs(os.path.dirname(BRIDGE_LOG), exist_ok=True)
    with open(BRIDGE_LOG, "a") as f:
        f.write(log_line + "\n")

def sync_insights():
    """同步Hermes洞察到OpenClaw"""
    os.makedirs(OPENCLAW_INSIGHTS, exist_ok=True)
    
    if not os.path.exists(HERMES_INSIGHTS):
        log("⚠️ Hermes insights目录不存在")
        return 0
    
    synced = 0
    for filename in os.listdir(HERMES_INSIGHTS):
        if not filename.endswith('.json'):
            continue
        
        src = os.path.join(HERMES_INSIGHTS, filename)
        dst = os.path.join(OPENCLAW_INSIGHTS, filename)
        
        # 跳过已同步的
        if os.path.exists(dst):
            continue
        
        try:
            shutil.copy2(src, dst)
            log(f"✅ 同步洞察: {filename}")
            synced += 1
        except Exception as e:
            log(f"❌ 同步失败 {filename}: {e}")
    
    return synced

if __name__ == "__main__":
    log("🚀 Hermes Insight Bridge 启动")
    synced = sync_insights()
    log(f"📊 同步完成: {synced} 个洞察")
