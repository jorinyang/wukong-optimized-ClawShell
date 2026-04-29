#!/usr/bin/env python3
"""
self_repair_detector.py - ClawShell全景架构自修复检测器
版本: v2.0
覆盖范围: ClawShell v0.8完整架构

检测模块:
├── 架构层 (Architecture)
│   ├── Gateway状态
│   ├── Skills加载
│   └── Symlink安全
├── 调度层 (Scheduling)
│   ├── TaskScheduler
│   ├── TaskQueue
│   └── DispatchProtocol
├── 协作层 (Collaboration)
│   ├── EventBus
│   ├── ContextManager
│   └── TaskMarket
├── 性能层 (Performance)
│   ├── 日志管理
│   ├── 磁盘空间
│   └── Gateway进程
├── 守护进程层 (Daemons)
│   ├── AgentDaemon
│   ├── EventBusDaemon
│   ├── ContextManagerDaemon
│   └── HermesBridge
├── 通道层 (Channels)
│   ├── Discord
│   └── DingTalk
└── 知识层 (Knowledge)
    ├── KnowledgeBase
    └── LibArchive
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
REPAIR_QUEUE_FILE = os.path.join(SHARED_DIR, "repair_queue.json")
REPAIR_LOG = os.path.join(SHARED_DIR, "logs", "self_repair.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(REPAIR_LOG), exist_ok=True)
    with open(REPAIR_LOG, "a") as f:
        f.write(line + "\n")

# ========== 架构层检测 ==========

def check_gateway():
    """检查Gateway服务"""
    result = subprocess.run(
        ["openclaw", "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    return "running" in result.stdout.lower()

def check_gateway_process():
    """检查Gateway进程"""
    result = subprocess.run(
        ["pgrep", "-f", "openclaw-gateway"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def check_skills():
    """检查Skills加载"""
    result = subprocess.run(
        ["openclaw", "skills", "list"],
        capture_output=True, text=True, timeout=30
    )
    symlink_warnings = result.stdout.count("symlink")
    ljg_count = result.stdout.count("ljg-")
    return symlink_warnings == 0 and ljg_count >= 16

def check_symlinks():
    """检查symlink安全"""
    skills_dir = os.path.join(WORKSPACE, "skills")
    if not os.path.exists(skills_dir):
        return True
    for item in os.listdir(skills_dir):
        path = os.path.join(skills_dir, item)
        if os.path.islink(path):
            target = os.readlink(path)
            # 检查是否指向OpenClaw外部
            if ".agents" in target or ".nix-profile" in target:
                return False
    return True

# ========== 调度层检测 ==========

def check_task_scheduler():
    """检查TaskScheduler语法"""
    scheduler = os.path.join(SHARED_DIR, "task_scheduler.py")
    if not os.path.exists(scheduler):
        return False
    try:
        with open(scheduler, 'r') as f:
            compile(f.read(), scheduler, 'exec')
        return True
    except:
        return False

def check_task_queue():
    """检查TaskQueue文件"""
    queue_file = os.path.join(SHARED_DIR, "task-queue.json")
    if not os.path.exists(queue_file):
        return True  # 空队列是正常的
    try:
        with open(queue_file, 'r') as f:
            data = json.load(f)
        # 检查是否有异常数量的pending任务
        pending = [t for t in data.get("tasks", []) if t.get("status") == "pending"]
        return len(pending) < 50  # 超过50个pending说明可能有问题
    except:
        return False

def check_dispatch_protocol():
    """检查分发协议v2实现"""
    scheduler = os.path.join(SHARED_DIR, "task_scheduler.py")
    if not os.path.exists(scheduler):
        return False
    with open(scheduler, 'r') as f:
        content = f.read()
    # 检查关键函数是否存在
    required = ["notify_agent_via_cli", "check_timeouts", "dispatch_to_agent"]
    return all(fn in content for fn in required)

# ========== 协作层检测 ==========

def check_event_bus():
    """检查EventBus进程"""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    return "ai.openclaw.event-bus" in result.stdout

def check_event_bus_process():
    """检查EventBus处理逻辑"""
    script = os.path.join(SHARED_DIR, "scripts/event_bus.py")
    return os.path.exists(script)

def check_context_manager():
    """检查ContextManager"""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    return "ai.openclaw.context-manager" in result.stdout

def check_context_manager_output():
    """检查ContextManager输出"""
    ctx_file = os.path.join(SHARED_DIR, "context_manager.json")
    if not os.path.exists(ctx_file):
        return False
    try:
        with open(ctx_file, 'r') as f:
            data = json.load(f)
        ts = data.get("timestamp")
        if not ts:
            return False
        last_update = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now()
        return (now - last_update.replace(tzinfo=None)).total_seconds() < 600
    except:
        return False

def check_task_market():
    """检查TaskMarket（已归档检测）"""
    # TaskMarket应该已被归档
    archive_dir = os.path.join(WORKSPACE, "archive")
    market_archive = os.path.join(archive_dir, "task-market_20260429")
    queue_file = os.path.join(SHARED_DIR, "task-queue.json")
    # 如果归档存在且队列文件存在，说明已统一
    return os.path.exists(market_archive) and os.path.exists(queue_file)

# ========== 性能层检测 ==========

def check_gateway_log():
    """检查Gateway日志"""
    log_file = os.path.expanduser("~/.openclaw/logs/gateway.err.log")
    if not os.path.exists(log_file):
        return True
    size_mb = os.path.getsize(log_file) / (1024 * 1024)
    return size_mb < 10

def check_disk_space():
    """检查磁盘空间"""
    workspace = os.path.expanduser("~/.openclaw")
    result = subprocess.run(
        ["df", "-h", workspace],
        capture_output=True, text=True, timeout=5
    )
    try:
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            usage = lines[1].split()[-2] if len(lines[1].split()) >= 5 else "0%"
            pct = int(usage.rstrip('%')) if '%' in usage else 0
            return pct < 90  # 小于90%正常
    except:
        pass
    return True

def check_launchd_config():
    """检查launchd配置警告"""
    result = subprocess.run(
        ["openclaw", "doctor"],
        capture_output=True, text=True, timeout=120
    )
    # 检查是否有严重警告（排除info级别）
    warnings = ["error", "Error", "failed", "Failed", "missing", "Missing"]
    return not any(w in result.stdout for w in warnings)

# ========== 守护进程层检测 ==========

def check_all_daemons():
    """检查所有守护进程"""
    required_daemons = [
        "ai.openclaw.event-bus",
        "ai.openclaw.context-manager",
        "ai.openclaw.agent-daemon",
    ]
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    running = [d for d in required_daemons if d in result.stdout]
    return len(running) == len(required_daemons)

def check_agent_daemon():
    """检查Agent守护进程"""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    return "ai.openclaw.agent-daemon" in result.stdout

def check_lib_archive():
    """检查Lib归档守护进程"""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    return "ai.openclaw.lib-archive" in result.stdout

def check_log_rotate():
    """检查日志轮转守护进程"""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True, timeout=10
    )
    return "ai.openclaw.log-rotate" in result.stdout

# ========== Agent层检测 ==========

def check_agent_sessions():
    """检查Agent会话状态"""
    result = subprocess.run(
        ["openclaw", "sessions", "--all-agents"],
        capture_output=True, text=True, timeout=30
    )
    required_agents = ["lab", "dev", "doc", "pub", "lib", "dat"]
    for agent in required_agents:
        # 检查是否有最近的会话（带时间戳）
        if f"{agent}\t" not in result.stdout and f"{agent} " not in result.stdout:
            return False
        # 检查会话是否在合理时间内（2小时内）
        # 简化：只要有会话就行
    return True

def check_agent_inbox():
    """检查Agent inbox目录"""
    inbox_dir = os.path.join(SHARED_DIR, "inbox")
    if not os.path.exists(inbox_dir):
        return False
    # 检查各Agent的inbox是否存在
    for agent in ["lab", "dev", "doc", "pub", "lib", "dat"]:
        agent_inbox = os.path.join(inbox_dir, agent)
        if not os.path.exists(agent_inbox):
            return False
    return True

# ========== Hermes层检测 ==========

def check_hermes_bridge():
    """检查Hermes桥接"""
    bridge = os.path.join(SHARED_DIR, "scripts/execution_bridge.py")
    return os.path.exists(bridge)

def check_hermes_insight_bridge():
    """检查Hermes洞察桥接"""
    bridge = os.path.join(SHARED_DIR, "scripts/hermes_insight_bridge.py")
    return os.path.exists(bridge)

def check_hermes_guardian():
    """检查Hermes Guardian进程"""
    guardian_pid = os.path.expanduser("~/.hermes/guardian.pid")
    if not os.path.exists(guardian_pid):
        return False
    try:
        with open(guardian_pid, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # 检查进程是否存在
        return True
    except:
        return False

# ========== 知识层检测 ==========

def check_knowledge_base():
    """检查知识库目录"""
    kb_dir = os.path.join(SHARED_DIR, "knowledge-base")
    return os.path.exists(kb_dir)

def check_lib_auto_archive():
    """检查lib归档脚本"""
    script = os.path.join(SHARED_DIR, "lib_auto_archive.py")
    return os.path.exists(script)

# ========== 通道层检测 ==========

def check_discord_channel():
    """检查Discord通道配置"""
    config = os.path.join(WORKSPACE, "openclaw.json")
    try:
        with open(config, 'r') as f:
            data = json.load(f)
        channels = data.get("channels", {})
        return "discord" in channels
    except:
        return True  # 配置检查失败不阻断

def check_dingtalk_channel():
    """检查钉钉通道配置"""
    config = os.path.join(WORKSPACE, "openclaw.json")
    try:
        with open(config, 'r') as f:
            data = json.load(f)
        channels = data.get("channels", {})
        return "dingtalk" in channels
    except:
        return True

# ========== 综合检测执行 ==========

CHECKS = [
    # 架构层 (4项)
    ("arch.gateway", "Gateway服务", check_gateway),
    ("arch.gateway_process", "Gateway进程", check_gateway_process),
    ("arch.skills", "Skills加载", check_skills),
    ("arch.symlinks", "Symlink安全", check_symlinks),
    
    # 调度层 (3项)
    ("sched.task_scheduler", "TaskScheduler", check_task_scheduler),
    ("sched.task_queue", "TaskQueue", check_task_queue),
    ("sched.dispatch_protocol", "分发协议v2", check_dispatch_protocol),
    
    # 协作层 (4项)
    ("collab.event_bus", "EventBus守护进程", check_event_bus),
    ("collab.event_bus_logic", "EventBus逻辑", check_event_bus_process),
    ("collab.context_manager", "ContextManager守护进程", check_context_manager),
    ("collab.context_output", "ContextManager输出", check_context_manager_output),
    
    # 性能层 (3项)
    ("perf.gateway_log", "Gateway日志", check_gateway_log),
    ("perf.disk_space", "磁盘空间", check_disk_space),
    ("perf.launchd_config", "Launchd配置", check_launchd_config),
    
    # 守护进程层 (4项)
    ("daemon.all", "全部守护进程", check_all_daemons),
    ("daemon.agent", "AgentDaemon", check_agent_daemon),
    ("daemon.lib_archive", "LibArchiveDaemon", check_lib_archive),
    ("daemon.log_rotate", "LogRotateDaemon", check_log_rotate),
    
    # Agent层 (2项)
    ("agent.sessions", "Agent会话", check_agent_sessions),
    ("agent.inbox", "Agent Inbox", check_agent_inbox),
    
    # Hermes层 (3项)
    ("hermes.bridge", "Hermes桥接", check_hermes_bridge),
    ("hermes.insight_bridge", "Hermes洞察桥接", check_hermes_insight_bridge),
    ("hermes.guardian", "Hermes Guardian", check_hermes_guardian),
    
    # 知识层 (2项)
    ("knowledge.kb", "知识库", check_knowledge_base),
    ("knowledge.lib_archive", "Lib归档脚本", check_lib_auto_archive),
    
    # 通道层 (2项)
    ("channel.discord", "Discord通道", check_discord_channel),
    ("channel.dingtalk", "钉钉通道", check_dingtalk_channel),
]

# 修复动作映射
REPAIR_ACTIONS = {
    "arch.gateway": ("restart_gateway", "Gateway服务未运行"),
    "arch.gateway_process": ("restart_gateway", "Gateway进程不存在"),
    "arch.skills": ("fix_symlinks", "Skills加载异常"),
    "arch.symlinks": ("fix_symlinks", "Symlink指向外部目录"),
    
    "sched.task_scheduler": ("fix_scheduler", "TaskScheduler语法错误"),
    "sched.task_queue": ("fix_scheduler", "TaskQueue文件损坏"),
    "sched.dispatch_protocol": ("fix_scheduler", "分发协议未实现"),
    
    "collab.event_bus": ("restart_event_bus", "EventBus守护进程未运行"),
    "collab.event_bus_logic": ("fix_event_bus", "EventBus脚本缺失"),
    "collab.context_manager": ("restart_context_manager", "ContextManager未运行"),
    "collab.context_output": ("restart_context_manager", "ContextManager无输出"),
    
    "perf.gateway_log": ("rotate_logs", "Gateway日志过大"),
    "perf.disk_space": ("alert_disk", "磁盘空间不足"),
    "perf.launchd_config": ("run_doctor", "Launchd配置有误"),
    
    "daemon.all": ("restart_all_daemons", "部分守护进程未运行"),
    "daemon.agent": ("restart_agent_daemon", "AgentDaemon未运行"),
    "daemon.lib_archive": ("restart_lib_archive", "LibArchiveDaemon未运行"),
    "daemon.log_rotate": ("restart_log_rotate", "LogRotateDaemon未运行"),
    
    "agent.sessions": ("activate_agents", "Agent会话离线"),
    "agent.inbox": ("create_inboxes", "Agent Inbox缺失"),
    
    "hermes.bridge": ("fix_hermes_bridge", "Hermes桥接缺失"),
    "hermes.insight_bridge": ("fix_hermes_bridge", "Hermes洞察桥接缺失"),
    "hermes.guardian": ("restart_hermes", "Hermes Guardian未运行"),
    
    "knowledge.kb": ("create_kb", "知识库目录缺失"),
    "knowledge.lib_archive": ("fix_lib_archive", "Lib归档脚本缺失"),
    
    "channel.discord": ("alert_channel", "Discord通道未配置"),
    "channel.dingtalk": ("alert_channel", "钉钉通道未配置"),
}

def run_all_checks():
    """执行所有检测"""
    results = []
    for check_id, name, func in CHECKS:
        try:
            status = func()
            results.append({
                "id": check_id,
                "name": name,
                "status": "ok" if status else "warning",
                "checked_at": datetime.now().isoformat()
            })
        except Exception as e:
            results.append({
                "id": check_id,
                "name": name,
                "status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            })
    return results

def generate_repair_plan(results):
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
                    "priority": get_priority(check_id)
                })
    # 按优先级排序
    plan.sort(key=lambda x: x["priority"])
    return plan

def get_priority(check_id):
    """获取检查项优先级"""
    priorities = {
        "arch.gateway": 1,
        "arch.gateway_process": 1,
        "sched.task_scheduler": 2,
        "collab.event_bus": 2,
        "collab.context_manager": 2,
        "daemon.all": 3,
        "agent.sessions": 4,
        "perf.gateway_log": 5,
    }
    return priorities.get(check_id, 10)

def save_repair_queue(plan):
    """保存修复队列"""
    queue = {
        "version": "v2.0",
        "created_at": datetime.now().isoformat(),
        "total_checks": len(CHECKS),
        "plan": plan,
        "executed_phases": [],
        "status": "pending" if plan else "completed"
    }
    
    with open(REPAIR_QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    
    return queue

# 执行检测
log("=" * 60)
log("🚀 ClawShell全景架构自修复检测 v2.0")
log("=" * 60)

results = run_all_checks()
passed = sum(1 for r in results if r["status"] == "ok")
warnings = sum(1 for r in results if r["status"] == "warning")
errors = sum(1 for r in results if r["status"] == "error")

log(f"📊 检测完成: {passed}/{len(results)} 通过, {warnings} 警告, {errors} 错误")

for result in results:
    if result["status"] == "ok":
        log(f"  ✅ {result['name']}")
    elif result["status"] == "warning":
        log(f"  ⚠️ {result['name']}")
    else:
        log(f"  ❌ {result['name']}: {result.get('error', 'unknown')}")

# 生成修复计划
plan = generate_repair_plan(results)
queue = save_repair_queue(plan)

if plan:
    log(f"📋 生成修复计划: {len(plan)}项")
    for i, item in enumerate(plan, 1):
        log(f"  阶段{i}: {item['action']} - {item['issue']}")
else:
    log("✅ 无需修复，系统正常")

log("=" * 60)
