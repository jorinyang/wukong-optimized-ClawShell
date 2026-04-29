#!/usr/bin/env python3
# hermes_bridge/bridge.py
"""
Hermes双脑协同桥接器主模块

集成所有组件，提供完整的Hermes-OpenClaw双向通信
"""

import asyncio
import json
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from hermes_bridge.events import (
    ClawshellEvent, HermesEvent,
    TaskType, Priority, Environment, ResponseMode,
    EventType, priority_to_response_time
)
from hermes_bridge.classifier import PriorityClassifier
from hermes_bridge.matcher import ResponseModeMatcher
from hermes_bridge.subscriber import EventBusSubscriber
from hermes_bridge.publisher import EventBusPublisher
from hermes_bridge.queue import MessageQueue
from hermes_bridge.trigger_config import TriggerConfig
from hermes_bridge.scenario_integrator import HermesScenarioIntegrator


class HermesBridge:
    """
    Hermes双脑协同桥接器
    
    职责：
    1. 订阅OpenClaw EventBus事件
    2. 分类任务优先级
    3. 匹配Hermes响应模式
    4. 管理消息队列
    5. 分发到Hermes处理
    6. 发布Hermes事件回EventBus
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        
        # 初始化组件
        self.classifier = PriorityClassifier(self.config.get('classifier'))
        self.matcher = ResponseModeMatcher(self.config.get('matcher'))
        self.subscriber = EventBusSubscriber(self.config.get('subscriber'))
        self.publisher = EventBusPublisher(self.config.get('publisher'))
        self.queue = MessageQueue(self.config.get('queue'))
        
        # Phase 1.5: 分级触发配置
        self.trigger_config = TriggerConfig()
        self.scenario_integrator = HermesScenarioIntegrator()
        
        # 状态
        self.running = False
        self.started_at: Optional[datetime] = None
        
        # 统计
        self.stats = {
            'events_received': 0,
            'events_classified': 0,
            'events_dispatched': 0,
            'insights_received': 0,
            'skills_created': 0,
            'errors': 0
        }
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        home = Path.home()
        return {
            'subscriber': {
                'path': str(home / '.openclaw/workspace/shared/eventbus'),
                'patterns': ['clawshell.*.json'],
                'poll_interval': 1.0
            },
            'publisher': {
                'path': str(home / '.openclaw/workspace/shared/eventbus')
            },
            'queue': {
                'max_size': 1000,
                'batch_size': 10
            },
            'classifier': {},
            'matcher': {},
            'dispatch': {
                'instant_webhook': 'http://localhost:30000/receive',
                'batch_interval': 3600
            }
        }
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())
    
    async def start(self):
        """启动桥接器"""
        if self.running:
            print("[WARN] Bridge already running")
            return
        
        print("[INFO] Starting Hermes Bridge...")
        
        self.running = True
        self.started_at = datetime.now()
        
        # 启动组件
        await self.publisher.start()
        self.subscriber.start()
        
        # 订阅事件
        self.subscriber.subscribe(
            ['clawshell.task.*', 'clawshell.error.*', 'clawshell.session.*'],
            self.handle_event
        )
        
        # 发布启动状态
        await self.publisher.publish_status('started', {
            'version': '0.8.3',
            'config': self.config
        })
        
        print(f"[INFO] Hermes Bridge started at {self.started_at}")
        
        # 启动处理循环
        asyncio.create_task(self._process_loop())
    
    async def stop(self):
        """停止桥接器"""
        if not self.running:
            return
        
        print("[INFO] Stopping Hermes Bridge...")
        
        self.running = False
        
        # 停止组件
        self.subscriber.stop()
        await self.publisher.stop()
        
        # 发布停止状态
        await self.publisher.publish_status('stopped', {
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'stats': self.stats
        })
        
        print("[INFO] Hermes Bridge stopped")
    
    async def handle_event(self, event: ClawshellEvent):
        """
        处理接收到的OpenClaw事件
        
        参数:
            event: ClawshellEvent
        """
        self.stats['events_received'] += 1
        
        try:
            # 1. 分类优先级
            classification = self.classifier.classify(event)
            self.stats['events_classified'] += 1
            
            # 2. 匹配响应模式
            response_mode = self.matcher.match_from_event(event, classification)
            
            # 3. 入队
            queued_item = {
                'event': event,
                'classification': classification,
                'response_mode': response_mode,
                'received_at': datetime.now().isoformat()
            }
            
            await self.queue.enqueue(queued_item)
            self.stats['events_dispatched'] += 1
            
            print(f"[DISPATCH] {event.event_type} -> {response_mode.value} ({classification['reason']})")
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"[ERROR] Handle event error: {e}")
            await self._handle_error(event, e)
    
    async def _process_loop(self):
        """消息处理循环"""
        print("[INFO] Starting message processing loop...")
        
        while self.running:
            try:
                # 按响应模式处理队列
                for mode in ['instant', 'fast', 'standard', 'batch']:
                    batch = await self.queue.dequeue_batch(mode=mode, max_count=5)
                    
                    if batch:
                        await self._dispatch_batch(mode, batch)
                
                # 批量间隔
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.stats['errors'] += 1
                print(f"[ERROR] Process loop error: {e}")
                await asyncio.sleep(5)
    
    async def _dispatch_batch(self, mode: str, items: List[Dict]):
        """
        分发批量消息到Hermes
        
        参数:
            mode: 响应模式
            items: 消息列表
        """
        if mode == 'instant':
            # 即时：逐个发送
            for item in items:
                await self._dispatch_to_hermes(item)
        else:
            # 批量：汇总发送
            await self._dispatch_batch_to_hermes(mode, items)
    
    async def _dispatch_to_hermes(self, item: Dict):
        """发送单个消息到Hermes"""
        event = item['event']
        classification = item['classification']
        response_mode = item['response_mode']
        
        # 构建Hermes消息
        hermes_payload = {
            'original_event': event.event_type,
            'task_type': classification['task_type'].value,
            'priority': classification['priority'].value,
            'environment': classification['environment'].value,
            'response_mode': response_mode.value,
            'response_time': priority_to_response_time(classification['priority']),
            'payload': event.payload,
            'metadata': event.metadata
        }
        
        # 发送到Hermes (通过HTTP webhook)
        # TODO: 实现实际的Hermes API调用
        print(f"[HERMES] Sending to Hermes: {hermes_payload['original_event']}")
    
    async def _dispatch_batch_to_hermes(self, mode: str, items: List[Dict]):
        """批量发送消息到Hermes"""
        batch_summary = {
            'mode': mode,
            'count': len(items),
            'items': [
                {
                    'event': item['event'].event_type,
                    'priority': item['classification']['priority'].value,
                    'reason': item['classification']['reason']
                }
                for item in items
            ]
        }
        
        print(f"[HERMES] Batch dispatch ({mode}): {len(items)} items")
        # TODO: 实现实际的Hermes批量API调用
    
    async def _handle_error(self, event: ClawshellEvent, error: Exception):
        """错误处理"""
        await self.publisher.publish(
            event_type='hermes.bridge.error',
            payload={
                'original_event': event.event_type,
                'error': str(error)
            }
        )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'running': self.running,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'queue_stats': self.queue.get_stats(),
            'subscriber_stats': self.subscriber.get_stats(),
            'publisher_stats': self.publisher.get_stats()
        }
    
    async def handle_hermes_event(self, event: HermesEvent):
        """
        处理来自Hermes的事件
        
        参数:
            event: HermesEvent
        """
        if event.event_type == 'hermes.insight.generated':
            self.stats['insights_received'] += 1
            print(f"[INSIGHT] Received insight from Hermes")
        
        elif event.event_type == 'hermes.skill.created':
            self.stats['skills_created'] += 1
            print(f"[SKILL] Created skill from Hermes")


async def main():
    """主入口"""
    print("=" * 60)
    print("Hermes × ClawShell 双脑协同桥接器")
    print("版本: 0.8.3")
    print("=" * 60)
    
    bridge = HermesBridge()
    
    try:
        await bridge.start()
        
        # 保持运行
        while bridge.running:
            await asyncio.sleep(10)
            
            # 定期打印统计
            stats = bridge.get_stats()
            print(f"\n[STATS] Events: {stats['events_received']}, "
                  f"Classified: {stats['events_classified']}, "
                  f"Dispatched: {stats['events_dispatched']}")
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
