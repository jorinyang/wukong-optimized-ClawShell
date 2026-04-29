#!/usr/bin/env python3
"""
Hermes Execution Processor - Hermes端执行记录处理器
功能：
1. 消费OpenClaw执行记录
2. 分析执行模式
3. 生成洞察
4. 技能自动封装

注意：此脚本需要在Hermes环境中运行
如在OpenClaw端测试，请使用 --dry-run 模式
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 配置
HERMES_DIR = Path.home() / ".hermes"
OPENCLAW_INBOX = HERMES_DIR / "inbox" / "openclaw_feed"
INSIGHTS_DIR = HERMES_DIR / "insights" / "pending"
STATE_FILE = HERMES_DIR / ".execution_processor_state.json"

# MemOS配置（用于推送洞察）
MEMOS_BASE_URL = os.environ.get("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")
MEMOS_API_KEY = os.environ.get("MEMOS_API_KEY", "")


class ExecutionRecordProcessor:
    """执行记录处理器"""
    
    def __init__(self):
        self.state = self._load_state()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {MEMOS_API_KEY}"
        } if MEMOS_API_KEY else {}
    
    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_processed": None,
            "processed_hashes": [],
            "patterns_detected": [],
            "insights_generated": 0
        }
    
    def _save_state(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")
    
    def _get_file_hash(self, path: Path) -> str:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def poll_records(self, dry_run: bool = False) -> int:
        """轮询执行记录"""
        if not OPENCLAW_INBOX.exists():
            self._log(f"Inbox不存在: {OPENCLAW_INBOX}")
            return 0
        
        processed = 0
        
        for record_file in sorted(OPENCLAW_INBOX.glob("*.json")):
            if self._is_already_processed(record_file):
                continue
            
            if dry_run:
                self._log(f"待处理: {record_file.name}")
                processed += 1
                continue
            
            try:
                self._process_record(record_file)
                processed += 1
            except Exception as e:
                self._log(f"Error: {record_file.name}: {e}")
        
        if not dry_run:
            self.state["last_processed"] = datetime.now().isoformat()
            self._save_state()
        
        return processed
    
    def _is_already_processed(self, path: Path) -> bool:
        file_hash = self._get_file_hash(path)
        return file_hash in self.state.get("processed_hashes", [])
    
    def _mark_processed(self, path: Path):
        file_hash = self._get_file_hash(path)
        if "processed_hashes" not in self.state:
            self.state["processed_hashes"] = []
        self.state["processed_hashes"].append(file_hash)
        # 只保留最近100个hash
        self.state["processed_hashes"] = self.state["processed_hashes"][-100:]
    
    def _process_record(self, path: Path):
        """处理执行记录"""
        with open(path, 'r') as f:
            record = json.load(f)
        
        self._log(f"处理: {path.name}")
        
        # 分析模式
        pattern = self._analyze_pattern(record)
        
        # 生成洞察
        if pattern:
            self._generate_insight(pattern, record)
        
        # 检测技能模式
        skill_pattern = self._detect_skill_pattern(record)
        if skill_pattern:
            self._generate_skill_template(skill_pattern, record)
        
        # 标记已处理
        self._mark_processed(path)
        
        # 移动到已处理目录
        processed_dir = OPENCLAW_INBOX / "processed"
        processed_dir.mkdir(exist_ok=True)
        
        # 移动原文件
        import shutil
        dest = processed_dir / path.name
        shutil.move(str(path), str(dest))
    
    def _analyze_pattern(self, record: Dict) -> Optional[Dict]:
        """分析执行模式"""
        execution = record.get("execution", {})
        status = execution.get("status")
        task_type = execution.get("task_type")
        
        # 检测错误模式
        if status == "failed":
            return {
                "type": "error_pattern",
                "task_type": task_type,
                "severity": "high",
                "pattern": f"{task_type}_failed",
                "recommendation": f"建议优化{task_type}错误处理"
            }
        
        # 检测慢执行模式
        duration_ms = execution.get("duration_ms", 0)
        if duration_ms > 10000:  # 超过10秒
            return {
                "type": "slow_execution",
                "task_type": task_type,
                "duration_ms": duration_ms,
                "recommendation": f"建议优化{task_type}性能"
            }
        
        # 检测高频任务
        return None
    
    def _detect_skill_pattern(self, record: Dict) -> Optional[Dict]:
        """检测技能模式"""
        # 检测重复执行的任务序列
        # 这里简化处理，实际需要更复杂的模式识别
        
        execution = record.get("execution", {})
        task_type = execution.get("task_type")
        tools_used = execution.get("tools_used", [])
        
        # 如果使用了多个工具，可能是技能候选
        if len(tools_used) >= 3:
            return {
                "type": "multi_tool_sequence",
                "task_type": task_type,
                "tools": tools_used,
                "recommendation": f"检测到{len(tools_used)}个工具的序列执行"
            }
        
        return None
    
    def _generate_insight(self, pattern: Dict, record: Dict):
        """生成洞察"""
        insight = {
            "stream_type": "optimization_suggestion",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "source": {
                "agent": "hermes",
                "generation_mode": "execution_analysis"
            },
            "insight": {
                "type": pattern["type"],
                "category": "execution_optimization",
                "priority": "P2",
                "title": pattern.get("recommendation", "执行优化建议"),
                "summary": f"基于{record.get('execution', {}).get('task_type')}分析",
                "reasoning": f"检测到{pattern['type']}: {pattern.get('pattern', '')}",
                "action_plan": {
                    "target": "system_monitor.sh",
                    "parameter": "STUCK_THRESHOLD_MINUTES",
                    "suggested_value": 15,
                    "rollback_value": 30
                }
            },
            "trigger_config": {
                "mode": "suggest",
                "requires_approval": True
            }
        }
        
        # 保存洞察
        INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        insight_id = f"insight-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(INSIGHTS_DIR / insight_id, 'w') as f:
            json.dump(insight, f, indent=2)
        
        self._log(f"生成洞察: {insight_id}")
        self.state["insights_generated"] = self.state.get("insights_generated", 0) + 1
        
        # 同时推送到MemOS（如果配置了）
        if MEMOS_API_KEY:
            self._push_to_memos(insight)
    
    def _generate_skill_template(self, pattern: Dict, record: Dict):
        """生成技能模板"""
        if pattern["type"] != "multi_tool_sequence":
            return
        
        skill_template = {
            "stream_type": "skill_template",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "source": {
                "agent": "hermes",
                "generation_mode": "skill_detection"
            },
            "template": {
                "name": f"{pattern['task_type']}-automation",
                "description": f"自动化执行{pattern['task_type']}任务序列",
                "trigger_conditions": [
                    f"task_type:{pattern['task_type']}",
                    "manual"
                ],
                "actions": [
                    {"type": tool} for tool in pattern.get("tools", [])
                ],
                "output_format": "auto",
                "priority": "P3"
            }
        }
        
        # 保存技能模板到insights目录
        skill_id = f"skill-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(INSIGHTS_DIR / skill_id, 'w') as f:
            json.dump(skill_template, f, indent=2)
        
        self._log(f"生成技能模板: {skill_id}")
    
    def _push_to_memos(self, insight: Dict):
        """推送洞察到MemOS"""
        if not MEMOS_API_KEY:
            return
        
        try:
            data = {
                "user_id": "hermes-insights",
                "conversation_id": "hermes-insight-push",
                "messages": [{
                    "role": "user",
                    "content": json.dumps(insight, ensure_ascii=False)
                }]
            }
            
            res = requests.post(
                f"{MEMOS_BASE_URL}/add/message",
                headers=self.headers,
                json=data,
                timeout=10
            )
            
            if res.json().get("code") == 0:
                self._log("洞察已推送到MemOS")
        except Exception as e:
            self._log(f"MemOS推送失败: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Execution Processor")
    parser.add_argument("--dry-run", action="store_true", help="仅显示待处理记录")
    parser.add_argument("--status", action="store_true", help="显示处理状态")
    args = parser.parse_args()
    
    processor = ExecutionRecordProcessor()
    
    if args.status:
        print("=== Hermes Execution Processor Status ===")
        print(f"上次处理: {processor.state.get('last_processed', '从未')}")
        print(f"已处理记录: {len(processor.state.get('processed_hashes', []))}")
        print(f"生成洞察: {processor.state.get('insights_generated', 0)}")
        return
    
    processed = processor.poll_records(dry_run=args.dry_run)
    print(f"处理完成: {processed}条记录")


if __name__ == "__main__":
    main()
