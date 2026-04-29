#!/bin/bash
#
# N8N 版本监控工作流 v1.0
# 定时检测版本并生成报告
#

LOG_FILE="${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/n8n_version_workflow.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 版本检测
run_version_check() {
    log "========================================="
    log "N8N 版本监控工作流"
    log "========================================="
    
    log "1. 运行版本检测..."
    python3 ~/.openclaw/scripts/openclaw_version_monitor.py >> "$LOG_FILE" 2>&1
    
    log "2. 运行影响分析..."
    python3 ~/.openclaw/scripts/openclaw_impact_analyzer.py >> "$LOG_FILE" 2>&1
    
    log "3. 检查最新报告..."
    if [ -f ~/.openclaw/.version_state.json ]; then
        log "✅ 版本报告已生成"
    else
        log "❌ 版本报告生成失败"
    fi
    
    if [ -f ~/.openclaw/.impact_report.json ]; then
        log "✅ 影响报告已生成"
    else
        log "❌ 影响报告生成失败"
    fi
    
    log "========================================="
    log "✅ 版本监控完成"
    log "========================================="
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  run    - 运行版本监控"
    echo "  check  - 检查服务状态"
    echo "  help   - 显示帮助"
}

# 检查服务状态
check_services() {
    log "检查服务状态..."
    
    # 检查N8N HTTP
    if curl -s --max-time 3 http://localhost:5680/health > /dev/null 2>&1; then
        log "✅ N8N HTTP服务正常"
    else
        log "❌ N8N HTTP服务异常"
    fi
    
    # 检查Python脚本
    for script in openclaw_version_monitor.py openclaw_impact_analyzer.py openclaw_adaptive_executor.py; do
        if [ -f ~/.openclaw/scripts/$script ]; then
            log "✅ $script 存在"
        else
            log "❌ $script 缺失"
        fi
    done
}

main() {
    local command="${1:-run}"
    
    case "$command" in
        "run")
            run_version_check
            ;;
        "check")
            check_services
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo "未知命令: $command"
            show_help
            ;;
    esac
}

main "$@"
