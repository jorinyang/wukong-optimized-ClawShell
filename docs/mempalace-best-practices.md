# MemPalace 安装最佳实践

> 适用版本：MemPalace v3.3.4 + ChromaDB 1.5.8 + ONNXMiniLM_L6_V2
> 适用平台：Windows 10/11 + Python 3.12/3.13/3.14
> 更新日期：2026-05-02

---

## 目录

1. [系统架构](#1-系统架构)
2. [快速安装](#2-快速安装)
3. [依赖验证](#3-依赖验证)
4. [核心模块说明](#4-核心模块说明)
5. [功能测试](#5-功能测试)
6. [已知限制与解决方案](#6-已知限制与解决方案)
7. [最佳实践](#7-最佳实践)

---

## 1. 系统架构

```
ClawShell (Python)
  └─ lib/bridge/mempalace_mcp.py
        └─ MemPalaceMCPTools (9个记忆工具)
              └─ ChromaDB (向量数据库)
                    └─ ONNXMiniLM_L6_V2 (384维嵌入模型)
```

### 核心组件

| 组件 | 版本 | 用途 |
|------|------|------|
| MemPalace | v3.3.4 | 记忆存储框架 |
| ChromaDB | 1.5.8 | 向量数据库后端 |
| ONNXMiniLM_L6_V2 | - | 384维中文语义嵌入 |
| ClawShell lib | - | Bridge 桥接层 |

---

## 2. 快速安装

### 2.1 环境要求

- Python 3.12+（推荐 3.12，兼容性最佳）
- Windows 10/11
- 磁盘空间：约 200MB（ChromaDB + ONNX 模型）

### 2.2 安装命令

```bash
# 1. 安装核心依赖
pip install mempalace==3.3.4 chromadb==0.5.8 onnxruntime==1.20.0

# 2. 安装 Bridge 工具类（ClawShell 专用）
#    文件位置：lib/bridge/mempalace_mcp.py
#    直接 import 使用，无需 MCP Server 注册

# 3. 验证安装
python -c "from mempalace import MemPalace; print('MemPalace OK')"
python -c "import chromadb; print('ChromaDB OK')"
```

### 2.3 ONNX 模型下载（首次运行自动触发）

ONNX 模型在首次调用语义搜索时自动下载（约 90MB）：

```
缓存路径: C:/Users/<用户名>/.cache/chroma/onnx_models/
模型文件: ONNXMiniLM_L6_V2.onnx
```

如需手动预下载：

```python
from mempalace.utils.onnx_utils import download_onnx_model
download_onnx_model(force=True)
```

---

## 3. 依赖验证

运行以下检查确认环境就绪：

```python
import sys
sys.path.insert(0, "C:/Users/Aorus/.ClawShell")

# 1. MemPalace 导入
from mempalace import MemPalace
print("MemPalace 导入成功")

# 2. ChromaDB 后端
import chromadb
client = chromadb.Client()
print("ChromaDB 后端正常")

# 3. Bridge 工具
from lib.bridge.mempalace_mcp import MemPalaceMCPTools
tools = MemPalaceMCPTools()
print("Bridge 工具就绪")

# 4. ONNX 模型（首次下载）
from mempalace.utils.onnx_utils import get_onnx_model_path
model_path = get_onnx_model_path()
print(f"ONNX 模型: {model_path}")
```

### 验证检查清单

| 检查项 | 预期结果 |
|--------|---------|
| `import mempalace` | 无报错 |
| `chromadb.Client()` | 返回客户端对象 |
| `MemPalace().get_or_create()` | 返回 Collection 对象 |
| `get_onnx_model_path()` | 返回 .onnx 文件路径 |
| 语义搜索首次调用 | 自动下载模型后返回结果 |

---

## 4. 核心模块说明

### 4.1 MemPalaceMCPTools（推荐使用方式）

文件：`lib/bridge/mempalace_mcp.py`

```python
import sys
sys.path.insert(0, "C:/Users/Aorus/.ClawShell")
from lib.bridge.mempalace_mcp import MemPalaceMCPTools

tools = MemPalaceMCPTools()

# 健康检查
result = tools.call_tool("mempalace_health", {})
print(result)  # {'status': 'ok', 'version': '3.3.4', ...}

# 语义搜索
result = tools.call_tool("mempalace_search", {
    "query": "用户偏好设置",
    "top_k": 5
})

# 写入记忆
result = tools.call_tool("mempalace_write", {
    "content": "用户在2026年5月2日安装了MemPalace",
    "metadata": {"type": "install_log"}
})
```

### 4.2 MemPalace Bridge（高级用法）

文件：`lib/bridge/mempalace_bridge.py`

```python
from lib.bridge.mempalace_bridge import MemPalaceBridge

bridge = MemPalaceBridge()
await bridge.initialize()

# 语义搜索
results = await bridge.semantic_search("项目进度", top_k=5)

# 写入记忆
await bridge.write_memory(
    content="标书初稿已完成",
    metadata={"project": "建筑投标", "date": "2026-05-02"}
)
```

### 4.3 EventBus 生命周期集成

文件：`lib/core/eventbus/mempalace_hooks.py`

将 MemPalace 记忆写入与 ClawShell EventBus 对话生命周期挂钩：

```python
from lib.core.eventbus.core import get_eventbus
from lib.core.eventbus.mempalace_hooks import MemPalaceHookSubscriber

eventbus = get_eventbus()
hooks = MemPalaceHookSubscriber.get_instance(eventbus=eventbus, wing="wukong")
hooks.register(eventbus=eventbus)

# 之后所有对话事件自动触发记忆写入
eventbus.publish(Event(type=EventType.CONVERSATION_STARTED, source="wukong", payload={...}))
```

---

## 5. 功能测试

### 5.1 完整集成测试

```python
import sys
sys.path.insert(0, "C:/Users/Aorus/.ClawShell")

from lib.bridge.mempalace_mcp import MemPalaceMCPTools

tools = MemPalaceMCPTools()

tests = [
    ("mempalace_health", {}),
    ("mempalace_stats", {}),
    ("mempalace_search", {"query": "测试查询", "top_k": 3}),
    ("mempalace_write", {"content": "测试记忆内容", "metadata": {"test": True}}),
    ("mempalace_get_recent", {"limit": 5}),
]

for name, args in tests:
    try:
        result = tools.call_tool(name, args)
        status = "OK" if "error" not in result else "FAIL"
        print(f"[{status}] {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
```

### 5.2 ChromaDB 后端验证

```python
import chromadb

client = chromadb.Client()

# 测试集合创建
collection = client.get_or_create_collection("test_verify")
collection.add(
    ids=["test-1"],
    documents=["这是一个测试文档"],
    metadatas=[{"source": "verify"}]
)

# 验证查询
results = collection.query(
    query_texts=["测试"],
    n_results=1
)
print(f"向量检索结果: {len(results['documents'][0])} 条")
```

---

## 6. 已知限制与解决方案

### 6.1 MCP Server 注册（不推荐）

ClawShell 的 MCP 运行时通过 subprocess 启动 Python 进程，stdio 传输层与 Python stdin/stdout 的 `TextIOWrapper` 双重包装存在兼容性问题，导致进程异常退出。

解决方案：不依赖 MCP Server，直接在 Python 中 import 使用。

```python
# 推荐：直接 import
from lib.bridge.mempalace_mcp import MemPalaceMCPTools

# 不推荐：MCP Server 注册
# mcp_runtime call_tool 在 ClawShell 环境中存在传输层兼容性问题
```

### 6.2 首次运行 ONNX 模型下载

首次语义搜索时需要下载约 90MB 的 ONNX 模型，可能耗时较长。

解决方案：预先手动触发下载：

```python
from mempalace.utils.onnx_utils import download_onnx_model
download_onnx_model(force=True)
```

### 6.3 内存占用

ChromaDB 嵌入式模式（in-memory）在处理大量数据时内存占用较高。

解决方案：生产环境建议配置持久化后端：

```python
client = chromadb.PersistentClient(path="C:/chroma_data")
```

### 6.4 中文语义搜索质量

MiniLM-L6-V2 是通用英语模型，中文语义依赖字面分词。

解决方案：如需更好的中文效果，可替换为支持中文的嵌入模型（如 shibing624/text2vec-base-chinese）。

---

## 7. 最佳实践

### 7.1 目录结构建议

```
C:/Users/Aorus/.ClawShell/
  lib/
    bridge/
      mempalace_mcp.py      <- Bridge 工具入口
      mempalace_bridge.py   <- 高级 Bridge
      wukong_memory.py      <- 悟空记忆集成
    core/eventbus/
      mempalace_hooks.py    <- 生命周期 Hook
  .cache/
    chroma/                 <- ChromaDB 数据
      onnx_models/          <- ONNX 嵌入模型
        ONNXMiniLM_L6_V2.onnx
```

### 7.2 初始化脚本

在 ClawShell 环境中自动初始化 MemPalace：

```python
# 放在 lib/__init__.py 或 ClawShell 启动脚本中
import sys

CLAWSHELL_ROOT = "C:/Users/Aorus/.ClawShell"
if CLAWSHELL_ROOT not in sys.path:
    sys.path.insert(0, CLAWSHELL_ROOT)

# 预热 ONNX 模型（可选）
try:
    from mempalace.utils.onnx_utils import get_onnx_model_path
    get_onnx_model_path()  # 提前下载模型
except Exception:
    pass  # 模型在首次使用时自动下载
```

### 7.3 记忆分类建议

使用 Wing / Room / Drawer 三层结构组织记忆：

| 层级 | 用途 | 示例 |
|------|------|------|
| Wing | 主体/用户 | wukong, user_1062695814 |
| Room | 会话/话题 | session_xxx, project_bidding |
| Drawer | 记忆类型 | preference, knowledge, history |

### 7.4 性能优化

- **批量写入**：使用 `mempalace_batch_write` 而非多次单条写入
- **缓存复用**：保持 `MemPalaceMCPTools` 实例，避免重复初始化
- **向量预热**：服务启动时执行一次空搜索，加载 ONNX 模型到内存

---

## 更新历史

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-05-02 | v1.0 | 初始版本，包含安装、验证、测试全流程 |

---

本文档由 WuKong AI 自动生成，基于 jorinyang/wukong-optimized-ClawShell 仓库最佳实践验证。
