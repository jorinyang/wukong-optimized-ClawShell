#!/usr/bin/env python3
# hermes_bridge/classifier.py
"""
优先级分类器

根据任务类型、优先级、环境进行分类
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from .events import (
    TaskType, Priority, Environment, 
    ClawshellEvent, identify_task_type
)


class PriorityClassifier:
    """
    任务优先级分类器
    
    职责：
    1. 根据事件特征识别任务类型
    2. 判定优先级
    3. 识别环境
    """
    
    # 优先级矩阵: (task_type, explicit_priority) -> calculated_priority
    PRIORITY_MATRIX = {
        # Execution tasks
        ('execution', 'P0'): Priority.P0_CRITICAL,
        ('execution', 'P1'): Priority.P1_HIGH,
        ('execution', 'P2'): Priority.P2_NORMAL,
        ('execution', 'P3'): Priority.P3_LOW,
        
        # Analysis tasks
        ('analysis', 'P0'): Priority.P0_CRITICAL,
        ('analysis', 'P1'): Priority.P1_HIGH,
        ('analysis', 'P2'): Priority.P2_NORMAL,
        ('analysis', 'P3'): Priority.P3_LOW,
        
        # Creation tasks
        ('creation', 'P0'): Priority.P0_CRITICAL,
        ('creation', 'P1'): Priority.P1_HIGH,
        ('creation', 'P2'): Priority.P2_NORMAL,
        ('creation', 'P3'): Priority.P3_LOW,
        
        # Decision tasks (higher priority)
        ('decision', 'P0'): Priority.P0_CRITICAL,
        ('decision', 'P1'): Priority.P1_HIGH,
        ('decision', 'P2'): Priority.P1_HIGH,   # 升级
        ('decision', 'P3'): Priority.P2_NORMAL,  # 升级
        
        # Maintenance tasks (generally lower)
        ('maintenance', 'P0'): Priority.P0_CRITICAL,
        ('maintenance', 'P1'): Priority.P1_HIGH,
        ('maintenance', 'P2'): Priority.P3_LOW,   # 降级
        ('maintenance', 'P3'): Priority.P3_LOW,
    }
    
    # 环境修正: 环境 -> (原始优先级 -> 修正后优先级)
    ENVIRONMENT_MODIFIERS = {
        'production': {
            'P0': 'P0',  # 保持P0
            'P1': 'P0',   # 升级P1->P0
            'P2': 'P1',   # 升级P2->P1
            'P3': 'P2'    # 升级P3->P2
        },
        'staging': {
            'P0': 'P1',  # 降级P0->P1
            'P1': 'P1',   # 保持P1
            'P2': 'P2',   # 保持P2
            'P3': 'P2'    # 升级P3->P2
        },
        'development': {
            'P0': 'P2',   # 大幅降级
            'P1': 'P2',   # 降级
            'P2': 'P3',   # 降级
            'P3': 'P3'    # 保持P3
        }
    }
    
    # 错误事件优先级映射
    ERROR_PRIORITY_MAP = {
        'critical': Priority.P0_CRITICAL,
        'error': Priority.P1_HIGH,
        'warning': Priority.P2_NORMAL,
        'info': Priority.P3_LOW
    }
    
    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict:
        """加载分类规则"""
        if not self.rules_file:
            return {}
        
        path = Path(self.rules_file).expanduser()
        if path.exists():
            with open(path) as f:
                return json.load(f)
        
        return {}
    
    def classify(self, event: ClawshellEvent) -> Dict:
        """
        分类事件
        
        参数:
            event: ClawshellEvent
        
        返回:
            {
                'task_type': TaskType,
                'priority': Priority,
                'environment': Environment,
                'reason': str
            }
        """
        # 1. 识别任务类型
        task_type = self._identify_task_type(event)
        
        # 2. 获取显式优先级
        explicit_priority = self._get_explicit_priority(event)
        
        # 3. 查表获取计算优先级
        key = (task_type.value, explicit_priority.value)
        calculated_priority = self.PRIORITY_MATRIX.get(
            key, 
            Priority.P2_NORMAL
        )
        
        # 4. 识别环境
        environment = self._identify_environment(event)
        
        # 5. 环境修正
        if environment:
            modifiers = self.ENVIRONMENT_MODIFIERS.get(environment.value, {})
            modified_priority_str = modifiers.get(
                calculated_priority.value, 
                calculated_priority.value
            )
            calculated_priority = Priority(modified_priority_str)
        
        return {
            'task_type': task_type,
            'priority': calculated_priority,
            'environment': environment or Environment.DEVELOPMENT,
            'reason': f'{task_type.value} + {explicit_priority.value} + {environment.value if environment else "unknown"}'
        }
    
    def _identify_task_type(self, event: ClawshellEvent) -> TaskType:
        """识别任务类型"""
        # 优先使用事件中已有的类型
        if event.task_type:
            try:
                return TaskType(event.task_type)
            except ValueError:
                pass
        
        # 从事件类型和payload中识别
        event_type = event.event_type
        payload = event.payload or {}
        
        return identify_task_type(event_type, payload)
    
    def _get_explicit_priority(self, event: ClawshellEvent) -> Priority:
        """获取显式优先级"""
        # 从metadata获取
        metadata = event.metadata or {}
        if 'priority' in metadata:
            try:
                return Priority(metadata['priority'])
            except ValueError:
                pass
        
        # 从payload获取
        payload = event.payload or {}
        if 'priority' in payload:
            try:
                return Priority(payload['priority'])
            except ValueError:
                pass
        
        # 从事件类型中提取
        event_type = event.event_type.upper()
        for p in ['P0', 'P1', 'P2', 'P3']:
            if p in event_type:
                return Priority(p)
        
        # 检查是否是错误事件
        error_severity = metadata.get('severity') or payload.get('severity', '')
        if 'error' in event.event_type.lower() or 'critical' in error_severity.lower():
            return Priority.P0_CRITICAL
        
        return Priority.P2_NORMAL  # 默认P2
    
    def _identify_environment(self, event: ClawshellEvent) -> Environment:
        """识别环境"""
        metadata = event.metadata or {}
        payload = event.payload or {}
        
        # 优先从metadata获取
        env_str = metadata.get('environment') or payload.get('environment', '')
        
        for env in Environment:
            if env_str == env.value:
                return env
        
        # 从事件源路径推断
        source = event.source or ''
        source_lower = source.lower()
        
        if 'production' in source_lower or 'prod' in source_lower:
            return Environment.PRODUCTION
        elif 'staging' in source_lower or 'test' in source_lower:
            return Environment.STAGING
        
        return Environment.DEVELOPMENT  # 默认开发环境


def create_classifier(config: Dict = None) -> PriorityClassifier:
    """工厂函数：创建分类器"""
    rules_file = None
    if config:
        rules_file = config.get('rules_file')
    
    return PriorityClassifier(rules_file)


if __name__ == "__main__":
    # 测试代码
    print("=== PriorityClassifier 测试 ===\n")
    
    classifier = PriorityClassifier()
    
    # 测试用例
    test_cases = [
        # (event_type, source, priority_in_metadata, expected_task, expected_priority)
        ("clawshell.task.execute.P1", "openclaw", "P1", "execution", "P1"),
        ("clawshell.task.create.P2", "openclaw", "P2", "creation", "P2"),
        ("clawshell.task.analyze.P1", "production", "P1", "analysis", "P0"),  # production升级
        ("clawshell.error.critical", "production", None, "execution", "P0"),  # 错误升级
        ("clawshell.task.maintain.P2", "development", "P2", "maintenance", "P3"),  # 开发降级
    ]
    
    for i, (event_type, source, meta_priority, expected_task, expected_priority) in enumerate(test_cases):
        event = ClawshellEvent(
            event_id=f"test-{i}",
            event_type=event_type,
            source=source,
            timestamp="2026-04-29T00:00:00",
            metadata={'priority': meta_priority} if meta_priority else {}
        )
        
        result = classifier.classify(event)
        
        status = "✅" if (
            result['task_type'].value == expected_task and 
            result['priority'].value == expected_priority
        ) else "❌"
        
        print(f"{status} Case {i+1}:")
        print(f"   事件: {event_type}")
        print(f"   任务类型: {result['task_type'].value} (预期: {expected_task})")
        print(f"   优先级: {result['priority'].value} (预期: {expected_priority})")
        print(f"   环境: {result['environment'].value}")
        print(f"   原因: {result['reason']}")
        print()
