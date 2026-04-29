"""
External Bridge - 外部工具集成 (ClawShell v1.0)
==============================================

功能: MemOS同步, Obsidian同步, N8N客户端, Hermes反馈, Wiki客户端, 新闻聚合

使用示例:
    from lib.bridge.external import N8NClient, MemOSSync
"""

try:
    from .memos_sync import MemOSSync
    from .obsidian_sync import ObsidianSync
    from .n8n_client import N8NClient
    from .hermes_feedback import HermesFeedback
    from .hermes_sync import HermesSync
    from .wikipedia_client import WikipediaClient
    from .news_aggregator import NewsAggregator
    
    __all__ = [
        "MemOSSync", "ObsidianSync", "N8NClient",
        "HermesFeedback", "HermesSync",
        "WikipediaClient", "NewsAggregator"
    ]
except ImportError as e:
    class _FallbackMixin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"External bridge unavailable: {e}")
    
    MemOSSync = ObsidianSync = N8NClient = _FallbackMixin
    
    __all__ = ["MemOSSync", "ObsidianSync", "N8NClient"]
