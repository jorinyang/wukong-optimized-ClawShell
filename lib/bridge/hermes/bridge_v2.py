#!/usr/bin/env python3
# hermes_bridge/bridge_v2.py
"""
Hermes双脑协同桥接器 v2

集成Phase 1 (EventBus) + Phase 1.5 (分级触发)
"""

import asyncio
import json
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from .events import (
    ClawshellEvent, HermesEvent,
    TaskType, Priority, Environment, ResponseMode,
    EventType, priority_to_response_time
)
from .classifier import PriorityClassifier
from .matcher import ResponseModeMatcher
from .subscriber import EventBusSubscriber
from .publisher import EventBusPublisher
from .queue import MessageQueue
from .trigger_config import TriggerConfig
from .scenario_integrator import HermesScenarioIntegrator


class HermesBridgeV2:
    """
    Hermes双脑协同桥接器 v2
    
    Phase 1 + Phase 1.5 完整实现
    
    新增功能:
    - 分级触发配置
    - Hermes场景集成
    - 事件-场景自动映射
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_default_config()
        
        # Phase 1 组件
        self.classifier = PriorityClassifier(self.config.get('classifier'))
        self.matcher = ResponseModeMatcher(self.config.get('matcher'))
        self.subscriber = EventBusSubscriber(self.config.get('subscriber'))
        self.publisher = EventBusPublisher(self.config.get('publisher'))
        self.queue = MessageQueue(self.config.get('queue'))
        
        # Phase 1.5 组件
        self.trigger_config = TriggerConfig()
        self.scenario_integrator = HermesScenarioIntegrator()
        
        # 状态
        self.running = False
        self.started_at: Optional[datetime] = None
        
        # 统计
        self.stats = {
            # Phase 1 统计
            'events_received': 0,
            'events_classified': 0,
            'events_dispatched': 0,
            # Phase 1.5 统计
            'rules_matched': 0,
            'scenarios_invoked': 0,
            'scenarios_success': 0,
            'scenarios_failed': 0,
            # 通用统计
            'errors': 0
        }
        
        # 信号处理
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
            'matcher': {}
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
        
        print("[INFO] Starting Hermes Bridge v2 (Phase 1 + 1.5)...")
        
        self.running = True
        self.started_at = datetime.now()
        
        # 启动组件
        await self.publisher.start()
        self.subscriber.start()
        
        # 订阅事件
        self.subscriber.subscribe(
            ['clawshell.task.*', 'clawshell.error.*', 'clawshell.session.*', 'clawshell.cron.*'],
            self.handle_event
        )
        
        # 发布启动状态
        await self.publisher.publish_status('started', {
            'version': '0.8.3-phase1.5',
            'phase': 'Phase 1 + 1.5',
            'available_scenarios': self.scenario_integrator.get_available_scenarios()
        })
        
        print(f"[INFO] Hermes Bridge v2 started at {self.started_at}")
        print(f"[INFO] Available Hermes scenarios: {self.scenario_integrator.get_available_scenarios()}")
        
        # 启动处理循环
        asyncio.create_task(self._process_loop())
    
    async def stop(self):
        """停止桥接器"""
        if not self.running:
            return
        
        print("[INFO] Stopping Hermes Bridge v2...")
        
        self.running = False
        
        # 停止组件
        self.subscriber.stop()
        await self.publisher.stop()
        
        # 发布停止状态
        await self.publisher.publish_status('stopped', {
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'stats': self.stats
        })
        
        print("[INFO] Hermes Bridge v2 stopped")
    
    async def handle_event(self, event: ClawshellEvent):
        """
        处理接收到的OpenClaw事件
        
        Phase 1.5增强:
        - 触发规则匹配
        - Hermes场景调用
        """
        self.stats['events_received'] += 1
        
        try:
            # Phase 1: 分类和匹配
            classification = self.classifier.classify(event)
            response_mode = self.matcher.match_from_event(event, classification)
            
            self.stats['events_classified'] += 1
            
            # Phase 1.5: 触发规则评估
            trigger_result = self.trigger_config.evaluate_event({
                'event_type': event.event_type,
                'priority': classification['priority'].value,
                'task_type': classification['task_type'].value,
                'metadata': event.metadata,
                'payload': event.payload
            })
            
            # 使用触发规则的结果（如果匹配）
            hermes_action = trigger_result['hermes_action']
            matched_rule = trigger_result['matched_rule']
            
            if matched_rule:
                self.stats['rules_matched'] += 1
                print(f"[TRIGGER] Rule matched: {matched_rule['name']}")
            
            # 构建消息
            queued_item = {
                'event': event,
                'classification': classification,
                'response_mode': response_mode,
                'hermes_action': hermes_action,
                'trigger_result': trigger_result,
                'received_at': datetime.now().isoformat()
            }
            
            # 入队
            await self.queue.enqueue(queued_item)
            self.stats['events_dispatched'] += 1
            
            print(f"[DISPATCH] {event.event_type} -> {response_mode.value} ({hermes_action})")
            
            # Phase 1.5: 即时模式直接调用Hermes场景
            if response_mode == ResponseMode.INSTANT and hermes_action:
                asyncio.create_task(self._invoke_hermes_scenario(hermes_action, event, classification))
        
        except Exception as e:
            self.stats['errors'] += 1
            print(f"[ERROR] Handle event error: {e}")
            await self._handle_error(event, e)
    
    async def _invoke_hermes_scenario(self, scenario: str, event: ClawshellEvent, classification: Dict):
        """调用Hermes场景"""
        print(f"[SCENARIO] Invoking {scenario}...")
        
        result = await self.scenario_integrator.invoke_scenario(
            scenario,
            {
                'event_type': event.event_type,
                'priority': classification['priority'].value,
                'task_type': classification['task_type'].value,
                'payload': event.payload
            }
        )
        
        self.stats['scenarios_invoked'] += 1
        
        if result['success']:
            self.stats['scenarios_success'] += 1
            print(f"[SCENARIO] {scenario} succeeded ({result['duration']:.2f}s)")
            
            # 发布Hermes事件
            await self.publisher.publish_insight({
                'scenario': scenario,
                'result': result['output'],
                'event_type': event.event_type
            })
        else:
            self.stats['scenarios_failed'] += 1
            print(f"[SCENARIO] {scenario} failed: {result['error']}")
    
    async def _process_loop(self):
        """消息处理循环"""
        print("[INFO] Starting message processing loop...")
        
        while self.running:
            try:
                # 处理队列
                for mode in ['instant', 'fast', 'standard', 'batch']:
                    batch = await self.queue.dequeue_batch(mode=mode, max_count=5)
                    
                    if batch:
                        await self._dispatch_batch(mode, batch)
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.stats['errors'] += 1
                print(f"[ERROR] Process loop error: {e}")
                await asyncio.sleep(5)
    
    async def _dispatch_batch(self, mode: str, items: List[Dict]):
        """分发批量消息"""
        if mode == 'instant':
            # 即时：逐个调用场景
            for item in items:
                scenario = item.get('hermes_action')
                if scenario:
                    await self._invoke_hermes_scenario(
                        scenario,
                        item['event'],
                        item['classification']
                    )
        else:
            # 其他模式：批量处理
            print(f"[BATCH] Processing {len(items)} items in {mode} mode")
    
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
            'trigger_stats': self.trigger_config.get_stats(),
            'scenario_stats': self.scenario_integrator.get_stats()
        }


async def main():
    """主入口"""
    print("=" * 60)
    print("Hermes × ClawShell 双脑协同桥接器 v2")
    print("Phase 1 (EventBus) + Phase 1.5 (分级触发)")
    print("版本: 0.8.3-phase1.5")
    print("=" * 60)
    
    bridge = HermesBridgeV2()
    
    try:
        await bridge.start()
        
        # 保持运行
        while bridge.running:
            await asyncio.sleep(10)
            
            # 定期打印统计
            stats = bridge.get_stats()
            print(f"\n[STATS] Events: {stats['events_received']}, "
                  f"Classified: {stats['events_classified']}, "
                  f"Rules: {stats['rules_matched']}, "
                  f"Scenarios: {stats['scenarios_invoked']}/{stats['scenarios_success']}")
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    finally:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
