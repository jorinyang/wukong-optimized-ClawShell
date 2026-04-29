#!/usr/bin/env python3
# hermes_bridge/events.py
"""
事件类型定义

定义ClawShell和Hermes之间通信的事件类型
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


class TaskType(Enum):
    """任务类型"""
    EXECUTION = "execution"          # 任务执行类
    ANALYSIS = "analysis"             # 分析研究类
    CREATION = "creation"            # 创作内容类
    DECISION = "decision"           # 决策判断类
    MAINTENANCE = "maintenance"      # 维护操作类
    UNKNOWN = "unknown"              # 未知类型


class Priority(Enum):
    """优先级"""
    P0_CRITICAL = "P0"   # 系统故障/数据损失 - 即时响应
    P1_HIGH = "P1"       # 重要任务/客户相关 - 2小时内
    P2_NORMAL = "P2"      # 常规任务 - 24小时内
    P3_LOW = "P3"        # 后台任务/探索 - 周级


class Environment(Enum):
    """环境"""
    PRODUCTION = "production"      # 生产环境 - 高可靠性
    STAGING = "staging"           # 预发环境 - 验证模式
    DEVELOPMENT = "development"   # 开发环境 - 探索模式


class ResponseMode(Enum):
    """Hermes响应模式"""
    INSTANT = "instant"       # 即时介入 (<5min)
    FAST = "fast"             # 快速响应 (<2hr)
    STANDARD = "standard"     # 标准流程 (<24hr)
    BATCH = "batch"           # 批量处理 (<7days)


class EventType(Enum):
    """ClawShell事件类型"""
    # 任务事件
    TASK_SUBMITTED = "clawshell.task.submitted"
    TASK_STARTED = "clawshell.task.started"
    TASK_COMPLETED = "clawshell.task.completed"
    TASK_FAILED = "clawshell.task.failed"
    
    # 错误事件
    ERROR_OCCURRED = "clawshell.error.occurred"
    ERROR_CRITICAL = "clawshell.error.critical"
    
    # 会话事件
    SESSION_START = "clawshell.session.start"
    SESSION_END = "clawshell.session.end"
    
    # Hermes事件
    HERMES_INSIGHT = "hermes.insight.generated"
    HERMES_SKILL = "hermes.skill.created"
    HERMES_PATTERN = "hermes.pattern.detected"
    HERMES_STATUS = "hermes.status"


@dataclass
class ClawshellEvent:
    """ClawShell事件"""
    event_id: str
    event_type: str
    source: str
    timestamp: str
    task_type: Optional[str] = None
    priority: Optional[str] = None
    environment: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ClawshellEvent':
        data = json.loads(json_str)
        return cls(**data)
    
    @property
    def task_type_enum(self) -> TaskType:
        return TaskType(self.task_type) if self.task_type else TaskType.UNKNOWN
    
    @property
    def priority_enum(self) -> Priority:
        return Priority(self.priority) if self.priority else Priority.P2_NORMAL
    
    @property
    def environment_enum(self) -> Environment:
        return Environment(self.environment) if self.environment else Environment.DEVELOPMENT


@dataclass
class HermesEvent:
    """Hermes事件"""
    event_id: str
    event_type: str
    source: str = "hermes_bridge"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    response_mode: str = "standard"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'HermesEvent':
        data = json.loads(json_str)
        return cls(**data)
    
    @property
    def response_mode_enum(self) -> ResponseMode:
        return ResponseMode(self.response_mode)


# 事件类型到任务类型的映射
TASK_TYPE_KEYWORDS = {
    TaskType.EXECUTION: ['execute', 'run', 'task', 'job', 'perform', 'do'],
    TaskType.ANALYSIS: ['analyze', 'research', 'investigate', 'study', 'examine', 'review'],
    TaskType.CREATION: ['create', 'write', 'generate', 'design', 'produce', 'build'],
    TaskType.DECISION: ['decide', 'choose', 'select', 'evaluate', 'judge', 'assess'],
    TaskType.MAINTENANCE: ['maintain', 'fix', 'repair', 'update', 'patch', 'improve']
}


def identify_task_type(event_type: str, payload: Dict = None) -> TaskType:
    """根据事件类型识别任务类型"""
    event_type_lower = event_type.lower()
    payload_str = json.dumps(payload or {}).lower()
    
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if any(kw in event_type_lower or kw in payload_str for kw in keywords):
            return task_type
    
    return TaskType.EXECUTION  # 默认执行类


def priority_to_response_time(priority: Priority) -> str:
    """优先级对应的响应时间"""
    return {
        Priority.P0_CRITICAL: "<5分钟",
        Priority.P1_HIGH: "<2小时",
        Priority.P2_NORMAL: "<24小时",
        Priority.P3_LOW: "<7天"
    }.get(priority, "<24小时")


if __name__ == "__main__":
    # 测试代码
    print("=== 事件类型测试 ===")
    
    # 测试ClawshellEvent
    event = ClawshellEvent(
        event_id="test-001",
        event_type="clawshell.task.execution.P1",
        source="openclaw",
        timestamp=datetime.now().isoformat(),
        payload={"task": "test_task"},
        metadata={"environment": "production"}
    )
    
    print(f"事件: {event.event_type}")
    print(f"任务类型: {identify_task_type(event.event_type, event.payload)}")
    print(f"JSON: {event.to_json()[:100]}...")
