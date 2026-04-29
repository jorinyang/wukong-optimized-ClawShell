# ClawShell

> **版本**: 1.0.0
> **定位**: OpenClaw 增强型外骨骼功能插件
> **架构**: 自感知 × 自适应 × 自组织 × 多Agent集群

ClawShell 是一个专为类 OpenClaw 架构设计的增强型外骨骼插件，通过四层架构（自感知、自适应、自组织、集群层）为核心系统叠加新能力，实现无需侵入原有代码的功能增强。

详情请查看项目手册：ARCHITECTURE.md

---

## 目录

- [特性](#特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [架构概览](#架构概览)
- [模块详解](#模块详解)
- [使用指南](#使用指南)
- [配置参考](#配置参考)
- [开发指南](#开发指南)
- [故障排除](#故障排除)
- [许可证](#许可证)

---

## 特性

| 特性 | 说明 |
|------|------|
| **四层增强架构** | 自感知 → 自适应 → 自组织 → 多Agent集群 |
| **无侵入设计** | 不修改 OpenClaw 核心代码，保持版本解耦 |
| **低耦合通信** | 模块间通过 EventBus 和文件协议通信 |
| **Hermes 双脑协同** | OpenClaw（后脑）+ Hermes（前脑）双向联动 |
| **自修复系统** | 凌晨自动检测 + 分阶段修复，故障自愈 |
| **多持久层支持** | Genome / MemOS / MemPalace / Obsidian / 知识图谱 |
| **N8N 工作流集成** | 完整的工作流自动化编排 |
| **幂等安装** | 重复安装无副作用，可随时回滚 |

---

## 安装

### 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.8+ | 主运行环境 |
| psutil | 5.9.0 | 系统监控 |
| pyyaml | 6.0 | 配置管理 |
| requests | 2.28.0 | HTTP 请求 |
| curl | - | Shell 工具 |
| git | - | 版本控制 |

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/jorinyang/ClawShell.git
cd ClawShell

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装系统工具（如缺少）
# macOS
brew install curl jq git
# Ubuntu/Debian
sudo apt-get install curl jq git

# 4. 运行安装脚本
bash install.sh

# 5. 验证安装
python -m clawshell.cli status
```

### 验证安装

```bash
# 检查健康状态
clawshell health

# 检查版本
clawshell version

# 检查所有组件
clawshell status
```

---

## 快速开始

### CLI 使用

```bash
# 查看状态
clawshell status

# 查看健康检查
clawshell health

# 查看事件总线
clawshell events

# 查看任务市场
clawshell market

# 查看集群状态
clawshell swarm
```

### Python API 使用

```python
from lib.layer1 import HealthMonitor
from lib.layer2 import SelfHealing, Discovery
from lib.layer3 import DAG, TaskMarket
from lib.layer4 import SwarmDiscovery
from lib.bridge.hermes import HermesBridge

# 健康检查
monitor = HealthMonitor()
report = monitor.check()

# 任务市场
market = TaskMarket()
tasks = market.list_tasks()

# Hermes 桥接
bridge = HermesBridge()
bridge.connect()
```

---

## 架构概览

### 系统定位

ClawShell 以"外骨骼"的定位叠加于 OpenClaw 之上，通过标准化接口与 OpenClaw 交互，不修改其核心代码，实现能力增强的同时保持版本独立演进。

### 四层架构

```
┌─────────────────────────────────────────────────────┐
│                  ClawShell 外骨骼层                    │
├─────────────────────────────────────────────────────┤
│  Layer 4: 多Agent集群                               │
│  ├─ SwarmDiscovery  集群发现                       │
│  ├─ TrustManager    信任评估                       │
│  ├─ EcologyMatcher   生态位匹配                     │
│  └─ SwarmProtocol   协作协议                       │
├─────────────────────────────────────────────────────┤
│  Layer 3: 自组织                                    │
│  ├─ Organizer       任务编排                       │
│  ├─ TaskMarket      任务市场                       │
│  ├─ DAGManager      依赖管理                       │
│  └─ N8NClient       工作流集成                      │
├─────────────────────────────────────────────────────┤
│  Layer 2: 自适应                                    │
│  ├─ SelfHealing     自修复系统                     │
│  ├─ Discovery       能力发现                       │
│  ├─ ConditionEngine  条件引擎                       │
│  └─ StrategyEval     策略评估                       │
├─────────────────────────────────────────────────────┤
│  Layer 1: 自感知                                    │
│  ├─ HealthMonitor   健康检测                       │
│  ├─ SystemMonitor   系统监控                       │
│  ├─ DiskMonitor     磁盘监控                       │
│  ├─ ProcessMonitor  进程监控                       │
│  └─ AgentMonitor    Agent监控                      │
└─────────────────────────────────────────────────────┘
                    ↕ EventBus ↕
┌─────────────────────────────────────────────────────┐
│                  OpenClaw 核心层                      │
│  ├─ Gateway        网关                           │
│  ├─ Agents         Agent调度                       │
│  ├─ Skills         技能加载                        │
│  └─ Channels       通道管理                        │
└─────────────────────────────────────────────────────┘
```

### 与 OpenClaw 的关系

```
┌─────────────────────────────────────────────────────────┐
│                      OpenClaw                           │
│  (后脑 - 执行引擎)                                     │
│  ├─ Gateway        网关路由                         │
│  ├─ Agent调度      任务分发                        │
│  └─ Skills         技能执行                        │
└───────────────────────┬───────────────────────────────┘
                        │ EventBus 双向通信
┌───────────────────────▼───────────────────────────────┐
│                      ClawShell                          │
│  (外骨骼 - 增强层)                                    │
│  ├─ 自感知         环境信息收集                     │
│  ├─ 自适应         参数调控优化                     │
│  ├─ 自组织         任务编排协调                     │
│  └─ 集群层         多节点协作                       │
└───────────────────────┬───────────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────────┐
│                      Hermes                             │
│  (前脑 - 进化引擎)                                    │
│  ├─ 深度思考       洞察生成                         │
│  ├─ 模式识别       趋势分析                         │
│  └─ 自进化         能力迭代                         │
└─────────────────────────────────────────────────────────┘
```

---

## 模块详解

### Layer 1 - 自感知层

| 模块 | 文件 | 功能 |
|------|------|------|
| HealthMonitor | `lib/layer1/health_check.py` | 27项健康检测 |
| SystemMonitor | `lib/layer1/system_mon.py` | CPU/内存监控 |
| DiskMonitor | `lib/layer1/disk_mon.py` | 磁盘使用监控 |
| ProcessMonitor | `lib/layer1/process_mon.py` | 进程状态检测 |
| AgentMonitor | `lib/layer1/agent_mon.py` | Agent会话监控 |
| GatewayMonitor | `lib/layer1/gateway_mon.py` | Gateway状态监控 |
| ServiceMonitor | `lib/layer1/service_mon.py` | 外部服务可用性 |

### Layer 2 - 自适应层

| 模块 | 文件 | 功能 |
|------|------|------|
| SelfHealing | `lib/layer2/self_healing.py` | 自修复系统 |
| Discovery | `lib/layer2/discovery.py` | 能力自发现 |
| ConditionEngine | `lib/layer2/condition.py` | 事件条件过滤 |
| StrategyEval | `lib/layer2/strategy.py` | 策略效果评估 |
| StateCollector | `lib/layer2/state_collector.py` | 状态收集 |
| Analyzer | `lib/layer2/analyzer.py` | 数据分析 |
| Responder | `lib/layer2/responder.py` | 响应生成 |
| Emergency | `lib/layer2/emergency.py` | 应急处理 |
| MLEngine | `lib/layer2/ml_engine.py` | AI/ML 推理 |
| MarketDiscovery | `lib/layer2/market_discovery.py` | 市场发现 |

### Layer 3 - 自组织层

| 模块 | 文件 | 功能 |
|------|------|------|
| Organizer | `lib/layer3/organizer.py` | 任务编排引擎 |
| DAGManager | `lib/layer3/dag.py` | 依赖关系管理 |
| TaskMarket | `lib/layer3/task_market.py` | 任务分发市场 |
| TaskRegistry | `lib/layer3/task_registry.py` | 任务注册表 |
| TaskCoordinator | `lib/layer3/task_coordinator.py` | 任务协调 |
| Scheduler | `lib/layer3/scheduler.py` | 调度器 |
| N8NClient | `lib/layer3/n8n_client.py` | N8N 工作流 |
| ContextManager | `lib/layer3/context_manager.py` | 上下文管理 |

### Layer 4 - 集群层

| 模块 | 文件 | 功能 |
|------|------|------|
| SwarmDiscovery | `lib/layer4/swarm_discovery.py` | P2P 节点发现 |
| TrustManager | `lib/layer4/trust_manager.py` | 信任评分管理 |
| TrustEvaluator | `lib/layer4/trust_evaluator.py` | 信任评估计算 |
| TrustRevocator | `lib/layer4/trust_revocator.py` | 信任动态撤销 |
| EcologyMatcher | `lib/layer4/ecology.py` | 生态位匹配 |
| FailureDetector | `lib/layer4/failure_detector.py` | 节点失败检测 |
| MetricsCollector | `lib/layer4/metrics_collector.py` | 指标收集 |
| WeightCalculator | `lib/layer4/weight_calculator.py` | 权重计算 |

### Bridge - 接口层

#### Hermes Bridge

| 模块 | 文件 | 功能 |
|------|------|------|
| HermesBridge | `lib/bridge/hermes/bridge.py` | EventBus 双向通信 |
| ScenarioIntegrator | `lib/bridge/hermes/scenario_integrator.py` | 7大场景集成 |
| TriggerConfig | `lib/bridge/hermes/trigger_config.py` | 分级触发配置 |
| Classifier | `lib/bridge/hermes/classifier.py` | 优先级分类 |
| Matcher | `lib/bridge/hermes/matcher.py` | 响应模式匹配 |

#### Persistence Bridge

| 模块 | 文件 | 功能 |
|------|------|------|
| GenomeBridge | `lib/bridge/persistence/` | 知识传承 |
| MemOSBridge | `lib/bridge/persistence/` | MemOS 云端 |
| MemPalaceBridge | `lib/bridge/persistence/` | 记忆宫殿 |
| ObsidianBridge | `lib/bridge/persistence/` | Obsidian 笔记 |
| KnowledgeGraphBridge | `lib/bridge/persistence/` | 知识图谱 |

#### External Bridge

| 模块 | 文件 | 功能 |
|------|------|------|
| N8NBridge | `lib/bridge/external/n8n_client.py` | N8N 工作流 |
| DockerBridge | `lib/bridge/external/` | Docker 容器 |
| AliyunBridge | `lib/bridge/external/` | 阿里云服务 |
| GitHubBridge | `lib/bridge/external/` | GitHub API |
| TrainBridge | `lib/bridge/external/` | 12306 车次 |
| RedisBridge | `lib/bridge/external/` | Redis 队列 |
| DiscordBridge | `lib/bridge/external/` | Discord 通知 |

### Core - 核心基础设施

| 模块 | 目录 | 功能 |
|------|------|------|
| EventBus | `lib/core/eventbus/` | 事件总线 |
| Genome | `lib/core/genome/` | 知识传承存储 |
| Strategy | `lib/core/strategy/` | 策略库 |

---

## 使用指南

### 事件总线

```python
from lib.core.eventbus import EventBus, Event

# 创建事件
event = Event(
    event_type="task.completed",
    payload={"task_id": "001", "agent": "lab"}
)

# 发布事件
bus = EventBus()
bus.publish(event)

# 订阅事件
def on_task_completed(event):
    print(f"Task {event.payload['task_id']} completed")

bus.subscribe("task.completed", on_task_completed)
```

### 任务市场

```python
from lib.layer3 import TaskMarket

market = TaskMarket()

# 注册任务
market.register({
    "task_id": "research-001",
    "type": "analysis",
    "priority": "high",
    "budget_minutes": 60
})

# 认领任务
task = market.claim(agent_id="lab")

# 完成任务
market.complete(task["task_id"])
```

### 自修复系统

```python
from lib.layer2 import SelfHealing

healer = SelfHealing()

# 运行自检
issues = healer.detect()

# 执行修复
for issue in issues:
    result = healer.repair(issue)
    print(f"Repaired: {issue['type']} - {result}")
```

---

## 配置参考

### 环境配置

```yaml
# config/default.yaml
clawshell:
  version: "1.0.0"
  
  layer1:
    health_check_interval: 300  # 5分钟
    monitor_intervals:
      system: 60
      disk: 300
      process: 30
      agent: 300

  layer2:
    self_repair_enabled: true
    self_repair_schedule: "0 5 * * *"  # 每日5点
    discovery_auto_register: true

  layer3:
    task_budget_default: 30  # 分钟
    market_matching_threshold: 0.7

  layer4:
    swarm_port: 7890
    trust_initial: 0.5
    trust_decay_rate: 0.95

  bridge:
    hermes:
      enabled: true
      sync_interval: 300
    persistence:
      genome_path: "~/.openclaw/genome/"
      memos_api_url: "https://memos.memtensor.cn/api/"
```

---

## 开发指南

### 添加新模块

1. 在对应层级目录创建模块文件
2. 在 `__init__.py` 中导出
3. 添加单元测试到 `tests/`
4. 更新 `MANIFEST.json`

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定层级测试
python -m pytest tests/test_layer1/
python -m pytest tests/test_layer2/

# 生成覆盖率报告
python -m pytest tests/ --cov=lib --cov-report=html
```

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 导入错误 | 检查 `PYTHONPATH` 是否包含项目根目录 |
| 权限错误 | 确保 `bin/` 目录有执行权限 `chmod +x bin/*` |
| 依赖缺失 | 运行 `pip install -r requirements.txt` |
| EventBus 连接失败 | 检查 OpenClaw Gateway 是否运行 |
| Hermes 同步失败 | 检查网络连通性和 API 配置 |

### 日志位置

```
~/.openclaw/logs/
├── clawshell.log          # 主日志
├── eventbus.log           # 事件总线日志
├── hermes_bridge.log      # Hermes 桥接日志
└── self_repair.log       # 自修复日志
```

---

## 架构文档

完整的系统架构文档请参考 [ARCHITECTURE.md](./ARCHITECTURE.md)，包含：

- 第一章：系统概述与定位
- 第二章：双脑协同系统生态全景图
- 第三章：目录结构与组件分布
- 第八章：双脑协同架构
- 第九章：自修复系统
- 第十三章：依赖关系与数据流

---

## 许可证

MIT License

Copyright (c) 2026 智询工作室

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
