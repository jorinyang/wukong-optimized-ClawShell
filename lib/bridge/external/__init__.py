"""
External Bridge - 外部工具集成 (ClawShell v1.0 Wrapper)
=======================================================
来源: ~/.openclaw/external/
功能: MemOS同步, Obsidian同步, N8N客户端, Hermes反馈/同步, Wiki客户端, 新闻聚合
"""

import sys
from pathlib import Path

_src = Path("~/.openclaw/external").expanduser()
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from memos_sync import MemOSSync
    from obsidian_sync import ObsidianSync
    from n8n_client import N8NClient
    from hermes_feedback import HermesFeedback
    from hermes_sync import HermesSync
    from wikipedia_client import WikipediaClient
    from news_aggregator import NewsAggregator
    
    __all__ = [
        "MemOSSync", "ObsidianSync", "N8NClient",
        "HermesFeedback", "HermesSync",
        "WikipediaClient", "NewsAggregator"
    ]
except ImportError as e:
    __all__ = []
    __import_error__ = str(e)
