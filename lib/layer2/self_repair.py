#!/usr/bin/env python3
"""
ClawShell 自修复引擎 (Self-Healing Engine)
版本: v0.2.1-B
功能: 自动备份、自动迁移、自动回滚、备用切换
"""

import os
import json
import time
import shutil
import subprocess
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

# ============ 配置 ============

HEALING_STATE_PATH = Path("~/.real/.healing_state.json").expanduser()
BACKUP_DIR = Path("~/.real/backups").expanduser()
CHECKPOINT_DIR = Path("~/.real/checkpoints").expanduser()
CONFIG_DIR = Path("~/.real/config").expanduser()


# ============ 数据结构 ============

@dataclass
class Backup:
    """备份描述"""
    id: str
    timestamp: float
    type: str  # full, incremental, config, state
    path: str
    size: int
    checksum: str
    description: str
    status: str  # completed, failed, pending
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "path": self.path,
            "size": self.size,
            "checksum": self.checksum,
            "description": self.description,
            "status": self.status
        }


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    timestamp: float
    name: str
    description: str
    components: List[str]  # 已备份的组件
    status: str  # created, applied, expired
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "name": self.name,
            "description": self.description,
            "components": self.components,
            "status": self.status,
            "metadata": self.metadata
        }


@dataclass
class HealingAction:
    """修复动作"""
    action: str  # backup, restore, migrate, switch
    target: str
    source: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "target": self.target,
            "source": self.source,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp
        }


@dataclass
class HealingReport:
    """修复报告"""
    timestamp: float
    actions: List[HealingAction]
    summary: Dict[str, int]  # 各状态计数
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "actions": [a.to_dict() for a in self.actions],
            "summary": self.summary,
            "recommendations": self.recommendations
        }


# ============ 工具函数 ============

def calculate_checksum(path: Path) -> str:
    """计算文件校验和"""
    import hashlib
    
    if path.is_file():
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    elif path.is_dir():
        # 计算目录哈希
        hash_md5 = hashlib.md5()
        for item in sorted(path.rglob("*")):
            if item.is_file():
                with open(item, 'rb') as f:
                    hash_md5.update(item.name.encode())
                    hash_md5.update(f.read())
        return hash_md5.hexdigest()
    
    return ""


def get_dir_size(path: Path) -> int:
    """计算目录大小"""
    total = 0
    if path.is_file():
        total = path.stat().st_size
    elif path.is_dir():
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    return total


def format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


