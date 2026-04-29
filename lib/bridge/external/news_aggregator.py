#!/usr/bin/env python3
"""
ClawShell News Aggregator
新闻聚合器 - Phase 4
版本: v1.0.0
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

class NewsAggregator:
    """新闻聚合器"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.news_history: deque = deque(maxlen=max_history)
        self.categories = ["technology", "business", "science", "health"]
    
    def fetch_tech_news(self, limit: int = 10) -> List[Dict]:
        """获取科技新闻 (使用NewsAPI或RSS)"""
        # 这里使用一个免费的RSS源
        rss_url = "https://feeds.feedburner.com/techcrunch"
        
        # 模拟新闻数据
        mock_news = [
            {
                "title": "AI Breakthrough in Reasoning",
                "source": "TechCrunch",
                "published": datetime.now().isoformat(),
                "url": "https://example.com/ai-reasoning",
                "category": "technology"
            },
            {
                "title": "New Programming Language Released",
                "source": "Hacker News",
                "published": datetime.now().isoformat(),
                "url": "https://example.com/new-lang",
                "category": "technology"
            }
        ]
        
        return mock_news[:limit]
    
    def add_news(self, news: Dict):
        """添加新闻到历史"""
        news["added_at"] = datetime.now().isoformat()
        self.news_history.append(news)
    
    def get_recent_news(self, limit: int = 20) -> List[Dict]:
        """获取最近新闻"""
        return list(self.news_history)[-limit:]
    
    def search_news(self, keyword: str) -> List[Dict]:
        """搜索新闻"""
        keyword_lower = keyword.lower()
        results = []
        
        for news in self.news_history:
            title = news.get("title", "").lower()
            if keyword_lower in title:
                results.append(news)
        
        return results
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_news": len(self.news_history),
            "max_history": self.max_history,
            "categories": self.categories
        }

if __name__ == "__main__":
    aggregator = NewsAggregator()
    
    print("=== 新闻聚合器测试 ===")
    
    # 获取新闻
    news = aggregator.fetch_tech_news(limit=5)
    print(f"\n获取到 {len(news)} 条新闻:")
    for n in news:
        print(f"  - {n['title']}")
    
    # 添加到历史
    for n in news:
        aggregator.add_news(n)
    
    print(f"\n历史新闻数: {aggregator.get_stats()}")
    
    # 搜索
    results = aggregator.search_news("AI")
    print(f"\n搜索 'AI' 结果: {len(results)}")
