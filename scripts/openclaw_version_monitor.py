#!/usr/bin/env python3
"""
OpenClaw 版本主动感知系统 v1.0
功能：
1. 检测OpenClaw及所有第三方依赖版本
2. 对比最新版本差异
3. 评估影响范围
4. 生成应对策略报告
"""

import json
import subprocess
import requests
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 加载 .env 配置
ENV_FILE = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# ==================== 配置 ====================

VERSION_STATE_FILE = "~/.openclaw/.version_state.json"
LOG_FILE = "~/.openclaw/logs/version_monitor.log"

OPENCLAW_REPO = "openclaw/openclaw"
GITHUB_API = "https://api.github.com/repos/{}/releases/latest"

# 第三方依赖配置
DEPENDENCIES_CONFIG = {
    "openclaw": {
        "name": "OpenClaw",
        "type": "core",
        "version_cmd": ["openclaw", "--version"],
        "latest_url": GITHUB_API.format(OPENCLAW_REPO),
        "impact_areas": ["核心功能", "API接口", "配置格式"]
    },
    "memos": {
        "name": "MemOS",
        "type": "external",
        "config_key": "MEMOS_API_KEY",
        "version_url": "https://memos.memtensor.cn/api/openmem/v1/version",
        "health_url": "https://memos.memtensor.cn/api/openmem/v1/health",
        "impact_areas": ["记忆同步", "跨Agent共享", "会话摘要"]
    },
    "n8n": {
        "name": "n8n",
        "type": "external",
        "install_path": "~/n8n-app/",
        "version_cmd": ["bash", "-c", "cd ~/n8n-app && ./node_modules/.bin/n8n --version"],
        "impact_areas": ["W1-W4工作流", "任务编排", "流程自动化"]
    },
    "obsidian": {
        "name": "Obsidian",
        "type": "external",
        "vault_path": "~/Documents/Obsidian/OpenClaw",
        "impact_areas": ["笔记同步", "知识图谱", "任务管理"]
    },
    "hermes": {
        "name": "Hermes Agent",
        "type": "agent",
        "config_path": "~/.hermes/config.yaml",
        "log_path": "~/.hermes/logs/insight_generator.log",
        "impact_areas": ["深度复盘", "洞察生成", "自进化能力", "技能工厂", "模式识别", "预测分析"]
    },
    "openclaw-weixin": {
        "name": "WeChat Plugin",
        "type": "plugin",
        "extension_path": "~/.openclaw/extensions/openclaw-weixin",
        "impact_areas": ["公众号消息", "自动回复", "内容发布"]
    },
    "openclaw-dingtalk": {
        "name": "DingTalk Plugin",
        "type": "plugin",
        "extension_path": "~/.openclaw/extensions/dingtalk",
        "impact_areas": ["钉钉消息", "待办管理", "日历集成"]
    }
}

# ==================== 数据类 ====================

class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

@dataclass
class DependencyInfo:
    name: str
    installed_version: str
    latest_version: Optional[str]
    status: str
    impact_areas: List[str]
    extra: Dict[str, Any]

@dataclass
class ChangeInfo:
    type: str
    description: str
    risk_level: RiskLevel
    affected_areas: List[str]
    action_required: str

@dataclass
class VersionReport:
    timestamp: str
    openclaw_current: str
    openclaw_latest: Optional[str]
    has_update: bool
    dependencies: List[DependencyInfo]
    changes: List[ChangeInfo]
    risk_summary: Dict[str, int]
    recommendations: List[Dict]

# ==================== 版本检测类 ====================

