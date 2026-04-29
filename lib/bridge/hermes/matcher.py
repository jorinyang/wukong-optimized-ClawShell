#!/usr/bin/env python3
# hermes_bridge/matcher.py
"""
响应模式匹配器

根据任务类型、优先级、环境匹配Hermes响应模式
"""

import json
from typing import Dict, List, Tuple
from .events import (
    TaskType, Priority, Environment, 
    ResponseMode, ClawshellEvent
)


class ResponseModeMatcher:
    """
    Hermes响应模式匹配器
    
    职责：
    1. 根据(优先级, 环境)查表获取基础响应模式
    2. 根据任务类型进行修正
    3. 提供响应时间目标
    """
    
    # 基础匹配矩阵: (priority, environment) -> response_mode
    BASE_MATCH_MATRIX: Dict[Tuple[str, str], ResponseMode] = {
        # P0 - 系统故障/数据损失
        ('P0', 'production'): ResponseMode.INSTANT,
        ('P0', 'staging'): ResponseMode.INSTANT,
        ('P0', 'development'): ResponseMode.FAST,
        
        # P1 - 重要任务
        ('P1', 'production'): ResponseMode.FAST,
        ('P1', 'staging'): ResponseMode.FAST,
        ('P1', 'development'): ResponseMode.FAST,
        
        # P2 - 常规任务
        ('P2', 'production'): ResponseMode.STANDARD,
        ('P2', 'staging'): ResponseMode.STANDARD,
        ('P2', 'development'): ResponseMode.BATCH,
        
        # P3 - 后台任务
        ('P3', 'production'): ResponseMode.STANDARD,
        ('P3', 'staging'): ResponseMode.BATCH,
        ('P3', 'development'): ResponseMode.BATCH,
    }
    
    # 任务类型修正: task_type -> {original_mode: corrected_mode}
    TASK_TYPE_MODIFIERS: Dict[str, Dict[str, str]] = {
        TaskType.DECISION.value: {  # 决策类更紧急
            ResponseMode.STANDARD.value: ResponseMode.FAST.value,
            ResponseMode.BATCH.value: ResponseMode.STANDARD.value
        },
        TaskType.ANALYSIS.value: {  # 分析类可接受批量
            ResponseMode.FAST.value: ResponseMode.STANDARD.value,
            ResponseMode.STANDARD.value: ResponseMode.BATCH.value
        },
        TaskType.CREATION.value: {  # 创作类保持标准
            ResponseMode.BATCH.value: ResponseMode.STANDARD.value
        }
    }
    
    # 错误事件修正
    ERROR_MODIFIERS = {
        'critical': ResponseMode.INSTANT,  # 严重错误即时响应
        'error': ResponseMode.FAST,
        'warning': ResponseMode.STANDARD,
        'info': ResponseMode.BATCH
    }
    
    # 响应时间目标
    RESPONSE_TIME_TARGETS = {
        ResponseMode.INSTANT: "<5分钟",
        ResponseMode.FAST: "<2小时",
        ResponseMode.STANDARD: "<24小时",
        ResponseMode.BATCH: "<7天"
    }
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.matrix = self.BASE_MATCH_MATRIX.copy()
        self._load_custom_matrix()
    
    def _load_custom_matrix(self):
        """从配置加载自定义矩阵"""
        custom_matrix = self.config.get('match_matrix', {})
        for key_str, mode_str in custom_matrix.items():
            priority, env = key_str.split(',')
            self.matrix[(priority, env)] = ResponseMode(mode_str)
    
    def match(
        self, 
        task_type: TaskType,
        priority: Priority, 
        environment: Environment,
        is_error: bool = False,
        error_severity: str = None
    ) -> ResponseMode:
        """
        匹配响应模式
        
        参数:
            task_type: 任务类型
            priority: 优先级
            environment: 环境
            is_error: 是否是错误事件
            error_severity: 错误严重程度
        
        返回:
            ResponseMode: 匹配的响应模式
        """
        # 1. 错误事件特殊处理
        if is_error:
            if error_severity in self.ERROR_MODIFIERS:
                return self.ERROR_MODIFIERS[error_severity]
            return ResponseMode.INSTANT  # 默认错误即时响应
        
        # 2. 查表获取基础模式
        key = (priority.value, environment.value)
        mode = self.matrix.get(key, ResponseMode.STANDARD)
        
        # 3. 任务类型修正
        modifiers = self.TASK_TYPE_MODIFIERS.get(task_type.value, {})
        mode_str = modifiers.get(mode.value, mode.value)
        mode = ResponseMode(mode_str)
        
        return mode
    
    def match_from_event(self, event: ClawshellEvent, classification: Dict) -> ResponseMode:
        """
        从事件和分类结果匹配响应模式
        
        参数:
            event: ClawshellEvent
            classification: PriorityClassifier.classify()的返回值
        
        返回:
            ResponseMode: 匹配的响应模式
        """
        is_error = 'error' in event.event_type.lower()
        error_severity = None
        
        if is_error:
            metadata = event.metadata or {}
            payload = event.payload or {}
            error_severity = metadata.get('severity') or payload.get('severity', '')
        
        return self.match(
            task_type=classification['task_type'],
            priority=classification['priority'],
            environment=classification['environment'],
            is_error=is_error,
            error_severity=error_severity
        )
    
    def get_response_time(self, mode: ResponseMode) -> str:
        """获取响应时间目标"""
        return self.RESPONSE_TIME_TARGETS.get(mode, "<24小时")
    
    def get_match_details(
        self, 
        task_type: TaskType,
        priority: Priority, 
        environment: Environment
    ) -> Dict:
        """
        获取匹配的详细信息
        
        返回:
            {
                'mode': ResponseMode,
                'response_time': str,
                'reason': str
            }
        """
        mode = self.match(task_type, priority, environment)
        
        return {
            'mode': mode,
            'response_time': self.get_response_time(mode),
            'reason': f'{priority.value} + {environment.value} + {task_type.value}'
        }


