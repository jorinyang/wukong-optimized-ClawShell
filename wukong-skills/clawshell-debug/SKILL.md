---
name: ClawShell-Debug
description: ClawShell插件安装及调试。当用户提到ClawShell安装、调试、出错、无法导入，或遇到lib.core/lib.layer1-4/bridge/detector/utils模块问题时触发。提供标准化的模块验证、功能测试、问题诊断和修复流程。
author: WuKong
version: '0.08'
default_repo: https://github.com/jorinyang/wukong-optimized-ClawShell
---

# ClawShell-Debug 技能 (悟空专项优化版)

## 触发条件

**必须触发**当用户提到：
- ClawShell 安装、调试、出错、无法导入
- lib.core / lib.layer1-4 / lib.bridge / lib.detector / lib.utils 模块问题
- 导入 `lib` 失败、模块未找到

**不要触发**当：
- 用户只是用 ClawShell 做业务部署 → 参见 `clawshell-cicd-deploy`
- 用户要新建 ClawShell 模块代码 → 参见 `应用开发` 技能

---

## 关键路径

| 项目 | 路径 |
|------|------|
| ClawShell 根目录 | `C:\Users\Aorus\.ClawShell` |
| 核心库 | `C:\Users\Aorus\.ClawShell\lib\` |
| 悟空内置 Python | `C:\Users\Aorus\.real\.bin\python-3.12-windows-x64\python.exe` |
| 悟空优化版仓库 | `https://github.com/jorinyang/wukong-optimized-ClawShell` |
| 验证脚本临时目录 | `<workspace>\tmp\` |

---

## 执行流程

### Step 1: 确认 Python 环境

执行：
```cmd
<inner-python> -c "import sys; print(sys.executable); print(sys.version)"
```

**判断标准**：
- 路径含 `.real\` → 悟空内置 Python，`.pth` 机制已生效，可直接 `import lib`
- 其他路径 → 系统 Python，需在脚本开头加 `sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')`

### Step 2: 生成并运行模块导入测试

将以下脚本写入 `<workspace>\tmp\clawshell_import_test.py`：

```python
import sys, os
# 系统 Python 需要这句，悟空内置 Python 可省略
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

results = []

# === TOP LEVEL ===
for mod_name in ['lib', 'lib.core', 'lib.layer1', 'lib.layer2', 'lib.layer3', 'lib.layer4', 'lib.bridge', 'lib.detector', 'lib.utils']:
    try:
        __import__(mod_name, fromlist=[''])
        results.append(f'OK   {mod_name}')
    except Exception as e:
        results.append(f'FAIL {mod_name}: {e}')

# === SUB MODULES ===
sub_modules = [
    ('lib.core.eventbus', 'EventBus, Event, EventType'),
    ('lib.core.genome', 'GenomeManager, genome'),
    ('lib.core.strategy', 'StrategyRegistry, strategy'),
    ('lib.layer1.health_check', 'HealthMonitor, HealthStatus, HealthReport'),
    ('lib.layer1.system_mon', 'monitor functions'),
    ('lib.layer1.disk_mon', 'disk functions'),
    ('lib.layer1.process_mon', 'process functions'),
    ('lib.layer1.agent_mon', 'agent functions'),
    ('lib.layer1.gateway_mon', 'gateway functions'),
    ('lib.layer1.service_mon', 'service functions'),
    ('lib.layer2.self_healing', 'SelfHealingEngine, BackupManager'),
    ('lib.layer2.discovery', 'DiscoveryEngine, Capability'),
    ('lib.layer2.condition', 'ConditionEngine, ConditionTrigger'),
    ('lib.layer2.responder', 'AutoResponder'),
    ('lib.layer2.sense', 'SelfSenseEngine'),
    ('lib.layer2.adaptive_controller', 'AdaptiveController'),
    ('lib.layer3.task_market', 'TaskMarket, TaskMatcher, DAGNode'),
    ('lib.layer3.dag', 'TaskDAG, DAGValidator'),
    ('lib.layer3.coordinator', 'NodeCoordinator'),
    ('lib.layer3.context_manager', 'ContextManager'),
    ('lib.layer3.task_registry', 'TaskRegistry'),
    ('lib.layer4.swarm', 'NodeRegistry, Node, NodeType'),
    ('lib.layer4.trust', 'TrustManager, TrustLevel'),
    ('lib.layer4.failure_detector', 'FailureDetector'),
    ('lib.bridge.external', 'ExternalBridge, N8NClient, WebhookBridge'),
    ('lib.bridge.hermes', 'HermesBridge, HermesBridgeV2'),
    ('lib.bridge.hermes.bridge', 'HermesBridge'),
    ('lib.bridge.hermes.scenario_integrator', 'HermesScenarioIntegrator'),
    ('lib.bridge.hermes.classifier', 'PriorityClassifier'),
    ('lib.bridge.hermes.matcher', 'ResponseModeMatcher'),
    ('lib.bridge.hermes.publisher', 'EventBusPublisher'),
    ('lib.bridge.hermes.subscriber', 'EventBusSubscriber'),
    ('lib.bridge.persistence', 'genome_bridge, memos_bridge, mempalace_bridge, obsidian_bridge'),
    ('lib.detector.framework_detector', 'FrameworkDetector'),
    ('lib.detector.dependency_checker', 'DependencyChecker'),
    ('lib.detector.persistence_detector', 'PersistenceDetector'),
    ('lib.detector.external_detector', 'ExternalDetector'),
    ('lib.utils.logger', 'Logger, get_logger'),
    ('lib.utils.config', 'Config, get_config'),
    ('lib.utils.event_bus', 'SimpleEventBus'),
]

stdlib_names = {'sys','os','time','json','re','pathlib','Path','typing','abc','io','collections','datetime','threading','subprocess','logging','logger','Any','Callable','Dict','List','Optional','Union','Set','Enum','dataclass','field','annotations'}

for sub, desc in sub_modules:
    try:
        m = __import__(sub, fromlist=[''])
        names = [n for n in dir(m) if not n.startswith('_')]
        real_names = [n for n in names if n not in stdlib_names]
        results.append(f'OK   {sub:<50} | {", ".join(real_names[:6])}')
    except Exception as e:
        results.append(f'FAIL {sub:<50} | {desc}: {e}')

for r in results:
    print(r)
ok_count = sum(1 for r in results if r.startswith('OK'))
fail_count = sum(1 for r in results if r.startswith('FAIL'))
print(f'\n=== SUMMARY: {ok_count} OK, {fail_count} FAILED ===')
```

