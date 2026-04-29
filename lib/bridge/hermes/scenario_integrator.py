#!/usr/bin/env python3
# hermes_bridge/scenario_integrator.py
"""
Hermes场景集成器

将分级触发与Hermes 7大场景集成
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ScenarioConfig:
    """场景配置"""
    name: str
    cli_path: str  # hermes_scenarios/cli.py路径
    hermes_scenarios: List[str]  # 支持的场景列表
    timeout: int = 300  # 超时时间(秒)


class HermesScenarioIntegrator:
    """
    Hermes场景集成器
    
    职责：
    1. 管理Hermes场景调用
    2. 响应模式到场景的映射
    3. 批量场景执行
    4. 场景结果处理
    """
    
    # 响应模式到Hermes场景的默认映射
    MODE_SCENARIO_MAP = {
        'instant': ['review'],  # 即时 → review
        'fast': ['summarize', 'meeting'],  # 快速 → summarize, meeting
        'standard': ['summarize', 'coach', 'review'],  # 标准 → summarize, coach, review
        'batch': ['predict', 'graph', 'coach', 'backup']  # 批量 → predict, graph, coach, backup
    }
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        
        self.cli_path = self.config.get('cli_path', 
                                       '~/.hermes/scripts/hermes_scenarios/cli.py')
        self.scenarios = self._discover_scenarios()
        self.mode_map = self.config.get('mode_scenario_map', self.MODE_SCENARIO_MAP)
        
        # 执行统计
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'by_scenario': {}
        }
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'cli_path': os.path.expanduser('~/.hermes/scripts/hermes_scenarios/cli.py'),
            'timeout': 300,
            'mode_scenario_map': self.MODE_SCENARIO_MAP
        }
    
    def _discover_scenarios(self) -> List[str]:
        """发现可用的Hermes场景"""
        cli_path = Path(self.cli_path)
        
        if not cli_path.exists():
            return []
        
        # 默认场景
        default_scenarios = [
            'summarize',    # 智能对话摘要
            'predict',      # 任务预判
            'meeting',      # 会议助手
            'backup',       # 智能备份
            'review',       # 代码审查
            'graph',        # 知识图谱
            'coach'        # 知识教练
        ]
        
        # 检查CLI是否支持这些场景
        available = []
        for scenario in default_scenarios:
            if self._check_scenario(scenario):
                available.append(scenario)
        
        return available
    
    def _check_scenario(self, scenario: str) -> bool:
        """检查场景是否可用"""
        try:
            result = subprocess.run(
                ['python3', self.cli_path, '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return scenario in result.stdout or scenario in result.stderr
        except:
            return False
    
    async def invoke_scenario(
        self, 
        scenario: str, 
        event_data: Dict,
        options: Dict = None
    ) -> Dict:
        """
        调用Hermes场景
        
        参数:
            scenario: 场景名称 (summarize, predict, review, etc.)
            event_data: 事件数据
            options: 可选配置
        
        返回:
            {
                'success': bool,
                'scenario': str,
                'output': str,
                'error': Optional[str],
                'duration': float
            }
        """
        start_time = datetime.now()
        
        # 检查场景是否可用
        if scenario not in self.scenarios:
            return {
                'success': False,
                'scenario': scenario,
                'output': None,
                'error': f'Scenario {scenario} not available',
                'duration': 0
            }
        
        try:
            # 构建命令
            cmd = ['python3', self.cli_path, scenario]
            
            # 添加选项
            if options:
                for key, value in options.items():
                    if value is not None:
                        cmd.extend([f'--{key}', str(value)])
            
            # 添加事件相关选项
            if event_data.get('priority'):
                cmd.extend(['--priority', event_data['priority']])
            
            if event_data.get('task_type'):
                cmd.extend(['--task-type', event_data['task_type']])
            
            # 执行
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=self.config.get('timeout', 300)
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                self.stats['total_calls'] += 1
                self.stats['successful_calls'] += 1
                self._update_scenario_stats(scenario, True)
                
                return {
                    'success': True,
                    'scenario': scenario,
                    'output': stdout.decode().strip(),
                    'error': None,
                    'duration': duration
                }
            else:
                self.stats['total_calls'] += 1
                self.stats['failed_calls'] += 1
                self._update_scenario_stats(scenario, False)
                
                return {
                    'success': False,
                    'scenario': scenario,
                    'output': None,
                    'error': stderr.decode().strip(),
                    'duration': duration
                }
        
        except asyncio.TimeoutError:
            self.stats['total_calls'] += 1
            self.stats['failed_calls'] += 1
            self._update_scenario_stats(scenario, False)
            
            return {
                'success': False,
                'scenario': scenario,
                'output': None,
                'error': f'Timeout after {self.config.get("timeout")} seconds',
                'duration': self.config.get('timeout', 300)
            }
        
        except Exception as e:
            self.stats['total_calls'] += 1
            self.stats['failed_calls'] += 1
            self._update_scenario_stats(scenario, False)
            
            return {
                'success': False,
                'scenario': scenario,
                'output': None,
                'error': str(e),
                'duration': 0
            }
    
    async def invoke_by_mode(
        self,
        mode: str,
        event_data: Dict,
        options: Dict = None
    ) -> List[Dict]:
        """
        根据响应模式调用相应场景
        
        参数:
            mode: 响应模式 (instant, fast, standard, batch)
            event_data: 事件数据
            options: 可选配置
        
        返回:
            List[Dict]: 各场景调用结果
        """
        scenarios = self.mode_map.get(mode, ['summarize'])
        results = []
        
        for scenario in scenarios:
            result = await self.invoke_scenario(scenario, event_data, options)
            results.append(result)
        
        return results
    
    def _update_scenario_stats(self, scenario: str, success: bool):
        """更新场景统计"""
        if scenario not in self.stats['by_scenario']:
            self.stats['by_scenario'][scenario] = {
                'calls': 0,
                'successes': 0,
                'failures': 0
            }
        
        self.stats['by_scenario'][scenario]['calls'] += 1
        if success:
            self.stats['by_scenario'][scenario]['successes'] += 1
        else:
            self.stats['by_scenario'][scenario]['failures'] += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'available_scenarios': self.scenarios,
            'mode_map': self.mode_map
        }
    
    def get_available_scenarios(self) -> List[str]:
        """获取可用场景列表"""
        return self.scenarios.copy()


class BatchScenarioRunner:
    """
    批量场景运行器
    
    用于批量处理事件并调用相应Hermes场景
    """
    
    def __init__(self, integrator: HermesScenarioIntegrator = None):
        self.integrator = integrator or HermesScenarioIntegrator()
        self.batch_queue: List[Dict] = []
        self.processing = False
    
    async def add_to_batch(self, event_data: Dict, mode: str):
        """添加到批量队列"""
        self.batch_queue.append({
            'event_data': event_data,
            'mode': mode,
            'added_at': datetime.now().isoformat()
        })
    
    async def process_batch(self) -> List[Dict]:
        """处理批量队列"""
        if not self.batch_queue or self.processing:
            return []
        
        self.processing = True
        results = []
        
        try:
            # 按模式分组
            by_mode: Dict[str, List] = {}
            for item in self.batch_queue:
                mode = item['mode']
                if mode not in by_mode:
                    by_mode[mode] = []
                by_mode[mode].append(item)
            
            # 处理每组
            for mode, items in by_mode.items():
                mode_results = await self.integrator.invoke_by_mode(
                    mode,
                    items[0]['event_data']  # 使用第一个事件的数据
                )
                results.extend(mode_results)
            
            # 清空队列
            self.batch_queue.clear()
        
        finally:
            self.processing = False
        
        return results
    
    async def size(self) -> int:
        """获取队列大小"""
        return len(self.batch_queue)


def main():
    """测试入口"""
    print("=== HermesScenarioIntegrator 测试 ===\n")
    
    integrator = HermesScenarioIntegrator()
    
    print(f"可用场景: {integrator.scenarios}")
    print(f"模式映射: {integrator.mode_map}")
    
    # 测试调用 (如果有可用场景)
    if integrator.scenarios:
        print("\n--- 测试场景调用 ---")
        # 实际调用需要事件数据


if __name__ == "__main__":
    main()
