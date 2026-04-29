#!/usr/bin/env python3
"""
ClawShell MemOS 同步模块
版本: v0.2.2-C
功能: MemOS 双向同步、知识推送/拉取
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

# ============ 配置 ============

MEMOS_CONFIG_PATH = Path("~/.openclaw/.memos_config.json").expanduser()
MEMOS_STATE_PATH = Path("~/.openclaw/.memos_sync_state.json").expanduser()

# MemOS 默认配置
DEFAULT_MEMOS_API_KEY = "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ"
DEFAULT_MEMOS_BASE_URL = "https://memos.memtensor.cn/api/openmem/v1"


# ============ 数据结构 ============

@dataclass
class Knowledge:
    """知识条目"""
    id: Optional[str]
    content: str
    tags: List[str] = field(default_factory=list)
    visibility: str = "private"  # public, private
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags,
            "visibility": self.visibility,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metadata": self.metadata
        }


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    pushed: int = 0
    pulled: int = 0
    errors: List[str] = field(default_factory=list)
    last_sync: float = field(default_factory=time.time)


# ============ MemOS 客户端 ============

class MemOSSync:
    """MemOS 同步"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or DEFAULT_MEMOS_API_KEY
        self.base_url = (base_url or DEFAULT_MEMOS_BASE_URL).rstrip("/")
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if MEMOS_STATE_PATH.exists():
            try:
                with open(MEMOS_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": 0,
            "last_push_id": None,
            "last_pull_id": None,
            "sync_count": 0
        }
    
    def _save_state(self):
        """保存状态"""
        with open(MEMOS_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        
        if data:
            req.data = json.dumps(data).encode("utf-8")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8")
                if content:
                    return json.loads(content)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise MemOSError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise MemOSError(f"Connection failed: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self._make_request("GET", "/health")
            return response.get("healthy", False)
        except:
            return False
    
    # ---- 知识操作 ----
    
    def create_knowledge(self, knowledge: Knowledge) -> Optional[str]:
        """创建知识"""
        try:
            data = {
                "content": knowledge.content,
                "visibility": knowledge.visibility,
                "tags": knowledge.tags
            }
            
            response = self._make_request("POST", "/memos", data)
            
            if response.get("id"):
                return str(response["id"])
            return None
        except MemOSError as e:
            print(f"Create knowledge failed: {e}")
            return None
    
    def get_knowledge(self, knowledge_id: str) -> Optional[Knowledge]:
        """获取知识"""
        try:
            response = self._make_request("GET", f"/memos/{knowledge_id}")
            
            if response.get("id"):
                return Knowledge(
                    id=str(response["id"]),
                    content=response.get("content", ""),
                    tags=response.get("tags", []),
                    visibility=response.get("visibility", "private"),
                    created_at=response.get("createdAt"),
                    updated_at=response.get("updatedAt")
                )
            return None
        except MemOSError:
            return None
    
    def list_knowledge(self, limit: int = 50, offset: int = 0) -> List[Knowledge]:
        """列出知识"""
        try:
            response = self._make_request("GET", f"/memos?limit={limit}&offset={offset}")
            
            memos = response.get("data", []) if isinstance(response, dict) else response
            
            result = []
            for memo in memos:
                result.append(Knowledge(
                    id=str(memo.get("id", "")),
                    content=memo.get("content", ""),
                    tags=memo.get("tags", []),
                    visibility=memo.get("visibility", "private"),
                    created_at=memo.get("createdAt"),
                    updated_at=memo.get("updatedAt")
                ))
            
            return result
        except MemOSError as e:
            print(f"List knowledge failed: {e}")
            return []
    
    def update_knowledge(self, knowledge: Knowledge) -> bool:
        """更新知识"""
        if not knowledge.id:
            return False
        
        try:
            data = {
                "content": knowledge.content,
                "visibility": knowledge.visibility,
                "tags": knowledge.tags
            }
            
            self._make_request("PATCH", f"/memos/{knowledge.id}", data)
            return True
        except MemOSError as e:
            print(f"Update knowledge failed: {e}")
            return False
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识"""
        try:
            self._make_request("DELETE", f"/memos/{knowledge_id}")
            return True
        except MemOSError:
            return False
    
    # ---- 同步操作 ----
    
    def push_to_memos(self, knowledge_list: List[Knowledge]) -> int:
        """推送到 MemOS"""
        pushed = 0
        
        for knowledge in knowledge_list:
            if knowledge.id:
                # 更新
                if self.update_knowledge(knowledge):
                    pushed += 1
            else:
                # 创建
                new_id = self.create_knowledge(knowledge)
                if new_id:
                    pushed += 1
        
        if pushed > 0:
            self.state["last_push_id"] = knowledge_list[-1].id
            self._save_state()
        
        return pushed
    
    def pull_from_memos(self, since_id: Optional[str] = None, limit: int = 50) -> List[Knowledge]:
        """从 MemOS 拉取"""
        try:
            if since_id:
                # 拉取指定ID之后的
                all_memos = self.list_knowledge(limit=100)
                result = []
                found = since_id is None
                
                for memo in all_memos:
                    if not found and memo.id == since_id:
                        found = True
                        continue
                    if found:
                        result.append(memo)
                
                return result[:limit]
            else:
                return self.list_knowledge(limit=limit)
        except:
            return []
    
    def bidirectional_sync(self, local_knowledge: List[Knowledge]) -> SyncResult:
        """
        双向同步
        
        1. 推送本地新增/更新的知识到 MemOS
        2. 从 MemOS 拉取新知识
        """
        result = SyncResult(success=True)
        
        try:
            # 1. 推送本地知识
            pushed = self.push_to_memos(local_knowledge)
            result.pushed = pushed
            
            # 2. 拉取 MemOS 知识
            since_id = self.state.get("last_pull_id")
            pulled = self.pull_from_memos(since_id=since_id)
            result.pulled = len(pulled)
            
            # 更新状态
            if pulled:
                self.state["last_pull_id"] = pulled[-1].id
            
            self.state["last_sync"] = time.time()
            self.state["sync_count"] += 1
            self._save_state()
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            "last_sync": self.state.get("last_sync", 0),
            "last_push_id": self.state.get("last_push_id"),
            "last_pull_id": self.state.get("last_pull_id"),
            "sync_count": self.state.get("sync_count", 0),
            "api_key_set": bool(self.api_key),
            "base_url": self.base_url
        }


class MemOSError(Exception):
    """MemOS 错误"""
    pass


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell MemOS同步")
    parser.add_argument("--health", action="store_true", help="健康检查")
    parser.add_argument("--list", action="store_true", help="列出知识")
    parser.add_argument("--push", metavar="CONTENT", help="推送知识")
    parser.add_argument("--pull", action="store_true", help="拉取知识")
    parser.add_argument("--status", action="store_true", help="同步状态")
    args = parser.parse_args()
    
    memos = MemOSSync()
    
    if args.health:
        health = memos.health_check()
        print(f"{'✅' if health else '❌'} MemOS {'正常' if health else '异常'}")
    
    elif args.list:
        knowledge_list = memos.list_knowledge(limit=20)
        print(f"知识列表 ({len(knowledge_list)} 条):")
        for k in knowledge_list:
            tags = f"[{', '.join(k.tags)}]" if k.tags else ""
            print(f"  [{k.id}] {k.content[:50]}... {tags}")
    
    elif args.push:
        k = Knowledge(content=args.push, tags=["clawshell"])
        k.id = memos.create_knowledge(k)
        print(f"✅ 知识已推送: {k.id}")
    
    elif args.pull:
        knowledge_list = memos.pull_from_memos()
        print(f"拉取 {len(knowledge_list)} 条知识:")
        for k in knowledge_list:
            print(f"  [{k.id}] {k.content[:50]}...")
    
    elif args.status:
        status = memos.get_sync_status()
        print("=" * 60)
        print("MemOS 同步状态")
        print("=" * 60)
        print(f"最后同步: {time.ctime(status['last_sync']) if status['last_sync'] else '从未'}")
        print(f"同步次数: {status['sync_count']}")
        print(f"Base URL: {status['base_url']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
