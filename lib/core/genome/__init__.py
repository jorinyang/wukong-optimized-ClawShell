"""
Genome - 知识传承模块 (ClawShell v1.0)
====================================

功能: 版本管理、知识图谱、语义搜索、IQ评估、继承追踪

使用示例:
    from lib.core.genome import GenomeManager, SemanticSearch
"""

try:
    from .manager import GenomeManager
except ImportError:
    GenomeManager = None

try:
    from .semantic_search import SemanticSearch
except ImportError:
    SemanticSearch = None

try:
    from .knowledge_graph import KnowledgeGraph
except ImportError:
    KnowledgeGraph = None

try:
    from .version_manager import VersionManager
except ImportError:
    VersionManager = None

try:
    from .heritage import HeritageProtocol as Heritage
except ImportError:
    Heritage = None

__all__ = [
    "GenomeManager", "SemanticSearch",
    "KnowledgeGraph", "VersionManager", "Heritage"
]
