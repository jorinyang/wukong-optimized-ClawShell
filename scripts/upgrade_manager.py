#!/usr/bin/env python3
"""
Upgrade Manager - 升级机制脚本
功能：
1. 版本检查
2. 自动升级
3. 回滚机制
4. 升级日志
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

SCRIPT_DIR = Path.home() / ".openclaw/scripts"
BACKUP_DIR = Path.home() / ".openclaw/backups"
UPGRADE_LOG = Path.home() / ".openclaw/logs/upgrade.log"

# ==================== 版本管理器 ====================

class Version:
    def __init__(self, version_str: str):
        self.string = version_str
        parts = version_str.lstrip('v').split('.')
        self.major = int(parts[0]) if len(parts) > 0 else 0
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
    
    def __str__(self):
        return self.string
    
    def __eq__(self, other):
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other):
        return self == other or self < other
    
    def __gt__(self, other):
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    def __ge__(self, other):
        return self == other or self > other

class UpgradeManager:
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.scripts = self._scan_scripts()
    
    def _scan_scripts(self) -> Dict[str, str]:
        """扫描脚本目录"""
        scripts = {}
        
        if SCRIPT_DIR.exists():
            for script_file in SCRIPT_DIR.glob("*.py"):
                scripts[script_file.name] = str(script_file)
        
        return scripts
    
    def get_script_version(self, script_name: str) -> Optional[str]:
        """获取脚本版本"""
        script_path = SCRIPT_DIR / script_name
        
        if not script_path.exists():
            return None
        
        with open(script_path, 'r') as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
        
        return None
    
    def create_backup(self, script_name: str = None) -> Optional[str]:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if script_name:
            script_path = SCRIPT_DIR / script_name
            if not script_path.exists():
                return None
            
            backup_name = f"{script_name}.{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(script_path, backup_path)
            
            # 计算hash
            with open(backup_path, 'rb') as f:
                hash_value = hashlib.md5(f.read()).hexdigest()
            
            # 记录备份信息
            self._log_upgrade("backup", {
                "script": script_name,
                "backup": str(backup_path),
                "hash": hash_value
            })
            
            return str(backup_path)
        
        else:
            # 备份所有脚本
            backup_name = f"all_scripts.{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            for script_path in SCRIPT_DIR.glob("*.py"):
                shutil.copy2(script_path, backup_path / script_path.name)
            
            self._log_upgrade("backup_all", {"backup": str(backup_path)})
            
            return str(backup_path)
    
    def restore_backup(self, backup_path: str, script_name: str = None) -> bool:
        """恢复备份"""
        backup = Path(backup_path)
        
        if not backup.exists():
            return False
        
        try:
            if backup.is_file():
                # 单文件恢复
                target = SCRIPT_DIR / (script_name or backup.name.replace(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak", ""))
                shutil.copy2(backup, target)
            elif backup.is_dir():
                # 目录恢复
                for script_path in backup.glob("*.py"):
                    shutil.copy2(script_path, SCRIPT_DIR / script_path.name)
            
            self._log_upgrade("restore", {
                "backup": str(backup),
                "script": script_name
            })
            
            return True
        
        except Exception as e:
            self._log_upgrade("restore_error", {"error": str(e)})
            return False
    
    def list_backups(self) -> List[Dict]:
        """列出备份"""
        backups = []
        
        for backup in sorted(self.backup_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({
                "name": backup.name,
                "path": str(backup),
                "size": backup.stat().st_size,
                "modified": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
                "type": "file" if backup.is_file() else "directory"
            })
        
        return backups
    
    def check_upgrade(self) -> Dict:
        """检查升级"""
        # 这里简化处理，实际应连接远程仓库检查
        return {
            "current_version": "1.0.0",
            "latest_version": "1.0.0",
            "update_available": False,
            "scripts": len(self.scripts)
        }
    
    def _log_upgrade(self, action: str, details: Dict):
        """记录升级日志"""
        UPGRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
        
        with open(UPGRADE_LOG, 'a') as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "details": details
            }
            f.write(json.dumps(log_entry) + "\n")

# ==================== 主函数 ====================

def main():
    manager = UpgradeManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  upgrade_manager.py check")
        print("  upgrade_manager.py backup [script_name]")
        print("  upgrade_manager.py restore <backup_path> [script_name]")
        print("  upgrade_manager.py list")
        print("  upgrade_manager.py version [script_name]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        result = manager.check_upgrade()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "backup":
        script_name = sys.argv[2] if len(sys.argv) > 2 else None
        backup_path = manager.create_backup(script_name)
        
        if backup_path:
            print(f"备份成功: {backup_path}")
        else:
            print("备份失败")
    
    elif command == "restore":
        backup_path = sys.argv[2] if len(sys.argv) > 2 else ""
        script_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        if manager.restore_backup(backup_path, script_name):
            print("恢复成功")
        else:
            print("恢复失败")
    
    elif command == "list":
        backups = manager.list_backups()
        print(f"备份列表 ({len(backups)}个):")
        for backup in backups[:10]:
            print(f"  {backup['modified'][:19]} - {backup['name']} ({backup['size']} bytes)")
    
    elif command == "version":
        script_name = sys.argv[2] if len(sys.argv) > 2 else None
        if script_name:
            version = manager.get_script_version(script_name)
            print(f"{script_name}: {version or '未知版本'}")
        else:
            print("脚本版本:")
            for name in sorted(manager.scripts.keys()):
                version = manager.get_script_version(name)
                print(f"  {name}: {version or '未知版本'}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
