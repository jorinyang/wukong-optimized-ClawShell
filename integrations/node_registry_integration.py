"""
ClawShell 节点注册集成 - 多悟空协作
集成 Layer4 NodeRegistry 到悟空的集群管理
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer4.swarm import NodeRegistry, Node, NodeType, NodeStatus
from lib.layer4.trust import TrustManager, TrustLevel
from lib.layer4.failure_detector import FailureDetector

class WuKongClusterManager:
    """悟空集群管理器"""
    
    def __init__(self, node_id='wukong-primary'):
        self.node_registry = NodeRegistry()
        self.trust_manager = TrustManager()
        self.failure_detector = FailureDetector()
        self.node_id = node_id
        
        # 注册自身节点
        self.register_self()
        
    def register_self(self, capabilities=None):
        """注册当前悟空实例"""
        capabilities = capabilities or [
            'task_execution',
            'skill_management',
            'health_monitoring',
            'context_management',
            'integration'
        ]
        
        node = Node(
            node_id=self.node_id,
            node_type=NodeType.AGENT,
            name='WuKong Primary',
            status=NodeStatus.ACTIVE,
            capabilities=capabilities
        )
        
        self.node_registry.register(node)
        return node
    
    def discover_peers(self):
        """发现集群中的其他节点"""
        nodes = self.node_registry.list_nodes()
        return [n for n in nodes if n.node_id != self.node_id]
    
    def register_peer(self, peer_id, peer_type, capabilities):
        """注册对等节点"""
        peer = Node(
            node_id=peer_id,
            node_type=NodeType.AGENT if peer_type == 'agent' else NodeType.WORKER,
            name=f'Peer {peer_id}',
            status=NodeStatus.ACTIVE,
            capabilities=capabilities
        )
        self.node_registry.register(peer)
        return peer
    
    def update_peer_status(self, peer_id, status):
        """更新对等节点状态"""
        node = self.node_registry.get_node(peer_id)
        if node:
            node.status = status
            return True
        return False
    
    def record_peer_success(self, peer_id):
        """记录对等节点成功"""
        return self.failure_detector.record_success(peer_id)
    
    def record_peer_failure(self, peer_id):
        """记录对等节点失败"""
        return self.failure_detector.record_failure(peer_id)
    
    def get_peer_trust(self, peer_id):
        """获取对等节点信任度"""
        return self.trust_manager.evaluate(peer_id)
    
    def select_best_peer(self, required_capability):
        """选择最佳对等节点"""
        peers = self.discover_peers()
        best_peer = None
        best_trust = TrustLevel.UNTRUSTED
        
        for peer in peers:
            if required_capability in peer.capabilities:
                trust = self.get_peer_trust(peer.node_id)
                if trust.level >= best_trust:
                    best_trust = trust.level
                    best_peer = peer
        
        return best_peer
    
    def get_cluster_stats(self):
        """获取集群统计"""
        all_nodes = self.node_registry.list_nodes()
        active = [n for n in all_nodes if n.status == NodeStatus.ACTIVE]
        
        return {
            'total_nodes': len(all_nodes),
            'active_nodes': len(active),
            'self_node': self.node_id,
            'trust_stats': {
                level.name: len([n for n in all_nodes 
                               if self.trust_manager.evaluate(n.node_id).level == level])
                for level in TrustLevel
            }
        }


# 集成示例
if __name__ == '__main__':
    cluster = WuKongClusterManager('wukong-main')
    
    # 注册一些测试对等节点
    cluster.register_peer('wukong-worker-1', 'agent', ['task_execution', 'data_processing'])
    cluster.register_peer('wukong-worker-2', 'agent', ['integration', 'monitoring'])
    
    # 获取集群统计
    stats = cluster.get_cluster_stats()
    print(f"集群统计: {stats}")
    
    # 选择最佳节点
    best = cluster.select_best_peer('data_processing')
    if best:
        print(f"最佳节点: {best.node_id}")
