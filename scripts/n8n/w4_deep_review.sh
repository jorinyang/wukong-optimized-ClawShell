#!/bin/bash
# W4: 深度复盘工作流
# 触发时间: 21:00
# 功能: 触发Hermes深度复盘 + 生成洞察 + optimization→任务队列

echo "[W4] 深度复盘开始 - $(date)"

# 1. 触发Hermes深度复盘
echo "[W4] 触发Hermes深度复盘..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ~/.hermes/hermes_watchdog.py --deep-review >> ~/.hermes/logs/deep_review.log 2>&1

# 2. 生成洞察
echo "[W4] 生成洞察..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ~/.hermes/hermes_watchdog.py --generate-insights >> ~/.hermes/logs/insight_generator.log 2>&1

# 3. 消费洞察（optimization→任务队列）
echo "[W4] 消费Hermes洞察..."
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ${CLAWSHELL_HOME:-$HOME/.clawshell}/scripts/hermes_insight_consumer.py --poll >> ${CLAWSHELL_HOME:-$HOME/.clawshell}/logs/hermes_consumer.log 2>&1

# 4. 统计本次复盘结果
echo "[W4] 复盘统计..."
INSIGHT_COUNT=$(ls -t ~/.openclaw/shared/hermes_insights/*.json 2>/dev/null | head -1 | xargs cat 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('suggestions',[])))" 2>/dev/null || echo "0")
TASK_COUNT=$(cat ${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/task-queue.json 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); tasks=d.get('tasks',[]);
  hermes=[t for t in tasks if t.get('source')=='hermes_insight'];
  print(len(hermes))" 2>/dev/null || echo "0")

echo "[W4] 生成洞察数: $INSIGHT_COUNT"
echo "[W4] Hermes任务数: $TASK_COUNT"
echo "[W4] 深度复盘完成 - $(date)"