**执行命令**：
```
C:\Users\Aorus\.real\.bin\python-3.12-windows-x64\python.exe <workspace>\tmp\clawshell_import_test.py
```

**解读标准**：
- 38+ OK → 模块加载基本正常
- FAIL 在设计阶段未实现的模块 → 不影响核心
- FAIL 在核心模块 → 导入路径错误，见陷阱速查

### Step 3: 功能实例化测试

将以下脚本写入 `<workspace>\tmp\clawshell_func_test.py`：

```python
import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

tests = []

# === Layer2 ===
try:
    from lib.layer2.condition import ConditionEngine
    eng = ConditionEngine()
    assert hasattr(eng, 'add_trigger')
    assert hasattr(eng, 'update_metric')
    tests.append(('ConditionEngine', 'PASS', f'{len(eng.triggers)} triggers'))
except Exception as e:
    tests.append(('ConditionEngine', 'FAIL', str(e)))

try:
    from lib.layer2.self_healing import SelfHealingEngine
    sh = SelfHealingEngine()
    assert hasattr(sh, 'get_health_report')
    tests.append(('SelfHealingEngine', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('SelfHealingEngine', 'FAIL', str(e)))

try:
    from lib.layer2.discovery import DiscoveryEngine
    de = DiscoveryEngine()
    tests.append(('DiscoveryEngine', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('DiscoveryEngine', 'FAIL', str(e)))

# === Layer4（先实例化 NodeRegistry，TaskMarket 依赖它）===
try:
    from lib.layer4.swarm import NodeRegistry
    reg = NodeRegistry()
    assert hasattr(reg, 'register')
    tests.append(('NodeRegistry', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('NodeRegistry', 'FAIL', str(e)))
    reg = None

# === Layer3 ===
if reg:
    try:
        from lib.layer3.task_market import TaskMarket, TaskMatcher
        tm = TaskMarket(node_registry=reg)
        tmatcher = TaskMatcher(node_registry=reg)
        tests.append(('TaskMarket+TaskMatcher', 'PASS', 'instantiated'))
    except Exception as e:
        tests.append(('TaskMarket+TaskMatcher', 'FAIL', str(e)))

try:
    from lib.layer3.dag import TaskDAG, DAGValidator
    dag = TaskDAG()
    tests.append(('TaskDAG', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('TaskDAG', 'FAIL', str(e)))

try:
    from lib.layer3.coordinator import NodeCoordinator
    nc = NodeCoordinator()
    tests.append(('NodeCoordinator', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('NodeCoordinator', 'FAIL', str(e)))

try:
    from lib.layer3.context_manager import ContextManager
    cm = ContextManager()
    ctx = cm.create_context('test')
    tests.append(('ContextManager', 'PASS', f'context id={ctx.id}'))
except Exception as e:
    tests.append(('ContextManager', 'FAIL', str(e)))

# === Layer4 ===
try:
    from lib.layer4.trust import TrustManager
    tm = TrustManager()
    assert hasattr(tm, 'evaluate')
    tests.append(('TrustManager', 'PASS', f'{len(tm.state.trust_scores)} scores'))
except Exception as e:
    tests.append(('TrustManager', 'FAIL', str(e)))

try:
    from lib.layer4.failure_detector import FailureDetector
    fd = FailureDetector()
    assert hasattr(fd, 'record_success')
    tests.append(('FailureDetector', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('FailureDetector', 'FAIL', str(e)))

# === Layer1 ===
try:
    from lib.layer1.health_check import HealthMonitor
    hm = HealthMonitor()
    assert hasattr(hm, 'scan'), "should use scan() not check_all()"
    assert hasattr(hm, 'get_last_report')
    report = hm.scan()
    rkeys = list(report.keys()) if hasattr(report, 'keys') else str(type(report))
    tests.append(('HealthMonitor', 'PASS', f'report={rkeys}'))
except Exception as e:
    tests.append(('HealthMonitor', 'FAIL', str(e)))

# === Detector ===
try:
    from lib.detector.framework_detector import FrameworkDetector
    fd = FrameworkDetector()
    assert hasattr(fd, 'detect')
    tests.append(('FrameworkDetector', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('FrameworkDetector', 'FAIL', str(e)))

try:
    from lib.detector.dependency_checker import DependencyChecker
    dc = DependencyChecker()
    assert hasattr(dc, 'check')
    tests.append(('DependencyChecker', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('DependencyChecker', 'FAIL', str(e)))

# === Utils ===
try:
    from lib.utils.logger import get_logger
    logger = get_logger('test')
    tests.append(('Logger', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('Logger', 'FAIL', str(e)))

try:
    from lib.utils.config import get_config
    cfg = get_config()
    tests.append(('Config', 'PASS', 'instantiated'))
except Exception as e:
    tests.append(('Config', 'FAIL', str(e)))

print('=== FUNCTIONAL TESTS ===')
for name, status, detail in tests:
    print(f'[{status}] {name}: {detail}')

pass_count = sum(1 for _, s, _ in tests if s == 'PASS')
fail_count = sum(1 for _, s, _ in tests if s == 'FAIL')
print(f'\n=== SUMMARY: {pass_count} PASS, {fail_count} FAIL ===')
```

