"""
Persistence Bridge - 持久层集成 (ClawShell v1.0)
==============================================

功能: Genome持久化, MemOS持久化, MemPalace持久化, Obsidian持久化

使用示例:
    from lib.bridge.persistence import GenomeBridge, MemOSBridge
"""

from .genome_bridge import GenomeBridge
from .memos_bridge import MemOSBridge
from .mempalace_bridge import MemPalaceBridge
from .obsidian_bridge import ObsidianBridge

__all__ = [
    "GenomeBridge", "MemOSBridge",
    "MemPalaceBridge", "ObsidianBridge"
]
