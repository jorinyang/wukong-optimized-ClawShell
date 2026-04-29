#!/bin/bash
#
# N8N QA Webhook 工作流
# 触发智能问答系统
#

LOG_FILE="/Users/yangyang/.openclaw/logs/qa_webhook.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 处理问答请求
handle_qa_request() {
    local question="$1"
    local user_id="$2"
    local channel="$3"
    
    log "========================================="
    log "QA Webhook 处理请求"
    log "========================================="
    log "问题: $question"
    log "用户: $user_id"
    log "渠道: $channel"
    
    # 调用问答系统
    log "调用知识问答系统..."
    response=$(python3 ~/.openclaw/scripts/knowledge_qa.py "$question" 2>&1)
    
    log "响应: $response"
    
    # 返回响应
    echo "$response"
}

# 主函数
main() {
    case "$1" in
        "ask")
            handle_qa_request "$2" "$3" "$4"
            ;;
        *)
            echo "用法: $0 ask <问题> [用户ID] [渠道]"
            ;;
    esac
}

main "$@"
