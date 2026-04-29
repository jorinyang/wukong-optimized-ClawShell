"""
Emergency Response - ClawShell v0.1
===================================

应急响应机制。
提供错误自动重试、备用源切换、紧急恢复功能。
"""

import time
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0


@dataclass
class FallbackSource:
    """备用源"""
    name: str
    source_type: str  # api, mcp, model
    endpoint: str
    priority: int = 1
    enabled: bool = True


class EmergencyResponse:
    """
    应急响应机制
    =============
    
    功能：
    - 错误自动重试（指数退避）
    - 备用源自动切换
    - 紧急恢复流程
    
    使用示例：
        emergency = EmergencyResponse()
        
        # 带重试的调用
        result = emergency.retry_with_retry(
            func=call_api,
            config=RetryConfig(max_retries=3)
        )
        
        # 注册备用源
        emergency.register_fallback(FallbackSource(
            name="backup_api",
            source_type="api",
            endpoint="https://backup.example.com"
        ))
        
        # 带备用源的调用
        result = emergency.call_with_fallback(
            primary_func=call_primary,
            fallback_func=call_backup
        )
    """
    
    def __init__(self):
        self._fallback_sources: Dict[str, list] = {}  # service_name -> [FallbackSource]
        self._current_fallbacks: Dict[str, str] = {}  # service_name -> current_fallback
        self._retry_stats: Dict[str, Dict] = {}  # service_name -> stats
        
        logger.info("EmergencyResponse initialized")
    
    def retry_with_retry(
        self,
        func: Callable,
        config: RetryConfig = None,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试的函数调用
        
        Args:
            func: 要调用的函数
            config: 重试配置
            *args, **kwargs: 函数参数
        
        Returns:
            函数返回值
        """
        config = config or RetryConfig()
        
        last_error = None
        delay = config.initial_delay
        
        for attempt in range(config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Retry succeeded on attempt {attempt + 1}")
                
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < config.max_retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    
                    if config.exponential_backoff:
                        delay = min(delay * config.backoff_multiplier, config.max_delay)
        
        logger.error(f"All retries exhausted after {config.max_retries + 1} attempts")
        raise last_error
    
    def retry_decorator(self, config: RetryConfig = None):
        """
        重试装饰器
        
        使用示例：
            @emergency.retry_decorator(RetryConfig(max_retries=3))
            def fragile_function():
                ...
        """
        config = config or RetryConfig()
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.retry_with_retry(func, config, *args, **kwargs)
            return wrapper
        return decorator
    
    def register_fallback(self, source: FallbackSource):
        """
        注册备用源
        
        Args:
            source: 备用源配置
        """
        if source.name not in self._fallback_sources:
            self._fallback_sources[source.name] = []
        
        self._fallback_sources[source.name].append(source)
        
        # 按优先级排序
        self._fallback_sources[source.name].sort(key=lambda x: x.priority)
        
        logger.info(f"Registered fallback: {source.name} -> {source.endpoint}")
    
    def unregister_fallback(self, source_name: str):
        """注销备用源"""
        if source_name in self._fallback_sources:
            del self._fallback_sources[source_name]
            logger.info(f"Unregistered fallback: {source_name}")
    
    def call_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带备用源的函数调用
        
        Args:
            service_name: 服务名称
            primary_func: 主函数
            *args, **kwargs: 函数参数
        
        Returns:
            函数返回值
        """
        # 首先尝试主函数
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary call failed: {e}")
            
            # 获取备用源
            fallbacks = self._fallback_sources.get(service_name, [])
            if not fallbacks:
                raise
            
            # 尝试备用源
            for fallback in fallbacks:
                if not fallback.enabled:
                    continue
                
                try:
                    logger.info(f"Trying fallback: {fallback.name}")
                    # 这里应该调用备用函数，但简化处理
                    # 实际使用时应该传入对应的备用函数
                    raise Exception(f"Fallback {fallback.name} not implemented")
                except Exception as fallback_error:
                    logger.warning(f"Fallback {fallback.name} also failed: {fallback_error}")
                    continue
            
            # 所有都失败了
            raise
    
    def switch_to_fallback(self, service_name: str) -> Optional[str]:
        """
        切换到备用源
        
        Args:
            service_name: 服务名称
        
        Returns:
            切换后的备用源名称
        """
        fallbacks = self._fallback_sources.get(service_name, [])
        if not fallbacks:
            return None
        
        current = self._current_fallbacks.get(service_name)
        
        for i, fallback in enumerate(fallbacks):
            if fallback.name == current:
                # 切换到下一个
                next_idx = (i + 1) % len(fallbacks)
                next_fallback = fallbacks[next_idx]
                self._current_fallbacks[service_name] = next_fallback.name
                logger.info(f"Switched {service_name} from {current} to {next_fallback.name}")
                return next_fallback.name
        
        # 没有当前使用的，切换到第一个
        first_fallback = fallbacks[0]
        self._current_fallbacks[service_name] = first_fallback.name
        logger.info(f"Switched {service_name} to {first_fallback.name}")
        return first_fallback.name
    
    def get_current_fallback(self, service_name: str) -> Optional[str]:
        """获取当前使用的备用源"""
        return self._current_fallbacks.get(service_name)
    
    def enable_fallback(self, source_name: str):
        """启用备用源"""
        for sources in self._fallback_sources.values():
            for source in sources:
                if source.name == source_name:
                    source.enabled = True
                    logger.info(f"Enabled fallback: {source_name}")
                    return
    
    def disable_fallback(self, source_name: str):
        """禁用备用源"""
        for sources in self._fallback_sources.values():
            for source in sources:
                if source.name == source_name:
                    source.enabled = False
                    logger.info(f"Disabled fallback: {source_name}")
                    return
    
    def get_retry_stats(self, service_name: str = None) -> Dict:
        """获取重试统计"""
        if service_name:
            return self._retry_stats.get(service_name, {})
        return self._retry_stats.copy()
    
    def record_retry(self, service_name: str, attempt: int, success: bool):
        """记录重试"""
        if service_name not in self._retry_stats:
            self._retry_stats[service_name] = {
                "total_retries": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "last_retry": None,
            }
        
        stats = self._retry_stats[service_name]
        stats["total_retries"] += 1
        
        if success:
            stats["successful_retries"] += 1
        else:
            stats["failed_retries"] += 1
        
        stats["last_retry"] = datetime.now().isoformat()


# 全局单例
_emergency: Optional[EmergencyResponse] = None


def get_emergency() -> EmergencyResponse:
    """获取全局应急响应实例"""
    global _emergency
    if _emergency is None:
        _emergency = EmergencyResponse()
    return _emergency
