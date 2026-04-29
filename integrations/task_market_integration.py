"""
ClawShell 任务市场集成 - 替代悟空简单任务队列
集成 Layer3 TaskMarket 到悟空的任务管理
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer4.swarm import NodeRegistry, NodeType, NodeStatus
from lib.layer3.task_market import TaskMarket, TaskMatcher, TaskPriority, TaskStatus
from datetime import datetime, timedelta

class WuKongTaskMarket:
    """悟空任务市场集成类"""
    
    def __init__(self):
        # 初始化节点注册表
        self.node_registry = NodeRegistry()
        
        # 注册悟空为任务节点
        self.node_registry.register(
            name='wukong-primary',
            node_type=NodeType.AGENT,
            capabilities=['task_execution', 'skill_management', 'integration']
        )
        
        # 初始化任务市场
        self.market = TaskMarket(node_registry=self.node_registry)
        self.matcher = TaskMatcher(node_registry=self.node_registry)
        
    def submit_task(self, task_type, description, priority=TaskPriority.NORMAL, 
                    required_capabilities=None, timeout_seconds=300):
        """提交新任务"""
        deadline = datetime.now() + timedelta(seconds=timeout_seconds)
        
        task = self.market.submit_task(
            task_type=task_type,
            description=description,
            priority=priority,
            required_capabilities=required_capabilities or ['task_execution'],
            deadline=deadline
        )
        
        return {
            'task_id': task.task_id,
            'type': task.type,
            'priority': task.priority.name,
            'status': task.status.name,
            'deadline': task.deadline.isoformat()
        }
    
    def get_pending_tasks(self):
        """获取待处理任务"""
        return self.market.get_pending_tasks()
    
    def match_and_execute(self, agent_id):
        """匹配并执行任务"""
        matched = self.matcher.match_task(agent_id)
        if matched:
            task, node = matched
            self.market.assign_task(task.task_id, agent_id)
            return {'matched': True, 'task_id': task.task_id, 'node': node.node_id}
        return {'matched': False}
    
    def complete_task(self, task_id, result):
        """完成任务"""
        return self.market.complete_task(task_id, result)
    
    def get_market_stats(self):
        """获取市场统计"""
        pending = self.get_pending_tasks()
        return {
            'pending_count': len(pending),
            'total_capacity': len(self.node_registry.list_nodes()),
            'active_nodes': len([n for n in self.node_registry.list_nodes() 
                                 if n.status == NodeStatus.ACTIVE])
        }


# 集成示例
if __name__ == '__main__':
    market = WuKongTaskMarket()
    
    # 提交测试任务
    task1 = market.submit_task(
        task_type='data_processing',
        description='分析销售数据',
        priority=TaskPriority.HIGH,
        timeout_seconds=600
    )
    print(f"已提交任务: {task1['task_id']}")
    
    # 查看市场状态
    stats = market.get_market_stats()
    print(f"\n市场状态: {stats}")
    
    # 获取待处理任务
    pending = market.get_pending_tasks()
    print(f"\n待处理任务数: {len(pending)}")
