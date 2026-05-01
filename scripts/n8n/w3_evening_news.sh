#!/bin/bash
# W3: 晚报生成工作流
# 触发时间: 18:00
# 功能: 汇总今日完成 + 错误解决 + Hermes洞察 + 生成晚报 + 推送钉钉

echo "[W3] 晚报生成开始 - $(date)"

# 1. 汇总今日完成任务
echo "[W3] 汇总今日任务..."
TODAY=$(date '+%Y-%m-%d')
COMPLETED_TASKS=$(cat ${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/task-queue.json 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); tasks=d.get('tasks',[]);
  completed=[t for t in tasks if t.get('status')=='completed' and TODAY in t.get('completed_at','')]
  for t in completed[:5]: print(f'- {t.get(\"title\",\"无标题\")}')" TODAY=$TODAY 2>/dev/null || echo "暂无完成任务")

# 2. 汇总错误与解决
echo "[W3] 汇总错误解决..."
ERROR_SUMMARY=$(cat ${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/task-queue.json 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); tasks=d.get('tasks',[]);
  errors=[t for t in tasks if 'error' in t.get('status','').lower()]
  print(f'错误任务数: {len(errors)}')" 2>/dev/null || echo "无法统计")

# 3. 查询Hermes最新洞察
echo "[W3] 查询Hermes洞察..."
HERMES_INSIGHT=$(ls -t ~/.real/shared/hermes_insights/*.json 2>/dev/null | head -1 | xargs cat 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('context_injection','暂无洞察')[:200])" 2>/dev/null || echo "暂无洞察")

# 4. 生成晚报内容
EVENING_NEWS="📰 **晚报** | $(date '+%Y-%m-%d %H:%m')

---

## 今日完成
${COMPLETED_TASKS:-暂无完成}

## 错误统计
${ERROR_SUMMARY:-无法统计}

## Hermes洞察
${HERMES_INSIGHT:-暂无}

---

*由系统自动生成 | $(date '+%H:%M:%S')*"

# 5. 保存晚报
echo "$EVENING_NEWS" > ${CLAWSHELL_HOME:-$HOME/.clawshell}/inbox/evening_news_$(date '+%Y%m%d').md

echo "[W3] 晚报已生成"
echo "$EVENING_NEWS"
echo ""
echo "[W3] 晚报生成完成 - $(date)"
