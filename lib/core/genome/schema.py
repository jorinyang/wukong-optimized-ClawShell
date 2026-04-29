"""
Genome Schema - ClawShell v0.1
=============================

基因组格式定义。
每个Agent的知识以结构化文档形式存储。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import yaml


class AgentType(Enum):
    """Agent类型"""
    OPENCLAW = "openclaw"
    HERMES = "hermes"
    SHARED = "shared"


@dataclass
class KnowledgeEntry:
    """知识条目"""
    key: str
    value: Any
    category: str = "general"
    source: str = None
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str
    description: str
    solution: str
    occurrences: int = 0
    last_occurrence: str = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "error_type": self.error_type,
            "description": self.description,
            "solution": self.solution,
            "occurrences": self.occurrences,
            "last_occurrence": self.last_occurrence,
            "tags": self.tags,
        }


@dataclass
class SkillState:
    """技能状态"""
    skill_name: str
    status: str = "active"  # active, disabled, evolving
    version: str = "1.0.0"
    config: Dict = field(default_factory=dict)
    performance: float = 1.0  # 0-1
    last_used: str = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "skill_name": self.skill_name,
            "status": self.status,
            "version": self.version,
            "config": self.config,
            "performance": self.performance,
            "last_used": self.last_used,
            "tags": self.tags,
        }


@dataclass
class EvolutionRecord:
    """进化记录"""
    version: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    changes: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    from_version: str = None
    notes: str = None
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "changes": self.changes,
            "improvements": self.improvements,
            "from_version": self.from_version,
            "notes": self.notes,
        }


@dataclass
class Genome:
    """
    基因组
    ======
    
    存储Agent的核心知识、状态和配置。
    """
    agent_type: AgentType
    version: str = "0.1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 核心知识
    knowledge: List[KnowledgeEntry] = field(default_factory=list)
    
    # 用户偏好
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # 错误模式库
    error_patterns: List[ErrorPattern] = field(default_factory=list)
    
    # 技能状态
    skills: List[SkillState] = field(default_factory=list)
    
    # 进化历史
    evolution: List[EvolutionRecord] = field(default_factory=list)
    
    # 当前状态
    current_task: str = None
    context: str = None
    pending_issues: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "agent_type": self.agent_type.value if isinstance(self.agent_type, AgentType) else self.agent_type,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "knowledge": [k.to_dict() if hasattr(k, 'to_dict') else k for k in self.knowledge],
            "preferences": self.preferences,
            "error_patterns": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.error_patterns],
            "skills": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.skills],
            "evolution": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.evolution],
            "current_task": self.current_task,
            "context": self.context,
            "pending_issues": self.pending_issues,
            "metadata": self.metadata,
        }
    
    def to_yaml(self) -> str:
        """转换为YAML格式"""
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Genome":
        """从字典创建"""
        agent_type = data.get("agent_type", "shared")
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)
        
        return cls(
            agent_type=agent_type,
            version=data.get("version", "0.1.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            knowledge=[KnowledgeEntry(**k) if isinstance(k, dict) else k for k in data.get("knowledge", [])],
            preferences=data.get("preferences", {}),
            error_patterns=[ErrorPattern(**e) if isinstance(e, dict) else e for e in data.get("error_patterns", [])],
            skills=[SkillState(**s) if isinstance(s, dict) else s for s in data.get("skills", [])],
            evolution=[EvolutionRecord(**e) if isinstance(e, dict) else e for e in data.get("evolution", [])],
            current_task=data.get("current_task"),
            context=data.get("context"),
            pending_issues=data.get("pending_issues", []),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Genome":
        """从YAML创建"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    def add_knowledge(self, key: str, value: Any, category: str = "general", source: str = None, confidence: float = 1.0):
        """添加知识"""
        entry = KnowledgeEntry(
            key=key,
            value=value,
            category=category,
            source=source,
            confidence=confidence,
        )
        self.knowledge.append(entry)
        self.updated_at = datetime.now().isoformat()
    
    def add_error_pattern(self, error_type: str, description: str, solution: str, tags: List[str] = None):
        """添加错误模式"""
        pattern = ErrorPattern(
            error_type=error_type,
            description=description,
            solution=solution,
            tags=tags or [],
        )
        self.error_patterns.append(pattern)
        self.updated_at = datetime.now().isoformat()
    
    def record_evolution(self, version: str, changes: List[str], improvements: List[str] = None, notes: str = None):
        """记录进化"""
        record = EvolutionRecord(
            version=version,
            changes=changes,
            improvements=improvements or [],
            from_version=self.version,
            notes=notes,
        )
        self.evolution.append(record)
        self.version = version
        self.updated_at = datetime.now().isoformat()
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """获取知识"""
        for entry in self.knowledge:
            if entry.key == key:
                return entry.value
        return None
    
    def find_error_solution(self, error_type: str) -> Optional[str]:
        """查找错误解决方案"""
        for pattern in self.error_patterns:
            if pattern.error_type == error_type:
                return pattern.solution
        return None


@dataclass
class HeritageRecord:
    """
    传承记录
    =========
    
    记录一次传承事件。
    """
    from_version: str
    to_version: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    heritage_type: str = "restart"  # restart, upgrade, migration
    knowledge_transferred: int = 0
    errors_transferred: int = 0
    skills_transferred: int = 0
    notes: str = None
    
    def to_dict(self) -> Dict:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "timestamp": self.timestamp,
            "heritage_type": self.heritage_type,
            "knowledge_transferred": self.knowledge_transferred,
            "errors_transferred": self.errors_transferred,
            "skills_transferred": self.skills_transferred,
            "notes": self.notes,
        }
