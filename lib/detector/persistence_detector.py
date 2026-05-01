"""
Persistence Detector - 持久层检测
=================================

检测可用的持久层存储（Genome/MemOS/MemPalace/Obsidian/知识图谱）。
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class PersistenceLayer:
    """持久层"""
    name: str
    path: Optional[Path] = None
    api_url: Optional[str] = None
    available: bool = False
    connection_type: str = "file"  # file, api, sqlite
    details: str = ""


class PersistenceDetector:
    """持久层检测器"""
    
    PERSISTENCE_LAYERS = {
        'genome': {
            'name': 'Genome',
            'default_path': '~/.real/genome/',
            'connection_type': 'file',
            'detect_file': 'genome.yaml'
        },
        'memos': {
            'name': 'MemOS',
            'api_url': 'https://memos.memtensor.cn/api/',
            'connection_type': 'api',
            'env_var': 'MEMOS_API_KEY'
        },
        'mempalace': {
            'name': 'MemPalace',
            'default_path': '~/.claude/palace/',
            'connection_type': 'sqlite'
        },
        'obsidian': {
            'name': 'Obsidian',
            'env_var': 'OBSIDIAN_VAULT',
            'default_path': '~/Documents/Obsidian/',
            'connection_type': 'file'
        },
        'knowledge_graph': {
            'name': 'KnowledgeGraph',
            'default_path': '~/.real/workspace/shared/kg/',
            'connection_type': 'file',
            'detect_file': 'graph.json'
        }
    }
    
    def __init__(self, home_dir: Optional[Path] = None):
        self.home_dir = home_dir or Path.home()
    
    def detect_all(self) -> List[PersistenceLayer]:
        """检测所有持久层"""
        detected = []
        
        for layer_id, config in self.PERSISTENCE_LAYERS.items():
            layer = self._detect_layer(layer_id, config)
            detected.append(layer)
        
        return detected
    
    def get_available_layers(self) -> List[str]:
        """获取可用的持久层名称列表"""
        return [layer.name for layer in self.detect_all() if layer.available]
    
    def _detect_layer(self, layer_id: str, config: Dict) -> PersistenceLayer:
        """检测单个持久层"""
        name = config['name']
        connection_type = config.get('connection_type', 'file')
        
        # API类型检测
        if connection_type == 'api':
            api_url = config.get('api_url')
            env_var = config.get('env_var')
            
            # 检查环境变量
            api_key = os.environ.get(env_var, '') if env_var else ''
            
            available = bool(api_key and api_url)
            
            return PersistenceLayer(
                name=name,
                api_url=api_url,
                available=available,
                connection_type=connection_type,
                details=f"API Key: {'已配置' if api_key else '未配置'}"
            )
        
        # 文件类型检测
        default_path = config.get('default_path', '')
        path = Path(default_path.replace('~', str(self.home_dir)))
        detect_file = config.get('detect_file')
        
        if detect_file:
            available = (path / detect_file).exists()
        else:
            available = path.exists()
        
        return PersistenceLayer(
            name=name,
            path=path,
            available=available,
            connection_type=connection_type,
            details=f"路径: {path}"
        )
    
    def detect_and_configure(self) -> Dict:
        """检测并生成配置"""
        layers = self.detect_all()
        
        config = {}
        for layer in layers:
            if layer.available:
                if layer.connection_type == 'api':
                    config[layer.name.lower()] = {
                        'enabled': True,
                        'type': 'api',
                        'api_url': layer.api_url
                    }
                else:
                    config[layer.name.lower()] = {
                        'enabled': True,
                        'type': layer.connection_type,
                        'path': str(layer.path)
                    }
        
        return config
