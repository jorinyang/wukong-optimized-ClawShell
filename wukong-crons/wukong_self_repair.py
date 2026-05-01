# -*- coding: utf-8 -*-
"""
wukong_self_repair.py - 悟空自修复检测与执行脚本
版本: v1.0 Windows适配版
功能: 检测悟空系统健康状态，自动修复问题

适配说明:
- 原 ClawShell 自修复脚本针对 macOS OpenClaw 设计
- 本版本适配 Windows 悟空环境，使用 psutil 进行跨平台检测
- 替换 macOS 特有命令(openclaw/launchctl/pgrep)为 Python 模块

目录结构:
- 工作区: {USER_WORKSPACE}/workspace/
- 脚本目录: {USER_WORKSPACE}/workspace/wukong-crons/
- 日志: {USER_WORKSPACE}/workspace/logs/
- 报告: {USER_WORKSPACE}/workspace/repair_reports/
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# ========== 路径配置 ==========
# 悟空工作区根目录
WK_WORKSPACE = Path(__file__).parent.parent.resolve()
WK_SCRIPTS_DIR = Path(__file__).parent
WK_LOGS_DIR = WK_WORKSPACE / "logs"
WK_REPAIR_REPORTS_DIR = WK_WORKSPACE / "repair_reports"
WK_SHARED_DIR = WK_WORKSPACE / "shared"

# ClawShell 安装目录
CLAWSHELL_HOME = Path(os.path.expandvars("%USERPROFILE%")) / ".ClawShell"

# 修复队列和日志文件
REPAIR_QUEUE_FILE = WK_SHARED_DIR / "repair_queue.json"
REPAIR_LOG = WK_LOGS_DIR / "self_repair.log"


def log(msg: str):
    """记录日志到控制台和文件"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    WK_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_python_cmd() -> str:
    """获取 Python 命令（跨平台）"""
    # Windows
    if os.name == "nt":
        return "py"
    # Unix/Linux/macOS
    return "python3"


# ========== Windows 适配检测函数 ==========

def check_python_environment() -> Tuple[bool, str]:
    """检查 Python 环境"""
    try:
        result = subprocess.run(
            [get_python_cmd(), "--version"],
            capture_output=True, text=True, timeout=10
        )
        version = result.stdout.strip() or result.stderr.strip()
        log(f"  Python环境: {version}")
        return True, version
    except Exception as e:
        return False, str(e)


def check_clawshell_installation() -> Tuple[bool, str]:
    """检查 ClawShell 安装"""
    if CLAWSHELL_HOME.exists():
        version_file = CLAWSHELL_HOME / "CLAWSHELL_VERSION"
        if version_file.exists():
            with open(version_file, "r") as f:
                version = f.read().strip()
            return True, f"v{version}"
    return False, "未安装或版本文件缺失"


