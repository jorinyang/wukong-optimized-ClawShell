# MemPalace + ChromaDB 安装问题总结与解决方案

> **文档版本**: v1.0  
> **创建日期**: 2026-05-02  
> **适用环境**: ClawShell + 悟空 + Windows  
> **维护者**: 悟空(WuKong) AI Assistant

---

## 一、问题概述

在将 MemPalace 记忆系统集成到悟空(ClawShell)运行时的过程中，遇到了以下主要问题：

| 问题类型 | 问题描述 | 状态 |
|---------|---------|------|
| MCP Server 注册失败 | `memory_search` 工具不可用 | ✅ 已解决 |
| ONNX 模型下载缓慢 | 79MB 模型下载中断/速度慢 | ✅ 已解决 |
| ChromaDB API 变更 | 1.5.x 版本接口与旧代码不兼容 | ✅ 已解决 |
| 路径配置错误 | 硬编码路径导致跨环境失败 | ✅ 已解决 |
| 向量搜索未激活 | 仅关键词搜索可用 | ✅ 已解决 |

---

## 二、详细问题与解决方案

### 问题1：MCP Server 无法注册到悟空运行时

**症状**: 
- `memory_search` 工具不可用
- `real_cli mcp add` 命令不支持 Python 模块直接注册
- stdio 模式子进程立即退出

**根本原因**:
1. 悟空 MCP 运行时通过 `mcpServerConfig.json` 配置，只能通过 subprocess 启动外部进程
2. Python 模块无法直接作为 MCP Server 被注册
3. stdio 子进程需要完整的启动环境和依赖，但初始实现缺少必要配置

**解决方案**:
采用**直接 Import 模式**，绕过 MCP Server 注册：

```python
import sys
sys.path.insert(0, 'C:/Users/Aorus/.ClawShell')
sys.path.insert(0, 'C:/Users/Aorus/.ClawShell/lib')

from lib.bridge.mempalace_mcp import MemPalaceMCPTools

tools = MemPalaceMCPTools()
result = tools.call_tool('memory_search', {'query': '搜索内容', 'mode': 'semantic'})
```

**关键文件**:
- `lib/bridge/mempalace_mcp.py` - MCP 工具接口
- `lib/bridge/persistence/mempalace_bridge.py` - SQLite 持久化层

---

### 问题2：ONNX Embedding 模型下载失败

**症状**:
- `onnx.tar.gz` 下载速度极慢（约15MB/79MB，需数小时）
- 下载多次中断
- `all-MiniLM-L6-v2` 模型文件缺失

**根本原因**:
HuggingFace Hub 下载受网络限制，且默认使用官方 S3 存储。

**解决方案**:
1. **方案A（推荐）**: 使用 ChromaDB 缓存目录中已有的模型
   ```
   C:/Users/Aorus/.cache/chroma/onnx_models/all-MiniLM-L6-v2/
   C:/Users/Aorus/.cache/chroma/onnx_models/paraphrase-multilingual-MiniLM-L12-v2/
   ```

2. **方案B**: 使用国内镜像或预下载
   ```python
   # 设置镜像源
   import os
   os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
   ```

3. **方案C**: 直接下载
   ```
   链接: https://www.modelscope.cn/models/AI-ModelScope/all-MiniLM-L6-v2
   ```

**验证命令**:
```python
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
ef = ONNXMiniLM_L6_V2()
result = ef(['测试文本'])
print('嵌入维度:', len(result[0]))  # 应输出 384
```

---

### 问题3：ChromaDB 1.5.x API 不兼容

**症状**:
```python
# 错误1: 模块导入变更
from chromadb.utils.embedding_functions import ONNXEmbeddingFunction
# ModuleNotFoundError: cannot import name 'ONNXEmbeddingFunction'

# 错误2: API 变更
chromadb.Client()  # 废弃
chromadb.PersistentClient()  # 新API
```

**根本原因**:
ChromaDB 1.5.x 版本进行了 API 重构：
- `embedding_functions` 模块结构改变
- `Client()` 改为 `PersistentClient()`
- 部分类名变更

**解决方案**:
```python
# 正确代码 (ChromaDB 1.5.x)
from chromadb import Client
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

# 初始化客户端
client = Client()
embedding_fn = ONNXMiniLM_L6_V2()

# 创建集合
collection = client.get_or_create_collection(
    name="wukong_memories",
    embedding_function=embedding_fn
)
```

**已验证可用版本组合**:
- ChromaDB: 1.5.8
- MemPalace: 3.3.4
- ONNX Runtime: 内置 all-MiniLM-L6-v2 (384维)

---

### 问题4：路径硬编码问题

**症状**:
```python
# Windows 路径问题
db_path = Path.home() / ".claude" / "palace" / "memories.db"
# 在不同用户目录下会失败
```

**解决方案**:
使用相对路径和环境变量：

