#!/bin/bash
# 日志轮转脚本
# 功能：当日志文件超过阈值时自动归档

LOG_FILE="${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/gateway.err.log"
LOG_DIR="${CLAWSHELL_HOME:-$HOME/.clawshell}/logs"
MAX_SIZE_MB=50
MAX_ARCHIVES=7

# 检查日志文件是否存在
if [ ! -f "$LOG_FILE" ]; then
    exit 0
fi

# 获取当前文件大小(MB)
SIZE_MB=$(du -m "$LOG_FILE" 2>/dev/null | cut -f1)

if [ "$SIZE_MB" -gt "$MAX_SIZE_MB" ]; then
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    ARCHIVE_NAME="gateway.err.log.${TIMESTAMP}.bak"
    
    # 归档当前日志
    mv "$LOG_FILE" "$LOG_DIR/$ARCHIVE_NAME"
    
    # 创建新空日志
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    # 清理旧归档（保留最近N个）
    cd "$LOG_DIR" || exit 1
    ls -t gateway.err.log.*.bak | tail -n +$((MAX_ARCHIVES + 1)) | xargs rm -f 2>/dev/null
    
    echo "$(date): Log rotated to $ARCHIVE_NAME (size: ${SIZE_MB}MB)"
fi
