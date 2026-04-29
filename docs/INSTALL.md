# ClawShell v1.0 安装指南

## 环境要求

- Python 3.10+
- macOS/Linux
- OpenClaw 环境

## 安装步骤

### 方式一: 直接使用 (推荐)

```bash
# 添加到 PATH
export CLAWSHELL_ROOT="$HOME/.openclaw/clawshell_v1"
export PATH="$CLAWSHELL_ROOT/bin:$PATH"

# 测试安装
clawshell status
```

### 方式二: 符号链接到系统路径

```bash
ln -sf ~/.openclaw/clawshell_v1/bin/clawshell /usr/local/bin/clawshell
ln -sf ~/.openclaw/clawshell_v1/bin/clawsync /usr/local/bin/clawsync
```

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| CLAWSHELL_ROOT | ~/.openclaw/clawshell_v1 | 根目录 |
| CLAWSHELL_LOG_LEVEL | INFO | 日志级别 |

### 持久化配置

将以下内容添加到 `~/.bashrc` 或 `~/.zshrc`:

```bash
export CLAWSHELL_ROOT="$HOME/.openclaw/clawshell_v1"
export PATH="$CLAWSHELL_ROOT/bin:$PATH"
```

## 验证安装

```bash
# 查看版本
clawshell version

# 健康检查
clawshell health

# 运行测试
python3 -c "
import sys
sys.path.insert(0, '$HOME/.openclaw/clawshell_v1')
from lib.core import eventbus
from lib.layer1 import HealthMonitor
print('All imports OK')
"
```

## 卸载

```bash
# 移除v1.0
rm -rf ~/.openclaw/clawshell_v1

# 移除符号链接 (如已创建)
rm -f /usr/local/bin/clawshell /usr/local/bin/clawsync
```

## 故障排除

### 导入失败

确保所有源目录存在:
- ~/.openclaw/eventbus/
- ~/.openclaw/genome/
- ~/.openclaw/strategies/
- ~/.openclaw/adaptor/
- ~/.openclaw/organizer/
- ~/.openclaw/swarm/

### CLI不可用

检查执行权限:
```bash
chmod +x ~/.openclaw/clawshell_v1/bin/clawshell
chmod +x ~/.openclaw/clawshell_v1/bin/clawsync
```

---
*智询工作室 - 2026-04-30*
