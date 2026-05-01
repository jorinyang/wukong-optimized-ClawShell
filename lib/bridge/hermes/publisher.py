#!/usr/bin/env python3
# hermes_bridge/publisher.py
"""
EventBus发布者

向EventBus发布Hermes事件
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import uuid


class EventBusPublisher:
    """
    EventBus发布者
    
    职责：
    1. 将Hermes事件写入EventBus目录
    2. 提供事件查询接口
    3. 事件归档管理
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.eventbus_path = Path(self.config.get('path', '~/.real/workspace/shared/eventbus')).expanduser()
        self.hermes_path = self.eventbus_path / 'hermes'
        self.running = False
        self.published_count = 0
    
    def _default_config(self) -> Dict:
        return {
            'path': '~/.real/workspace/shared/eventbus',
            'hermes_prefix': 'hermes.',
            'auto_archive': True,
            'archive_after_days': 7
        }
    
    def start(self):
        """启动发布者"""
        self.running = True
        self._ensure_directories()
    
    def stop(self):
        """停止发布者"""
        self.running = False
    
    def _ensure_directories(self):
        """确保目录存在"""
        self.eventbus_path.mkdir(parents=True, exist_ok=True)
        self.hermes_path.mkdir(parents=True, exist_ok=True)
    
    async def publish(self, event_type: str, payload: Dict, metadata: Dict = None) -> str:
        """
        发布事件
        
        参数:
            event_type: 事件类型，如 'hermes.insight.generated'
            payload: 事件载荷
            metadata: 事件元数据
        
        返回:
            str: 事件ID
        """
        from .events import HermesEvent
        
        event = HermesEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source='hermes_bridge',
            timestamp=datetime.now().isoformat(),
            payload=payload,
            metadata=metadata or {}
        )
        
        return await self._write_event(event)
    
    async def _write_event(self, event) -> str:
        """写入事件到文件"""
        filename = f"{event.event_type}.{event.event_id}.json"
        filepath = self.hermes_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(event.__dict__, f, ensure_ascii=False, indent=2)
        
        self.published_count += 1
        
        return event.event_id
    
    async def publish_insight(self, insight: Dict) -> str:
        """
        发布洞察事件
        
        参数:
            insight: 洞察内容
        
        返回:
            str: 事件ID
        """
        return await self.publish(
            event_type='hermes.insight.generated',
            payload={
                'insight': insight,
                'source': 'hermes_bridge'
            },
            metadata={
                'insight_type': insight.get('type', 'unknown'),
                'priority': insight.get('priority', 'P2')
            }
        )
    
    async def publish_skill(self, skill: Dict) -> str:
        """
        发布技能创建事件
        
        参数:
            skill: 技能内容
        
        返回:
            str: 事件ID
        """
        return await self.publish(
            event_type='hermes.skill.created',
            payload={
                'skill': skill,
                'source': 'hermes_bridge'
            },
            metadata={
                'skill_name': skill.get('name', 'unknown'),
                'skill_type': skill.get('type', 'unknown')
            }
        )
    
    async def publish_pattern(self, pattern: Dict) -> str:
        """
        发布模式识别事件
        
        参数:
            pattern: 模式内容
        
        返回:
            str: 事件ID
        """
        return await self.publish(
            event_type='hermes.pattern.detected',
            payload={
                'pattern': pattern,
                'source': 'hermes_bridge'
            },
            metadata={
                'pattern_type': pattern.get('type', 'unknown')
            }
        )
    
    async def publish_status(self, status: str, details: Dict = None) -> str:
        """
        发布状态事件
        
        参数:
            status: 状态 (started, stopped, error, etc.)
            details: 详细信息
        
        返回:
            str: 事件ID
        """
        return await self.publish(
            event_type='hermes.status',
            payload={
                'status': status,
                'details': details or {}
            },
            metadata={
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def get_recent_events(self, event_type: str = None, limit: int = 10) -> list:
        """
        获取最近的事件
        
        参数:
            event_type: 事件类型过滤 (可选)
            limit: 返回数量限制
        
        返回:
            list: 事件列表
        """
        events = []
        
        search_path = self.hermes_path if event_type and event_type.startswith('hermes') else self.eventbus_path
        
        if not search_path.exists():
            return events
        
        pattern = f"{event_type}*.json" if event_type else "*.json"
        
        for event_file in sorted(search_path.glob(pattern), reverse=True)[:limit]:
            try:
                with open(event_file) as f:
                    events.append(json.load(f))
            except Exception as e:
                print(f"[ERROR] Read event error: {e}")
        
        return events
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'published_count': self.published_count,
            'running': self.running,
            'eventbus_path': str(self.eventbus_path),
            'hermes_path': str(self.hermes_path)
        }
    
    def archive_old_events(self, days: int = None):
        """归档旧事件"""
        if days is None:
            days = self.config.get('archive_after_days', 7)
        
        archive_dir = self.eventbus_path / 'archive'
        archive_dir.mkdir(exist_ok=True)
        
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        for event_file in self.eventbus_path.glob('hermes.*.json'):
            if event_file.stat().st_mtime < cutoff:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archived_name = f"{timestamp}_{event_file.name}"
                event_file.rename(archive_dir / archived_name)


if __name__ == "__main__":
    # 测试代码
    print("=== EventBusPublisher 测试 ===\n")
    
    import asyncio
    
    publisher = EventBusPublisher({
        'path': '/tmp/test_eventbus'
    })
    
    async def test_publish():
        await publisher.start()
        
        # 测试发布洞察
        insight_id = await publisher.publish_insight({
            'type': 'pattern_recognition',
            'content': '检测到重复错误模式',
            'priority': 'P1'
        })
        print(f"[PUBLISHED] Insight: {insight_id}")
        
        # 测试发布技能
        skill_id = await publisher.publish_skill({
            'name': 'test_skill',
            'type': 'workflow',
            'content': '# Test Skill'
        })
        print(f"[PUBLISHED] Skill: {skill_id}")
        
        # 测试发布状态
        status_id = await publisher.publish_status('test', {'test': True})
        print(f"[PUBLISHED] Status: {status_id}")
        
        # 获取统计
        stats = publisher.get_stats()
        print(f"\n统计: {stats}")
        
        # 获取最近事件
        recent = publisher.get_recent_events('hermes.insight')
        print(f"\n最近洞察事件: {len(recent)}")
        
        await publisher.stop()
    
    asyncio.run(test_publish())
