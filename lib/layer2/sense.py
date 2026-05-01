#!/usr/bin/env python3
"""
ClawShell 自感知引擎 (Self-Sense Engine)
版本: v0.2.1-A
功能: 感知MCP服务/Skills/API端点/N8N工作流状态
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# ============ 配置 ============

SENSE_CONFIG_PATH = Path("~/.real/.sense_config.json").expanduser()
SENSE_STATE_PATH = Path("~/.real/.sense_state.json").expanduser()
SKILLS_DIR = Path("~/.real/skills").expanduser()
SCRIPTS_DIR = Path("~/.real/scripts").expanduser()

DEFAULT_SENSE_INTERVAL = 300  # 5分钟
DEFAULT_TIMEOUT = 5  # 5秒超时


# ============ 数据结构 ============

class ServiceStatus(Enum):
    """服务状态枚举"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    type: str  # mcp, skill, api, n8n, script
    status: ServiceStatus
    last_check: float
    response_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "status": self.status.value,
            "last_check": self.last_check,
            "response_time": self.response_time,
            "error": self.error,
            "metadata": self.metadata or {}
        }


@dataclass
class SenseReport:
    """感知报告"""
    timestamp: float
    services: Dict[str, ServiceInfo]
    summary: Dict[str, int]  # 各状态计数
    issues: List[str]  # 问题列表

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "summary": self.summary,
            "issues": self.issues
        }


# ============ 自感知引擎 ============

