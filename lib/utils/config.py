"""
Config - 配置管理工具
=====================

提供YAML/JSON配置文件加载和保存功能。
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field, asdict


@dataclass
class Config:
    """配置数据类"""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持嵌套键（用.分隔）"""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """设置配置值，支持嵌套键（用.分隔）"""
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]):
        """更新配置"""
        self.data.update(updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.data.copy()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """从字典创建"""
        return cls(data=data)


def load_config(path: Union[str, Path], format: Optional[str] = None) -> Config:
    """
    加载配置文件
    
    Args:
        path: 配置文件路径
        format: 文件格式 ('yaml', 'json', 'auto')，默认自动检测
    
    Returns:
        Config对象
    """
    path = Path(path)
    
    if not path.exists():
        return Config()
    
    # 自动检测格式
    if format is None or format == 'auto':
        suffix = path.suffix.lower()
        if suffix in ('.yaml', '.yml'):
            format = 'yaml'
        elif suffix == '.json':
            format = 'json'
        else:
            format = 'yaml'  # 默认用yaml
    
    with open(path, 'r', encoding='utf-8') as f:
        if format == 'yaml':
            data = yaml.safe_load(f) or {}
        elif format == 'json':
            data = json.load(f)
        else:
            data = {}
    
    return Config(data=data)


def save_config(config: Config, path: Union[str, Path], format: Optional[str] = None):
    """
    保存配置文件
    
    Args:
        config: Config对象
        path: 配置文件路径
        format: 文件格式 ('yaml', 'json', 'auto')，默认自动检测
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 自动检测格式
    if format is None or format == 'auto':
        suffix = path.suffix.lower()
        if suffix in ('.yaml', '.yml'):
            format = 'yaml'
        elif suffix == '.json':
            format = 'json'
        else:
            format = 'yaml'  # 默认用yaml
    
    with open(path, 'w', encoding='utf-8') as f:
        if format == 'yaml':
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        elif format == 'json':
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
    
    return path


def merge_configs(*configs: Config) -> Config:
    """合并多个配置，后面的覆盖前面的"""
    result = Config()
    
    for config in configs:
        result.update(config.to_dict())
    
    return result
