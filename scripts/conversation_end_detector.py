#!/usr/bin/env python3
"""
会话结束判断器 - Phase 1
用于判断会话是否结束，触发对话摘要生成
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, List
import argparse

OPENCLAW_DIR = Path(os.path.expanduser("~/.openclaw"))
CONFIG_FILE = OPENCLAW_DIR / ".conversation_end_config.json"
SESSION_DIR = OPENCLAW_DIR / "agents/main/sessions"
LAST_ACTIVITY_FILE = OPENCLAW_DIR / ".session_last_activity.json"


def load_config() -> Dict:
    default = {
        "timeout_minutes": 30,
        "check_interval": 5,
        "before_cleanup_minutes": 10,
        "cleanup_hour": 6,
        "cleanup_minute": 1,
        "new_session_triggers_close": True,
        "preserve_main_session": True,
        "main_session_keywords": ["main", "primary", "principal"]
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**default, **json.load(f)}
        except:
            pass
    return default


def load_last_activity() -> Dict[str, str]:
    if LAST_ACTIVITY_FILE.exists():
        try:
            with open(LAST_ACTIVITY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_last_activity(data: Dict):
    with open(LAST_ACTIVITY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_sessions(config: Dict) -> List[str]:
    sessions = []
    keywords = config.get("main_session_keywords", [])
    if SESSION_DIR.exists():
        for f in SESSION_DIR.glob("*.jsonl"):
            if f.suffix == '.jsonl' and not f.name.endswith('.lock'):
                session_id = f.stem
                if not any(kw in session_id.lower() for kw in keywords):
                    sessions.append(session_id)
    return sessions


def check_timeout(session_id: str, config: Dict, last_activity: Dict) -> Tuple[bool, str]:
    last_time = None
    if session_id in last_activity:
        last_time = datetime.fromisoformat(last_activity[session_id])
    else:
        session_file = SESSION_DIR / f"{session_id}.jsonl"
        if session_file.exists():
            last_time = datetime.fromtimestamp(session_file.stat().st_mtime)
    
    if not last_time:
        return False, "no_activity_record"
    
    elapsed = datetime.now() - last_time
    timeout_min = config.get("timeout_minutes", 30)
    if elapsed >= timedelta(minutes=timeout_min):
        return True, f"timeout_{int(elapsed.total_seconds()//60)}min"
    return False, ""


def is_main_session(session_id: str, config: Dict) -> bool:
    if not config.get("preserve_main_session", True):
        return False
    keywords = config.get("main_session_keywords", [])
    return any(kw in session_id.lower() for kw in keywords)


def check_pre_cleanup(config: Dict) -> bool:
    now = datetime.now()
    cleanup_hour = config.get("cleanup_hour", 6)
    cleanup_min = config.get("cleanup_minute", 1)
    buffer_min = config.get("before_cleanup_minutes", 10)
    
    cleanup_time = now.replace(hour=cleanup_hour, minute=cleanup_min, second=0, microsecond=0)
    before_cleanup = cleanup_time - timedelta(minutes=buffer_min)
    after_cleanup = cleanup_time + timedelta(minutes=10)
    
    return before_cleanup <= now <= after_cleanup


def detect_ended_sessions(config: Dict, last_activity: Dict, current_session: str = None) -> Dict[str, Dict]:
    results = {}
    all_sessions = get_all_sessions(config)
    
    for session_id in all_sessions:
        if is_main_session(session_id, config):
            continue
        
        timed_out, reason = check_timeout(session_id, config, last_activity)
        if timed_out:
            results[session_id] = {"reason": reason, "trigger": "timeout"}
    
    if current_session and config.get("new_session_triggers_close"):
        for session_id in all_sessions:
            if session_id == current_session or session_id in results:
                continue
            if is_main_session(session_id, config):
                continue
            if session_id in last_activity:
                last_time = datetime.fromisoformat(last_activity[session_id])
                elapsed = datetime.now() - last_time
                if elapsed >= timedelta(minutes=10):
                    results[session_id] = {"reason": "new_session_started", "trigger": "new_session"}
    
    if check_pre_cleanup(config):
        for session_id in all_sessions:
            if is_main_session(session_id, config) or session_id in results:
                continue
            results[session_id] = {"reason": "pre_cleanup_trigger", "trigger": "pre_cleanup"}
    
    return results


def main():
    parser = argparse.ArgumentParser(description="会话结束判断器")
    parser.add_argument("--check", action="store_true", help="执行一次检查")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅记录错误")
    parser.add_argument("--status", action="store_true", help="显示所有会话状态")
    parser.add_argument("--update", type=str, help="更新指定会话的活动时间")
    parser.add_argument("--config", action="store_true", help="显示当前配置")
    args = parser.parse_args()
    
    # 静默模式：重定向stdout到/dev/null
    import sys
    if args.quiet:
        sys.stdout = open('/dev/null', 'w')
    
    config = load_config()
    last_activity = load_last_activity()
    
    if args.config:
        print("=== 当前配置 ===")
        for k, v in config.items():
            print(f"  {k}: {v}")
        return
    
    if args.update:
        last_activity[args.update] = datetime.now().isoformat()
        save_last_activity(last_activity)
        print(f"已更新会话 {args.update} 的活动时间")
        return
    
    if args.status:
        print("=== 会话状态 ===")
        all_sessions = get_all_sessions(config)
        print(f"共 {len(all_sessions)} 个会话")
        for session_id in all_sessions[:10]:
            timed_out, reason = check_timeout(session_id, config, last_activity)
            status = "⏰ 超时" if timed_out else "✅ 活跃"
            last_time = last_activity.get(session_id, "未知")
            if last_time != "未知":
                last_time = datetime.fromisoformat(last_time).strftime("%H:%M:%S")
            print(f"  {session_id[:20]}... | 最后: {last_time} | {status}")
        if len(all_sessions) > 10:
            print(f"  ... 还有 {len(all_sessions)-10} 个会话")
        return
    
    if args.check:
        # --check 模式默认静默，仅在有重要事件时输出
        ended = detect_ended_sessions(config, last_activity)
        
        # 有会话需要结束时才输出
        if ended:
            print(f"[会话检测] 发现 {len(ended)} 个应结束的会话: {', '.join(list(ended.keys())[:3])}", file=sys.stderr)
        
        # 接近清理时间时警告
        if check_pre_cleanup(config):
            print("[会话检测] 接近清理时间(06:01)，请准备生成摘要", file=sys.stderr)
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()
