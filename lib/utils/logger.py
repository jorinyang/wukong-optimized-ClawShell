"""
Logger - 日志工具
=================

提供统一的日志记录功能。
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# 全局日志配置
_LOGGERS = {}
_LOG_LEVEL = logging.INFO
_LOG_FILE = None


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
        format_string: 日志格式
    
    Returns:
        配置好的Logger实例
    """
    if name in _LOGGERS:
        return _LOGGERS[name]
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # 清除已有处理器
    
    # 格式化
    if format_string is None:
        format_string = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    _LOGGERS[name] = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        Logger实例，如果不存在则创建默认配置
    """
    if name not in _LOGGERS:
        return setup_logger(name, _LOG_LEVEL, _LOG_FILE)
    return _LOGGERS[name]


def set_log_level(level: int):
    """设置全局日志级别"""
    global _LOG_LEVEL
    _LOG_LEVEL = level
    for logger in _LOGGERS.values():
        logger.setLevel(level)


def set_log_file(log_file: Optional[Path]):
    """设置全局日志文件"""
    global _LOG_FILE
    _LOG_FILE = log_file


class LoggerMixin:
    """日志混入类，用于为类添加日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return get_logger(name)
