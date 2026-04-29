#!/usr/bin/env python3
"""
Memory Bidirectional Sync - 记忆双向同步
功能：
1. OpenClaw记忆 → Hermes
2. Hermes记忆 → OpenClaw
3. 冲突检测与处理
4. 同步状态记录
"""

import os
import sys
import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Set

# 配置
OPENCLAW_DIR = Path.home() / ".openclaw"
MEMORY_DIR = OPENCLAW_DIR / "workspace" / "memory"
BRIDGE_DIR = OPENCLAW_DIR / "shared" / "memory_bridge"
OPENCLAW_TO_HERMES = BRIDGE_DIR / "openclaw_to_hermes"
HERMES_TO_OPENCLAW = BRIDGE_DIR / "hermes_to_openclaw"
STATE_FILE = BRIDGE_DIR / ".sync_state.json"
LOG_FILE = OPENCLAW_DIR / "logs" / "memory_sync.log"

# 同步配置
SYNC_CONFIG = {
    "openclaw_to_hermes": {
        "enabled": True,
        "memory_types": ["strategic", "project", "client"],
        "exclude_patterns": ["backups", "sessions", ".", "_"],
        "max_age_days": 7
    },
    "hermes_to_openclaw": {
        "enabled": True,
        "memory_types": ["insight", "reflection", "pattern"],
        "conflict_strategy": "skip"  # skip, hermes_wins, openclaw_wins
    }
}


class MemorySync:
    """记忆同步器"""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": None,
            "openclaw_synced": [],
            "hermes_synced": [],
            "conflicts": []
        }
    
    def _save_state(self):
        """保存状态"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, msg: str):
        """写日志"""
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {msg}\n")
    
    def sync_openclaw_to_hermes(self) -> int:
        """同步OpenClaw记忆到Hermes"""
        if not SYNC_CONFIG["openclaw_to_hermes"]["enabled"]:
            return 0
        
        synced = 0
        config = SYNC_CONFIG["openclaw_to_hermes"]
        max_age = datetime.now() - timedelta(days=config["max_age_days"])
        
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        OPENCLAW_TO_HERMES.mkdir(parents=True, exist_ok=True)
        
        for memory_file in MEMORY_DIR.glob("*.md"):
            # 检查文件名是否被排除
            filename = memory_file.name
            if any(pattern in filename for pattern in config["exclude_patterns"]):
                continue
            
            # 检查时间
            mtime = datetime.fromtimestamp(memory_file.stat().st_mtime)
            if mtime < max_age:
                continue
            
            # 检查是否已同步
            file_hash = self._get_file_hash(memory_file)
            if file_hash in self.state.get("openclaw_synced", []):
                continue
            
            # 同步
            if self._sync_file(memory_file, OPENCLAW_TO_HERMES):
                if "openclaw_synced" not in self.state:
                    self.state["openclaw_synced"] = []
                self.state["openclaw_synced"].append(file_hash)
                synced += 1
        
        self.state["last_sync"] = datetime.now().isoformat()
        self._save_state()
        
        return synced
    
    def sync_hermes_to_openclaw(self) -> int:
        """同步Hermes记忆到OpenClaw"""
        if not SYNC_CONFIG["hermes_to_openclaw"]["enabled"]:
            return 0
        
        synced = 0
        config = SYNC_CONFIG["hermes_to_openclaw"]
        
        HERMES_TO_OPENCLAW.mkdir(parents=True, exist_ok=True)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        for memory_file in HERMES_TO_OPENCLAW.glob("*.md"):
            file_hash = self._get_file_hash(memory_file)
            
            if file_hash in self.state.get("hermes_synced", []):
                continue
            
            # 检查冲突
            target_file = MEMORY_DIR / memory_file.name
            if target_file.exists():
                if not self._check_no_conflict(target_file, memory_file):
                    continue
            
            # 同步
            if self._sync_file(memory_file, MEMORY_DIR):
                if "hermes_synced" not in self.state:
                    self.state["hermes_synced"] = []
                self.state["hermes_synced"].append(file_hash)
                synced += 1
        
        self._save_state()
        return synced
    
    def _sync_file(self, source: Path, target_dir: Path) -> bool:
        """同步单个文件"""
        try:
            target = target_dir / source.name
            shutil.copy2(str(source), str(target))
            self._log(f"Synced: {source.name}")
            return True
        except Exception as e:
            self._log(f"Sync error: {source.name}: {e}")
            return False
    
    def _get_file_hash(self, path: Path) -> str:
        """获取文件hash"""
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _check_no_conflict(self, file1: Path, file2: Path) -> bool:
        """检查是否有冲突"""
        hash1 = self._get_file_hash(file1)
        hash2 = self._get_file_hash(file2)
        
        if hash1 == hash2:
            return True  # 内容相同，无冲突
        
        # 内容不同，记录冲突但仍然同步
        if "conflicts" not in self.state:
            self.state["conflicts"] = []
        self.state["conflicts"].append({
            "file": str(file1.name),
            "strategy": "copied_both"
        })
        
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Memory Bidirectional Sync")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--direction", choices=["both", "to_hermes", "from_hermes"], default="both")
    args = parser.parse_args()
    
    sync = MemorySync()
    
    if args.dry_run:
        print(f"最后同步: {sync.state.get('last_sync', '从未')}")
        print(f"OpenClaw已同步: {len(sync.state.get('openclaw_synced', []))}")
        print(f"Hermes已同步: {len(sync.state.get('hermes_synced', []))}")
    else:
        if args.direction in ["both", "to_hermes"]:
            o2h = sync.sync_openclaw_to_hermes()
            print(f"OpenClaw→Hermes: {o2h}个文件")
        
        if args.direction in ["both", "from_hermes"]:
            h2o = sync.sync_hermes_to_openclaw()
            print(f"Hermes→OpenClaw: {h2o}个文件")


if __name__ == "__main__":
    main()