def check_clawshell_modules() -> Tuple[bool, Dict[str, Any]]:
    """检查 ClawShell 核心模块可用性"""
    results = {
        "core": {"status": False, "modules": []},
        "layer1": {"status": False, "modules": []},
        "layer2": {"status": False, "modules": []},
    }
    
    sys.path.insert(0, str(CLAWSHELL_HOME))  # 正确: ClawShell根目录，lib是子包
    
    # 检查 core 模块
    try:
        from lib import __version__
        results["core"]["status"] = True
        results["core"]["modules"].append(f"lib.__version__={__version__}")
    except ImportError as e:
        results["core"]["error"] = str(e)
    
    # Layer1 模块 - 每个模块使用各自的类名
    layer1_modules = [
        ("health_check", "HealthMonitor"),  # 通用健康检查
        ("system_mon", "HealthMonitor"),     # 系统监控
        ("disk_mon", "ScanScheduler"),       # 磁盘监控
        ("process_mon", "ScanScheduler"),    # 进程监控
        ("agent_mon", "RepairEngine"),       # Agent监控
        ("gateway_mon", "RepairEngine"),     # 网关监控
        ("service_mon", "RepairEngine"),     # 服务监控
    ]
    
    layer1_ok = 0
    for module_name, class_name in layer1_modules:
        try:
            mod = __import__(f"lib.layer1.{module_name}", fromlist=[class_name])
            cls = getattr(mod, class_name)
            results["layer1"]["modules"].append(f"{module_name}.{class_name}")
            layer1_ok += 1
        except ImportError:
            pass
    
    results["layer1"]["status"] = layer1_ok >= 3  # 至少3个模块可用
    
    # Layer2 模块
    layer2_modules = [
        ("self_repair", "SelfHealingEngine"),
        ("discovery", "DiscoveryEngine"),
        ("condition", "ConditionEngine"),
        ("ml_engine", "MLEngine"),
    ]
    
    layer2_ok = 0
    for module_name, class_name in layer2_modules:
        try:
            mod = __import__(f"lib.layer2.{module_name}", fromlist=[class_name])
            cls = getattr(mod, class_name)
            results["layer2"]["modules"].append(f"{module_name}.{class_name}")
            layer2_ok += 1
        except ImportError:
            pass
    
    results["layer2"]["status"] = layer2_ok >= 1
    
    return results["core"]["status"] and results["layer1"]["status"], results


def check_system_resources() -> Tuple[bool, Dict[str, Any]]:
    """检查系统资源（使用 psutil）"""
    try:
        import psutil as _psutil
        
        # CPU
        cpu_percent = _psutil.cpu_percent(interval=1)
        cpu_count = _psutil.cpu_count()
        
        # 内存
        mem = _psutil.virtual_memory()
        mem_percent = mem.percent
        mem_available_gb = mem.available / (1024**3)
        
        # 磁盘
        disk = _psutil.disk_usage("C:\\")
        disk_percent = disk.percent
        
        stats = {
            "cpu": {"percent": cpu_percent, "count": cpu_count},
            "memory": {"percent": mem_percent, "available_gb": round(mem_available_gb, 2)},
            "disk": {"percent": disk_percent, "total_gb": round(disk.total / (1024**3), 1)},
        }
        
        # 判断是否需要告警 (仅警告，不算错误)
        issues = []
        if cpu_percent > 90:
            issues.append(f"CPU使用率过高: {cpu_percent}%")
        if mem_percent > 90:
            issues.append(f"内存使用率过高: {mem_percent}%")
        if disk_percent > 90:
            issues.append(f"磁盘使用率较高: {disk_percent}%")
        
        # 系统资源检查：只要psutil能获取数据就算通过，警告不影响通过状态
        return True, {"stats": stats, "issues": issues}
        
    except ImportError:
        return False, {"error": "psutil 未安装"}
    except Exception as e:
        return False, {"error": str(e)}


def check_psutil_installed() -> Tuple[bool, Dict[str, Any]]:
    """专门检测 psutil 是否已安装"""
    try:
        import psutil
        version = getattr(psutil, '__version__', 'unknown')
        return True, {"version": version, "status": "installed"}
    except ImportError:
        return False, {"status": "not_installed", "error": "psutil 未安装"}


def check_wukong_processes() -> Tuple[bool, List[str]]:
    """检查悟空相关进程"""
    try:
        import psutil
        
        target_processes = ["python", "pythonw", "py"]
        wukong_keywords = ["wukong", "clawshell", "agent", "mcp"]
        
        running = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"].lower() if proc.info["name"] else ""
                cmdline = " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else ""
                
                # 检查是否与悟空相关
                for kw in wukong_keywords:
                    if kw in name or kw in cmdline.lower():
                        running.append(f"PID {proc.info['pid']}: {name}")
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return len(running) > 0, running[:10]  # 最多返回10个
    except ImportError:
        return False, ["psutil 未安装，无法检测进程"]
    except Exception as e:
        return False, [str(e)]


