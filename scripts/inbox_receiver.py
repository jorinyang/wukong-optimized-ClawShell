#!/usr/bin/env python3
"""
OpenClaw 消息接收器
用于接收钉钉/微信消息并写入队列
零侵入设计 - 不修改OpenClaw核心
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

BASE_DIR = Path(os.path.expanduser("~/.openclaw"))
INBOX_DIR = BASE_DIR / "inbox"
PENDING_DIR = INBOX_DIR / "pending"

# 优先级映射规则
PRIORITY_RULES = {
    "P0": ["紧急", "立即", "马上", " urgent", " asap", "critical"],
    "P1": ["重要", "尽快", "优先", "priority", "important"],
    "P2": []  # 默认优先级
}


def detect_priority(content: str) -> str:
    """根据内容自动检测优先级"""
    content_lower = content.lower()
    
    for priority, keywords in PRIORITY_RULES.items():
        if any(kw.lower() in content_lower for kw in keywords):
            return priority
    
    return "P2"


def create_task(message_data: Dict[str, Any]) -> str:
    """
    创建消息任务
    
    Args:
        message_data: 消息数据字典，包含:
            - content: 消息内容
            - source: 消息来源 (dingtalk/wechat/etc)
            - sender_id: 发送者ID
            - sender_name: 发送者名称
            - message_id: 原始消息ID
            - priority: 优先级 (可选，自动检测)
    
    Returns:
        任务ID
    """
    # 确保目录存在
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成任务ID
    task_id = hashlib.md5(
        f"{message_data.get('message_id', '')}:{message_data['content']}:{time.time()}".encode()
    ).hexdigest()[:16]
    
    # 检测优先级
    priority = message_data.get('priority') or detect_priority(message_data['content'])
    
    # 构建任务数据
    task = {
        "id": task_id,
        "message_id": message_data.get('message_id', ''),
        "content": message_data['content'],
        "priority": priority,
        "source": message_data.get('source', 'unknown'),
        "sender_id": message_data.get('sender_id', ''),
        "sender_name": message_data.get('sender_name', ''),
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "retry_count": 0,
        "subtasks": [],
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None
    }
    
    # 保存任务文件
    task_file = PENDING_DIR / f"{task_id}.json"
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    
    return task_id


def receive_message(
    content: str,
    source: str = "dingtalk",
    sender_id: str = "",
    sender_name: str = "",
    message_id: str = "",
    priority: Optional[str] = None
) -> str:
    """
    接收消息并创建任务
    
    这是主入口函数，可以被OpenClaw调用
    """
    message_data = {
        "content": content,
        "source": source,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "message_id": message_id,
        "priority": priority
    }
    
    task_id = create_task(message_data)
    
    # 返回确认信息
    return json.dumps({
        "status": "queued",
        "task_id": task_id,
        "priority": priority or detect_priority(content),
        "message": "消息已加入队列，将尽快处理"
    }, ensure_ascii=False)


def main():
    """CLI入口"""
    parser = argparse.ArgumentParser(description="OpenClaw 消息接收器")
    parser.add_argument("content", help="消息内容")
    parser.add_argument("--source", "-s", default="dingtalk", 
                       help="消息来源 (dingtalk/wechat)")
    parser.add_argument("--sender-id", default="", help="发送者ID")
    parser.add_argument("--sender-name", "-n", default="", help="发送者名称")
    parser.add_argument("--message-id", "-m", default="", help="消息ID")
    parser.add_argument("--priority", "-p", choices=["P0", "P1", "P2"],
                       help="优先级 (未指定则自动检测)")
    
    args = parser.parse_args()
    
    result = receive_message(
        content=args.content,
        source=args.source,
        sender_id=args.sender_id,
        sender_name=args.sender_name,
        message_id=args.message_id,
        priority=args.priority
    )
    
    print(result)


if __name__ == "__main__":
    main()
