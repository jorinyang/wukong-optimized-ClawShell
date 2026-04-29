#!/bin/bash
# W1: 深夜归档整理工作流
# 触发时间: 05:30
# 功能: memory_organizer.py dream + 错误归档 + Hermes自迭代

echo "[W1] 深夜归档开始 - $(date)"

# 1. 执行Dream每日整理
echo "[W1] 执行 memory_organizer.py dream..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ${CLAWSHELL_HOME:-$HOME/.clawshell}/scripts/memory_organizer.py dream >> ${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/memory_organizer.log 2>&1

# 2. 归档错误日志（按季度）
echo "[W1] 归档错误日志..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ${CLAWSHELL_HOME:-$HOME/.clawshell}/scripts/error_archiver.py --quarterly >> ${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/error_archiver.log 2>&1

# 3. 触发Hermes自迭代
echo "[W1] 触发Hermes自迭代..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ${CLAWSHELL_HOME:-$HOME/.clawshell}/scripts/memory_organizer.py iteration >> ${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/iteration.log 2>&1

echo "[W1] 深夜归档完成 - $(date)"