**执行命令**：
```
C:\Users\Aorus\.real\.bin\python-3.12-windows-x64\python.exe <workspace>\tmp\clawshell_func_test.py
```

### Step 4: 已知陷阱速查

| 症状 | 根因 | 修复 |
|------|------|------|
| `No module named 'lib'` | 系统 Python 未加载 .pth | 用悟空内置 Python，或加 `sys.path.insert` |
| `HealthMonitor.check_all` 找不到 | 方法名不同 | 改用 `scan()` |
| `DAGExecutor` 找不到 | 类名变更 | 改用 `TaskDAG` |
| `Coordinator` 找不到 | 类名变更 | 改用 `NodeCoordinator` |
| `Swarm` 找不到 | 类名变更 | 改用 `NodeRegistry` + `Node` |
| `SystemMonitor` 找不到 | 类名变更 | layer1 监控模块实际导出 `HealthMonitor`/`ScanConfig`/`RepairEngine` |
| `DiskMonitor` / `ProcessMonitor` 找不到 | 类名变更 | 改用 `ScanConfig`（disk_mon / process_mon） |
| `AgentMonitor` / `GatewayMonitor` / `ServiceMonitor` 找不到 | 类名变更 | 改用 `RepairEngine`（agent_mon / gateway_mon / service_mon） |
| `CapabilityDiscovery` 找不到 | 类名变更 | 改用 `DiscoveryEngine`（lib.layer2.discovery） |
| `SenseEngine` 找不到 | 类名变更 | 改用 `SelfSenseEngine`（lib.layer2.sense） |
| `ResponseEngine` 找不到 | 类名变更 | 改用 `AutoResponder`（lib.layer2.responder） |
| `ScenarioIntegrator` 找不到 | 类名变更 | 改用 `HermesScenarioIntegrator` |
| `Classifier` 找不到 | 类名变更 | 改用 `PriorityClassifier` |
| `Matcher` / `TriggerMatcher` 找不到 | 类名变更 | 改用 `ResponseModeMatcher` |
| `Publisher` / `EventPublisher` 找不到 | 类名变更 | 改用 `EventBusPublisher` |
| `Subscriber` 找不到 | 类名变更 | 改用 `EventBusSubscriber` |
| TaskMarket 初始化报错 | 缺必需参数 | 传入 `node_registry=NodeRegistry()` |
| `from hermes_bridge.xxx` 绝对导入 | 包名路径错误 | 改 `from .xxx import` 相对导入 |
| `from .schema import` 找不到 | schema 不在当前包 | 确认 `core/eventbus/schema.py` 实际路径 |
| `condition.py` 导入 schema 失败 | 相对导入路径错误 | 改为 `from lib.core.eventbus.schema import Event, EventType` |
| detector/utils 模块导入失败 | 旧版本未实现 | 升级到最新版本（已在 wukong/main 实现） |

