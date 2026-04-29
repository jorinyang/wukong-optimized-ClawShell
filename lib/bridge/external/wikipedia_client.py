#!/usr/bin/env python3
"""
ClawShell Wikipedia Client
Wikipedia知识接入 - Phase 4
版本: v1.0.1 (SSL修复)
"""

import json
import ssl
import urllib.request
import urllib.parse
from typing import Dict, List, Optional

class WikipediaClient:
    """Wikipedia客户端"""
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        # 创建不验证SSL的context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索Wikipedia"""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json"
        }
        
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_context) as response:
                data = json.loads(response.read().decode())
                results = data.get("query", {}).get("search", [])
                return [
                    {
                        "title": r["title"],
                        "snippet": r["snippet"],
                        "pageid": r["pageid"]
                    }
                    for r in results
                ]
        except Exception as e:
            print(f"Wikipedia search error: {e}")
            return []
    
    def get_page(self, title: str) -> Optional[Dict]:
        """获取页面内容"""
        if title in self.cache:
            return self.cache[title]
        
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "format": "json"
        }
        
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=self.ssl_context) as response:
                data = json.loads(response.read().decode())
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if page_id != "-1":
                        result = {
                            "title": page_data.get("title"),
                            "extract": page_data.get("extract", ""),
                            "pageid": page_id
                        }
                        self.cache[title] = result
                        return result
        except Exception as e:
            print(f"Wikipedia get_page error: {e}")
            return None

if __name__ == "__main__":
    client = WikipediaClient()
    
    print("=== Wikipedia 客户端测试 ===")
    
    # 搜索
    results = client.search("artificial intelligence", limit=3)
    print(f"\n搜索 'artificial intelligence':")
    for r in results:
        print(f"  - {r['title']}")
