#!/bin/bash
# Agent守护进程脚本 v2
# 功能：定期激活Agent会话并维持活跃
# 使用nohup后台执行，避免阻塞

# 设置PATH（launchd环境变量有限）
export PATH="/usr/local/bin:/usr/local/opt/node@22/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="$HOME"

AGENTS=("lab" "dev" "doc" "pub" "lib" "dat")
INTERVAL_MINUTES=25
# ClawShell运行时路径（用于日志/PID文件）
CLAWSHELL_RUNTIME="${CLAWSHELL_HOME:-$HOME/.real}"
LOG_FILE="${CLAWSHELL_RUNTIME}/users/user-bd1b229d4eff8f6a45c456149072cb3b/workspace/shared/agent_daemon.log"
PID_FILE="${CLAWSHELL_RUNTIME}/users/user-bd1b229d4eff8f6a45c456149072cb3b/workspace/shared/agent_daemon.pid"
LOCK_FILE="${CLAWSHELL_RUNTIME}/users/user-bd1b229d4eff8f6a45c456149072cb3b/workspace/shared/agent_daemon.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查是否已有守护进程在运行（防止重复启动）
if [ -f "$LOCK_FILE" ]; then
    OLD_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "守护进程已在运行 (PID: $OLD_PID)"
        exit 0
    fi
    # 清理无效锁文件
    rm -f "$LOCK_FILE"
fi

# 保存当前PID
echo $$ > "$LOCK_FILE"
echo $$ > "$PID_FILE"

log "=== Agent守护进程启动 (PID: $$) ==="
log "间隔: ${INTERVAL_MINUTES}分钟"
log "Agents: ${AGENTS[*]}"

# 主循环
while true; do
    for agent in "${AGENTS[@]}"; do
        log "激活 $agent..."
        
        # 使用nohup后台执行，避免阻塞
        nohup /usr/local/bin/openclaw agent --agent "$agent" --message "【心跳检测】维持会话活跃，每${INTERVAL_MINUTES}分钟一次心跳" > /dev/null 2>&1 &
        CMD_PID=$!
        
        # 等待最多30秒
        sleep 30
        kill -0 $CMD_PID 2>/dev/null && kill $CMD_PID 2>/dev/null
        
        if [ $? -eq 0 ]; then
            log "✅ $agent 激活成功"
        else
            log "⚠️ $agent 激活超时"
        fi
        
        # 短暂休眠避免并发
        sleep 2
    done
    
    log "=== 守护进程心跳 $(date '+%Y-%m-%d %H:%M:%S') ==="
    
    # 等待下一个周期
    sleep $((INTERVAL_MINUTES * 60))
done
