"""
Detector 模块 - 环境检测套件
============================

提供框架检测、依赖检测、持久层检测和外部工具检测功能。
"""

from .framework_detector import FrameworkDetector
from .dependency_checker import DependencyChecker
from .persistence_detector import PersistenceDetector
from .external_detector import ExternalDetector

__all__ = [
    "FrameworkDetector",
    "DependencyChecker", 
    "PersistenceDetector",
    "ExternalDetector",
]
