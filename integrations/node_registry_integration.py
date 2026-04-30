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
    """悟空集群管理器 - Layer4 多节点协作核心"""
    
    def __init__(self, node_id='wukong-primary'):
        self.node_registry = NodeRegistry()
        self.trust_manager = TrustManager()
        self.failure_detector = FailureDetector()
        self.node_id = node_id
        
        # 注册自身节点
        self.register_self()
    
    def register_self(self, capabilities=None):
        """注册当前悟空实例到集群"""
        capabilities = capabilities or [
            'task_execution',
            'skill_management',
            'health_monitoring',
            'context_management',
            'integration'
        ]
        
        # 使用新的 register API (name, node_type, capabilities)
        self.node_registry.register(
            name=self.node_id,
            node_type=NodeType.AGENT,
            capabilities=capabilities
        )
        print(f'✅ 节点 {self.node_id} 已注册到集群')
        return self.node_id
    
    def discover_peers(self):
        """发现集群中的其他节点"""
        nodes = self.node_registry.list_nodes()
        return [n for n in nodes if n.get('name', n.get('node_id', '')) != self.node_id]
    
    def register_peer(self, peer_id, peer_type='agent', capabilities=None):
        """注册对等节点"""
        capabilities = capabilities or ['task_execution']
        peer_type_enum = NodeType.AGENT if peer_type == 'agent' else NodeType.WORKER
        
        self.node_registry.register(
            name=peer_id,
            node_type=peer_type_enum,
            capabilities=capabilities
        )
        print(f'✅ 对等节点 {peer_id} 已注册')
        return peer_id
    
    def record_peer_success(self, peer_id):
        """记录对等节点成功交互"""
        return self.failure_detector.record_success(peer_id)
    
    def record_peer_failure(self, peer_id):
        """记录对等节点失败"""
        return self.failure_detector.record_failure(peer_id)
    
    def get_peer_trust(self, peer_id):
        """获取对等节点信任度"""
        return self.trust_manager.evaluate(peer_id)
    
    def select_best_peer(self, required_capability):
        """选择最佳对等节点（基于信任度）"""
        peers = self.discover_peers()
        best_peer = None
        best_score = -1
        
        for peer in peers:
            peer_id = peer.get('name', peer.get('node_id', ''))
            if required_capability in peer.get('capabilities', []):
                trust = self.get_peer_trust(peer_id)
                # TrustLevel enum: UNTRUSTED=0, LOW=1, MEDIUM=2, HIGH=3, TRUSTED=4
                score = trust.get('level', TrustLevel.UNTRUSTED).value if hasattr(trust.get('level'), 'value') else trust.get('score', 0)
                if score > best_score:
                    best_score = score
                    best_peer = peer_id
        
        return best_peer
    
    def get_cluster_stats(self):
        """获取集群统计信息"""
        return {
            'total_nodes': len(self.node_registry.nodes),
            'self_node': self.node_id,
            'nodes': list(self.node_registry.nodes.keys()) if hasattr(self.node_registry.nodes, 'keys') else self.node_registry.nodes
        }


# 导出
__all__ = ['WuKongClusterManager']
