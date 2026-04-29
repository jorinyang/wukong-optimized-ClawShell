# ClawShell v1.0 - 自感知自适应自组织AI Agent编排系统

## 概述

ClawShell是基于钱学森《工程控制论》思想构建的增强型外骨骼AI Agent编排系统，具备**自感知**、**自适应**、**自组织**三大核心能力。

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         ClawShell v1.0                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer4 (集群层)  │ Swarm │ Trust │ Ecology │ Protocol        │
├─────────────────────────────────────────────────────────────────┤
│  Layer3 (自组织层) │ DAG   │ TaskMarket │ Scheduler │ N8N     │
├─────────────────────────────────────────────────────────────────┤
│  Layer2 (自适应层) │ Self-Repair │ Discovery │ Condition │ ML  │
├─────────────────────────────────────────────────────────────────┤
│  Layer1 (自感知层) │ Health │ System │ Disk │ Process │ Agent │
├─────────────────────────────────────────────────────────────────┤
│  Core (核心设施)   │ EventBus │ Genome │ Strategy              │
├─────────────────────────────────────────────────────────────────┤
│  Bridge           │ Hermes │ Persistence │ External             │
└─────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
clawshell_v1/
├── CLAWSHELL_VERSION      # 版本标识 (1.0.0)
├── MANIFEST.json           # 能力清单
├── bin/
│   ├── clawshell          # 主入口CLI
│   └── clawsync           # Hermes同步脚本
├── lib/
│   ├── core/              # 核心基础设施
│   │   ├── eventbus/     # 事件总线
│   │   ├── genome/       # 知识传承
│   │   └── strategy/     # 策略库
│   ├── layer1/           # 自感知层
│   ├── layer2/           # 自适应层
│   ├── layer3/           # 自组织层
│   ├── layer4/           # 集群层
│   ├── bridge/           # Bridge接口
│   ├── detector/         # 检测模块
│   └── utils/            # 工具函数
├── scripts/              # 运维脚本
├── config/               # 配置模板
├── tests/                # 测试套件
└── docs/                 # 文档
```

## 核心能力

### Layer1 - 自感知层
- 健康检查 (health_check)
- 系统监控 (system_mon)
- 磁盘监控 (disk_mon)
- 进程监控 (process_mon)
- Agent监控 (agent_mon)
- 网关监控 (gateway_mon)
- 服务监控 (service_mon)

### Layer2 - 自适应层
- 自修复 (self_repair)
- 市场发现 (market_discovery)
- 条件引擎 (condition)
- 策略选择 (strategy)
- 状态收集 (state_collector)
- 分析响应 (analyzer/responder)
- 紧急响应 (emergency)
- ML引擎 (ml_engine)

### Layer3 - 自组织层
- DAG编排 (dag)
- 任务市场 (task_market)
- 任务注册 (task_registry)
- 任务协调 (task_coordinator)
- 调度器 (scheduler)
- N8N集成 (n8n_client)
- 上下文管理 (context_manager)

### Layer4 - 集群层
- Swarm管理 (swarm)
- 信任评估 (trust)
- 生态系统 (ecology)
- 协议 (protocol)
- 节点发现 (swarm_discovery)
- 信任撤销 (trust_revocator)

## 使用方法

### CLI入口
```bash
# 查看状态
clawshell status

# 健康检查
clawshell health

# EventBus状态
clawshell events

# TaskMarket状态
clawshell market

# Swarm集群状态
clawshell swarm

# Hermes同步
clawshell sync
```

### Python导入
```python
import sys
sys.path.insert(0, '~/.openclaw/clawshell_v1')

from lib.core import eventbus, genome, strategy
from lib.layer1 import HealthMonitor
from lib.layer2 import SelfHealing, Discovery
from lib.layer3 import DAG, TaskMarket
from lib.layer4 import SwarmDiscovery
```

## 版本历史

- v1.0.0 (2026-04-30) - 统一封装，整合v0.1-v0.9全部模块

---
*基于工程控制论原理构建 | 智询工作室*
