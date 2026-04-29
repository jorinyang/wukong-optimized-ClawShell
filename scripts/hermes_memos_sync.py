#!/usr/bin/env python3
"""
Hermes-MemOS Bridge - 基于MemOS的双向记忆同步
功能：
1. OpenClaw记忆 → MemOS (带hermes标签)
2. MemOS → Hermes洞察提取
3. 实时双向同步
"""

import os
import sys
import json
import requests
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# MemOS配置
MEMOS_BASE_URL = os.environ.get("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")
MEMOS_API_KEY = os.environ.get("MEMOS_API_KEY", "")

# 本地配置
OPENCLAW_DIR = Path.home() / ".openclaw"
STATE_FILE = OPENCLAW_DIR / "shared" / ".memos_sync_state.json"
LOG_FILE = OPENCLAW_DIR / "logs" / "memos_sync.log"

# 同步配置
SYNC_CONFIG = {
    "openclaw_user_id": "openclaw-hermes-bridge",
    "hermes_user_id": "hermes-insights",
    "sync_interval_hours": 24,
    "batch_size": 20
}


class MemOSBridge:
    """MemOS桥接器"""
    
    def __init__(self):
        self.state = self._load_state()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {MEMOS_API_KEY}"
        }
    
    def _load_state(self) -> Dict:
        """加载同步状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": None,
            "synced_memories": [],
            "hermes_insights": []
        }
    
    def _save_state(self):
        """保存状态"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, msg: str):
        """写日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {msg}\n")
    
    def _get_file_hash(self, content: str) -> str:
        """获取内容hash"""
        return hashlib.md5(content.encode()).hexdigest()
    
    # ========== MemOS API调用 ==========
    
    def _api_add_memory(self, content: str, user_id: str, tags: List[str] = None, 
                        conversation_id: str = "hermes-memos-bridge") -> Optional[str]:
        """添加记忆到MemOS"""
        data = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "messages": [{"role": "user", "content": content}]
        }
        
        try:
            res = requests.post(
                f"{MEMOS_BASE_URL}/add/message",
                headers=self.headers,
                json=data,
                timeout=10
            )
            result = res.json()
            
            if result.get("code") == 0:
                task_id = result.get("data", {}).get("task_id")
                self._log(f"Added memory: {task_id}")
                return task_id
            else:
                self._log(f"Add failed: {result.get('message')}")
                return None
        except Exception as e:
            self._log(f"API error: {e}")
            return None
    
    def _api_search_memory(self, query: str, user_id: str = None, 
                           limit: int = 10) -> Dict:
        """搜索MemOS记忆"""
        if user_id is None:
            user_id = SYNC_CONFIG["openclaw_user_id"]
        
        data = {
            "query": query,
            "user_id": user_id,
            "conversation_id": "hermes-memos-search",
            "limit": limit
        }
        
        try:
            res = requests.post(
                f"{MEMOS_BASE_URL}/search/memory",
                headers=self.headers,
                json=data,
                timeout=10
            )
            result = res.json()
            
            if result.get("code") == 0:
                return result.get("data", {})
            return {}
        except Exception as e:
            self._log(f"Search error: {e}")
            return {}
    
    def _api_get_memories(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取用户记忆列表"""
        data = {
            "user_id": user_id,
            "conversation_id": "hermes-memos-list",
            "limit": limit
        }
        
        try:
            res = requests.post(
                f"{MEMOS_BASE_URL}/get/memories",
                headers=self.headers,
                json=data,
                timeout=10
            )
            result = res.json()
            
            if result.get("code") == 0:
                return result.get("data", {}).get("memories", [])
            return []
        except Exception as e:
            self._log(f"Get memories error: {e}")
            return []
    
    # ========== 同步操作 ==========
    
    def sync_openclaw_to_memos(self, memory_content: str, tags: List[str] = None,
                               memory_type: str = "general") -> bool:
        """同步OpenClaw记忆到MemOS
        
        Args:
            memory_content: 记忆内容
            tags: 标签列表
            memory_type: 记忆类型 (execution/error/insight/strategy)
        
        Returns:
            bool: 是否成功
        """
        # 构建带标签的内容
        type_tags = [f"openclaw", memory_type]
        if tags:
            type_tags.extend(tags)
        
        content = f"[{memory_type.upper()}] {memory_content}"
        
        task_id = self._api_add_memory(
            content=content,
            user_id=SYNC_CONFIG["openclaw_user_id"],
            tags=type_tags,
            conversation_id=f"openclaw-{memory_type}"
        )
        
        if task_id:
            content_hash = self._get_file_hash(content)
            self.state["synced_memories"].append({
                "task_id": task_id,
                "hash": content_hash,
                "type": memory_type,
                "synced_at": datetime.now().isoformat()
            })
            self._save_state()
            return True
        
        return False
    
    def fetch_hermes_insights(self, since_hours: int = 24) -> List[Dict]:
        """获取Hermes生成的洞察
        
        Args:
            since_hours: 获取最近多少小时内的洞察
        
        Returns:
            List[Dict]: 洞察列表
        """
        # 从Hermes用户ID获取洞察
        insights = self._api_get_memories(
            user_id=SYNC_CONFIG["hermes_user_id"],
            limit=SYNC_CONFIG["batch_size"]
        )
        
        # 过滤出洞察类型
        hermes_insights = []
        for memory in insights:
            content = memory.get("content", "")
            if "insight" in content.lower() or "hermes" in content.lower():
                hermes_insights.append(memory)
                self.state["hermes_insights"].append({
                    "memory_id": memory.get("id"),
                    "content": content[:100],
                    "fetched_at": datetime.now().isoformat()
                })
        
        self._save_state()
        return hermes_insights
    
    def sync_strategy_memory(self, strategic_content: str) -> bool:
        """同步战略级记忆到MemOS
        
        Args:
            strategic_content: 战略记忆内容
        
        Returns:
            bool: 是否成功
        """
        return self.sync_openclaw_to_memos(
            memory_content=strategic_content,
            tags=["strategy", "important"],
            memory_type="strategy"
        )
    
    def sync_execution_record(self, task_type: str, status: str, 
                              duration_ms: int, summary: str) -> bool:
        """同步执行记录到MemOS
        
        Args:
            task_type: 任务类型
            status: 状态
            duration_ms: 耗时
            summary: 摘要
        
        Returns:
            bool: 是否成功
        """
        content = f"任务执行 | 类型:{task_type} | 状态:{status} | 耗时:{duration_ms}ms | {summary}"
        
        return self.sync_openclaw_to_memos(
            memory_content=content,
            tags=["execution", task_type],
            memory_type="execution"
        )
    
    def sync_error_pattern(self, category: str, severity: str,
                          pattern: str, resolution: str) -> bool:
        """同步错误模式到MemOS
        
        Args:
            category: 错误类别
            severity: 严重程度
            pattern: 错误模式
            resolution: 解决方法
        
        Returns:
            bool: 是否成功
        """
        content = f"错误模式 | 类别:{category} | 级别:{severity} | 模式:{pattern} | 解决:{resolution}"
        
        return self.sync_openclaw_to_memos(
            memory_content=content,
            tags=["error", category, severity],
            memory_type="error"
        )
    
    def get_recent_insights(self, limit: int = 5) -> List[Dict]:
        """获取最近的洞察
        
        Args:
            limit: 返回数量
        
        Returns:
            List[Dict]: 洞察列表
        """
        result = self._api_search_memory(
            query="insight hermes optimization",
            user_id=SYNC_CONFIG["hermes_user_id"],
            limit=limit
        )
        
        insights = []
        for pref in result.get("preference_detail_list", []):
            insights.append({
                "preference": pref.get("preference", ""),
                "source": pref.get("source", "")
            })
        
        return insights


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes-MemOS Bridge")
    parser.add_argument("--dry-run", action="store_true", help="仅显示状态")
    parser.add_argument("--sync-openclaw", metavar="CONTENT", help="同步OpenClaw记忆")
    parser.add_argument("--sync-execution", nargs=4, metavar=("TYPE", "STATUS", "DURATION", "SUMMARY"),
                       help="同步执行记录: TYPE STATUS DURATION_MS SUMMARY")
    parser.add_argument("--sync-error", nargs=4, metavar=("CATEGORY", "SEVERITY", "PATTERN", "RESOLUTION"),
                       help="同步错误模式: CATEGORY SEVERITY PATTERN RESOLUTION")
    parser.add_argument("--fetch-insights", action="store_true", help="获取Hermes洞察")
    parser.add_argument("--status", action="store_true", help="显示同步状态")
    
    args = parser.parse_args()
    bridge = MemOSBridge()
    
    if args.dry_run or args.status:
        print("=== Hermes-MemOS Bridge Status ===")
        print(f"上次同步: {bridge.state.get('last_sync', '从未')}")
        print(f"已同步记忆: {len(bridge.state.get('synced_memories', []))}")
        print(f"Hermes洞察: {len(bridge.state.get('hermes_insights', []))}")
        
        if args.dry_run:
            return
    
    if args.sync_openclaw:
        success = bridge.sync_openclaw_to_memos(args.sync_openclaw)
        print(f"同步{'成功' if success else '失败'}: {args.sync_openclaw[:50]}...")
    
    elif args.sync_execution:
        task_type, status, duration, summary = args.sync_execution
        success = bridge.sync_execution_record(
            task_type, status, int(duration), summary
        )
        print(f"执行记录同步{'成功' if success else '失败'}")
    
    elif args.sync_error:
        category, severity, pattern, resolution = args.sync_error
        success = bridge.sync_error_pattern(category, severity, pattern, resolution)
        print(f"错误模式同步{'成功' if success else '失败'}")
    
    elif args.fetch_insights:
        insights = bridge.fetch_hermes_insights()
        print(f"获取到 {len(insights)} 条洞察:")
        for i, insight in enumerate(insights[:5], 1):
            print(f"  {i}. {insight.get('content', '')[:80]}...")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
