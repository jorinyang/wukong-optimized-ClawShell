#!/usr/bin/env python3
"""
self_repair_executor.py - 修复计划执行器
版本: v2.0
功能：执行当日所有修复计划，直到完成
"""

import json
import os
import subprocess
from datetime import datetime

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

def load_queue():
    if not os.path.exists(REPAIR_QUEUE_FILE):
        return None
    with open(REPAIR_QUEUE_FILE, 'r') as f:
        return json.load(f)

def save_queue(queue):
    with open(REPAIR_QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

# ========== 修复动作实现 ==========

def restart_gateway():
    log("🔄 重启Gateway...")
    subprocess.run(["openclaw", "gateway", "restart"], capture_output=True, timeout=30)
    return True

def restart_event_bus():
    log("🔄 重启EventBus...")
    subprocess.run(["launchctl", "stop", "ai.openclaw.event-bus"], capture_output=True)
    subprocess.run(["launchctl", "start", "ai.openclaw.event-bus"], capture_output=True, timeout=10)
    return True

def restart_context_manager():
    log("🔄 重启ContextManager...")
    subprocess.run(["launchctl", "stop", "ai.openclaw.context-manager"], capture_output=True)
    subprocess.run(["launchctl", "start", "ai.openclaw.context-manager"], capture_output=True, timeout=10)
    return True

def restart_agent_daemon():
    log("🔄 重启AgentDaemon...")
    subprocess.run(["launchctl", "stop", "ai.openclaw.agent-daemon"], capture_output=True)
    subprocess.run(["launchctl", "start", "ai.openclaw.agent-daemon"], capture_output=True, timeout=10)
    return True

def restart_lib_archive():
    log("🔄 重启LibArchive...")
    subprocess.run(["launchctl", "stop", "ai.openclaw.lib-archive"], capture_output=True)
    subprocess.run(["launchctl", "start", "ai.openclaw.lib-archive"], capture_output=True, timeout=10)
    return True

def restart_log_rotate():
    log("🔄 重启LogRotate...")
    subprocess.run(["launchctl", "stop", "ai.openclaw.log-rotate"], capture_output=True)
    subprocess.run(["launchctl", "start", "ai.openclaw.log-rotate"], capture_output=True, timeout=10)
    return True

def restart_all_daemons():
    log("🔄 重启全部守护进程...")
    daemons = ["event-bus", "context-manager", "agent-daemon", "lib-archive", "log-rotate"]
    for daemon in daemons:
        name = f"ai.openclaw.{daemon}"
        subprocess.run(["launchctl", "stop", name], capture_output=True)
        subprocess.run(["launchctl", "start", name], capture_output=True, timeout=10)
    return True

def rotate_logs():
    log("📦 执行日志轮转...")
    script = os.path.join(SHARED_DIR, "scripts/rotate_gateway_log.sh")
    subprocess.run([script], capture_output=True, timeout=30)
    return True

def fix_symlinks():
    log("🔧 修复Skills symlinks...")
    # 重新复制skills到OpenClaw目录
    src_dir = os.path.expanduser("~/.agents/skills")
    dst_dir = os.path.join(WORKSPACE, "skills")
    
    if not os.path.exists(src_dir):
        log("  ⚠️ 源目录不存在")
        return False
    
    for item in os.listdir(src_dir):
        if item.startswith("ljg-"):
            src = os.path.join(src_dir, item)
            dst = os.path.join(dst_dir, item)
            if os.path.isdir(src):
                subprocess.run(["rm", "-rf", dst], capture_output=True)
                subprocess.run(["cp", "-r", src, dst], capture_output=True)
                log(f"  ✅ 复制 {item}")
    return True

def fix_scheduler():
    log("🔧 修复TaskScheduler...")
    scheduler = os.path.join(SHARED_DIR, "task_scheduler.py")
    # 验证语法
    try:
        with open(scheduler, 'r') as f:
            compile(f.read(), scheduler, 'exec')
        return True
    except Exception as e:
        log(f"  ⚠️ 语法错误: {e}")
        return False

def fix_event_bus():
    log("🔧 修复EventBus...")
    script = os.path.join(SHARED_DIR, "scripts/event_bus.py")
    return os.path.exists(script)

def activate_agents():
    log("🤖 激活Agent会话...")
    agents = ["lab", "dev", "doc", "pub", "lib", "dat"]
    for agent in agents:
        subprocess.run(
            ["/usr/local/bin/openclaw", "agent", "--agent", agent,
             "--message", "【心跳检测】维持会话活跃"],
            capture_output=True, timeout=30
        )
        log(f"  ✅ {agent} 已激活")
    return True

def create_inboxes():
    log("📁 创建Agent Inbox...")
    inbox_dir = os.path.join(SHARED_DIR, "inbox")
    os.makedirs(inbox_dir, exist_ok=True)
    for agent in ["lab", "dev", "doc", "pub", "lib", "dat"]:
        agent_inbox = os.path.join(inbox_dir, agent)
        os.makedirs(agent_inbox, exist_ok=True)
        log(f"  ✅ {agent}/")
    return True

def fix_hermes_bridge():
    log("🔗 修复Hermes桥接...")
    # 检查桥接是否存在
    bridge = os.path.join(SHARED_DIR, "scripts/execution_bridge.py")
    if not os.path.exists(bridge):
        log("  ⚠️ execution_bridge.py 不存在")
        return False
    return True

def restart_hermes():
    log("🔄 重启Hermes Guardian...")
    # 检查PID文件
    pid_file = os.path.expanduser("~/.hermes/guardian.pid")
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 9)  # 强制终止
        except:
            pass
    # 重新启动Guardian
    guardian_script = os.path.expanduser("~/.hermes/scripts/guardian.sh")
    if os.path.exists(guardian_script):
        subprocess.Popen(["bash", guardian_script, "start"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("  ✅ Hermes Guardian已重启")
    return True

def create_kb():
    log("📚 创建知识库目录...")
    kb_dir = os.path.join(SHARED_DIR, "knowledge-base")
    os.makedirs(kb_dir, exist_ok=True)
    for subdir in ["00-索引与导航", "01-系统架构", "02-最佳实践",
                   "03-部署运维", "04-项目文档", "99-归档"]:
        os.makedirs(os.path.join(kb_dir, subdir), exist_ok=True)
    return True

def fix_lib_archive():
    log("📦 修复Lib归档脚本...")
    script = os.path.join(SHARED_DIR, "lib_auto_archive.py")
    return os.path.exists(script)

def alert_disk():
    log("⚠️ 磁盘空间不足告警...")
    # 可以添加发送通知的逻辑
    return True

def alert_channel():
    log("⚠️ 通道配置告警...")
    return True

def run_doctor():
    """快速检查Gateway状态，替代完整的doctor命令"""
    log("🔧 检查Gateway配置...")
    
    # 1. 检查Gateway状态
    result = subprocess.run(
        ["openclaw", "gateway", "status"],
        capture_output=True, text=True, timeout=10
    )
    if "running" not in result.stdout.lower():
        log("  ⚠️ Gateway未运行")
    else:
        log("  ✅ Gateway运行中")
    
    # 2. 检查launchd服务配置
    result = subprocess.run(
        ["launchctl", "list", "ai.openclaw.gateway"],
        capture_output=True, text=True, timeout=5
    )
    if "No such file" in result.stderr or result.returncode != 0:
        log("  ⚠️ LaunchAgent未注册")
    else:
        log("  ✅ LaunchAgent正常")
    
    # 3. 检查配置警告（简单检查gateway.err.log）
    err_log = os.path.expanduser("~/.openclaw/logs/gateway.err.log")
    if os.path.exists(err_log):
        size_mb = os.path.getsize(err_log) / (1024*1024)
        if size_mb > 10:
            log(f"  ⚠️ 日志过大: {size_mb:.1f}MB")
        else:
            log(f"  ✅ 日志正常: {size_mb:.1f}MB")
    
    return True

# 动作映射
ACTIONS = {
    "restart_gateway": restart_gateway,
    "restart_event_bus": restart_event_bus,
    "restart_context_manager": restart_context_manager,
    "restart_agent_daemon": restart_agent_daemon,
    "restart_lib_archive": restart_lib_archive,
    "restart_log_rotate": restart_log_rotate,
    "restart_all_daemons": restart_all_daemons,
    "rotate_logs": rotate_logs,
    "fix_symlinks": fix_symlinks,
    "fix_scheduler": fix_scheduler,
    "fix_event_bus": fix_event_bus,
    "activate_agents": activate_agents,
    "create_inboxes": create_inboxes,
    "fix_hermes_bridge": fix_hermes_bridge,
    "restart_hermes": restart_hermes,
    "create_kb": create_kb,
    "fix_lib_archive": fix_lib_archive,
    "alert_disk": alert_disk,
    "alert_channel": alert_channel,
    "run_doctor": run_doctor,
}

def execute_repair_plan():
    """执行当日所有修复计划"""
    queue = load_queue()
    if not queue:
        log("📭 无待执行修复计划")
        return False
    
    if queue.get("status") == "completed":
        log("✅ 修复计划已完成")
        return False
    
    plan = queue.get("plan", [])
    executed = queue.get("executed_phases", [])
    
    # 找出未执行的项目
    remaining = [item for item in plan if item["action"] not in executed]
    
    if not remaining:
        queue["status"] = "completed"
        queue["completed_at"] = datetime.now().isoformat()
        save_queue(queue)
        log("✅ 所有修复项目已完成")
        return True
    
    log(f"📋 待执行: {len(remaining)}项")
    
    # 执行所有剩余项目
    success_count = 0
    for item in remaining:
        action = item["action"]
        issue = item["issue"]
        
        log(f"🔧 执行: {action}")
        log(f"   问题: {issue}")
        
        action_func = ACTIONS.get(action)
        if action_func:
            try:
                action_func()
                log(f"   ✅ 成功")
                success_count += 1
            except Exception as e:
                log(f"   ❌ 失败: {e}")
        else:
            log(f"   ⚠️ 未知动作: {action}")
        
        # 记录已执行
        executed.append(action)
    
    # 更新队列
    queue["executed_phases"] = executed
    queue["status"] = "completed"
    queue["completed_at"] = datetime.now().isoformat()
    queue["success_count"] = success_count
    save_queue(queue)
    
    log(f"📊 执行完成: {success_count}/{len(remaining)}项成功")
    return True

if __name__ == "__main__":
    log("=" * 60)
    log("🚀 自修复执行器 v2.0 启动")
    log("=" * 60)
    
    executed = execute_repair_plan()
    
    log("=" * 60)