### Step 5: 生成评估报告

根据测试结果，生成结构化报告，包含：

1. **模块加载状态**：顶层包和子模块导入成功率（目标38/44）
2. **功能验证**：所有引擎实例化结果
3. **问题清单**：发现的问题及修复方案
4. **价值评估**：六层架构（Layer1-4 + Detector + Utils）对悟空的赋能评估

---

## 已知类名映射（v0.07 修正）

以下为文档/旧代码中常见的错误类名与实际类名对照，来源于 `wukong_module_check.py` 的实测修正：

| 模块 | 错误类名 | 正确类名 |
|------|---------|---------|
| `lib.layer1.system_mon` | `SystemMonitor` | `HealthMonitor` |
| `lib.layer1.disk_mon` | `DiskMonitor` | `ScanConfig` |
| `lib.layer1.process_mon` | `ProcessMonitor` | `ScanConfig` |
| `lib.layer1.agent_mon` | `AgentMonitor` | `RepairEngine` |
| `lib.layer1.gateway_mon` | `GatewayMonitor` | `RepairEngine` |
| `lib.layer1.service_mon` | `ServiceMonitor` | `RepairEngine` |
| `lib.layer2.discovery` | `CapabilityDiscovery` | `DiscoveryEngine` |
| `lib.layer2.sense` | `SenseEngine` | `SelfSenseEngine` |
| `lib.layer2.responder` | `ResponseEngine` | `AutoResponder` |
| `lib.layer3.dag` | `DAGExecutor` | `TaskDAG` |
| `lib.layer3.coordinator` | `Coordinator` | `NodeCoordinator` |
| `lib.layer4.swarm` | `Swarm` | `NodeRegistry` |
| `lib.bridge.hermes.scenario_integrator` | `ScenarioIntegrator` / `ScenarioWatcher` | `HermesScenarioIntegrator` |
| `lib.bridge.hermes.classifier` | `Classifier` | `PriorityClassifier` |
| `lib.bridge.hermes.matcher` | `Matcher` / `TriggerMatcher` | `ResponseModeMatcher` |
| `lib.bridge.hermes.publisher` | `Publisher` / `EventPublisher` | `EventBusPublisher` |
| `lib.bridge.hermes.subscriber` | `Subscriber` | `EventBusSubscriber` |

---

## 悟空专项优化

本版本相比原版增加了以下优化：

1. **新增模块测试**：detector 和 utils 模块的完整导入和功能测试，bridge/persistence 持久层（genome_bridge / memos_bridge / mempalace_bridge / obsidian_bridge）
2. **类名修正**：补充 Layer1/Layer2/Bridge 所有模块的实际类名（来源：wukong_module_check.py 实测，v0.07 修正）
3. **自动修复**：hermes 桥接模块的相对导入修复脚本，condition.py 导入路径修复
4. **悟空仓库**：悟空优化版 Fork 仓库地址

---

## 版本历史

| 版本 | 说明 |
|------|------|
| v0.07 | 补充 Layer1/Layer2/Bridge 全量类名映射（Fix class names commit 6a7ae94 + 20d73c5）；bridge/persistence 子模块测试；导入测试扩展至 44 项 |
| v0.06 | 新增 detector/utils 模块测试；bridge/__init__.py 导出修复；condition.py 导入路径修复 |
| v2.0  | 初始悟空优化版，基础模块验证流程 |

---

## 依赖工具

- `execute_shell`：运行 Python 验证脚本
- `create_file`：生成测试脚本到 `tmp\` 目录
- `read_file`：读取 ClawShell 源码定位问题
- `modify_file`：修复导入路径等代码问题
