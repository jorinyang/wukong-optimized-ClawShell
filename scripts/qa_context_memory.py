#!/usr/bin/env python3
"""
qa_context_memory.py - 智能问答上下文记忆
功能：与MemOS集成，实现持久化上下文记忆
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QA_DIR = os.path.join(SHARED_DIR, "qa")
MEMORY_DIR = os.path.join(QA_DIR, "memory")

# MemOS配置
MEMOS_API_KEY = os.getenv("MEMOS_API_KEY", "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ")
MEMOS_BASE_URL = os.getenv("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")

class QAContextMemory:
    """上下文记忆管理器"""
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.memos_enabled = self._check_memos()
        
    def _check_memos(self) -> bool:
        """检查MemOS是否可用"""
        if not MEMOS_API_KEY or MEMOS_API_KEY == "your-memos-api-key":
            return False
        try:
            response = requests.get(
                f"{MEMOS_BASE_URL}/memos",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}"},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def save_context(self, session_id: str, context: dict, user_id: str = "default") -> bool:
        """保存上下文到本地和MemOS"""
        # 1. 保存到本地
        self._save_local(session_id, context)
        
        # 2. 保存到MemOS
        if self.memos_enabled:
            return self._save_to_memos(session_id, context, user_id)
        return True
    
    def load_context(self, session_id: str) -> dict:
        """加载上下文"""
        # 1. 优先从MemOS加载
        if self.memos_enabled:
            memos_context = self._load_from_memos(session_id)
            if memos_context:
                # 同时更新本地缓存
                self._save_local(session_id, memos_context)
                return memos_context
        
        # 2. 从本地加载
        return self._load_local(session_id)
    
    def update_context(self, session_id: str, new_turn: dict, user_id: str = "default") -> bool:
        """增量更新上下文"""
        # 1. 加载现有上下文
        context = self.load_context(session_id)
        
        # 2. 添加新轮次
        if "turns" not in context:
            context["turns"] = []
        context["turns"].append(new_turn)
        context["last_updated"] = datetime.now().isoformat()
        
        # 3. 保存更新
        return self.save_context(session_id, context, user_id)
    
    def get_recent_memory(self, user_id: str = "default", hours: int = 24) -> list:
        """获取最近N小时的记忆"""
        if not self.memos_enabled:
            return []
        
        try:
            # 计算时间范围
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            response = requests.get(
                f"{MEMOS_BASE_URL}/memos",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}"},
                params={"creator": user_id, "limit": 50},
                timeout=10
            )
            
            if response.status_code == 200:
                memos = response.json().get("memos", [])
                recent = []
                for memo in memos:
                    created = memo.get("created_ts", 0)
                    if created > (datetime.now() - timedelta(hours=hours)).timestamp():
                        # 检查是否与QA相关
                        content = memo.get("content", "")
                        if any(kw in content for kw in ["QA:", "问答:", "question:", "answer:"]):
                            recent.append(memo)
                return recent
        except Exception as e:
            print(f"加载记忆失败: {e}")
        return []
    
    def search_related_context(self, query: str, user_id: str = "default") -> list:
        """搜索相关上下文"""
        if not self.memos_enabled:
            return []
        
        try:
            response = requests.get(
                f"{MEMOS_BASE_URL}/memos",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}"},
                params={"creator": user_id, "search": query, "limit": 10},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get("memos", [])
        except:
            pass
        return []
    
    def clear_old_contexts(self, days: int = 30) -> int:
        """清理N天前的本地缓存"""
        if not os.path.exists(MEMORY_DIR):
            return 0
        
        cutoff = datetime.now().timestamp() - (days * 86400)
        removed = 0
        
        for filename in os.listdir(MEMORY_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(MEMORY_DIR, filename)
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    os.remove(filepath)
                    removed += 1
        
        return removed
    
    def _save_local(self, session_id: str, context: dict):
        """保存到本地"""
        filepath = os.path.join(MEMORY_DIR, f"{session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
    
    def _load_local(self, session_id: str) -> dict:
        """从本地加载"""
        filepath = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if not os.path.exists(filepath):
            return {"session_id": session_id, "turns": [], "context": {}}
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _save_to_memos(self, session_id: str, context: dict, user_id: str) -> bool:
        """保存到MemOS"""
        try:
            # 构建记忆内容
            content = f"[QA Session {session_id}]\n"
            content += f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            turns = context.get("turns", [])
            for turn in turns[-10:]:  # 只保存最近10轮
                role = turn.get("role", "unknown")
                text = turn.get("content", "")[:200]
                content += f"- [{role}] {text}\n"
            
            # 保存到MemOS
            response = requests.post(
                f"{MEMOS_BASE_URL}/memos",
                headers={
                    "Authorization": f"Bearer {MEMOS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "content": content,
                    "visibility": "PRIVATE",
                    "tags": ["QA", "conversation", f"session-{session_id}"]
                },
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"保存到MemOS失败: {e}")
            return False
    
    def _load_from_memos(self, session_id: str) -> dict:
        """从MemOS加载"""
        try:
            response = requests.get(
                f"{MEMOS_BASE_URL}/memos",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}"},
                params={"tag": f"session-{session_id}", "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                memos = response.json().get("memos", [])
                if memos:
                    # 解析最新的记忆
                    latest = memos[0]
                    return self._parse_memo_context(latest)
        except:
            pass
        return None
    
    def _parse_memo_context(self, memo: dict) -> dict:
        """解析Memo为上下文格式"""
        content = memo.get("content", "")
        context = {
            "session_id": "",
            "turns": [],
            "context": {}
        }
        
        # 简单解析
        lines = content.split("\n")
        for line in lines:
            if line.startswith("[QA Session"):
                context["session_id"] = line.split()[2]
            elif line.startswith("- ["):
                # 解析对话轮次
                parts = line[2:].split("]", 1)
                if len(parts) == 2:
                    role = parts[0].strip()
                    content_text = parts[1].strip()
                    context["turns"].append({
                        "role": role,
                        "content": content_text
                    })
        
        return context


if __name__ == "__main__":
    # 测试上下文记忆
    memory = QAContextMemory()
    
    print(f"MemOS可用: {memory.memos_enabled}")
    
    # 测试保存
    test_context = {
        "session_id": "test123",
        "turns": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮你的？"},
            {"role": "user", "content": "ClawShell是什么？"},
            {"role": "assistant", "content": "ClawShell是一个增强型外骨骼功能插件..."}
        ],
        "context": {"topic": "ClawShell介绍"}
    }
    
    if memory.save_context("test123", test_context):
        print("✅ 上下文保存成功")
    else:
        print("⚠️ 上下文保存失败（MemOS可能不可用）")
    
    # 测试加载
    loaded = memory.load_context("test123")
    print(f"加载上下文: {len(loaded.get('turns', []))} 轮对话")
    
    print("\n✅ 上下文记忆测试完成")
