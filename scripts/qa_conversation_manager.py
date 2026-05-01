#!/usr/bin/env python3
"""
qa_conversation_manager.py - 智能问答对话管理器
功能：管理对话会话，支持上下文记忆和多轮对话
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QA_DIR = os.path.join(SHARED_DIR, "qa")
SESSIONS_DIR = os.path.join(QA_DIR, "sessions")

class QAConversationManager:
    """对话会话管理器"""
    
    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        os.makedirs(QA_DIR, exist_ok=True)
        
    def create_session(self, user_id: str = "default") -> str:
        """创建新的对话会话"""
        session_id = str(uuid.uuid4())[:8]
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "turns": [],
            "context": {},
            "status": "active"
        }
        self._save_session(session)
        return session_id
    
    def add_turn(self, session_id: str, role: str, content: str, metadata: dict = None) -> bool:
        """添加对话轮次"""
        session = self._load_session(session_id)
        if not session:
            return False
        
        turn = {
            "turn_id": len(session["turns"]) + 1,
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        session["turns"].append(turn)
        session["last_active"] = datetime.now().isoformat()
        self._save_session(session)
        return True
    
    def get_context(self, session_id: str, max_turns: int = 5) -> list:
        """获取最近N轮对话上下文"""
        session = self._load_session(session_id)
        if not session:
            return []
        
        turns = session.get("turns", [])
        # 返回最近的max_turns轮
        return turns[-max_turns:] if len(turns) > max_turns else turns
    
    def get_full_context(self, session_id: str) -> list:
        """获取完整对话上下文"""
        session = self._load_session(session_id)
        return session.get("turns", []) if session else []
    
    def update_context(self, session_id: str, key: str, value):
        """更新上下文数据"""
        session = self._load_session(session_id)
        if not session:
            return False
        session["context"][key] = value
        session["last_active"] = datetime.now().isoformat()
        self._save_session(session)
        return True
    
    def get_context_value(self, session_id: str, key: str, default=None):
        """获取上下文值"""
        session = self._load_session(session_id)
        if not session:
            return default
        return session.get("context", {}).get(key, default)
    
    def close_session(self, session_id: str):
        """关闭会话"""
        session = self._load_session(session_id)
        if session:
            session["status"] = "closed"
            session["closed_at"] = datetime.now().isoformat()
            self._save_session(session)
    
    def list_sessions(self, user_id: str = None, status: str = "active") -> list:
        """列出所有会话"""
        sessions = []
        if not os.path.exists(SESSIONS_DIR):
            return sessions
        
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SESSIONS_DIR, filename)
                with open(filepath, 'r') as f:
                    session = json.load(f)
                    if user_id and session.get("user_id") != user_id:
                        continue
                    if status and session.get("status") != status:
                        continue
                    sessions.append(session)
        
        return sorted(sessions, key=lambda x: x.get("last_active", ""), reverse=True)
    
    def delete_session(self, session_id: str):
        """删除会话"""
        filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
    
    def _session_path(self, session_id: str) -> str:
        return os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    def _load_session(self, session_id: str) -> dict:
        filepath = self._session_path(session_id)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _save_session(self, session: dict):
        filepath = self._session_path(session["session_id"])
        with open(filepath, 'w') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 测试对话管理器
    manager = QAConversationManager()
    
    # 创建会话
    session_id = manager.create_session("test_user")
    print(f"创建会话: {session_id}")
    
    # 添加对话
    manager.add_turn(session_id, "user", "我想了解一下ClawShell系统")
    manager.add_turn(session_id, "assistant", "ClawShell是一个适用于类OpenClaw架构的增强型外骨骼功能插件...")
    manager.add_turn(session_id, "user", "它有哪些核心能力？")
    
    # 获取上下文
    context = manager.get_context(session_id, max_turns=3)
    print(f"\n最近3轮对话:")
    for turn in context:
        print(f"  [{turn['role']}] {turn['content'][:50]}...")
    
    # 更新上下文
    manager.update_context(session_id, "topic", "ClawShell系统介绍")
    topic = manager.get_context_value(session_id, "topic")
    print(f"\n上下文topic: {topic}")
    
    # 列出会话
    sessions = manager.list_sessions()
    print(f"\n当前会话数: {len(sessions)}")
    
    print("\n✅ 对话管理器测试通过")
