#!/bin/bash
# W2: 晨报生成工作流
# 触发时间: 05:55
# 功能: 读取MemOS计划 + 查询任务队列 + 生成晨报 + 推送钉钉

echo "[W2] 晨报生成开始 - $(date)"

# 1. 读取MemOS今日计划
echo "[W2] 读取MemOS今日计划..."
MEMOS_PLAN=$(curl -s -H "Authorization: Bearer mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ" \
  "${MEMOS_BASE_URL:-https://memos.memtensor.cn/api/openmem/v1}/memos?filter=tag:今日计划" 2>/dev/null | \
  python3 -c "import sys,json; data=json.load(sys.stdin); print('\\n'.join([m.get('content','') for m in data.get('data',[])]))" 2>/dev/null || echo "暂无计划")

# 2. 查询任务队列状态
echo "[W2] 查询任务队列..."
TASK_STATUS=$(python3 << 'PYEOF'
import json
try:
    with open('${CLAWSHELL_HOME:-$HOME/.clawshell}/workspace/shared/task-queue.json') as f:
        d = json.load(f)
    tasks = d.get('tasks', [])
    pending = [t for t in tasks if t.get('status') == 'pending']
    print(f'待处理任务: {len(pending)}')
    for t in pending[:3]:
        print(f'  - {t.get("title", "无标题")[:40]}')
except:
    print('无法读取任务队列')
PYEOF
)

# 3. 生成晨报内容
MORNING_NEWS="📰 **晨报** | $(date '+%Y-%m-%d %H:%M')

---

## 今日计划
${MEMOS_PLAN:-暂无计划}

## 任务状态
${TASK_STATUS:-无法读取}

## 健康度
$(/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 ${CLAWSHELL_HOME:-$HOME/.clawshell}/scripts/memory_organizer.py health 2>/dev/null | grep "健康度" || echo "检查中...")

---

*由系统自动生成 | $(date '+%H:%M:%S')*"

# 4. 保存晨报
echo "$MORNING_NEWS" > ${CLAWSHELL_HOME:-$HOME/.clawshell}/inbox/morning_news_$(date '+%Y%m%d').md

echo "[W2] 晨报已生成"
echo "$MORNING_NEWS"
echo ""
echo "[W2] 晨报生成完成 - $(date)"