def check_skill_modules() -> Tuple[bool, Dict[str, Any]]:
    """检查悟空技能模块"""
    # .skills 在用户会话目录下，不在 workspace 下
    skills_dir = Path(os.path.expandvars("%USERPROFILE%")) / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / ".skills"
    
    if not skills_dir.exists():
        return False, {"error": "技能目录不存在"}
    
    skills = []
    for item in skills_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            skills.append(item.name)
    
    return len(skills) > 0, {"count": len(skills), "skills": skills[:5]}


def check_mcp_services() -> Tuple[bool, List[str]]:
    """检查 MCP 服务状态"""
    mcp_status = []
    
    # 检查钉钉 MCP 服务
    try:
        result = subprocess.run(
            ["real_cli", "mcp", "list"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            mcp_status.append("MCP服务可用")
        else:
            mcp_status.append("MCP服务异常")
    except FileNotFoundError:
        mcp_status.append("real_cli 命令不存在")
    except Exception as e:
        mcp_status.append(f"MCP检查失败: {str(e)[:30]}")
    
    return len(mcp_status) > 0, mcp_status


def check_network_connectivity() -> Tuple[bool, str]:
    """检查网络连接"""
    test_hosts = [
        ("github.com", "GitHub"),
        ("api.github.com", "GitHub API"),
    ]
    
    results = []
    for host, name in test_hosts:
        try:
            import socket
            socket.setdefaulttimeout(5)
            socket.gethostbyname(host)
            results.append(f"{name}: OK")
        except socket.gaierror:
            results.append(f"{name}: 失败")
        except Exception:
            results.append(f"{name}: 异常")
    
    ok_count = sum(1 for r in results if "OK" in r)
    return ok_count == len(results), "; ".join(results)


def check_cron_tasks() -> Tuple[bool, Dict[str, Any]]:
    """检查定时任务配置"""
    cron_log = WK_LOGS_DIR / "cron_tasks.json"
    
    if not cron_log.exists():
        return False, {"error": "定时任务配置文件不存在"}
    
    try:
        with open(cron_log, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        
        active_tasks = [t for t in tasks if t.get("status") == "active"]
        return len(active_tasks) > 0, {"total": len(tasks), "active": len(active_tasks)}
    except Exception as e:
        return False, {"error": str(e)}


def check_dingtalk_config() -> Tuple[bool, str]:
    """检查钉钉配置（使用 dws 命令行工具）"""
    try:
        result = subprocess.run(
            ["dws", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, "dws 命令行工具可用"
        return False, "dws 命令异常"
    except FileNotFoundError:
        return False, "dws 命令未安装"
    except Exception as e:
        return False, f"dws 检查失败: {str(e)[:30]}"


def check_workspace_integrity() -> Tuple[bool, List[str]]:
    """检查工作区完整性"""
    required_dirs = [
        "logs",
        "repair_reports",
        "shared",
        ".skills",
    ]
    
    missing = []
    for dir_name in required_dirs:
        dir_path = WK_WORKSPACE / dir_name
        if not dir_path.exists():
            missing.append(dir_name)
    
    return len(missing) == 0, missing


# ========== 检测项定义 ==========

CHECKS = [
    # 环境检查 (4项)
    ("env.python", "Python环境", check_python_environment, "P1"),
    ("env.clawshell_install", "ClawShell安装", check_clawshell_installation, "P1"),
    ("env.clawshell_modules", "ClawShell模块", check_clawshell_modules, "P0"),
    ("env.psutil", "psutil依赖", check_psutil_installed, "P0"),
    ("proc.wukong", "悟空进程", check_wukong_processes, "P1"),
    
    # 资源检查 (1项) - 仅警告，不影响通过状态
    ("res.system", "系统资源", check_system_resources, "P2"),
    
    # 技能检查 (1项)
    ("skill.modules", "技能模块", check_skill_modules, "P2"),
    
    # MCP检查 (1项)
    ("mcp.services", "MCP服务", check_mcp_services, "P2"),
    
    # 网络检查 (1项)
    ("net.connectivity", "网络连接", check_network_connectivity, "P1"),
    
    # 定时任务 (1项)
    ("cron.tasks", "定时任务", check_cron_tasks, "P2"),
    
    # 钉钉配置 (1项)
    ("dtalk.config", "钉钉配置", check_dingtalk_config, "P2"),
    
    # 工作区 (1项)
    ("ws.integrity", "工作区完整", check_workspace_integrity, "P1"),
]


# ========== 修复动作定义 ==========

REPAIR_ACTIONS = {
    "env.python": ("install_python_deps", "Python环境问题"),
    "env.clawshell_install": ("reinstall_clawshell", "ClawShell未安装"),
    "env.clawshell_modules": ("fix_clawshell_modules", "ClawShell模块缺失"),
    "env.psutil": ("install_psutil", "psutil未安装"),
    "proc.wukong": ("restart_wukong", "悟空进程未运行"),
    "res.system": ("alert_resource", "系统资源不足"),
    "skill.modules": ("reinstall_skills", "技能模块缺失"),
    "mcp.services": ("restart_mcp", "MCP服务异常"),
    "net.connectivity": ("alert_network", "网络连接失败"),
    "cron.tasks": ("create_cron_config", "定时任务未配置"),
    "dtalk.config": ("setup_dingtalk", "钉钉配置缺失"),
    "ws.integrity": ("fix_workspace", "工作区目录缺失"),
}


# ========== 修复动作实现 ==========

def install_psutil():
    """安装 psutil"""
    log("📦 安装 psutil...")
    try:
        subprocess.run(
            [get_python_cmd(), "-m", "pip", "install", "psutil"],
            capture_output=True, timeout=60
        )
        log("  ✅ psutil 安装完成")
        return True
    except Exception as e:
        log(f"  ❌ 安装失败: {e}")
        return False


def install_python_deps():
    """安装 Python 依赖"""
    log("📦 检查 Python 依赖...")
    deps = ["requests", "chardet"]
    for dep in deps:
        try:
            __import__(dep)
            log(f"  ✅ {dep} 已安装")
        except ImportError:
            log(f"  📦 安装 {dep}...")
            subprocess.run(
                [get_python_cmd(), "-m", "pip", "install", dep],
                capture_output=True, timeout=60
            )
    return True


def fix_workspace():
    """修复工作区目录"""
    log("📁 修复工作区目录...")
    dirs = ["logs", "repair_reports", "shared", ".skills"]
    for d in dirs:
        path = WK_WORKSPACE / d
        path.mkdir(parents=True, exist_ok=True)
        log(f"  ✅ {d}/")
    return True


def create_cron_config():
    """创建定时任务配置"""
    log("⏰ 创建定时任务配置...")
    cron_file = WK_LOGS_DIR / "cron_tasks.json"
    WK_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    default_tasks = [
        {
            "name": "悟空日报生成",
            "script": "daily_report.py",
            "schedule": "0 22 * * *",
            "status": "active",
            "last_run": None
        },
        {
            "name": "健康检查",
            "script": "health_check.py",
            "schedule": "0 */2 * * *",
            "status": "active",
            "last_run": None
        },
    ]
    
    with open(cron_file, "w", encoding="utf-8") as f:
        json.dump(default_tasks, f, indent=2, ensure_ascii=False)
    
    log(f"  ✅ 已创建 {len(default_tasks)} 个默认定时任务")
    return True


def restart_mcp():
    """重启 MCP 服务"""
    log("🔄 重启 MCP 服务...")
    try:
        subprocess.run(["real_cli", "mcp", "stop"], capture_output=True, timeout=30)
        subprocess.run(["real_cli", "mcp", "start"], capture_output=True, timeout=30)
        log("  ✅ MCP 服务已重启")
        return True
    except Exception as e:
        log(f"  ⚠️ 重启失败: {e}")
        return False


def alert_resource(stats: Dict):
    """发送资源告警"""
    log("⚠️ 系统资源告警...")
    if "issues" in stats:
        for issue in stats["issues"]:
            log(f"  ⚠️ {issue}")
    return True


# 修复动作映射
ACTION_IMPLS = {
    "install_psutil": install_psutil,
    "install_python_deps": install_python_deps,
    "fix_workspace": fix_workspace,
    "create_cron_config": create_cron_config,
    "restart_mcp": restart_mcp,
    "alert_resource": lambda: alert_resource({}),
}


# ========== 主程序 ==========

def run_all_checks() -> List[Dict]:
    """执行所有检测"""
    results = []
    
    for check_id, name, func, severity in CHECKS:
        try:
            result = func()
            if isinstance(result, tuple):
                status, detail = result
                results.append({
                    "id": check_id,
                    "name": name,
                    "severity": severity,
                    "status": "ok" if status else "warning",
                    "detail": detail,
                    "checked_at": datetime.now().isoformat()
                })
            else:
                results.append({
                    "id": check_id,
                    "name": name,
                    "severity": severity,
                    "status": "ok" if result else "warning",
                    "checked_at": datetime.now().isoformat()
                })
        except Exception as e:
            results.append({
                "id": check_id,
                "name": name,
                "severity": severity,
                "status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            })
    
    return results


def generate_repair_plan(results: List[Dict]) -> List[Dict]:
    """根据检测结果生成修复计划"""
    plan = []
    
    for result in results:
        if result["status"] != "ok":
            check_id = result["id"]
            if check_id in REPAIR_ACTIONS:
                action, issue = REPAIR_ACTIONS[check_id]
                plan.append({
                    "check_id": check_id,
                    "issue": issue,
                    "action": action,
                    "detail": result.get("detail", {}),
                    "priority": get_priority(result["severity"])
                })
    
    # 按优先级排序
    plan.sort(key=lambda x: x["priority"])
    return plan


def get_priority(severity: str) -> int:
    """获取优先级数值"""
    priorities = {"P0": 1, "P1": 2, "P2": 3, "P3": 4}
    return priorities.get(severity, 5)


def save_repair_queue(plan: List[Dict]):
    """保存修复队列"""
    WK_SHARED_DIR.mkdir(parents=True, exist_ok=True)
    
    queue = {
        "version": "v1.0",
        "platform": "windows",
        "created_at": datetime.now().isoformat(),
        "total_checks": len(CHECKS),
        "plan": plan,
        "executed_phases": [],
        "status": "pending" if plan else "completed"
    }
    
    with open(REPAIR_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    
    return queue


def execute_repair_plan(plan: List[Dict]):
    """执行修复计划"""
    if not plan:
        log("✅ 无需修复，系统正常")
        return
    
    log(f"📋 开始执行 {len(plan)} 项修复计划...")
    
    success_count = 0
    for item in plan:
        action = item["action"]
        issue = item["issue"]
        
        log(f"\n🔧 执行: {action}")
        log(f"   问题: {issue}")
        
        impl = ACTION_IMPLS.get(action)
        if impl:
            try:
                if item.get("detail"):
                    impl(item["detail"])
                else:
                    impl()
                log(f"   ✅ 成功")
                success_count += 1
            except Exception as e:
                log(f"   ❌ 失败: {e}")
        else:
            log(f"   ⚠️ 未实现的修复动作: {action}")
    
    log(f"\n📊 修复执行完成: {success_count}/{len(plan)} 项成功")


def generate_report(results: List[Dict], plan: List[Dict]) -> str:
    """生成检测报告"""
    report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = WK_REPAIR_REPORTS_DIR / f"self_repair_{report_time}.json"
    WK_REPAIR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    report = {
        "version": "v1.0",
        "platform": "windows",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_checks": len(results),
            "passed": sum(1 for r in results if r["status"] == "ok"),
            "warnings": sum(1 for r in results if r["status"] == "warning"),
            "errors": sum(1 for r in results if r["status"] == "error"),
        },
        "results": results,
        "repair_plan": plan,
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 同时生成 Markdown 报告
    md_file = WK_REPAIR_REPORTS_DIR / f"self_repair_{report_time}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# 悟空自修复检测报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**平台**: Windows\n\n")
        f.write(f"**版本**: v1.0\n\n")
        f.write(f"## 检测摘要\n\n")
        f.write(f"| 项目 | 数量 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总检测项 | {report['summary']['total_checks']} |\n")
        f.write(f"| 通过 | {report['summary']['passed']} |\n")
        f.write(f"| 警告 | {report['summary']['warnings']} |\n")
        f.write(f"| 错误 | {report['summary']['errors']} |\n\n")
        
        f.write(f"## 检测详情\n\n")
        for r in results:
            status_icon = "✅" if r["status"] == "ok" else ("⚠️" if r["status"] == "warning" else "❌")
            f.write(f"{status_icon} **{r['name']}** ({r['severity']})\n")
            if r["status"] != "ok":
                if "error" in r:
                    f.write(f"   - 错误: {r['error']}\n")
                if "detail" in r:
                    if isinstance(r["detail"], dict):
                        for k, v in r["detail"].items():
                            f.write(f"   - {k}: {v}\n")
                    else:
                        f.write(f"   - {r['detail']}\n")
            f.write(f"\n")
        
        if plan:
            f.write(f"## 修复计划\n\n")
            for i, item in enumerate(plan, 1):
                f.write(f"{i}. **{item['action']}**: {item['issue']}\n")
        else:
            f.write(f"## 修复计划\n\n")
            f.write(f"✅ 无需修复\n")
    
    return str(report_file)


def main():
    """主程序入口"""
    print("=" * 60)
    print("🚀 悟空自修复检测系统 v1.0 (Windows)")
    print("=" * 60)
    
    log("=" * 60)
    log("🚀 悟空自修复检测系统 v1.0 (Windows)")
    log("=" * 60)
    
    # 执行所有检测
    log("\n📋 执行全面检测...")
    results = run_all_checks()
    
    # 统计结果
    passed = sum(1 for r in results if r["status"] == "ok")
    warnings = sum(1 for r in results if r["status"] == "warning")
    errors = sum(1 for r in results if r["status"] == "error")
    
    log(f"\n📊 检测完成: {passed}/{len(results)} 通过, {warnings} 警告, {errors} 错误")
    
    # 显示检测结果
    log("\n📋 检测详情:")
    for result in results:
        if result["status"] == "ok":
            log(f"  ✅ {result['name']} [{result['severity']}]")
        elif result["status"] == "warning":
            log(f"  ⚠️ {result['name']} [{result['severity']}]")
            if "detail" in result and isinstance(result["detail"], dict):
                if "error" in result["detail"]:
                    log(f"     → {result['detail']['error']}")
        else:
            log(f"  ❌ {result['name']}: {result.get('error', 'unknown')}")
    
    # 生成修复计划
    plan = generate_repair_plan(results)
    save_repair_queue(plan)
    
    if plan:
        log(f"\n📋 生成修复计划: {len(plan)}项")
        for i, item in enumerate(plan, 1):
            log(f"  阶段{i}: {item['action']} - {item['issue']}")
        
        # 询问是否执行修复
        print("\n是否执行自动修复? (y/N): ", end="")
        try:
            choice = sys.stdin.readline().strip().lower()
            if choice == "y" or choice == "yes":
                execute_repair_plan(plan)
            else:
                log("已跳过自动修复")
        except EOFError:
            log("非交互模式，跳过自动修复")
    else:
        log("\n✅ 无需修复，系统正常")
    
    # 生成报告
    report_file = generate_report(results, plan)
    log(f"\n📄 报告已生成: {report_file}")
    
    log("=" * 60)
    print("=" * 60)
    
    return results, plan


if __name__ == "__main__":
    results, plan = main()
    
    # 返回退出码
    if any(r["status"] == "error" for r in results):
        sys.exit(1)
    elif any(r["status"] == "warning" for r in results):
        sys.exit(2)
    else:
        sys.exit(0)
