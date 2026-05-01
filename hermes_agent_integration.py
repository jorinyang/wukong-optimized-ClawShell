#!/usr/bin/env python3
"""
Hermes Agent × ClawShell 集成模块
====================================
将 Hermes Agent 接入 ClawShell 生态，作为"前脑/进化引擎"

功能:
1. 向 ClawShell NodeRegistry 注册为 HERMES 节点
2. 通过文件系统 EventBus 与悟空双向通信
3. 消费悟空事件，生成洞察/技能/模式识别
4. 发布 Hermes 洞察回 EventBus

# 通信方式:
- 文件系统 EventBus: ~/.real/eventbus/events/YYYY-MM-DD/
- 事件格式: JSON，符合 ClawshellEvent/HermesEvent 规范
"""

import sys
import json
import time
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

# ClawShell 路径
CLAWSHELL_PATH = Path(r"C:\Users\Aorus\.ClawShell")
sys.path.insert(0, str(CLAWSHELL_PATH))

# 导入 ClawShell 组件
try:
    from lib.layer4.node_registry import NodeRegistry, NodeType, NodeStatus
    from lib.core.eventbus.schema import Event, EventType, EventSource
    from lib.core.eventbus.core import EventBus, get_eventbus
    CLAWSHELL_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] ClawShell 导入失败: {e}")
    CLAWSHELL_AVAILABLE = False


# ============ 配置 ============

# 修正后的路径: 悟空实际 EventBus 路径
EVENTBUS_DIR = Path.home() / ".openclaw" / "eventbus"
EVENTBUS_EVENTS_DIR = EVENTBUS_DIR / "events"
EVENTBUS_CONDITIONS_DIR = EVENTBUS_DIR / "conditions"
EVENTBUS_DEADLETTER_DIR = EVENTBUS_DIR / "dead_letter"

# NodeRegistry 实际路径
NODEREGISTRY_PATH = Path.home() / ".openclaw" / ".node_registry.json"

HERMES_NODE_ID = "hermes-agent-primary"
HERMES_NODE_NAME = "Hermes Agent (前脑进化引擎)"
POLL_INTERVAL = 1.0  # 事件轮询间隔(秒)


# ============ Hermes 事件定义 ============

@dataclass
class HermesInsight:
    """Hermes 洞察"""
    insight_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_event_id: str = ""
    insight_type: str = "analysis"  # analysis/pattern/skill/review/prediction
    priority: str = "P2"  # P0/P1/P2/P3
    content: str = ""
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.8
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "insight_id": self.insight_id,
            "source_event_id": self.source_event_id,
            "insight_type": self.insight_type,
            "priority": self.priority,
            "content": self.content,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


@dataclass 
class HermesSkill:
    """Hermes 生成的技能"""
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    trigger_words: List[str] = field(default_factory=list)
    content: str = ""
    source_event_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "trigger_words": self.trigger_words,
            "content": self.content,
            "source_event_id": self.source_event_id,
            "timestamp": self.timestamp
        }


# ============ Hermes ClawShell 集成器 ============

