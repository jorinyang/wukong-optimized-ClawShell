#!/usr/bin/env python3
"""
会话摘要生成器 - Phase 1
为已结束的会话生成对话摘要
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import argparse

OPENCLAW_DIR = Path(os.path.expanduser("~/.real"))
SESSION_DIR = OPENCLAW_DIR / "agents/main/sessions"
SUMMARY_OUTPUT_DIR = OPENCLAW_DIR / "inbox/session_summaries"
SUMMARY_LOG = OPENCLAW_DIR / "workspace/memory/session-summary-log.md"


def load_session_messages(session_id: str) -> list:
    """加载会话的所有消息"""
    session_file = SESSION_DIR / f"{session_id}.jsonl"
    if not session_file.exists():
        return []
    
    messages = []
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    # 查找 type="message" 的记录
                    if record.get('type') == 'message':
                        msg_data = record.get('message', {})
                        content = msg_data.get('content', '')
                        # content可能是列表或字符串
                        if isinstance(content, list):
                            text_parts = []
                            for part in content:
                                if isinstance(part, dict) and part.get('type') == 'text':
                                    text_parts.append(part.get('text', ''))
                            content = ' '.join(text_parts)
                        elif not isinstance(content, str):
                            content = str(content)
                        
                        messages.append({
                            'role': msg_data.get('role', 'unknown'),
                            'content': content[:500],
                            'time': record.get('timestamp', '')
                        })
                except:
                    continue
    except:
        pass
    
    return messages


def generate_summary(session_id: str, messages: list) -> Dict:
    """生成会话摘要"""
    if not messages:
        return {
            "session_id": session_id,
            "status": "no_messages",
            "generated_at": datetime.now().isoformat()
        }
    
    user_msgs = [m for m in messages if m['role'] == 'user']
    assistant_msgs = [m for m in messages if m['role'] == 'assistant']
    
    total_messages = len(messages)
    user_count = len(user_msgs)
    assistant_count = len(assistant_msgs)
    
    # 提取关键主题
    topics = []
    for msg in user_msgs[:3]:
        content = msg['content'][:100]
        if content:
            topics.append(content)
    
    first_time = messages[0].get('time', '未知') if messages else '未知'
    last_time = messages[-1].get('time', '未知') if messages else '未知'
    
    return {
        "session_id": session_id,
        "status": "completed",
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "total_messages": total_messages,
            "user_messages": user_count,
            "assistant_messages": assistant_count
        },
        "first_message_time": first_time,
        "last_message_time": last_time,
        "topics": topics,
        "message_count": total_messages
    }


def save_summary(summary: Dict):
    """保存摘要"""
    SUMMARY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    summary_file = SUMMARY_OUTPUT_DIR / f"{summary['session_id']}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 追加日志
    SUMMARY_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_entry = f"\n## {summary['generated_at'][:10]} | {summary['session_id'][:16]}...\n"
    log_entry += f"- 消息数: {summary.get('message_count', 0)}\n"
    log_entry += f"- 用户/助手: {summary.get('stats', {}).get('user_messages', 0)}/{summary.get('stats', {}).get('assistant_messages', 0)}\n"
    if summary.get('topics'):
        log_entry += f"- 主题: {'; '.join(summary['topics'][:2])}\n"
    
    with open(SUMMARY_LOG, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def process_session(session_id: str, dry: bool = False) -> Dict:
    """处理单个会话"""
    print(f"处理会话: {session_id[:20]}...")
    
    messages = load_session_messages(session_id)
    summary = generate_summary(session_id, messages)
    
    if not dry:
        save_summary(summary)
    
    if summary['status'] == 'completed':
        print(f"  ✅ 完成: {summary['message_count']}条消息 ({summary['stats']['user_messages']}用户/{summary['stats']['assistant_messages']}助手)")
    else:
        print(f"  ⚠️ 无消息可摘要")
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="会话摘要生成器")
    parser.add_argument("--session", type=str, help="指定会话ID")
    parser.add_argument("--all", action="store_true", help="处理所有会话")
    parser.add_argument("--dry", action="store_true", help="仅显示不保存")
    args = parser.parse_args()
    
    if args.session:
        summary = process_session(args.session, args.dry)
        if args.dry:
            print("\n=== 摘要预览 ===")
            print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.all:
        sessions = list(SESSION_DIR.glob("*.jsonl"))
        sessions = [s for s in sessions if not s.name.endswith('.lock')]
        print(f"找到 {len(sessions)} 个会话")
        for session_file in sessions:
            session_id = session_file.stem
            process_session(session_id, args.dry)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