```python
from pathlib import Path
import os

# 方案1: 使用 ClawShell 根目录
CLAWSHELL_ROOT = Path(__file__).parent.parent.parent
db_path = CLAWSHELL_ROOT / "data" / "memories.db"

# 方案2: 使用用户目录
db_path = Path.home() / ".claude" / "palace" / "memories.db"
```

---

### 问题5：向量搜索未自动激活

**症状**:
- `memory_search` 默认使用关键词搜索
- 向量搜索需要手动配置

**根本原因**:
`_init_vector_search()` 方法初始化失败时未正确处理异常。

**解决方案**:
确保 ChromaDB 和 ONNX 模型正确安装后，向量搜索将自动激活：

```python
# 验证向量搜索状态
tools = MemPalaceMCPTools()
print(f'向量搜索可用: {tools._chroma_collection is not None}')
print(f'嵌入函数: {tools._embedding_fn}')
```

---

## 三、安装步骤（完整流程）

### 前置要求

1. **Python 环境**: Python 3.10+
2. **ClawShell**: 已安装并配置
3. **网络**: 能够访问 HuggingFace 或国内镜像

### Step 1: 安装依赖

```bash
pip install chromadb>=1.5.0 mempalace>=3.0.0 sentence-transformers
```

### Step 2: 配置 Python 路径

创建或编辑 `site-packages/clawshell.pth`:
```
C:\Users\Aorus\.ClawShell
C:\Users\Aorus\.ClawShell\lib
```

### Step 3: 下载 ONNX 模型（可选）

模型会自动从 ChromaDB 缓存加载。如需手动下载：
```bash
# 使用 modelscope 镜像
pip install modelscope
python -c "from modelscope.hub.snapshot_download import snapshot_download; snapshot_download('AI-ModelScope/all-MiniLM-L6-v2', cache_dir='C:/Users/Aorus/.cache/huggingface')"
```

### Step 4: 复制关键文件

将以下文件复制到 ClawShell 安装目录：
- `lib/bridge/mempalace_mcp.py`
- `lib/bridge/persistence/mempalace_bridge.py`

### Step 5: 验证安装

```python
import sys
sys.path.insert(0, 'C:/Users/Aorus/.ClawShell')
sys.path.insert(0, 'C:/Users/Aorus/.ClawShell/lib')

from lib.bridge.mempalace_mcp import MemPalaceMCPTools

tools = MemPalaceMCPTools()
stats = tools._stats({})

print(f'Bridge可用: {stats["bridge_available"]}')
print(f'向量搜索可用: {stats["vector_search_available"]}')
```

---

## 四、API 参考

### 核心类

```python
from lib.bridge.mempalace_mcp import MemPalaceMCPTools

# 初始化
tools = MemPalaceMCPTools()

# 调用工具
tools.call_tool('memory_search', {'query': '关键词', 'mode': 'semantic'})
tools.call_tool('memory_write', {'content': '记忆内容', 'key': '可选键名'})
tools.call_tool('memory_recall', {'key': '键名'})
tools.call_tool('memory_list', {'limit': 50})
tools.call_tool('memory_stats', {})
tools.call_tool('memory_delete', {'key': '键名'})
```

### 搜索模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `semantic` | 向量相似度搜索 | 理解语义，无需精确匹配 |
| `keyword` | SQLite LIKE 搜索 | 精确匹配特定词汇 |

### 返回格式

```python
# memory_search 返回
{
    'results': [
        {'id': 'xxx', 'content': '...', 'distance': 0.123, 'metadata': {...}},
        ...
    ],
    'mode': 'semantic',
    'query': '搜索词',
    'count': 3
}

# memory_write 返回
{
    'success': True,
    'key': '键名',
    'vector_id': 'vec_键名',
    'content_preview': '内容前200字...'
}
```

---

## 五、已知限制

1. **多语言支持**: 当前使用 `all-MiniLM-L6-v2` (英语为主)，中文语义理解有限
2. **向量维度**: 384维，适合短文本；长文本建议先摘要
3. **并发写入**: SQLite 不适合高并发场景，大规模应用需迁移到 PostgreSQL

---

## 六、故障排除

### 问题：向量搜索始终为 False

1. 检查 ChromaDB 版本：`pip show chromadb`
2. 检查 ONNX 模型：`dir C:\Users\Aorus\.cache\chroma\onnx_models`
3. 重新初始化：`tools._init_vector_search()`

### 问题：ImportError

1. 确认 Python 路径配置
2. 重新安装依赖
3. 检查 ClawShell 安装完整性

### 问题：数据库锁定

```python
# 使用读写锁
import fcntl
fcntl.flock(db_file, fcntl.LOCK_EX)
```

---

## 七、相关资源

- **ChromaDB 文档**: https://docs.trychroma.com/
- **MemPalace GitHub**: https://github.com/mempalace/mempalace
- **ONNX Models**: https://huggingface.co/models?library=onnx
- **ClawShell 文档**: https://github.com/wukong-optimized-ClawShell

---

*本文档由悟空 AI 助手自动生成，如有问题请联系维护者。*
