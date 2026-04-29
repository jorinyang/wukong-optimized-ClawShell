#!/bin/bash
#
# N8N watchdog - 保持N8N和HTTP服务在所需时可用
# 每5分钟检查一次，如果服务不可用则启动
#

LOG_FILE="${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/n8n_watchdog.log"
N8N_HTTP_PORT="5680"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_http_server() {
    # 检查HTTP服务器是否运行
    curl -s --max-time 3 "http://localhost:${N8N_HTTP_PORT}/health" > /dev/null 2>&1
    return $?
}

start_http_server() {
    log "HTTP服务器未运行，正在启动..."
    cd $HOME/n8n/scripts
    nohup python3 n8n_http_server.py 5680 >> ${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/n8n_server.log 2>&1 &
    sleep 2
    
    if check_http_server; then
        log "HTTP服务器启动成功 (PID: $!)"
        return 0
    else
        log "HTTP服务器启动失败"
        return 1
    fi
}

# 主逻辑
log "=== N8N Watchdog 检查 ==="

if check_http_server; then
    log "HTTP服务器运行正常"
else
    log "HTTP服务器未运行"
    start_http_server
fi

log "=== 检查完成 ==="