class SelfSenseEngine:
    """自感知引擎"""
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.config = self._load_config()
        self.state = self._load_state()
        
    def _load_config(self) -> Dict:
        """加载配置"""
        if SENSE_CONFIG_PATH.exists():
            try:
                with open(SENSE_CONFIG_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "interval": DEFAULT_SENSE_INTERVAL,
            "timeout": DEFAULT_TIMEOUT,
            "mcp_endpoints": [],
            "api_endpoints": [],
            "n8n_url": "http://localhost:5680",
            "enabled_services": ["mcp", "skills", "api", "n8n"]
        }
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if SENSE_STATE_PATH.exists():
            try:
                with open(SENSE_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {"last_sense": 0, "services": {}}
    
    def _save_state(self):
        """保存状态"""
        state = {
            "last_sense": time.time(),
            "services": {k: v.to_dict() for k, v in self.services.items()}
        }
        with open(SENSE_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    # ---- MCP服务感知 ----
    
    def sense_mcp_services(self) -> Dict[str, ServiceInfo]:
        """感知MCP服务状态"""
        # 扫描MCP相关配置
        mcp_configs = [
            Path("~/.real/config/mcp.json").expanduser(),
            Path("~/.real/config/mcp_settings.json").expanduser(),
        ]
        
        for config_path in mcp_configs:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        data = json.load(f)
                        # 解析MCP服务配置
                        if "mcpServers" in data:
                            for name, config in data["mcpServers"].items():
                                self._check_mcp_service(name, config)
                        elif "servers" in data:
                            for name, config in data["servers"].items():
                                self._check_mcp_service(name, config)
                except Exception as e:
                    print(f"解析MCP配置失败 {config_path}: {e}")
        
        return {k: v for k, v in self.services.items() if v.type == "mcp"}
    
    def _check_mcp_service(self, name: str, config: Any):
        """检查单个MCP服务"""
        now = time.time()
        
        # 提取服务信息
        if isinstance(config, dict):
            command = config.get("command", "")
            args = config.get("args", [])
            enabled = config.get("enabled", True)
        else:
            command = str(config)
            args = []
            enabled = True
        
        service_name = f"mcp_{name}"
        
        if not enabled:
            self.services[service_name] = ServiceInfo(
                name=name,
                type="mcp",
                status=ServiceStatus.MAINTENANCE,
                last_check=now,
                error="Disabled in config"
            )
            return
        
        # 检查进程是否存在（本地服务）
        import subprocess
        try:
            result = subprocess.run(
                ["pgrep", "-f", command.split('/')[-1] if '/' in command else command],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                self.services[service_name] = ServiceInfo(
                    name=name,
                    type="mcp",
                    status=ServiceStatus.HEALTHY,
                    last_check=now
                )
            else:
                self.services[service_name] = ServiceInfo(
                    name=name,
                    type="mcp",
                    status=ServiceStatus.DOWN,
                    last_check=now,
                    error="Process not found"
                )
        except Exception as e:
            self.services[service_name] = ServiceInfo(
                name=name,
                type="mcp",
                status=ServiceStatus.UNKNOWN,
                last_check=now,
                error=str(e)
            )
    
    # ---- Skills感知 ----
    
    def sense_skills(self) -> Dict[str, ServiceInfo]:
        """感知Skills状态"""
        if not SKILLS_DIR.exists():
            return {}
        
        skill_categories = [
            "workspace/skills",
            "skills",
        ]
        
        all_skills = {}
        
        for category in skill_categories:
            category_path = SKILLS_DIR / category
            if category_path.exists():
                skills = self._scan_skills_dir(category_path)
                all_skills.update(skills)
        
        # 也扫描顶层目录
        for item in SKILLS_DIR.iterdir():
            if item.is_dir() and item.name not in ["workspace", "skills"]:
                skill_info = self._check_skill_dir(item)
                if skill_info:
                    all_skills[f"skill_{item.name}"] = skill_info
        
        return all_skills
    
    def _scan_skills_dir(self, path: Path) -> Dict[str, ServiceInfo]:
        """扫描Skills目录"""
        result = {}
        now = time.time()
        
        for item in path.iterdir():
            if item.is_dir():
                skill_info = self._check_skill_dir(item)
                if skill_info:
                    result[f"skill_{item.name}"] = skill_info
        
        return result
    
    def _check_skill_dir(self, path: Path) -> Optional[ServiceInfo]:
        """检查单个Skill目录"""
        now = time.time()
        skill_name = path.name
        
        # 检查必要文件
        has_main = (path / "SKILL.md").exists() or (path / "skill.md").exists()
        has_scripts = any(path.glob("*.sh")) or any(path.glob("*.py"))
        
        if has_main:
            # 检查脚本可执行性
            executable_scripts = list(path.glob("*.sh"))
            if executable_scripts:
                # 简单检查脚本是否存在语法问题
                try:
                    import subprocess
                    for script in executable_scripts[:3]:  # 最多检查3个
                        result = subprocess.run(
                            ["file", str(script)],
                            capture_output=True,
                            timeout=2
                        )
                        if "script" in result.stdout.decode().lower():
                            return ServiceInfo(
                                name=skill_name,
                                type="skill",
                                status=ServiceStatus.HEALTHY,
                                last_check=now,
                                metadata={"path": str(path)}
                            )
                except:
                    pass
            
            return ServiceInfo(
                name=skill_name,
                type="skill",
                status=ServiceStatus.HEALTHY,
                last_check=now,
                metadata={"path": str(path)}
            )
        else:
            return ServiceInfo(
                name=skill_name,
                type="skill",
                status=ServiceStatus.DEGRADED,
                last_check=now,
                error="Missing SKILL.md"
            )
    
    # ---- API端点感知 ----
    
    def sense_api_endpoints(self) -> Dict[str, ServiceInfo]:
        """感知API端点状态"""
        endpoints = self.config.get("api_endpoints", [])
        result = {}
        now = time.time()
        
        import urllib.request
        import urllib.error
        
        for endpoint in endpoints:
            name = endpoint.get("name", endpoint["url"])
            url = endpoint["url"]
            
            try:
                start = time.time()
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "ClawShell-Sense/0.2")
                
                with urllib.request.urlopen(req, timeout=self.config.get("timeout", DEFAULT_TIMEOUT)) as resp:
                    response_time = time.time() - start
                    status_code = resp.getcode()
                    
                    if 200 <= status_code < 300:
                        status = ServiceStatus.HEALTHY
                    elif 300 <= status_code < 400:
                        status = ServiceStatus.DEGRADED
                    else:
                        status = ServiceStatus.DOWN
                    
                    result[f"api_{name}"] = ServiceInfo(
                        name=name,
                        type="api",
                        status=status,
                        last_check=now,
                        response_time=response_time
                    )
            except urllib.error.URLError as e:
                result[f"api_{name}"] = ServiceInfo(
                    name=name,
                    type="api",
                    status=ServiceStatus.DOWN,
                    last_check=now,
                    error=str(e)
                )
            except Exception as e:
                result[f"api_{name}"] = ServiceInfo(
                    name=name,
                    type="api",
                    status=ServiceStatus.UNKNOWN,
                    last_check=now,
                    error=str(e)
                )
        
        return result
    
    # ---- N8N工作流感知 ----
    
    def sense_n8n_workflows(self) -> Dict[str, ServiceInfo]:
        """感知N8N工作流"""
        n8n_url = self.config.get("n8n_url", "http://localhost:5680")
        result = {}
        now = time.time()
        
        import urllib.request
        import urllib.error
        
        # 检查N8N服务是否可用
        try:
            req = urllib.request.Request(f"{n8n_url}/healthz")
            start = time.time()
            
            with urllib.request.urlopen(req, timeout=self.config.get("timeout", DEFAULT_TIMEOUT)) as resp:
                response_time = time.time() - start
                result["n8n_server"] = ServiceInfo(
                    name="n8n_server",
                    type="n8n",
                    status=ServiceStatus.HEALTHY if resp.getcode() == 200 else ServiceStatus.DEGRADED,
                    last_check=now,
                    response_time=response_time
                )
        except urllib.error.URLError as e:
            result["n8n_server"] = ServiceInfo(
                name="n8n_server",
                type="n8n",
                status=ServiceStatus.DOWN,
                last_check=now,
                error=f"Connection failed: {e}"
            )
        except Exception as e:
            result["n8n_server"] = ServiceInfo(
                name="n8n_server",
                type="n8n",
                status=ServiceStatus.UNKNOWN,
                last_check=now,
                error=str(e)
            )
        
        return result
    
    # ---- 脚本感知 ----
    
    def sense_scripts(self) -> Dict[str, ServiceInfo]:
        """感知关键脚本"""
        if not SCRIPTS_DIR.exists():
            return {}
        
        result = {}
        now = time.time()
        
        # 关键脚本列表
        critical_scripts = [
            "openclaw_version_monitor.py",
            "openclaw_impact_analyzer.py",
            "obsidian_graph_builder.py",
            "knowledge_qa.py",
            "hermes_watchdog.py",
        ]
        
        for script_name in critical_scripts:
            script_path = SCRIPTS_DIR / script_name
            if script_path.exists():
                # 检查语法
                try:
                    import py_compile
                    py_compile.compile(str(script_path), doraise=True)
                    result[f"script_{script_name}"] = ServiceInfo(
                        name=script_name,
                        type="script",
                        status=ServiceStatus.HEALTHY,
                        last_check=now,
                        metadata={"path": str(script_path)}
                    )
                except py_compile.PyCompileError as e:
                    result[f"script_{script_name}"] = ServiceInfo(
                        name=script_name,
                        type="script",
                        status=ServiceStatus.DEGRADED,
                        last_check=now,
                        error=f"Syntax error: {e}"
                    )
            else:
                result[f"script_{script_name}"] = ServiceInfo(
                    name=script_name,
                    type="script",
                    status=ServiceStatus.DOWN,
                    last_check=now,
                    error="File not found"
                )
        
        return result
    
    # ---- 全局感知 ----
    
    def sense_all(self) -> SenseReport:
        """执行全局感知"""
        now = time.time()
        enabled = self.config.get("enabled_services", [])
        all_services = {}
        issues = []
        
        if "mcp" in enabled:
            all_services.update(self.sense_mcp_services())
        
        if "skills" in enabled:
            all_services.update(self.sense_skills())
        
        if "api" in enabled:
            all_services.update(self.sense_api_endpoints())
        
        if "n8n" in enabled:
            all_services.update(self.sense_n8n_workflows())
        
        if "scripts" in enabled:
            all_services.update(self.sense_scripts())
        
        # 更新实例状态
        self.services = all_services
        
        # 生成摘要
        summary = {status.value: 0 for status in ServiceStatus}
        for svc in all_services.values():
            summary[svc.status.value] += 1
        
        # 收集问题
        for svc in all_services.values():
            if svc.status in [ServiceStatus.DOWN, ServiceStatus.DEGRADED]:
                issues.append(f"{svc.type}/{svc.name}: {svc.error or svc.status.value}")
        
        # 保存状态
        self._save_state()
        
        return SenseReport(
            timestamp=now,
            services=all_services,
            summary=summary,
            issues=issues
        )
    
    def get_status_dashboard(self) -> Dict:
        """获取状态仪表板"""
        report = self.sense_all()
        
        return {
            "timestamp": report.timestamp,
            "status": "healthy" if report.summary.get("down", 0) == 0 else "issues_found",
            "summary": report.summary,
            "issues": report.issues,
            "services": {k: v.to_dict() for k, v in report.services.items()}
        }


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 自感知引擎")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--dashboard", action="store_true", help="显示仪表板")
    args = parser.parse_args()
    
    engine = SelfSenseEngine()
    
    if args.dashboard or args.format == "text":
        dashboard = engine.get_status_dashboard()
        
        if args.format == "json":
            print(json.dumps(dashboard, indent=2))
        else:
            print("=" * 60)
            print("ClawShell 自感知引擎 v0.2.1-A")
            print("=" * 60)
            print(f"检查时间: {dashboard['timestamp']}")
            print(f"状态: {dashboard['status']}")
            print()
            print("状态摘要:")
            for status, count in dashboard["summary"].items():
                if count > 0:
                    print(f"  {status}: {count}")
            print()
            
            if dashboard["issues"]:
                print("发现问题:")
                for issue in dashboard["issues"]:
                    print(f"  ⚠️  {issue}")
            else:
                print("✅ 所有服务正常运行")
    else:
        report = engine.sense_all()
        print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
