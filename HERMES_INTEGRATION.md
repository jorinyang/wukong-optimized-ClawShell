# Hermes × 悟空 双通道集成说明

## 实际目录结构 (已校验)

悟空主目录: `~/.real/` (不是 `~/.real`)

```
~/.real/
├── users/
│   └── user-bd1b229d4eff8f6a45c456149072cb3b/     ← 悟空用户目录
│       ├── .config/                                 ← 配置系统
│       │   ├── agent.md
│       │   ├── soul.md
│       │   └── config_index.md
│       ├── .mcp/
│       │   └── mcpServerConfig.json                 ← MCP 配置
│       ├── .skills/                                 ← 技能目录
│       ├── sessions/                                ← 会话历史
│       └── workspace/
│           ├── tmp/mcp_server.py                    ← MCP Server 脚本
│           └── shared/
│               └── hermes_bridge/                   ← Hermes-悟空 桥接
│                   ├── inbox/                         ← 悟空 → Hermes
│                   ├── outbox/                        ← Hermes → 悟空
│                   └── archive/                       ← 已处理归档
└── .mcp/
    └── http-bridge-port.json (17655)                ← HTTP Bridge 端口
```

## 通信方式: 双通道 (MCP主 + 文件系统备)

### 通道 1: MCP (主)

- **协议**: MCP stdio + HTTP Bridge
- **配置**: `~/.real/users/{user}/.mcp/mcpServerConfig.json`
- **Server**: `clawshell-mcp` (stdio 类型)
- **脚本**: `~/.real/users/{user}/workspace/tmp/mcp_server.py`
- **HTTP Bridge**: `127.0.0.1:47832`
- **可用工具**:
  - `eventbus_publish` — 发布事件
  - `eventbus_subscribe` — 订阅事件
  - `eventbus_query` — 查询历史
  - `eventbus_stats` — 统计信息

### 通道 2: 文件系统 (备)

- **路径**: `~/.real/users/{user}/workspace/shared/hermes_bridge/`
- **inbox/**: 悟空发送给 Hermes 的事件
- **outbox/**: Hermes 发送给悟空的洞察
- **archive/**: 已处理事件归档
- **事件格式**: JSON，文件名 `{timestamp}_{source}_{type}_{id}.json`

### 自动切换逻辑

```
1. 检测 MCP HTTP Bridge 端口 (47832) 是否可用
2. 可用 → 使用 MCP 通道
3. 不可用 → 降级到文件系统通道
4. 定期重试 MCP，恢复后自动升级
```

## 集成模块

文件: `~/.ClawShell/hermes_wukong_dual_channel.py`

### 启动方式

```python
from hermes_wukong_dual_channel import HermesWukongIntegration

integration = HermesWukongIntegration()
integration.start()

# 发布洞察
from hermes_wukong_dual_channel import HermesInsight
insight = HermesInsight(
    insight_type="analysis",
    priority="P2",
    content="深度分析结果",
    recommendations=["建议1", "建议2"]
)
integration.publish_insight(insight)
```

### 生态位
- **Layer**: L5 (前脑/进化引擎)
- **职责**: 深度思考、洞察生成、模式识别、技能进化
- **通信**: MCP主 + 文件系统备，自动降级/恢复

## 注意事项

1. `.openclaw` 目录存在但不是悟空实际工作目录
2. 悟空实际通过 MCP 与 ClawShell 通信
3. HTTP Bridge 端口 47832 需悟空运行时才能连接
4. 文件系统通道在任何时候都可用 (无需悟空在线)
