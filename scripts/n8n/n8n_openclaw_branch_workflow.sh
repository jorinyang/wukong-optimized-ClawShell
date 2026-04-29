#!/bin/bash
#
# N8N OpenClaw 分支工作流 v1.0
# 支持 LAB/DEV/DOC 并行分支
#

LOG_FILE="/Users/yangyang/.openclaw/logs/n8n_branch_workflow.log"
HTTP_SERVER="http://localhost:5680"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 发送HTTP请求到OpenClaw
send_request() {
    local action="$1"
    local task_type="$2"
    local description="$3"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"action\": \"$action\", \"task_type\": \"$task_type\", \"description\": \"$description\"}" \
        "$HTTP_SERVER/webhook" 2>/dev/null
}

# 分支处理函数
handle_lab_branch() {
    log "🔬 处理 LAB 分支..."
    local description="$1"
    
    log "  └─ 发送分析任务到 LAB Agent"
    local result=$(send_request "dispatch_task" "analyze" "$description")
    log "  └─ 响应: $result"
}

handle_dev_branch() {
    log "💻 处理 DEV 分支..."
    local description="$1"
    
    log "  └─ 发送开发任务到 DEV Agent"
    local result=$(send_request "dispatch_task" "develop" "$description")
    log "  └─ 响应: $result"
}

handle_doc_branch() {
    log "📝 处理 DOC 分支..."
    local description="$1"
    
    log "  └─ 发送写作任务到 DOC Agent"
    local result=$(send_request "dispatch_task" "write" "$description")
    log "  └─ 响应: $result"
}

handle_pub_branch() {
    log "🚀 处理 PUB 分支..."
    local description="$1"
    
    log "  └─ 发送发布任务到 PUB Agent"
    local result=$(send_request "dispatch_task" "publish" "$description")
    log "  └─ 响应: $result"
}

handle_lib_branch() {
    log "📚 处理 LIB 分支..."
    local description="$1"
    
    log "  └─ 发送归档任务到 LIB Agent"
    local result=$(send_request "dispatch_task" "archive" "$description")
    log "  └─ 响应: $result"
}

handle_dat_branch() {
    log "📊 处理 DAT 分支..."
    local description="$1"
    
    log "  └─ 发送数据分析任务到 DAT Agent"
    local result=$(send_request "dispatch_task" "analyze_data" "$description")
    log "  └─ 响应: $result"
}

# 并行分支处理
run_parallel_branches() {
    local branch_type="$1"
    local description="$2"
    
    log "▶️ 启动并行分支: $branch_type"
    
    case "$branch_type" in
        "lab")
            handle_lab_branch "$description"
            ;;
        "dev")
            handle_dev_branch "$description"
            ;;
        "doc")
            handle_doc_branch "$description"
            ;;
        "pub")
            handle_pub_branch "$description"
            ;;
        "lib")
            handle_lib_branch "$description"
            ;;
        "dat")
            handle_dat_branch "$description"
            ;;
        "all")
            # 所有分支并行执行
            log "▶️ 启动全部分支..."
            handle_lab_branch "$description" &
            handle_dev_branch "$description" &
            handle_doc_branch "$description" &
            wait
            log "✅ 全部分支完成"
            ;;
        *)
            log "❌ 未知分支类型: $branch_type"
            ;;
    esac
}

# 主流程
main() {
    local command="${1:-help}"
    local description="${2:-N8N并行分支测试任务}"
    
    log "========================================="
    log "N8N OpenClaw 分支工作流"
    log "命令: $command | 描述: $description"
    log "========================================="
    
    case "$command" in
        "lab")
            run_parallel_branches "lab" "$description"
            ;;
        "dev")
            run_parallel_branches "dev" "$description"
            ;;
        "doc")
            run_parallel_branches "doc" "$description"
            ;;
        "pub")
            run_parallel_branches "pub" "$description"
            ;;
        "lib")
            run_parallel_branches "lib" "$description"
            ;;
        "dat")
            run_parallel_branches "dat" "$description"
            ;;
        "all")
            run_parallel_branches "all" "$description"
            ;;
        "help")
            echo "用法: $0 <分支> [描述]"
            echo ""
            echo "可用分支:"
            echo "  lab   - 分析分支"
            echo "  dev   - 开发分支"
            echo "  doc   - 文档分支"
            echo "  pub   - 发布分支"
            echo "  lib   - 归档分支"
            echo "  dat   - 数据分析分支"
            echo "  all   - 全部分支并行"
            echo "  help  - 显示帮助"
            ;;
        *)
            log "❌ 未知命令: $command"
            log "使用 '$0 help' 查看帮助"
            ;;
    esac
    
    log "========================================="
    log "工作流执行完成"
    log "========================================="
}

main "$@"
