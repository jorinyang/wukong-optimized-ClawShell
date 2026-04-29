#!/bin/bash
# Self-Repair Cron配置
# 功能：设置每日凌晨5点检测 + 每10分钟执行修复

CRON_USER="yangyang"
OPENCLAW_SHARE="/Users/yangyang/.openclaw/workspace/shared"

# 检测器执行时间：每日凌晨5:00
DETECTOR_CRON="0 5 * * * /usr/local/bin/python3 ${OPENCLAW_SHARE}/scripts/self_repair_detector.py >> ${OPENCLAW_SHARE}/logs/self_repair_detector.log 2>&1"

# 执行器执行时间：每10分钟
EXECUTOR_CRON="*/10 * * * * /usr/local/bin/python3 ${OPENCLAW_SHARE}/scripts/self_repair_executor.py >> ${OPENCLAW_SHARE}/logs/self_repair_executor.log 2>&1"

echo "Self-Repair Cron任务配置："
echo ""
echo "【检测器】每日凌晨5:00执行系统瓶颈检测"
echo "${DETECTOR_CRON}"
echo ""
echo "【执行器】每10分钟执行一个修复阶段"
echo "${EXECUTOR_CRON}"
echo ""
echo "要安装这些Cron任务，请运行："
echo "  (crontab -l 2>/dev/null | grep -v self_repair; echo '${DETECTOR_CRON}'; echo '${EXECUTOR_CRON}') | crontab -"
