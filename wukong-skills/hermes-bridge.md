# ClawShell-Hermes-Bridge 技能

## 触发词

- "hermes 分析"
- "hermes 洞察"
- "前脑思考"
- "进化引擎"
- "clawshell 状态"
- "系统复盘"
- "模式识别"

## 功能

当用户触发以上关键词时，Hermes (前脑/进化引擎) 会:

1. 读取 ClawShell EventBus 中的事件
2. 分析系统状态和任务执行记录
3. 生成深度洞察和优化建议
4. 发布回 EventBus 供悟空执行

## 集成方式

```python
from hermes_agent_integration import HermesClawShellIntegration

# 启动集成
hermes = HermesClawShellIntegration()
hermes.start()

# 注册洞察回调
def on_insight(insight):
    print(f"收到洞察: {insight.content}")
    
hermes.register_insight_callback(on_insight)
```

## 事件类型映射

| 悟空事件 | Hermes 响应 | 优先级 |
|----------|-------------|--------|
| task.completed | 任务复盘洞察 | P2 |
| error.occurred | 错误根因分析 | P1 |
| task.started | 风险预测 | P3 |
| system.health_check | 优化建议 | P2 |

## 文件位置

- 集成模块: `~/.ClawShell/hermes_agent_integration.py`
- EventBus: `~/.real/workspace/shared/eventbus/`