class HermesClawShellIntegration:
    """
    Hermes × ClawShell 集成器
    =========================
    
    生态位: 前脑/进化引擎 (Layer 5)
    
    职责:
    - 注册为 ClawShell HERMES 节点
    - 订阅悟空事件 (clawshell.task.*, clawshell.error.*)
    - 生成洞察 (insight.generated)
    - 生成技能 (skill.created)
    - 发布回 EventBus
    """
    
    def __init__(self):
        self.node_registry = NodeRegistry() if CLAWSHELL_AVAILABLE else None
        self.eventbus = get_eventbus() if CLAWSHELL_AVAILABLE else None
        self.node_id = None
        self.running = False
        self.poll_thread = None
        self.processed_events = set()
        
        # 统计
        self.stats = {
            "events_received": 0,
            "insights_generated": 0,
            "skills_generated": 0,
            "patterns_detected": 0
        }
        
        # 回调注册
        self.insight_callbacks: List[Callable] = []
        self.skill_callbacks: List[Callable] = []
    
    def register_to_clawshell(self, capabilities: List[str] = None):
        """
        注册 Hermes 到 ClawShell 节点注册表
        
        节点类型: NodeType.HERMES
        能力: 深度思考、洞察生成、模式识别、技能进化
        """
        if not self.node_registry:
            print("[WARN] NodeRegistry 不可用，跳过注册")
            return None
        
        capabilities = capabilities or [
            "deep_thinking",
            "insight_generation",
            "pattern_recognition",
            "skill_evolution",
            "trend_analysis",
            "review_engine",
            "knowledge_coach"
        ]
        
        self.node_id = self.node_registry.register(
            name=HERMES_NODE_NAME,
            node_type=NodeType.HERMES,
            capabilities=capabilities,
            metadata={
                "role": "front_brain",
                "layer": "L5",
                "version": "1.0.0",
                "integration_type": "eventbus"
            }
        )
        
        print(f"[✓] Hermes 已注册到 ClawShell: {self.node_id}")
        print(f"    节点类型: HERMES")
        print(f"    能力: {capabilities}")
        return self.node_id
    
    def start(self):
        """启动 Hermes 集成服务"""
        if self.running:
            print("[WARN] Hermes 集成已在运行")
            return
        
        self.running = True
        
        # 注册节点
        self.register_to_clawshell()
        
        # 启动事件轮询
        self.poll_thread = threading.Thread(target=self._event_poll_loop, daemon=True)
        self.poll_thread.start()
        
        print("[✓] Hermes × ClawShell 集成已启动")
        print(f"    EventBus 路径: {EVENTBUS_DIR}")
        print(f"    事件目录: {EVENTBUS_EVENTS_DIR}/YYYY-MM-DD/")
        print(f"    NodeRegistry: {NODEREGISTRY_PATH}")
        print(f"    轮询间隔: {POLL_INTERVAL}s")
    
    def stop(self):
        """停止 Hermes 集成服务"""
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=5)
        
        # 更新节点状态为离线
        if self.node_registry and self.node_id:
            self.node_registry.update_status(self.node_id, NodeStatus.OFFLINE)
        
        print("[✓] Hermes × ClawShell 集成已停止")
    
    def _event_poll_loop(self):
        """事件轮询循环"""
        while self.running:
            try:
                self._poll_clawshell_events()
                time.sleep(POLL_INTERVAL)
            except Exception as e:
                print(f"[ERROR] 轮询错误: {e}")
                time.sleep(5)
    
    def _poll_clawshell_events(self):
        """轮询 ClawShell 事件 - 修正为实际悟空 EventBus 路径"""
        # 悟空实际 EventBus 路径: ~/.real/eventbus/events/YYYY-MM-DD/*.json
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
        
        if not today_events_dir.exists():
            return
        
        # 查找今日所有事件文件
        for event_file in sorted(today_events_dir.glob("*.json")):
            if event_file.name in self.processed_events:
                continue
            
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
                
                # 处理来自悟空系统的事件 (source 可能是多种标识)
                source = event_data.get("source", "")
                event_type = event_data.get("type", "")
                # 过滤: 不处理 Hermes 自己发布的事件，处理 clawshell/悟空相关事件
                if source == "hermes_agent":
                    pass  # 跳过自己发布的事件
                elif "clawshell." in event_type or "wukong." in event_type or source in [
                    "clawshell", "wukong", "wukong-agent", "mcp_runtime", 
                    "integration-test", "e2e-test", "test_boot", "smoke_test"
                ]:
                    self._handle_clawshell_event(event_data)
                
                self.processed_events.add(event_file.name)
                
            except Exception as e:
                print(f"[ERROR] 处理事件失败: {e}")
    
    def _handle_clawshell_event(self, event_data: Dict):
        """处理 ClawShell 事件"""
        event_type = event_data.get("type", "")
        event_id = event_data.get("id", "")
        
        print(f"[→] 收到事件: {event_type} ({event_id})")
        self.stats["events_received"] += 1
        
        # 根据事件类型生成不同的 Hermes 响应
        if "task.completed" in event_type:
            self._generate_task_review(event_data)
        elif "error.occurred" in event_type or "error.critical" in event_type:
            self._generate_error_analysis(event_data)
        elif "task.started" in event_type:
            self._generate_task_prediction(event_data)
        elif "system.health_check" in event_type:
            self._generate_health_insight(event_data)
        else:
            # 默认分析
            self._generate_general_insight(event_data)
    
    def _generate_task_review(self, event_data: Dict):
        """生成任务复盘洞察"""
        payload = event_data.get("payload", {})
        task_id = payload.get("task_id", "unknown")
        
        insight = HermesInsight(
            source_event_id=event_data.get("id", ""),
            insight_type="review",
            priority="P2",
            content=f"任务 {task_id} 已完成，建议复盘执行过程中的优化点",
            recommendations=[
                "分析任务执行时间是否符合预期",
                "检查是否有重复或可自动化的步骤",
                "评估输出质量是否达到标准"
            ],
            confidence=0.85
        )
        
        self.publish_insight(insight)
    
    def _generate_error_analysis(self, event_data: Dict):
        """生成错误分析洞察"""
        payload = event_data.get("payload", {})
        error = payload.get("error", "unknown error")
        
        insight = HermesInsight(
            source_event_id=event_data.get("id", ""),
            insight_type="analysis",
            priority="P1",  # 高优先级
            content=f"检测到错误: {error}。建议立即分析根因并制定修复方案",
            recommendations=[
                "检查相关组件的日志输出",
                "验证环境配置是否正确",
                "评估是否需要回滚到稳定版本"
            ],
            confidence=0.9
        )
        
        self.publish_insight(insight)
    
    def _generate_task_prediction(self, event_data: Dict):
        """生成任务预测洞察"""
        payload = event_data.get("payload", {})
        task_type = payload.get("task_type", "unknown")
        
        insight = HermesInsight(
            source_event_id=event_data.get("id", ""),
            insight_type="prediction",
            priority="P3",
            content=f"任务类型 '{task_type}' 已开始，基于历史数据预测可能的风险点",
            recommendations=[
                "监控资源使用情况",
                "准备备用执行方案",
                "设置关键检查点"
            ],
            confidence=0.75
        )
        
        self.publish_insight(insight)
    
    def _generate_health_insight(self, event_data: Dict):
        """生成健康检查洞察"""
        payload = event_data.get("payload", {})
        
        insight = HermesInsight(
            source_event_id=event_data.get("id", ""),
            insight_type="analysis",
            priority="P2",
            content="系统健康检查完成，生成优化建议",
            recommendations=[
                "定期清理过期日志文件",
                "优化高频任务的执行策略",
                "评估新技能的引入价值"
            ],
            confidence=0.8
        )
        
        self.publish_insight(insight)
    
    def _generate_general_insight(self, event_data: Dict):
        """生成通用洞察"""
        event_type = event_data.get("type", "")
        
        insight = HermesInsight(
            source_event_id=event_data.get("id", ""),
            insight_type="analysis",
            priority="P3",
            content=f"收到事件 '{event_type}'，已记录供后续模式分析",
            recommendations=["等待更多数据以识别模式"],
            confidence=0.6
        )
        
        self.publish_insight(insight)
    
    def publish_insight(self, insight: HermesInsight):
        """
        发布洞察到 EventBus - 修正为悟空实际 EventBus 路径
        
        写入: ~/.real/eventbus/events/YYYY-MM-DD/hermes_*.json
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
        today_events_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}_hermes_{insight.insight_id}.json"
        filepath = today_events_dir / filename
        
        event_data = {
            "id": insight.insight_id,
            "type": "hermes.insight.generated",
            "source": "hermes_agent",
            "timestamp": insight.timestamp,
            "payload": insight.to_dict(),
            "trace_id": insight.source_event_id,
            "tags": ["insight", insight.insight_type, insight.priority]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)
        
        self.stats["insights_generated"] += 1
        print(f"[←] 发布洞察: {insight.insight_type} ({insight.insight_id})")
        
        # 触发回调
        for callback in self.insight_callbacks:
            try:
                callback(insight)
            except Exception as e:
                print(f"[ERROR] 洞察回调错误: {e}")
    
    def publish_skill(self, skill: HermesSkill):
        """
        发布技能到 EventBus - 修正为悟空实际 EventBus 路径
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_events_dir = EVENTBUS_EVENTS_DIR / today_str
        today_events_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}_hermes_skill_{skill.skill_id}.json"
        filepath = today_events_dir / filename
        
        event_data = {
            "id": skill.skill_id,
            "type": "hermes.skill.created",
            "source": "hermes_agent",
            "timestamp": skill.timestamp,
            "payload": skill.to_dict(),
            "tags": ["skill", skill.name]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)
        
        self.stats["skills_generated"] += 1
        print(f"[←] 发布技能: {skill.name} ({skill.skill_id})")
        
        # 触发回调
        for callback in self.skill_callbacks:
            try:
                callback(skill)
            except Exception as e:
                print(f"[ERROR] 技能回调错误: {e}")
    
    def _archive_event(self, event_file: Path):
        """归档已处理的事件文件"""
        archive_dir = EVENTBUS_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_name = f"{timestamp}_{event_file.name}"
        
        try:
            event_file.rename(archive_dir / archived_name)
        except Exception:
            pass  # 如果移动失败，忽略
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "node_id": self.node_id,
            "running": self.running,
            "processed_events": len(self.processed_events)
        }
    
    def register_insight_callback(self, callback: Callable):
        """注册洞察回调"""
        self.insight_callbacks.append(callback)
    
    def register_skill_callback(self, callback: Callable):
        """注册技能回调"""
        self.skill_callbacks.append(callback)


