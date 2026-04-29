"""
ContextManager - 上下文管理器
ClawShell v0.8 核心模块

负责管理系统状态隔离和上下文管理。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)


class Context:
    """
    上下文对象
    
    存储单个会话或任务的上下文信息。
    """
    
    def __init__(self, context_id: str, context_type: str = "session"):
        self.id = context_id
        self.type = context_type
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.data: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.parent_id: Optional[str] = None
        self.child_ids: List[str] = []
    
    def set(self, key: str, value: Any) -> None:
        """设置上下文数据"""
        self.data[key] = value
        self.updated_at = datetime.now()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.data.get(key, default)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
        }


class ContextManager:
    """
    上下文管理器
    
    负责管理所有上下文的创建、存储和销毁。
    
    Example:
        manager = ContextManager()
        
        # 创建上下文
        ctx = manager.create_context("task_123", "task")
        ctx.set("user_id", "user_456")
        
        # 获取上下文
        ctx = manager.get_context("task_123")
        
        # 销毁上下文
        manager.destroy_context("task_123")
    """
    
    _instance: Optional['ContextManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """初始化上下文管理器"""
        self._contexts: Dict[str, Context] = {}
        self._lock = threading.Lock()
        logger.info("ContextManager initialized")
    
    @classmethod
    def get_instance(cls) -> 'ContextManager':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def create_context(self, context_id: str, context_type: str = "session",
                      parent_id: Optional[str] = None) -> Context:
        """
        创建上下文
        
        Args:
            context_id: 上下文 ID
            context_type: 上下文类型
            parent_id: 父上下文 ID
        
        Returns:
            创建的上下文对象
        """
        with self._lock:
            if context_id in self._contexts:
                logger.warning(f"Context {context_id} already exists, returning existing")
                return self._contexts[context_id]
            
            context = Context(context_id, context_type)
            
            if parent_id and parent_id in self._contexts:
                context.parent_id = parent_id
                self._contexts[parent_id].child_ids.append(context_id)
            
            self._contexts[context_id] = context
            logger.info(f"Created context: {context_id} ({context_type})")
            
            return context
    
    def get_context(self, context_id: str) -> Optional[Context]:
        """
        获取上下文
        
        Args:
            context_id: 上下文 ID
        
        Returns:
            上下文对象或 None
        """
        return self._contexts.get(context_id)
    
    def destroy_context(self, context_id: str) -> bool:
        """
        销毁上下文
        
        Args:
            context_id: 上下文 ID
        
        Returns:
            是否成功销毁
        """
        with self._lock:
            if context_id not in self._contexts:
                return False
            
            context = self._contexts[context_id]
            
            # 从父上下文中移除
            if context.parent_id and context.parent_id in self._contexts:
                parent = self._contexts[context.parent_id]
                if context_id in parent.child_ids:
                    parent.child_ids.remove(context_id)
            
            # 递归销毁子上下文
            for child_id in context.child_ids[:]:
                self.destroy_context(child_id)
            
            del self._contexts[context_id]
            logger.info(f"Destroyed context: {context_id}")
            
            return True
    
    def list_contexts(self, context_type: Optional[str] = None) -> List[Context]:
        """
        列出上下文
        
        Args:
            context_type: 可选的类型过滤
        
        Returns:
            上下文列表
        """
        contexts = list(self._contexts.values())
        
        if context_type:
            contexts = [c for c in contexts if c.type == context_type]
        
        return contexts
    
    def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        contexts_by_type = {}
        for ctx in self._contexts.values():
            ctx_type = ctx.type
            if ctx_type not in contexts_by_type:
                contexts_by_type[ctx_type] = 0
            contexts_by_type[ctx_type] += 1
        
        return {
            "total_contexts": len(self._contexts),
            "contexts_by_type": contexts_by_type,
        }
    
    def clear_all(self) -> None:
        """清除所有上下文"""
        with self._lock:
            self._contexts.clear()
            logger.info("All contexts cleared")
