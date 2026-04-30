"""
悟空任务队列升级 - WuKongTaskMarket 集成
替代悟空原有的简单任务队列，实现智能任务分发
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from integrations.task_market_integration import WuKongTaskMarket
from lib.layer3.task_market import TaskPriority
from datetime import datetime
import json
from pathlib import Path

class WuKongTaskQueue:
    """悟空智能任务队列 - 升级版"""
    
    def __init__(self):
        self.market = WuKongTaskMarket()
        self.log_dir = Path(r'C:\Users\Aorus\.real\users\user-bd1b229d4eff8f6a45c456149072cb3b\workspace\task_logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        print(f"[任务队列] WuKongTaskMarket 已初始化")
        print(f"[任务队列] 当前待处理任务: {len(self.market.get_pending_tasks())}")
    
    def submit(self, task_type, description, priority='NORMAL', timeout=300):
        """提交任务到队列"""
        priority_map = {
            'LOW': TaskPriority.LOW,
            'NORMAL': TaskPriority.NORMAL,
            'HIGH': TaskPriority.HIGH,
            'URGENT': TaskPriority.URGENT,
            'CRITICAL': TaskPriority.CRITICAL
        }
        
        result = self.market.submit_task(
            task_type=task_type,
            description=description,
            priority=priority_map.get(priority, TaskPriority.NORMAL),
            timeout_seconds=timeout
        )
        
        print(f"[任务队列] 已提交: {result['task_id']} ({priority})")
        return result
    
    def list_pending(self):
        """列出待处理任务"""
        pending = self.market.get_pending_tasks()
        print(f"[任务队列] 待处理任务数: {len(pending)}")
        return pending
    
    def get_stats(self):
        """获取队列统计"""
        stats = self.market.get_market_stats()
        print(f"[任务队列] 统计: {json.dumps(stats, ensure_ascii=False)}")
        return stats
    
    def complete(self, task_id, result):
        """完成任务"""
        return self.market.complete_task(task_id, result)

# 全局实例
_task_queue = None

def get_task_queue():
    """获取全局任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = WuKongTaskQueue()
    return _task_queue

if __name__ == "__main__":
    queue = get_task_queue()
    
    # 测试提交任务
    task = queue.submit(
        task_type='data_analysis',
        description='分析本周销售数据',
        priority='HIGH',
        timeout=600
    )
    
    # 查看统计
    queue.get_stats()
    
    # 列出待处理
    queue.list_pending()
