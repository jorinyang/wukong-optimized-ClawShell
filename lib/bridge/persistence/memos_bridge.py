"""
MemOS Bridge - MemOS云端持久化
===============================

提供MemOS云端存储的接口。
"""

import os
import requests
from typing import Optional, Dict, Any, List


class MemOSBridge:
    """MemOS云端持久化桥接器"""
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or os.environ.get(
            'MEMOS_API_URL',
            'https://memos.memtensor.cn/api/openmem/v1'
        )
        self.api_key = api_key or os.environ.get('MEMOS_API_KEY', '')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def is_available(self) -> bool:
        """检查MemOS是否可用"""
        if not self.api_key:
            return False
        try:
            response = requests.get(
                f"{self.api_url}/memo",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def create_memo(self, content: str, tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """创建备忘录"""
        try:
            data = {'content': content}
            if tags:
                data['tags'] = tags
            response = requests.post(
                f"{self.api_url}/memo",
                headers=self.headers,
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"MemOSBridge create error: {e}")
        return None
    
    def get_memos(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取备忘录列表"""
        try:
            response = requests.get(
                f"{self.api_url}/memo",
                headers=self.headers,
                params={'limit': limit},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('data', [])
        except Exception as e:
            print(f"MemOSBridge get error: {e}")
        return []
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """搜索备忘录"""
        try:
            response = requests.get(
                f"{self.api_url}/memo/search",
                headers=self.headers,
                params={'q': query},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('data', [])
        except Exception as e:
            print(f"MemOSBridge search error: {e}")
        return []