def create_matcher(config: Dict = None) -> ResponseModeMatcher:
    """工厂函数：创建匹配器"""
    return ResponseModeMatcher(config)


if __name__ == "__main__":
    # 测试代码
    print("=== ResponseModeMatcher 测试 ===\n")
    
    matcher = ResponseModeMatcher()
    
    # 测试矩阵
    test_cases = [
        # (task_type, priority, environment, expected_mode)
        (TaskType.EXECUTION, Priority.P0_CRITICAL, Environment.PRODUCTION, ResponseMode.INSTANT),
        (TaskType.EXECUTION, Priority.P1_HIGH, Environment.PRODUCTION, ResponseMode.FAST),
        (TaskType.EXECUTION, Priority.P2_NORMAL, Environment.PRODUCTION, ResponseMode.STANDARD),
        (TaskType.EXECUTION, Priority.P3_LOW, Environment.DEVELOPMENT, ResponseMode.BATCH),
        (TaskType.DECISION, Priority.P2_NORMAL, Environment.PRODUCTION, ResponseMode.FAST),  # 决策升级
        (TaskType.ANALYSIS, Priority.P1_HIGH, Environment.DEVELOPMENT, ResponseMode.BATCH),  # 分析降级
    ]
    
    for i, (task_type, priority, env, expected) in enumerate(test_cases):
        result = matcher.match(task_type, priority, env)
        status = "✅" if result == expected else "❌"
        response_time = matcher.get_response_time(result)
        
        print(f"{status} Case {i+1}:")
        print(f"   输入: {task_type.value} + {priority.value} + {env.value}")
        print(f"   匹配: {result.value} (预期: {expected.value})")
        print(f"   响应时间: {response_time}")
        print()
    
    # 测试错误事件
    print("=== 错误事件测试 ===\n")
    
    error_cases = [
        ('critical', ResponseMode.INSTANT),
        ('error', ResponseMode.FAST),
        ('warning', ResponseMode.STANDARD),
        ('info', ResponseMode.BATCH),
    ]
    
    for severity, expected in error_cases:
        result = matcher.match(
            TaskType.EXECUTION, 
            Priority.P2_NORMAL, 
            Environment.DEVELOPMENT,
            is_error=True,
            error_severity=severity
        )
        status = "✅" if result == expected else "❌"
        print(f"{status} 错误严重程度 '{severity}': {result.value}")