# ============ 快捷函数 ============

def create_hermes_integration() -> HermesClawShellIntegration:
    """创建并返回 Hermes ClawShell 集成器"""
    return HermesClawShellIntegration()


def publish_hermes_insight(content: str, insight_type: str = "analysis", 
                          priority: str = "P2", recommendations: List[str] = None):
    """快捷发布 Hermes 洞察"""
    integration = HermesClawShellIntegration()
    
    insight = HermesInsight(
        insight_type=insight_type,
        priority=priority,
        content=content,
        recommendations=recommendations or []
    )
    
    integration.publish_insight(insight)
    return insight.insight_id


def publish_hermes_skill(name: str, description: str, content: str, trigger_words: List[str] = None):
    """快捷发布 Hermes 技能"""
    integration = HermesClawShellIntegration()
    
    skill = HermesSkill(
        name=name,
        description=description,
        content=content,
        trigger_words=trigger_words or []
    )
    
    integration.publish_skill(skill)
    return skill.skill_id


# ============ 主入口 ============

if __name__ == "__main__":
    print("=" * 60)
    print("Hermes Agent × ClawShell 集成模块")
    print("=" * 60)
    
    # 创建集成器
    hermes = HermesClawShellIntegration()
    
    # 启动
    hermes.start()
    
    # 保持运行
    try:
        while hermes.running:
            time.sleep(10)
            stats = hermes.get_stats()
            print(f"\n[STATS] 事件: {stats['events_received']}, "
                  f"洞察: {stats['insights_generated']}, "
                  f"技能: {stats['skills_generated']}")
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    finally:
        hermes.stop()
