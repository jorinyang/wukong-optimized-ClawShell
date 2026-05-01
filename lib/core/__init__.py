"""
ClawShell Core Infrastructure - lib/core/
=========================================
包含事件总线(EventBus)、知识传承(Genome)、策略库(Strategy)三大核心模块
"""
import os

from lib.core import eventbus, genome, strategy

__all__ = ["eventbus", "genome", "strategy"]

# MemPalace lifecycle hooks lazy-register（避免在 MCP Server 环境中阻塞初始化）
# 设置 CLAWSHELL_NO_AUTO_HOOKS=1 可跳过自动注册
try:
    if os.environ.get("CLAWSHELL_NO_AUTO_HOOKS", "0") != "1":
        from lib.core.eventbus.lifecycle_hooks import MemPalaceHookSubscriber
        _hooks = MemPalaceHookSubscriber.get_instance()
        _hooks.register()
        print("[ClawShell.core] MemPalaceHookSubscriber registered")
except Exception as e:
    print("[ClawShell.core] MemPalace hooks skip:", e)