class VersionDetector:
    """版本检测器"""
    
    def detect_openclaw_version(self) -> Dict[str, str]:
        """检测OpenClaw版本"""
        try:
            result = subprocess.run(
                ["openclaw", "--version"],
                capture_output=True, text=True, timeout=10
            )
            version = result.stdout.strip()
            return {"version": version, "status": "success"}
        except FileNotFoundError:
            return {"version": "not_found", "status": "error", "error": "openclaw命令未找到"}
        except Exception as e:
            return {"version": "unknown", "status": "error", "error": str(e)}
    
    def get_github_latest(self, repo: str) -> Optional[str]:
        """获取GitHub最新版本"""
        try:
            url = GITHUB_API.format(repo)
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("tag_name", "").lstrip("v")
            return None
        except Exception as e:
            print(f"[WARN] 获取GitHub版本失败: {e}", file=sys.stderr)
            return None
    
    def detect_memos_version(self) -> Dict[str, str]:
        """检测MemOS版本 - 使用POST接口验证连接"""
        api_key = os.environ.get("MEMOS_API_KEY", "")
        base_url = os.environ.get("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")
        
        if not api_key:
            return {"version": "not_configured", "status": "error", "error": "MEMOS_API_KEY未配置"}
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # 使用POST接口验证连接（MemOS的GET接口有时返回500）
            test_data = {
                "user_id": "version-check",
                "conversation_id": "health-check",
                "messages": [{"role": "user", "content": "health check"}]
            }
            
            response = requests.post(
                f"{base_url}/add/message",
                headers=headers,
                json=test_data,
                timeout=30  # MemOS响应较慢，增加超时时间
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("data", {}).get("success"):
                    return {"version": "connected", "status": "success"}
                elif data.get("code") == 0:
                    return {"version": "connected", "status": "success"}
                else:
                    return {"version": "unknown", "status": "error", "error": f"API返回: {data.get('message', 'unknown')}"}
            elif response.status_code == 500 or response.status_code == 50000:
                return {"version": "unavailable", "status": "warning", "error": "MemOS服务暂不可用(500)"}
            elif response.status_code == 403:
                return {"version": "unauthorized", "status": "error", "error": "认证失败"}
            else:
                return {"version": "unknown", "status": "error", "error": f"HTTP {response.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"version": "unreachable", "status": "error", "error": "无法连接到MemOS服务"}
        except Exception as e:
            return {"version": "unknown", "status": "error", "error": str(e)}
    
    def detect_n8n_version(self) -> Dict[str, str]:
        """检测n8n版本"""
        try:
            result = subprocess.run(
                ["bash", "-c", "cd ~/n8n-app && ./node_modules/.bin/n8n --version"],
                capture_output=True, text=True, timeout=10
            )
            version = result.stdout.strip()
            return {"version": version, "status": "success"}
        except FileNotFoundError:
            return {"version": "not_installed", "status": "error", "error": "n8n未安装"}
        except Exception as e:
            return {"version": "unknown", "status": "error", "error": str(e)}
    
    def detect_obsidian(self) -> Dict[str, Any]:
        """检测Obsidian Vault状态"""
        vault_path = os.path.expanduser(DEPENDENCIES_CONFIG["obsidian"]["vault_path"])
        try:
            if os.path.exists(vault_path):
                files = os.listdir(vault_path)
                return {
                    "vault_exists": True,
                    "file_count": len(files),
                    "status": "success"
                }
            else:
                return {"vault_exists": False, "status": "not_found"}
        except Exception as e:
            return {"vault_exists": False, "status": "error", "error": str(e)}
    
    def detect_hermes(self) -> Dict[str, Any]:
        """检测Hermes Agent状态 - 通过Cron执行记录检测"""
        config_path = os.path.expanduser(DEPENDENCIES_CONFIG["hermes"]["config_path"])
        log_file = os.path.expanduser("~/.hermes/logs/insight_generator.log")
        
        try:
            if not os.path.exists(config_path):
                return {"config_exists": False, "status": "not_found"}
            
            # 检查Cron执行记录（而非进程）
            last_execution = None
            execution_count_24h = 0
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # 获取最后一行（最新执行）
                    if lines:
                        last_line = lines[-1]
                        # 解析时间戳格式: 2026-04-23 23:30:01,332
                        try:
                            from datetime import datetime, timedelta
                            timestamp_str = last_line.split(' - ')[0].strip()
                            last_execution = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            
                            # 统计24小时内的执行次数
                            now = datetime.now()
                            cutoff = now - timedelta(hours=24)
                            for line in lines:
                                if 'Generated insights' in line or 'Processing complete' in line:
                                    try:
                                        ts = datetime.strptime(line.split(' - ')[0].strip(), '%Y-%m-%d %H:%M:%S,%f')
                                        if ts >= cutoff:
                                            execution_count_24h += 1
                                    except:
                                        pass
                        except Exception as e:
                            pass
            
            return {
                "config_exists": True,
                "running": last_execution is not None,
                "last_execution": last_execution.isoformat() if last_execution else None,
                "executions_24h": execution_count_24h,
                "status": "success"
            }
        except Exception as e:
            return {"config_exists": False, "status": "error", "error": str(e)}
    
    def detect_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """检测插件状态"""
        config = DEPENDENCIES_CONFIG.get(plugin_name, {})
        path = os.path.expanduser(config.get("extension_path", ""))
        try:
            if os.path.exists(path):
                # 检查package.json获取版本
                pkg_file = os.path.join(path, "package.json")
                if os.path.exists(pkg_file):
                    with open(pkg_file) as f:
                        pkg = json.load(f)
                        return {
                            "installed": True,
                            "version": pkg.get("version", "unknown"),
                            "status": "success"
                        }
                return {"installed": True, "version": "unknown", "status": "success"}
            else:
                return {"installed": False, "status": "not_found"}
        except Exception as e:
            return {"installed": False, "status": "error", "error": str(e)}

# ==================== 影响分析类 ====================

class ImpactAnalyzer:
    """影响分析器"""
    
    def __init__(self):
        self.breaking_keywords = [
            "breaking", "breaking change", "破坏性",
            "will be removed", "deprecated",
            "migration required", "需要迁移",
            "renamed", "moved to", "restructured"
        ]
    
    def analyze_openclaw_changes(self, current: str, latest: str) -> List[ChangeInfo]:
        """分析OpenClaw版本变更"""
        changes = []
        
        if not latest:
            return changes
        
        # 模拟变更检测（实际应获取changelog）
        # 这里假设有新版本时需要进行以下检查
        if current != latest:
            changes.append(ChangeInfo(
                type="FEATURE",
                description=f"新版本可用: {current} → {latest}",
                risk_level=RiskLevel.INFO,
                affected_areas=["全部"],
                action_required="评估是否升级"
            ))
        
        return changes
    
    def analyze_dependency_impact(self, dep_name: str, dep_info: Dict, version_info: Dict) -> List[ChangeInfo]:
        """分析第三方依赖影响"""
        changes = []
        config = DEPENDENCIES_CONFIG.get(dep_name, {})
        
        # 检查是否不可达或错误状态
        status = version_info.get("status", "")
        if status in ["error", "not_found", "unreachable"]:
            changes.append(ChangeInfo(
                type="DEPENDENCY",
                description=f"{config.get('name', dep_name)}: {version_info.get('error', 'unknown error')}",
                risk_level=RiskLevel.HIGH,
                affected_areas=config.get("impact_areas", []),
                action_required=f"检查{config.get('name', dep_name)}服务状态"
            ))
        
        return changes

# ==================== 报告生成类 ====================

class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_markdown_report(report: VersionReport) -> str:
        """生成Markdown格式报告"""
        lines = [
            f"# OpenClaw 版本检测报告",
            f"",
            f"**检测时间**: {report.timestamp}",
            f"**OpenClaw当前版本**: {report.openclaw_current}",
            f"**OpenClaw最新版本**: {report.openclaw_latest or '未知'}",
            f"**有可用更新**: {'是 ⚠️' if report.has_update else '否 ✅'}",
            f"",
            f"---",
            f"",
            f"## 第三方依赖状态",
            f"",
            f"| 依赖 | 当前版本 | 状态 |",
            f"|------|----------|------|",
        ]
        
        for dep in report.dependencies:
            status_icon = {
                "success": "✅",
                "error": "❌",
                "warning": "⚠️"
            }.get(dep.status, "❓")
            
            lines.append(f"| {dep.name} | {dep.installed_version} | {status_icon} |")
        
        lines.extend([
            f"",
            f"## 风险汇总",
            f"",
        ])
        
        for risk, count in report.risk_summary.items():
            if count > 0:
                icon = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "🟢"
                }.get(risk, "❓")
                lines.append(f"- {icon} {risk}: {count}")
        
        if report.recommendations:
            lines.extend([
                f"",
                f"## 建议",
                f"",
            ])
            for rec in report.recommendations:
                lines.append(f"- **[{rec.get('priority', 'P?')}]** {rec.get('action', '')}: {rec.get('reason', '')}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_json_report(report: VersionReport) -> str:
        """生成JSON格式报告"""
        return json.dumps(asdict(report), ensure_ascii=False, indent=2)

# ==================== 主函数 ====================

def main():
    """主函数"""
    print(f"[Version Monitor] 开始检测... {datetime.now().isoformat()}")
    
    detector = VersionDetector()
    analyzer = ImpactAnalyzer()
    
    # 1. 检测OpenClaw版本
    print("[1/7] 检测OpenClaw版本...")
    openclaw_info = detector.detect_openclaw_version()
    openclaw_version = openclaw_info.get("version", "unknown")
    
    # 2. 获取OpenClaw最新版本
    print("[2/7] 获取OpenClaw最新版本...")
    latest_version = detector.get_github_latest(OPENCLAW_REPO)
    
    # 3. 检测MemOS
    print("[3/7] 检测MemOS...")
    memos_info = detector.detect_memos_version()
    
    # 4. 检测n8n
    print("[4/7] 检测n8n...")
    n8n_info = detector.detect_n8n_version()
    
    # 5. 检测Obsidian
    print("[5/7] 检测Obsidian...")
    obsidian_info = detector.detect_obsidian()
    
    # 6. 检测Hermes
    print("[6/7] 检测Hermes...")
    hermes_info = detector.detect_hermes()
    
    # 7. 检测插件
    print("[7/7] 检测插件...")
    weixin_info = detector.detect_plugin("openclaw-weixin")
    dingtalk_info = detector.detect_plugin("openclaw-dingtalk")
    
    # Hermes状态：通过Cron执行记录判断（非进程）
    hermes_running = hermes_info.get("running", False)
    hermes_executions = hermes_info.get("executions_24h", 0)
    hermes_version = f"active({hermes_executions}次/24h)" if hermes_running else f"idle(last: {hermes_info.get('last_execution', 'unknown')})"
    
    # 构建依赖列表
    dependencies = [
        DependencyInfo(
            name="MemOS",
            installed_version=memos_info.get("version", "unknown"),
            latest_version=None,
            status=memos_info.get("status", "unknown"),
            impact_areas=["记忆同步", "跨Agent共享", "会话摘要"],
            extra={}
        ),
        DependencyInfo(
            name="n8n",
            installed_version=n8n_info.get("version", "unknown"),
            latest_version=None,
            status=n8n_info.get("status", "unknown"),
            impact_areas=["W1-W4工作流", "任务编排"],
            extra={}
        ),
        DependencyInfo(
            name="Obsidian",
            installed_version=str(obsidian_info.get("file_count", 0)) + " 文件" if obsidian_info.get("vault_exists") else "未找到",
            latest_version=None,
            status="success" if obsidian_info.get("vault_exists") else "not_found",
            impact_areas=["笔记同步", "知识图谱"],
            extra={}
        ),
        DependencyInfo(
            name="Hermes Agent",
            installed_version=hermes_version,
            latest_version=None,
            status="success" if hermes_info.get("config_exists") else "not_found",
            impact_areas=["深度复盘", "洞察生成", "自进化能力", "技能工厂", "模式识别", "预测分析"],
            extra={
                "running": hermes_running,
                "last_execution": hermes_info.get("last_execution"),
                "executions_24h": hermes_executions
            }
        ),
        DependencyInfo(
            name="WeChat Plugin",
            installed_version=weixin_info.get("version", "unknown"),
            latest_version=None,
            status=weixin_info.get("status", "unknown"),
            impact_areas=["公众号消息", "自动回复"],
            extra={}
        ),
        DependencyInfo(
            name="DingTalk Plugin",
            installed_version=dingtalk_info.get("version", "unknown"),
            latest_version=None,
            status=dingtalk_info.get("status", "unknown"),
            impact_areas=["钉钉消息", "待办管理"],
            extra={}
        ),
    ]
    
    # 分析变更
    changes = []
    changes.extend(analyzer.analyze_openclaw_changes(openclaw_version, latest_version))
    
    # 分析依赖影响
    dep_checks = [
        ("memos", DEPENDENCIES_CONFIG.get("memos", {}), memos_info),
        ("n8n", DEPENDENCIES_CONFIG.get("n8n", {}), n8n_info),
        ("obsidian", DEPENDENCIES_CONFIG.get("obsidian", {}), obsidian_info),
        ("hermes", DEPENDENCIES_CONFIG.get("hermes", {}), hermes_info),
    ]
    for dep_name, config, dep_info in dep_checks:
        changes.extend(analyzer.analyze_dependency_impact(dep_name, config, dep_info))
    
    # 风险汇总
    risk_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for change in changes:
        risk_summary[change.risk_level.value] = risk_summary.get(change.risk_level.value, 0) + 1
    
    # 生成建议
    recommendations = []
    if risk_summary["CRITICAL"] > 0:
        recommendations.append({
            "priority": "P0",
            "action": "立即处理",
            "reason": f"发现{risk_summary['CRITICAL']}个严重问题"
        })
    if risk_summary["HIGH"] > 0:
        recommendations.append({
            "priority": "P1",
            "action": "尽快处理",
            "reason": f"发现{risk_summary['HIGH']}个高风险问题"
        })
    if latest_version and openclaw_version != latest_version:
        recommendations.append({
            "priority": "P2",
            "action": "评估升级",
            "reason": f"OpenClaw有可用更新: {openclaw_version} → {latest_version}"
        })
    
    # 转换changes中的RiskLevel为字符串
    changes_serializable = [
        {
            "type": c.type,
            "description": c.description,
            "risk_level": c.risk_level.value,
            "affected_areas": c.affected_areas,
            "action_required": c.action_required
        }
        for c in changes
    ]
    
    # 构建报告
    report = VersionReport(
        timestamp=datetime.now().isoformat(),
        openclaw_current=openclaw_version,
        openclaw_latest=latest_version,
        has_update=(latest_version is not None and openclaw_version != latest_version),
        dependencies=dependencies,
        changes=changes_serializable,
        risk_summary=risk_summary,
        recommendations=recommendations
    )
    
    # 输出报告
    print("\n" + "="*50)
    report_gen = ReportGenerator()
    
    # 控制台输出
    print(report_gen.generate_markdown_report(report))
    
    # 保存JSON报告
    os.makedirs(os.path.dirname(os.path.expanduser(VERSION_STATE_FILE)), exist_ok=True)
    with open(os.path.expanduser(VERSION_STATE_FILE), "w") as f:
        f.write(report_gen.generate_json_report(report))
    
    print(f"\n[Version Monitor] 检测完成，报告已保存到 {VERSION_STATE_FILE}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
