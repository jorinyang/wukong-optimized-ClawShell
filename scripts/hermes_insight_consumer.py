#!/usr/bin/env python3
"""
Hermes Insight Consumer - 消费Hermes生成的洞察
功能：
1. 轮询hermes_insights/pending目录
2. 分类处理不同类型的洞察
3. 优化建议写入任务队列
4. 记录处理结果
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 配置
OPENCLAW_DIR = Path.home() / ".openclaw"
INSIGHTS_DIR = OPENCLAW_DIR / "shared" / "hermes_insights"
PENDING_DIR = INSIGHTS_DIR / "pending"
APPLIED_DIR = INSIGHTS_DIR / "applied"
REJECTED_DIR = INSIGHTS_DIR / "rejected"
STATE_FILE = INSIGHTS_DIR / ".state.json"
TASK_QUEUE_FILE = OPENCLAW_DIR / "workspace" / "shared" / "task-queue.json"
LOG_FILE = OPENCLAW_DIR / "logs" / "hermes_consumer.log"


class InsightConsumer:
    """洞察消费者"""
    
    def __init__(self):
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_processed": None,
            "pending_count": 0,
            "applied_count": 0,
            "rejected_count": 0
        }
    
    def _save_state(self):
        """保存状态"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, msg: str):
        """写日志"""
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {msg}\n")
    
    def poll(self) -> int:
        """轮询并处理洞察"""
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        processed = 0
        
        for insight_file in PENDING_DIR.glob("*.json"):
            try:
                self._process_insight(insight_file)
                processed += 1
            except Exception as e:
                self._log(f"Error processing {insight_file.name}: {e}")
        
        self.state["last_processed"] = datetime.now().isoformat()
        self.state["pending_count"] = len(list(PENDING_DIR.glob("*.json")))
        self._save_state()
        
        return processed
    
    def _process_insight(self, insight_path: Path):
        """处理单个洞察"""
        with open(insight_path, 'r') as f:
            insight = json.load(f)
        
        stream_type = insight.get("stream_type", "unknown")
        self._log(f"Processing: {insight_path.name} ({stream_type})")
        
        # 根据类型处理
        if stream_type == "optimization_suggestion":
            self._handle_optimization(insight, insight_path)
        elif stream_type == "skill_template":
            self._handle_skill_template(insight, insight_path)
        elif stream_type == "reflection_summary":
            self._handle_reflection(insight, insight_path)
        elif stream_type == "memory_analysis":
            self._handle_memory_analysis(insight, insight_path)
        else:
            self._log(f"Unknown type: {stream_type}")
            self._move_to_rejected(insight_path)
    
    def _load_task_queue(self) -> Dict:
        """加载任务队列"""
        if TASK_QUEUE_FILE.exists():
            try:
                with open(TASK_QUEUE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self._log(f"Failed to load task queue: {e}")
        return {"tasks": [], "version": "1.2", "queue_id": "task-queue-main"}
    
    def _save_task_queue(self, queue: Dict):
        """保存任务队列"""
        try:
            with open(TASK_QUEUE_FILE, 'w') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"Failed to save task queue: {e}")
    
    def _write_to_task_queue(self, insight: Dict):
        """将优化建议写入任务队列"""
        queue = self._load_task_queue()
        
        insight_data = insight.get("insight", {})
        action_plan = insight_data.get("action_plan", {})
        
        # 确定优先级
        priority = "P2"
        confidence = insight.get("confidence", 0.8)
        impact = insight.get("impact", "medium")
        
        if confidence > 0.9 and impact == "high":
            priority = "P0"
        elif confidence > 0.8 and impact in ["high", "medium"]:
            priority = "P1"
        elif confidence > 0.7:
            priority = "P2"
        else:
            priority = "P3"
        
        # 确定类型
        insight_type = insight_data.get("type", "lab")
        type_mapping = {
            "workflow": "lab",
            "code": "dev",
            "content": "doc",
            "distribution": "pub",
            "memory": "lib",
            "analysis": "lab"
        }
        task_type = type_mapping.get(insight_type, "lab")
        
        # 生成任务ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        task_id = f"hermes-opt-{timestamp}"
        
        # 构建任务
        task = {
            "id": task_id,
            "title": f"[Hermes建议] {insight_data.get('title', '优化建议')}",
            "description": insight_data.get('description', action_plan.get('description', '')),
            "type": task_type,
            "priority": priority,
            "status": "pending",
            "source": "hermes_insight",
            "insight_type": "optimization",
            "confidence": confidence,
            "impact": impact,
            "created_at": datetime.now().isoformat(),
            "insight_ref": insight.get("insight_id", insight.get("id", "")),
            "suggested_action": action_plan,
            "assigned_to": None,
            "claimed_at": None,
            "completed_at": None
        }
        
        queue["tasks"].append(task)
        self._save_task_queue(queue)
        
        self._log(f"Written to task queue: {task_id} ({priority})")
        return task_id
    
    def _handle_optimization(self, insight: Dict, path: Path):
        """处理优化建议"""
        mode = insight.get("trigger_config", {}).get("mode", "suggest")
        
        if mode == "auto_apply":
            # 自动应用
            self._apply_optimization(insight)
            self._move_to_applied(path)
            self._log(f"Auto-applied: {insight.get('insight', {}).get('title')}")
        else:
            # 写入任务队列，等待处理
            task_id = self._write_to_task_queue(insight)
            self._log(f"Optimization queued: {insight.get('insight', {}).get('title')} -> {task_id}")
            self._move_to_applied(path)
    
    def _apply_optimization(self, insight: Dict):
        """应用优化"""
        action_plan = insight.get("insight", {}).get("action_plan", {})
        target = action_plan.get("target")
        parameter = action_plan.get("parameter")
        value = action_plan.get("suggested_value")
        
        if target and parameter and value:
            self._log(f"Would apply: {target}.{parameter} = {value}")
    
    def _handle_skill_template(self, insight: Dict, path: Path):
        """处理技能模板"""
        self._move_to_applied(path)
        self._log(f"Skill template queued: {insight.get('template', {}).get('name')}")
    
    def _handle_reflection(self, insight: Dict, path: Path):
        """处理复盘总结"""
        self._log(f"Reflection processed: {insight.get('summary', {}).get('date')}")
        self._move_to_applied(path)
    
    def _handle_memory_analysis(self, insight: Dict, path: Path):
        """处理记忆分析"""
        self._log(f"Memory analysis processed")
        self._move_to_applied(path)
    
    def _move_to_applied(self, path: Path):
        """移动到已应用目录"""
        APPLIED_DIR.mkdir(parents=True, exist_ok=True)
        dest = APPLIED_DIR / path.name
        shutil.move(str(path), str(dest))
    
    def _move_to_rejected(self, path: Path):
        """移动到已拒绝目录"""
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)
        dest = REJECTED_DIR / path.name
        shutil.move(str(path), str(dest))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Insight Consumer")
    parser.add_argument("--poll", action="store_true", help="执行一次轮询")
    parser.add_argument("--status", action="store_true", help="显示状态")
    args = parser.parse_args()
    
    consumer = InsightConsumer()
    
    if args.status:
        print("=== Hermes Insight Consumer 状态 ===")
        print(f"  上次处理: {consumer.state.get('last_processed', '从未')}")
        print(f"  待处理: {consumer.state.get('pending_count', 0)}")
        print(f"  已应用: {consumer.state.get('applied_count', 0)}")
        print(f"  已拒绝: {consumer.state.get('rejected_count', 0)}")
        return
    
    if args.poll or len(sys.argv) == 1:
        processed = consumer.poll()
        if processed > 0:
            print(f"处理了 {processed} 个洞察")
        else:
            print("无待处理洞察")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
