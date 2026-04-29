#!/bin/bash
#
# N8N 完整流水线闭环 v1.0
# 支持 PUB部署 → DAT分析 → LIB归档 → 结果通知
#

LOG_FILE="${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/n8n_complete_pipeline.log"
HTTP_SERVER="http://localhost:5680"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_request() {
    local action="$1"
    local task_type="$2"
    local description="$3"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"action\": \"$action\", \"task_type\": \"$task_type\", \"description\": \"$description\"}" \
        "$HTTP_SERVER/webhook" 2>/dev/null
}

# 各阶段处理函数
stage_publish() {
    log "🚀 [阶段1/4] PUB发布..."
    local input="$1"
    log "  └─ 发送到PUB Agent"
    send_request "dispatch_task" "publish" "$input"
    log "  └─ 发布完成"
}

stage_analyze_data() {
    log "📊 [阶段2/4] DAT数据分析..."
    local input="$1"
    log "  └─ 发送到DAT Agent"
    send_request "dispatch_task" "analyze_data" "$input"
    log "  └─ 分析完成"
}

stage_archive() {
    log "📚 [阶段3/4] LIB归档..."
    local input="$1"
    log "  └─ 发送到LIB Agent"
    send_request "dispatch_task" "archive" "$input"
    log "  └─ 归档完成"
}

stage_notify() {
    log "✅ [阶段4/4] 结果通知..."
    local result="$1"
    log "  └─ 任务完成: $result"
    # 通知可扩展：钉钉/邮件等
}

# 完整流水线
run_pipeline() {
    local task_id="$1"
    local description="$2"
    
    log "========================================="
    log "N8N 完整流水线"
    log "任务ID: $task_id"
    log "描述: $description"
    log "========================================="
    
    # 阶段1: PUB发布
    stage_publish "$description"
    
    # 阶段2: DAT分析
    stage_analyze_data "$description"
    
    # 阶段3: LIB归档
    stage_archive "$description"
    
    # 阶段4: 通知
    stage_notify "流水线执行完成"
    
    log "========================================="
    log "✅ 流水线闭环完成"
    log "========================================="
}

# 快速流水线（简化版）
run_quick_pipeline() {
    local description="$1"
    
    log "========================================="
    log "N8N 快速流水线 (PUB→LIB)"
    log "========================================="
    
    stage_publish "$description"
    stage_archive "$description"
    stage_notify "快速流水线完成"
    
    log "========================================="
    log "✅ 快速流水线完成"
    log "========================================="
}

# 主函数
main() {
    local command="${1:-help}"
    local task_id="${2:-pipeline-$(date +%Y%m%d%H%M%S)}"
    local description="${3:-完整流水线测试任务}"
    
    case "$command" in
        "full")
            run_pipeline "$task_id" "$description"
            ;;
        "quick")
            run_quick_pipeline "$description"
            ;;
        "pub")
            stage_publish "$description"
            ;;
        "dat")
            stage_analyze_data "$description"
            ;;
        "lib")
            stage_archive "$description"
            ;;
        "help")
            echo "用法: $0 <命令> [任务ID] [描述]"
            echo ""
            echo "命令:"
            echo "  full   - 完整流水线 (PUB→DAT→LIB→通知)"
            echo "  quick  - 快速流水线 (PUB→LIB)"
            echo "  pub    - 仅PUB发布"
            echo "  dat    - 仅DAT分析"
            echo "  lib    - 仅LIB归档"
            echo "  help   - 显示帮助"
            ;;
        *)
            log "❌ 未知命令: $command"
            $0 help
            ;;
    esac
}

main "$@"
