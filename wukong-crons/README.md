# 悟空定时任务体系

> 悟空专用的定时任务系统，适配悟空MCP架构

## 目录

- [定时任务清单](#定时任务清单)
- [每日时间线](#每日时间线)
- [快速配置](#快速配置)

---

## 定时任务清单

### 高优先级（核心功能）

| 任务 | 脚本 | 频率 | 说明 |
|------|------|------|------|
| **健康检查** | `wukong_health_check.py` | 每日 08:00, 20:00 | 全链路健康监测 |
| **日报生成** | `wukong_daily_report.py` | 每日 22:00 | 自动生成工作日报 |
| **晨报推送** | `wukong_morning_news.py` | 每日 07:00 | 推送今日信息早餐 |
| **自修复** | `wukong_self_repair.py` | 每日 05:00 | 自动检测修复问题 |

### 中优先级（增强能力）

| 任务 | 脚本 | 频率 | 说明 |
|------|------|------|------|
| **版本检测** | `wukong_version_monitor.py` | 每日 09:00 | 监控依赖版本变化 |
| **模块自检** | `wukong_module_check.py` | 每周一 09:00 | 检测ClawShell模块健康 |

---

## 每日时间线

```
00:00  ┌─────────────────────────────────────────┐
       │ 知识图谱构建 (Obsidian图谱自动更新)      │
       └─────────────────────────────────────────┘
05:00  ┌─────────────────────────────────────────┐
       │ 🔴 自修复检测与自动修复                  │
       └─────────────────────────────────────────┘
07:00  ┌─────────────────────────────────────────┐
       │ ☀️ 晨报推送 - 今日信息早餐              │
       └─────────────────────────────────────────┘
08:00  ┌─────────────────────────────────────────┐
       │ 🏥 健康检查 (上午)                       │
       └─────────────────────────────────────────┘
09:00  ┌─────────────────────────────────────────┐
       │ 📊 版本检测                             │
       │ 📋 模块自检 (每周一)                    │
       └─────────────────────────────────────────┘
18:00  ┌─────────────────────────────────────────┐
       │ 📰 w3晚报生成                           │
       └─────────────────────────────────────────┘
20:00  ┌─────────────────────────────────────────┐
       │ 🏥 健康检查 (下午)                      │
       └─────────────────────────────────────────┘
21:00  ┌─────────────────────────────────────────┐
       │ 🔍 w4深度复盘                           │
       └─────────────────────────────────────────┘
22:00  ┌─────────────────────────────────────────┐
       │ 📝 日报生成                             │
       └─────────────────────────────────────────┘
```

---

## Cron 表达式清单

```bash
# ===== 高优先级任务 =====

# 悟空健康检查 - 上午
0 8 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_health_check.py >> ~/logs/health_morning.log 2>&1

# 悟空健康检查 - 下午
0 20 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_health_check.py >> ~/logs/health_evening.log 2>&1

# 日报生成
0 22 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_daily_report.py >> ~/logs/daily_report.log 2>&1

# 晨报推送
0 7 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_morning_news.py >> ~/logs/morning_news.log 2>&1

# 自修复检测与执行
0 5 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_self_repair.py >> ~/logs/self_repair.log 2>&1

# ===== 中优先级任务 =====

# 版本检测
0 9 * * * /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_version_monitor.py >> ~/logs/version_monitor.log 2>&1

# 模块自检 - 每周一
0 9 * * 1 /usr/bin/python3 ~/ClawShell/wukong-crons/wukong_module_check.py >> ~/logs/module_check.log 2>&1
```

---

## 快速配置

### 方式一：通过悟空CLI配置

```
# 添加定时任务
cron add --name "健康检查" --schedule "0 8 * * *" --command "python wukong_health_check.py"

# 列出所有定时任务
cron list

# 查看任务状态
cron status <task_id>
```

### 方式二：手动添加到系统cron

```bash
# 编辑crontab
crontab -e

# 添加以下内容（根据实际路径调整）
0 8 * * * cd /path/to/ClawShell && python wukong-crons/wukong_health_check.py
0 20 * * * cd /path/to/ClawShell && python wukong-crons/wukong_health_check.py
0 22 * * * cd /path/to/ClawShell && python wukong-crons/wukong_daily_report.py
0 7 * * * cd /path/to/ClawShell && python wukong-crons/wukong_morning_news.py
0 5 * * * cd /path/to/ClawShell && python wukong-crons/wukong_self_repair.py
```

---

## 报告输出

任务执行后会生成以下报告：

| 报告类型 | 路径 | 说明 |
|---------|------|------|
| 健康检查 | `~/workspace/health_logs/` | JSON格式详细报告 |
| 日报 | `~/Documents/Obsidian/WuKong/Daily/` | Markdown日报 |
| 晨报 | `~/Documents/Obsidian/WuKong/Morning/` | Markdown晨报 |
| 自修复 | `~/workspace/repair_reports/` | 修复执行报告 |
| 版本检查 | `~/workspace/version_reports/` | 版本状态报告 |
| 模块检查 | `~/workspace/module_reports/` | 模块健康报告 |

---

## 自修复能力

悟空自修复系统支持自动检测和修复以下问题：

| 问题类型 | 严重程度 | 自动修复 |
|---------|---------|---------|
| 模块导入失败 | 高 | 重新配置Python路径 |
| 技能缺失 | 高 | 重新安装技能 |
| 定时任务失效 | 中 | 重建任务配置 |
| 配置文件损坏 | 高 | 从备份恢复 |
| 内存使用过高 | 高 | 清理缓存+重启会话 |
| 磁盘空间不足 | 中 | 清理日志和缓存 |

---

## 状态监控

查看任务执行状态：

```bash
# 查看日志
tail -f ~/logs/health_check.log

# 查看最近报告
ls -lt ~/workspace/health_logs/ | head -5

# 查看系统状态
python wukong_health_check.py --status
```

---

**版本**: v1.0  
**作者**: 悟空(WuKong)  
**更新**: 2026-04-30
