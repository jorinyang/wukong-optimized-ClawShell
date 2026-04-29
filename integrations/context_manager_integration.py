"""
ClawShell 上下文管理器集成 - 管理多会话状态
集成 Layer3 ContextManager 到悟空的多会话管理
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer3.context_manager import ContextManager
from datetime import datetime

class WuKongSessionManager:
    """悟空会话管理器集成类"""
    
    def __init__(self):
        self.manager = ContextManager()
        self.current_context = None
        
    def create_session(self, session_id, user_id=None, metadata=None):
        """创建新会话"""
        context = self.manager.create_context(session_id)
        
        # 设置会话元数据
        if metadata:
            for key, value in metadata.items():
                context.set_metadata(key, value)
        
        context.set_metadata('user_id', user_id or 'anonymous')
        context.set_metadata('created_at', datetime.now().isoformat())
        
        self.current_context = context
        return context
    
    def get_session(self, session_id):
        """获取会话"""
        return self.manager.get_context(session_id)
    
    def switch_session(self, session_id):
        """切换会话"""
        context = self.get_session(session_id)
        if context:
            self.current_context = context
            return True
        return False
    
    def save_session_data(self, key, value):
        """保存会话数据"""
        if self.current_context:
            self.current_context.set_variable(key, value)
            return True
        return False
    
    def get_session_data(self, key, default=None):
        """获取会话数据"""
        if self.current_context:
            return self.current_context.get_variable(key, default)
        return default
    
    def list_active_sessions(self):
        """列出活跃会话"""
        return self.manager.list_contexts()
    
    def archive_session(self, session_id):
        """归档会话"""
        return self.manager.archive_context(session_id)


class WuKongMultiSessionContext:
    """悟空多会话上下文管理器"""
    
    def __init__(self):
        self.sessions = {}  # session_id -> WuKongSessionManager
        
    def get_or_create_session(self, session_id, **kwargs):
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = WuKongSessionManager()
            self.sessions[session_id].create_session(session_id, **kwargs)
        return self.sessions[session_id]
    
    def get_session_count(self):
        """获取会话数量"""
        return len(self.sessions)
    
    def cleanup_inactive_sessions(self, max_age_hours=24):
        """清理不活跃会话"""
        now = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            if session.current_context:
                created = session.current_context.get_variable('created_at')
                if created:
                    # 简化处理：直接移除旧会话
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
        
        return len(to_remove)


# 集成示例
if __name__ == '__main__':
    mgr = WuKongMultiSessionContext()
    
    # 创建多个会话
    for i in range(3):
        session = mgr.get_or_create_session(
            f'session_{i}',
            user_id=f'user_{i}',
            metadata={'platform': 'dingtalk'}
        )
        session.save_session_data(f'key_{i}', f'value_{i}')
    
    print(f"活跃会话数: {mgr.get_session_count()}")
    
    # 测试会话切换
    session_0 = mgr.get_or_create_session('session_0')
    print(f"当前会话数据: {session_0.get_session_data('key_0')}")
