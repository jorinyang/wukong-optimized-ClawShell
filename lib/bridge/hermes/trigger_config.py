#!/usr/bin/env python3
# hermes_bridge/trigger_config.py
"""
分级触发配置器

配置不同优先级任务的触发规则和响应模式处理方式
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TriggerRule:
    """触发规则"""
    name: str
    condition: Dict[str, Any]  # 触发条件
    response_mode: str  # instant, fast, standard, batch
    hermes_action: str  # Hermes执行的场景
    priority_boost: Optional[str] = None  # 可选的优先级提升
    cooldown_seconds: int = 0  # 冷却时间
    enabled: bool = True


@dataclass
class ResponseModeConfig:
    """响应模式配置"""
    mode: str
    time_limit: str  # 响应时间限制
    batch_size: int  # 批量大小
    batch_interval: int  # 批量间隔(秒)
    hermes_scenario: str  # 对应的Hermes场景
    notification: bool = True  # 是否通知
    auto_apply: bool = False  # 是否自动应用


class TriggerConfig:
    """
    分级触发配置器
    
    职责：
    1. 管理触发规则
    2. 管理响应模式配置
    3. 与Hermes场景集成
    """
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or 
                              '~/.openclaw/workspace/shared/hermes_bridge').expanduser()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.rules_file = self.config_dir / 'trigger_rules.json'
        self.modes_file = self.config_dir / 'response_modes.json'
        
        self.rules = self._load_rules()
        self.modes = self._load_modes()
    
    def _load_rules(self) -> List[Dict]:
        """加载触发规则"""
        if self.rules_file.exists():
            with open(self.rules_file) as f:
                return json.load(f)
        
        # 默认规则
        return self._default_rules()
    
    def _load_modes(self) -> Dict[str, Dict]:
        """加载响应模式配置"""
        if self.modes_file.exists():
            with open(self.modes_file) as f:
                return json.load(f)
        
        # 默认模式
        return self._default_modes()
    
    def _default_rules(self) -> List[Dict]:
        """默认触发规则"""
        return [
            # P0 规则 - 即时介入
            {
                "name": "p0_system_error",
                "condition": {
                    "event_type": "clawshell.error.critical",
                    "severity": "critical"
                },
                "response_mode": "instant",
                "hermes_action": "review",
                "cooldown_seconds": 0,
                "enabled": True
            },
            {
                "name": "p0_data_loss",
                "condition": {
                    "event_type": "clawshell.task.failed",
                    "task_type": "critical"
                },
                "response_mode": "instant",
                "hermes_action": "review",
                "priority_boost": "P0",
                "cooldown_seconds": 0,
                "enabled": True
            },
            
            # P1 规则 - 快速响应
            {
                "name": "p1_important_task",
                "condition": {
                    "priority": "P1",
                    "task_type": ["execution", "analysis", "decision"]
                },
                "response_mode": "fast",
                "hermes_action": "summarize",
                "cooldown_seconds": 300,  # 5分钟冷却
                "enabled": True
            },
            {
                "name": "p1_customer_task",
                "condition": {
                    "metadata.customer_related": True,
                    "priority": "P1"
                },
                "response_mode": "fast",
                "hermes_action": "summarize",
                "cooldown_seconds": 600,  # 10分钟冷却
                "enabled": True
            },
            
            # P2 规则 - 标准流程
            {
                "name": "p2_regular_task",
                "condition": {
                    "priority": "P2"
                },
                "response_mode": "standard",
                "hermes_action": "summarize",
                "cooldown_seconds": 3600,  # 1小时冷却
                "enabled": True
            },
            {
                "name": "p2_knowledge_work",
                "condition": {
                    "task_type": ["analysis", "creation"]
                },
                "response_mode": "standard",
                "hermes_action": "coach",
                "cooldown_seconds": 7200,  # 2小时冷却
                "enabled": True
            },
            
            # P3 规则 - 批量处理
            {
                "name": "p3_background_task",
                "condition": {
                    "priority": "P3",
                    "task_type": "maintenance"
                },
                "response_mode": "batch",
                "hermes_action": "graph",
                "cooldown_seconds": 86400,  # 24小时冷却
                "enabled": True
            },
            {
                "name": "p3_exploration",
                "condition": {
                    "metadata.task_category": "exploration"
                },
                "response_mode": "batch",
                "hermes_action": "coach",
                "cooldown_seconds": 604800,  # 7天冷却
                "enabled": True
            },
            
            # 特殊规则
            {
                "name": "session_end",
                "condition": {
                    "event_type": "clawshell.session.end"
                },
                "response_mode": "standard",
                "hermes_action": "summarize",
                "cooldown_seconds": 0,
                "enabled": True
            },
            {
                "name": "daily_digest",
                "condition": {
                    "event_type": "clawshell.cron.daily"
                },
                "response_mode": "batch",
                "hermes_action": "predict",
                "cooldown_seconds": 86400,
                "enabled": True
            }
        ]
    
    def _default_modes(self) -> Dict[str, Dict]:
        """默认响应模式配置"""
        return {
            "instant": {
                "mode": "instant",
                "time_limit": "<5分钟",
                "batch_size": 1,
                "batch_interval": 0,
                "hermes_scenario": "review",
                "notification": True,
                "auto_apply": False,
                "description": "即时介入模式 - 用于P0紧急情况"
            },
            "fast": {
                "mode": "fast",
                "time_limit": "<2小时",
                "batch_size": 5,
                "batch_interval": 300,  # 5分钟
                "hermes_scenario": "summarize",
                "notification": True,
                "auto_apply": False,
                "description": "快速响应模式 - 用于P1重要任务"
            },
            "standard": {
                "mode": "standard",
                "time_limit": "<24小时",
                "batch_size": 20,
                "batch_interval": 3600,  # 1小时
                "hermes_scenario": "summarize",
                "notification": False,
                "auto_apply": False,
                "description": "标准流程模式 - 用于P2常规任务"
            },
            "batch": {
                "mode": "batch",
                "time_limit": "<7天",
                "batch_size": 100,
                "batch_interval": 86400,  # 24小时
                "hermes_scenario": "predict",
                "notification": False,
                "auto_apply": False,
                "description": "批量处理模式 - 用于P3后台/探索任务"
            }
        }
    
    def save_rules(self):
        """保存触发规则"""
        with open(self.rules_file, 'w') as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)
    
    def save_modes(self):
        """保存响应模式配置"""
        with open(self.modes_file, 'w') as f:
            json.dump(self.modes, f, ensure_ascii=False, indent=2)
    
    def get_rule(self, name: str) -> Optional[Dict]:
        """获取指定规则"""
        for rule in self.rules:
            if rule['name'] == name:
                return rule
        return None
    
    def get_rules_by_mode(self, mode: str) -> List[Dict]:
        """获取指定模式的规则"""
        return [r for r in self.rules if r.get('response_mode') == mode and r.get('enabled', True)]
    
    def get_mode_config(self, mode: str) -> Optional[Dict]:
        """获取响应模式配置"""
        return self.modes.get(mode)
    
    def add_rule(self, rule: Dict):
        """添加规则"""
        # 检查是否已存在
        existing = self.get_rule(rule['name'])
        if existing:
            # 更新
            self.rules = [r if r['name'] != rule['name'] else rule for r in self.rules]
        else:
            # 添加
            self.rules.append(rule)
        
        self.save_rules()
    
    def remove_rule(self, name: str) -> bool:
        """移除规则"""
        initial_len = len(self.rules)
        self.rules = [r for r in self.rules if r['name'] != name]
        
        if len(self.rules) < initial_len:
            self.save_rules()
            return True
        return False
    
    def enable_rule(self, name: str):
        """启用规则"""
        rule = self.get_rule(name)
        if rule:
            rule['enabled'] = True
            self.save_rules()
    
    def disable_rule(self, name: str):
        """禁用规则"""
        rule = self.get_rule(name)
        if rule:
            rule['enabled'] = False
            self.save_rules()
    
    def evaluate_event(self, event: Dict) -> Dict:
        """
        评估事件，返回匹配的规则和响应模式
        
        参数:
            event: ClawshellEvent字典
        
        返回:
            {
                'matched_rule': Optional[Dict],
                'response_mode': str,
                'hermes_action': str,
                'reason': str
            }
        """
        matched_rule = None
        best_priority = -1
        
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
            
            if self._match_condition(event, rule['condition']):
                # 计算优先级 (instant=0, fast=1, standard=2, batch=3)
                mode_priority = ['instant', 'fast', 'standard', 'batch'].index(
                    rule.get('response_mode', 'standard')
                )
                
                if mode_priority < best_priority or best_priority < 0:
                    best_priority = mode_priority
                    matched_rule = rule
        
        if matched_rule:
            return {
                'matched_rule': matched_rule,
                'response_mode': matched_rule['response_mode'],
                'hermes_action': matched_rule['hermes_action'],
                'reason': f"Rule: {matched_rule['name']}"
            }
        
        # 默认处理
        return {
            'matched_rule': None,
            'response_mode': 'standard',
            'hermes_action': 'summarize',
            'reason': 'Default (no rule matched)'
        }
    
    def _match_condition(self, event: Dict, condition: Dict) -> bool:
        """检查事件是否匹配条件"""
        for key, value in condition.items():
            if key == 'event_type':
                if value not in event.get('event_type', ''):
                    return False
            
            elif key == 'severity':
                metadata = event.get('metadata', {})
                if event.get('payload', {}).get('severity') != value:
                    if metadata.get('severity') != value:
                        return False
            
            elif key == 'task_type':
                event_task_type = event.get('task_type', '')
                if isinstance(value, list):
                    if event_task_type not in value:
                        return False
                else:
                    if event_task_type != value:
                        return False
            
            elif key == 'priority':
                event_priority = event.get('priority', 'P2')
                if isinstance(value, list):
                    if event_priority not in value:
                        return False
                else:
                    if event_priority != value:
                        return False
            
            elif key.startswith('metadata.') or key.startswith('payload.'):
                # 嵌套字段匹配
                prefix, field_name = key.split('.', 1)
                source = event.get(prefix, {})
                if source.get(field_name) != value:
                    return False
            
            else:
                # 直接字段匹配
                if event.get(key) != value:
                    return False
        
        return True
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules if r.get('enabled', True)]),
            'by_mode': {
                mode: len(self.get_rules_by_mode(mode))
                for mode in ['instant', 'fast', 'standard', 'batch']
            },
            'modes_configured': list(self.modes.keys())
        }


def main():
    """测试入口"""
    config = TriggerConfig()
    
    print("=== TriggerConfig 测试 ===\n")
    
    # 打印统计
    stats = config.get_stats()
    print(f"规则统计: {stats}")
    
    # 测试事件评估
    test_events = [
        {
            'event_type': 'clawshell.error.critical',
            'severity': 'critical',
            'priority': 'P0',
            'task_type': 'execution'
        },
        {
            'event_type': 'clawshell.task.completed',
            'priority': 'P1',
            'task_type': 'analysis'
        },
        {
            'event_type': 'clawshell.task.completed',
            'priority': 'P3',
            'task_type': 'maintenance'
        }
    ]
    
    print("\n=== 事件评估测试 ===")
    for event in test_events:
        result = config.evaluate_event(event)
        print(f"\n事件: {event['event_type']}")
        print(f"  匹配规则: {result['matched_rule']['name'] if result['matched_rule'] else 'None'}")
        print(f"  响应模式: {result['response_mode']}")
        print(f"  Hermes动作: {result['hermes_action']}")
        print(f"  原因: {result['reason']}")


if __name__ == "__main__":
    main()