# ============ 备份管理器 ============

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if HEALING_STATE_PATH.exists():
            try:
                with open(HEALING_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {"backups": [], "checkpoints": []}
    
    def _save_state(self):
        """保存状态"""
        with open(HEALING_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def create_backup(self, name: str, paths: List[str], backup_type: str = "full") -> Optional[Backup]:
        """创建备份"""
        backup_id = f"backup_{int(time.time())}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        description = f"{backup_type} backup: {name}"
        
        try:
            total_size = 0
            backed_up = []
            
            for path_str in paths:
                path = Path(path_str).expanduser()
                if not path.exists():
                    continue
                
                dest = backup_path / path.name
                
                if path.is_file():
                    shutil.copy2(path, dest)
                    total_size += path.stat().st_size
                elif path.is_dir():
                    shutil.copytree(path, dest, dirs_exist_ok=True)
                    total_size += get_dir_size(path)
                
                backed_up.append(path_str)
            
            checksum = calculate_checksum(backup_path)
            
            backup = Backup(
                id=backup_id,
                timestamp=time.time(),
                type=backup_type,
                path=str(backup_path),
                size=total_size,
                checksum=checksum,
                description=description,
                status="completed"
            )
            
            # 保存到状态
            self.state["backups"].append(backup.to_dict())
            self._save_state()
            
            return backup
            
        except Exception as e:
            return Backup(
                id=backup_id,
                timestamp=time.time(),
                type=backup_type,
                path=str(backup_path),
                size=0,
                checksum="",
                description=description,
                status="failed"
            )
    
    def restore_backup(self, backup_id: str, target_paths: Optional[List[str]] = None) -> bool:
        """恢复备份"""
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            return False
        
        backup_path = Path(backup_info["path"])
        if not backup_path.exists():
            return False
        
        try:
            if target_paths:
                for i, target_str in enumerate(target_paths):
                    target = Path(target_str).expanduser()
                    source = backup_path / target.name
                    
                    if source.exists():
                        if target.is_dir():
                            shutil.rmtree(target)
                        shutil.copytree(source, target)
            else:
                # 恢复到原始位置
                for item in backup_path.iterdir():
                    dest = Path.home() / item.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                    shutil.copytree(item, dest)
            
            return True
        except Exception as e:
            print(f"恢复失败: {e}")
            return False
    
    def _get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """获取备份信息"""
        for backup in self.state.get("backups", []):
            if backup["id"] == backup_id:
                return backup
        return None
    
    def list_backups(self, limit: int = 10) -> List[Backup]:
        """列出备份"""
        backups = [Backup(**b) for b in self.state.get("backups", [])]
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups[:limit]
    
    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            return False
        
        try:
            backup_path = Path(backup_info["path"])
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            self.state["backups"] = [
                b for b in self.state["backups"] if b["id"] != backup_id
            ]
            self._save_state()
            return True
        except:
            return False


# ============ 检查点管理器 ============

class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self):
        self.checkpoint_dir = CHECKPOINT_DIR
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if HEALING_STATE_PATH.exists():
            try:
                with open(HEALING_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {"backups": [], "checkpoints": []}
    
    def _save_state(self):
        with open(HEALING_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def create_checkpoint(self, name: str, description: str, components: List[str]) -> Checkpoint:
        """创建检查点"""
        checkpoint_id = f"cp_{int(time.time())}"
        
        # 备份关键组件
        backup_manager = BackupManager()
        backup = backup_manager.create_backup(
            name=f"checkpoint_{checkpoint_id}",
            paths=components,
            backup_type="full"
        )
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=time.time(),
            name=name,
            description=description,
            components=components,
            status="created",
            metadata={"backup_id": backup.id if backup else None}
        )
        
        # 保存检查点信息
        self.state["checkpoints"].append(checkpoint.to_dict())
        self._save_state()
        
        return checkpoint
    
    def apply_checkpoint(self, checkpoint_id: str) -> bool:
        """应用检查点"""
        checkpoint_info = self._get_checkpoint_info(checkpoint_id)
        if not checkpoint_info:
            return False
        
        backup_id = checkpoint_info.get("metadata", {}).get("backup_id")
        if not backup_id:
            return False
        
        backup_manager = BackupManager()
        return backup_manager.restore_backup(backup_id, checkpoint_info["components"])
    
    def _get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict]:
        """获取检查点信息"""
        for cp in self.state.get("checkpoints", []):
            if cp["id"] == checkpoint_id:
                return cp
        return None
    
    def list_checkpoints(self, limit: int = 10) -> List[Checkpoint]:
        """列出检查点"""
        checkpoints = [Checkpoint(**c) for c in self.state.get("checkpoints", [])]
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        return checkpoints[:limit]


# ============ 服务切换器 ============

class ServiceSwitcher:
    """服务切换器"""
    
    def __init__(self):
        self.primary_services: Dict[str, str] = {}  # service -> primary endpoint
        self.backup_services: Dict[str, str] = {}   # service -> backup endpoint
        self.current_services: Dict[str, str] = {}  # service -> current endpoint
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        config_path = Path("~/.real/.service_config.json").expanduser()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    self.primary_services = config.get("primary", {})
                    self.backup_services = config.get("backup", {})
                    self.current_services = config.get("current", self.primary_services.copy())
            except:
                pass
    
    def _save_config(self):
        """保存配置"""
        config_path = Path("~/.real/.service_config.json").expanduser()
        config = {
            "primary": self.primary_services,
            "backup": self.backup_services,
            "current": self.current_services
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def register_service(self, service: str, primary: str, backup: Optional[str] = None):
        """注册服务"""
        self.primary_services[service] = primary
        if backup:
            self.backup_services[service] = backup
        self.current_services[service] = primary
        self._save_config()
    
    def switch_to_backup(self, service: str) -> bool:
        """切换到备用服务"""
        if service not in self.backup_services:
            return False
        
        backup = self.backup_services[service]
        self.current_services[service] = backup
        self._save_config()
        
        print(f"✅ 服务 {service} 已切换到备用: {backup}")
        return True
    
    def switch_to_primary(self, service: str) -> bool:
        """切换到主服务"""
        if service not in self.primary_services:
            return False
        
        primary = self.primary_services[service]
        self.current_services[service] = primary
        self._save_config()
        
        print(f"✅ 服务 {service} 已切换到主服务: {primary}")
        return True
    
    def get_current(self, service: str) -> Optional[str]:
        """获取当前服务地址"""
        return self.current_services.get(service)
    
    def health_check(self, service: str) -> bool:
        """健康检查"""
        import urllib.request
        import urllib.error
        
        endpoint = self.current_services.get(service)
        if not endpoint:
            return False
        
        try:
            req = urllib.request.Request(endpoint)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.getcode() == 200
        except:
            return False


# ============ 自修复引擎主类 ============

class SelfHealingEngine:
    """自修复引擎"""
    
    def __init__(self):
        self.backup_manager = BackupManager()
        self.checkpoint_manager = CheckpointManager()
        self.service_switcher = ServiceSwitcher()
        self.actions: List[HealingAction] = []
    
    def auto_backup(self, components: Optional[List[str]] = None) -> Optional[Backup]:
        """自动备份"""
        if components is None:
            # 默认备份关键配置
            components = [
                str(Path.home() / ".openclaw" / "config"),
                str(Path.home() / ".openclaw" / "skills"),
                str(Path.home() / ".openclaw" / "agents"),
            ]
        
        name = f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.backup_manager.create_backup(name, components, "auto")
    
    def auto_migrate(self, source: str, target: str) -> bool:
        """自动迁移"""
        action = HealingAction(
            action="migrate",
            target=target,
            source=source,
            status="running"
        )
        self.actions.append(action)
        
        try:
            source_path = Path(source).expanduser()
            target_path = Path(target).expanduser()
            
            if not source_path.exists():
                raise FileNotFoundError(f"Source not found: {source}")
            
            # 创建目标目录
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行迁移
            if source_path.is_dir():
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, target_path)
            
            action.status = "completed"
            action.result = f"Migrated {source} to {target}"
            return True
            
        except Exception as e:
            action.status = "failed"
            action.error = str(e)
            return False
        
        finally:
            self._save_actions()
    
    def auto_rollback(self, checkpoint_id: str) -> bool:
        """自动回滚"""
        action = HealingAction(
            action="rollback",
            target=checkpoint_id,
            status="running"
        )
        self.actions.append(action)
        
        try:
            success = self.checkpoint_manager.apply_checkpoint(checkpoint_id)
            
            if success:
                action.status = "completed"
                action.result = f"Rolled back to checkpoint {checkpoint_id}"
            else:
                action.status = "failed"
                action.error = "Checkpoint application failed"
            
            return success
            
        except Exception as e:
            action.status = "failed"
            action.error = str(e)
            return False
        
        finally:
            self._save_actions()
    
    def switch_backup(self, primary: str, backup: str) -> bool:
        """备用切换"""
        action = HealingAction(
            action="switch",
            target=primary,
            source=backup,
            status="running"
        )
        self.actions.append(action)
        
        try:
            success = self.service_switcher.switch_to_backup(primary)
            
            if success:
                action.status = "completed"
                action.result = f"Switched {primary} from {self.service_switcher.primary_services.get(primary)} to {backup}"
            else:
                action.status = "failed"
                action.error = "Service not found or no backup available"
            
            return success
            
        except Exception as e:
            action.status = "failed"
            action.error = str(e)
            return False
        
        finally:
            self._save_actions()
    
    def create_recovery_checkpoint(self, name: str, description: str) -> Checkpoint:
        """创建恢复检查点"""
        components = [
            str(Path.home() / ".openclaw" / "config"),
            str(Path.home() / ".openclaw" / "workspace"),
        ]
        return self.checkpoint_manager.create_checkpoint(name, description, components)
    
    def get_health_report(self) -> Dict:
        """获取健康报告"""
        services = list(self.service_switcher.current_services.keys())
        health_status = {}
        
        for service in services:
            health_status[service] = {
                "current": self.service_switcher.get_current(service),
                "primary": self.service_switcher.primary_services.get(service),
                "backup": self.service_switcher.backup_services.get(service),
                "healthy": self.service_switcher.health_check(service)
            }
        
        backups = self.backup_manager.list_backups(5)
        checkpoints = self.checkpoint_manager.list_checkpoints(5)
        
        return {
            "timestamp": time.time(),
            "services": health_status,
            "recent_backups": [b.to_dict() for b in backups],
            "recent_checkpoints": [c.to_dict() for c in checkpoints],
            "pending_actions": len([a for a in self.actions if a.status == "pending"])
        }
    
    def _save_actions(self):
        """保存动作历史"""
        state = {
            "last_update": time.time(),
            "actions": [a.to_dict() for a in self.actions[-100:]]  # 保留最近100条
        }
        with open(HEALING_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 自修复引擎")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 备份命令
    backup_parser = subparsers.add_parser("backup", help="创建备份")
    backup_parser.add_argument("--name", required=True)
    backup_parser.add_argument("--paths", nargs="+", required=True)
    backup_parser.add_argument("--type", default="full")
    
    # 恢复命令
    restore_parser = subparsers.add_parser("restore", help="恢复备份")
    restore_parser.add_argument("backup_id")
    
    # 检查点命令
    checkpoint_parser = subparsers.add_parser("checkpoint", help="检查点管理")
    checkpoint_parser.add_argument("--create", action="store_true")
    checkpoint_parser.add_argument("--apply", type=str, help="检查点ID")
    checkpoint_parser.add_argument("--name", type=str)
    checkpoint_parser.add_argument("--desc", type=str)
    
    # 切换命令
    switch_parser = subparsers.add_parser("switch", help="服务切换")
    switch_parser.add_argument("service")
    switch_parser.add_argument("--to", choices=["primary", "backup"], default="backup")
    
    # 健康报告
    subparsers.add_parser("health", help="健康报告")
    
    # 列表命令
    list_parser = subparsers.add_parser("list", help="列出备份/检查点")
    list_parser.add_argument("--type", choices=["backups", "checkpoints"], default="backups")
    
    args = parser.parse_args()
    
    engine = SelfHealingEngine()
    
    if args.command == "backup":
        backup = engine.auto_backup(args.paths)
        if backup:
            print(f"✅ 备份创建成功: {backup.id}")
            print(f"   大小: {format_size(backup.size)}")
            print(f"   路径: {backup.path}")
        else:
            print("❌ 备份创建失败")
    
    elif args.command == "restore":
        success = engine.backup_manager.restore_backup(args.backup_id)
        print(f"{'✅' if success else '❌'} 恢复 {'成功' if success else '失败'}")
    
    elif args.command == "checkpoint":
        if args.create:
            cp = engine.create_recovery_checkpoint(
                args.name or f"checkpoint_{int(time.time())}",
                args.desc or ""
            )
            print(f"✅ 检查点创建成功: {cp.id}")
        elif args.apply:
            success = engine.auto_rollback(args.apply)
            print(f"{'✅' if success else '❌'} 回滚 {'成功' if success else '失败'}")
        else:
            checkpoints = engine.checkpoint_manager.list_checkpoints()
            print(f"检查点列表 ({len(checkpoints)} 个):")
            for cp in checkpoints:
                print(f"  [{cp.id}] {cp.name} - {cp.description} ({cp.status})")
    
    elif args.command == "switch":
        if args.to == "backup":
            success = engine.switch_backup(args.service, "")
        else:
            success = engine.service_switcher.switch_to_primary(args.service)
        print(f"{'✅' if success else '❌'} 切换 {'成功' if success else '失败'}")
    
    elif args.command == "health":
        report = engine.get_health_report()
        print("=" * 60)
        print("ClawShell 自修复引擎 - 健康报告")
        print("=" * 60)
        print(f"时间: {datetime.fromtimestamp(report['timestamp'])}")
        print()
        print(f"待处理动作: {report['pending_actions']}")
        print()
        print("服务状态:")
        for service, status in report["services"].items():
            health_icon = "✅" if status["healthy"] else "⚠️"
            print(f"  {health_icon} {service}: {status['current']}")
        print()
        print(f"最近备份: {len(report['recent_backups'])} 个")
        print(f"最近检查点: {len(report['recent_checkpoints'])} 个")
    
    elif args.command == "list":
        if args.type == "backups":
            backups = engine.backup_manager.list_backups()
            print(f"备份列表 ({len(backups)} 个):")
            for b in backups:
                print(f"  [{b.id}] {b.description}")
                print(f"      大小: {format_size(b.size)}, 状态: {b.status}")
        else:
            checkpoints = engine.checkpoint_manager.list_checkpoints()
            print(f"检查点列表 ({len(checkpoints)} 个):")
            for cp in checkpoints:
                print(f"  [{cp.id}] {cp.name} - {cp.description}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
