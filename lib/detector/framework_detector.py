"""
Framework Detector - 类OpenClaw框架自动发现
==========================================

自动检测系统中已部署的类OpenClaw框架。
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DetectedFramework:
    """检测到的框架"""
    name: str
    path: Path
    version: Optional[str] = None
    status: str = "unknown"
    components: List[str] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = []


class FrameworkDetector:
    """
    类OpenClaw框架自动检测器
    
    检测顺序：
    1. 扫描所有已知框架目录
    2. 验证识别特征
    3. 检测依赖组件
    4. 返回可用框架列表
    """
    
    FRAMEWORK_SIGNATURES = {
        'openclaw': {
            'name': 'OpenClaw',
            'dirs': ['agents', 'workspace', 'config', 'skills'],
            'files': ['gateway.json', 'config.yaml'],
            'markers': ['openclaw', 'agent'],
            'priority': 0
        },
        'hermes': {
            'name': 'Hermes',
            'dirs': ['scripts', 'skills', 'config'],
            'files': ['guardian.sh', 'crontab.txt'],
            'markers': ['hermes', 'insight'],
            'priority': 0
        },
        'real': {
            'name': '阿里悟空',
            'dirs': ['config', 'plugins', 'runtime'],
            'files': ['aliyun.json', 'config.json'],
            'markers': ['real', 'alibaba'],
            'priority': 1
        },
        'easyclaw': {
            'name': '猎豹EasyClaw',
            'dirs': ['agent', 'runtime', 'plugins'],
            'files': ['runtime.conf', 'agent.conf'],
            'markers': ['easyclaw', 'leopard'],
            'priority': 1
        }
    }
    
    def __init__(self, home_dir: Optional[Path] = None):
        self.home_dir = home_dir or Path.home()
    
    def detect_all(self) -> List[DetectedFramework]:
        """检测所有框架"""
        detected = []
        
        for framework_id, signature in self.FRAMEWORK_SIGNATURES.items():
            framework = self._detect_framework(framework_id, signature)
            if framework:
                detected.append(framework)
        
        # 按优先级排序
        detected.sort(key=lambda x: self.FRAMEWORK_SIGNATURES[x.name.lower().replace(' ', '')].get('priority', 99))
        
        return detected
    
    def _detect_framework(self, framework_id: str, signature: Dict) -> Optional[DetectedFramework]:
        """检测单个框架"""
        # 确定目录路径
        if framework_id == 'openclaw':
            base_dir = self.home_dir / '.openclaw'
        else:
            base_dir = self.home_dir / f'.{framework_id}'
        
        if not base_dir.exists():
            return None
        
        # 验证签名
        if not self._verify_signature(base_dir, signature):
            return None
        
        # 检测组件
        components = self._detect_components(base_dir, signature)
        
        return DetectedFramework(
            name=signature['name'],
            path=base_dir,
            status='ready',
            components=components
        )
    
    def _verify_signature(self, base_dir: Path, signature: Dict) -> bool:
        """验证框架签名"""
        # 检查必需目录
        for required_dir in signature.get('dirs', []):
            if not (base_dir / required_dir).exists():
                return False
        
        # 检查必需文件
        for required_file in signature.get('files', []):
            if not (base_dir / required_file).exists():
                return False
        
        return True
    
    def _detect_components(self, base_dir: Path, signature: Dict) -> List[str]:
        """检测框架组件"""
        components = []
        
        for marker in signature.get('markers', []):
            # 检测包含marker的子目录
            for item in base_dir.iterdir():
                if item.is_dir() and marker in item.name.lower():
                    components.append(item.name)
        
        return components
    
    def get_detected_names(self) -> List[str]:
        """获取检测到的框架名称列表"""
        return [f.name for f in self.detect_all()]
