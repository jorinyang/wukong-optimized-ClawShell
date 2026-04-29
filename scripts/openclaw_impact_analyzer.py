#!/usr/bin/env python3
"""
OpenClaw 影响分析引擎 v1.0
功能：
1. 解析OpenClaw Changelog
2. 评估架构、接口、依赖变更影响
3. 生成风险等级和建议
4. 第三方依赖影响评估
"""

import json
import re
import requests
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# ==================== 配置 ====================

OPENCLAW_REPO = "openclaw/openclaw"
GITHUB_API = "https://api.github.com/repos/{}/releases"
CHANGELOG_CACHE = "~/.openclaw/.changelog_cache.json"

# ==================== 数据类 ====================

class RiskLevel:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class ChangeType:
    BREAKING = "BREAKING"           # 破坏性变更
    ARCHITECTURE = "ARCHITECTURE"    # 架构变更
    INTERFACE = "INTERFACE"          # 接口变更
    DEPENDENCY = "DEPENDENCY"        # 依赖变更
    FEATURE = "FEATURE"              # 功能新增
    BUGFIX = "BUGFIX"               # 缺陷修复
    OPTIMIZE = "OPTIMIZE"           # 性能优化
    DOCS = "DOCS"                   # 文档更新

@dataclass
class Change:
    """单个变更项"""
    type: str
    description: str
    severity: str  # HIGH/MEDIUM/LOW
    affected_areas: List[str]
    breaking: bool
    migration_guide: Optional[str]

@dataclass
class ImpactReport:
    """影响分析报告"""
    timestamp: str
    current_version: str
    target_version: str
    changes: List[Dict]
    risk_summary: Dict[str, int]
    affected_dependencies: List[Dict]
    recommendations: List[Dict]
    migration_plan: List[Dict]

# ==================== 变更模式识别 ====================

CHANGE_PATTERNS = {
    # 破坏性变更模式
    "breaking": [
        (r"breaking[\s-]change", RiskLevel.HIGH),
        (r"will\s+remove", RiskLevel.HIGH),
        (r"deprecated", RiskLevel.MEDIUM),
        (r"migration\s+required", RiskLevel.HIGH),
        (r"破坏性", RiskLevel.HIGH),
        (r"不再兼容", RiskLevel.HIGH),
    ],
    
    # 架构变更模式
    "architecture": [
        (r"directory", RiskLevel.MEDIUM),
        (r"folder", RiskLevel.MEDIUM),
        (r"path\s+change", RiskLevel.HIGH),
        (r"restructur", RiskLevel.MEDIUM),
        (r"重构", RiskLevel.MEDIUM),
        (r"目录.*变更", RiskLevel.MEDIUM),
    ],
    
    # 接口变更模式
    "interface": [
        (r"api\s+change", RiskLevel.HIGH),
        (r"interface", RiskLevel.MEDIUM),
        (r"endpoint", RiskLevel.MEDIUM),
        (r"parameter", RiskLevel.LOW),
        (r"api.*废弃", RiskLevel.HIGH),
        (r"接口.*变更", RiskLevel.HIGH),
    ],
    
    # 依赖变更模式
    "dependency": [
        (r"require\s+python", RiskLevel.MEDIUM),
        (r"require\s+node", RiskLevel.MEDIUM),
        (r"upgrade\s+dependency", RiskLevel.LOW),
        (r"remove\s+dependency", RiskLevel.HIGH),
        (r"依赖.*更新", RiskLevel.LOW),
    ],
    
    # 功能新增模式
    "feature": [
        (r"new\s+feature", RiskLevel.INFO),
        (r"introduc", RiskLevel.INFO),
        (r"add\s+support", RiskLevel.INFO),
        (r"新增", RiskLevel.INFO),
        (r"新增功能", RiskLevel.INFO),
    ],
}

# ==================== 第三方依赖影响矩阵 ====================

DEPENDENCY_IMPACT_MATRIX = {
    "MemOS": {
        "keywords": ["memory", "memOS", "memos", "记忆"],
        "affected": ["记忆同步", "跨Agent共享", "会话摘要"],
        "risk_factors": {
            "api_change": RiskLevel.HIGH,
            "auth_change": RiskLevel.HIGH,
            "format_change": RiskLevel.MEDIUM,
        }
    },
    "n8n": {
        "keywords": ["n8n", "workflow", "工作流", "automation"],
        "affected": ["W1-W4工作流", "任务编排", "流程自动化"],
        "risk_factors": {
            "api_change": RiskLevel.HIGH,
            "node_change": RiskLevel.MEDIUM,
            "format_change": RiskLevel.MEDIUM,
        }
    },
    "Obsidian": {
        "keywords": ["obsidian", "vault", "笔记", "note", "markdown"],
        "affected": ["笔记同步", "知识图谱", "任务管理"],
        "risk_factors": {
            "format_change": RiskLevel.MEDIUM,
            "plugin_api_change": RiskLevel.MEDIUM,
        }
    },
    "Hermes": {
        "keywords": ["hermes", "insight", "洞察", "intelligence"],
        "affected": ["深度复盘", "洞察生成", "自进化能力"],
        "risk_factors": {
            "feed_format": RiskLevel.HIGH,
            "protocol_change": RiskLevel.HIGH,
        }
    },
    "DingTalk": {
        "keywords": ["dingtalk", "dingding", "钉钉"],
        "affected": ["钉钉消息", "待办管理", "日历集成"],
        "risk_factors": {
            "api_change": RiskLevel.HIGH,
            "oauth_change": RiskLevel.HIGH,
        }
    },
    "WeChat": {
        "keywords": ["wechat", "weixin", "微信"],
        "affected": ["公众号消息", "自动回复", "内容发布"],
        "risk_factors": {
            "api_change": RiskLevel.HIGH,
            "auth_change": RiskLevel.HIGH,
        }
    },
}

# ==================== 影响分析器 ====================

class ImpactAnalyzer:
    """影响分析引擎"""
    
    def __init__(self):
        self.change_patterns = CHANGE_PATTERNS
        self.dependency_matrix = DEPENDENCY_IMPACT_MATRIX
    
    def parse_changelog(self, changelog_text: str) -> List[Change]:
        """解析Changelog文本，提取变更项"""
        changes = []
        
        if not changelog_text:
            return changes
        
        # 按版本分割
        version_blocks = re.split(r'^##\s+', changelog_text, flags=re.MULTILINE)
        
        for block in version_blocks:
            if not block.strip():
                continue
            
            # 提取版本号
            version_match = re.match(r'\[?v?(\d+\.\d+\.\d+)\]?', block.split('\n')[0])
            if not version_match:
                continue
            
            version = version_match.group(1)
            
            # 识别变更类型
            for change_type, patterns in self.change_patterns.items():
                for pattern, severity in patterns:
                    if re.search(pattern, block, re.IGNORECASE):
                        # 提取相关行
                        lines = [l.strip() for l in block.split('\n') if re.search(pattern, l, re.IGNORECASE)]
                        
                        changes.append(Change(
                            type=change_type,
                            description=f"[v{version}] " + "; ".join(lines[:3]),
                            severity=severity,
                            affected_areas=self._detect_affected_areas(block),
                            breaking=(severity == RiskLevel.HIGH and change_type == "breaking"),
                            migration_guide=self._generate_migration_guide(change_type, severity, block)
                        ))
                        break
        
        return changes
    
    def _detect_affected_areas(self, text: str) -> List[str]:
        """检测受影响的区域"""
        areas = []
        text_lower = text.lower()
        
        area_keywords = {
            "skills": ["skill", "技能"],
            "scripts": ["script", "脚本"],
            "hooks": ["hook", "钩子"],
            "workspace": ["workspace", "工作空间"],
            "agents": ["agent", "代理"],
            "config": ["config", "配置"],
            "cron": ["cron", "定时任务"],
            "memory": ["memory", "记忆"],
        }
        
        for area, keywords in area_keywords.items():
            if any(k in text_lower for k in keywords):
                areas.append(area)
        
        return areas if areas else ["general"]
    
    def _generate_migration_guide(self, change_type: str, severity: str, context: str) -> Optional[str]:
        """生成迁移指南"""
        if severity == RiskLevel.LOW:
            return None
        
        guides = {
            "breaking": "⚠️ 需要迁移。请查阅官方迁移指南，可能需要手动更新配置或代码。",
            "architecture": "📁 目录结构变更。建议运行迁移脚本或手动调整路径。",
            "interface": "🔌 接口变更。请更新调用代码和参数格式。",
            "dependency": "📦 依赖变更。请更新相关包版本。",
        }
        
        return guides.get(change_type, "请查阅官方文档了解详情。")
    
    def assess_dependency_impact(self, changes: List[Change]) -> List[Dict]:
        """评估第三方依赖影响"""
        impacts = []
        
        for dep_name, dep_config in self.dependency_matrix.items():
            dep_impacts = []
            
            for change in changes:
                change_lower = change.description.lower()
                
                for keyword in dep_config["keywords"]:
                    if keyword.lower() in change_lower:
                        risk = dep_config["risk_factors"].get(change.type, RiskLevel.LOW)
                        if risk not in [RiskLevel.INFO, RiskLevel.LOW]:
                            dep_impacts.append({
                                "change": change.description,
                                "risk": risk,
                                "type": change.type
                            })
            
            if dep_impacts:
                impacts.append({
                    "dependency": dep_name,
                    "affected_areas": dep_config["affected"],
                    "impacts": dep_impacts,
                    "overall_risk": max([i["risk"] for i in dep_impacts], default=RiskLevel.LOW)
                })
        
        return impacts
    
    def generate_recommendations(self, changes: List[Change], dep_impacts: List[Dict]) -> List[Dict]:
        """生成建议"""
        recommendations = []
        
        # 基于变更的建议
        critical_changes = [c for c in changes if c.severity == RiskLevel.HIGH]
        if critical_changes:
            recommendations.append({
                "priority": "P0",
                "action": "阻塞升级",
                "reason": f"发现{len(critical_changes)}个高风险变更",
                "details": [c.description for c in critical_changes[:3]]
            })
        
        # 基于依赖影响的建议
        high_risk_deps = [d for d in dep_impacts if d["overall_risk"] == RiskLevel.HIGH]
        if high_risk_deps:
            recommendations.append({
                "priority": "P1",
                "action": "检查依赖兼容性",
                "reason": f"{len(high_risk_deps)}个第三方依赖受影响",
                "details": [d["dependency"] for d in high_risk_deps]
            })
        
        # 迁移指南
        breaking_changes = [c for c in changes if c.breaking]
        if breaking_changes:
            recommendations.append({
                "priority": "P1",
                "action": "准备迁移",
                "reason": f"存在{len(breaking_changes)}个破坏性变更",
                "details": [c.migration_guide for c in breaking_changes if c.migration_guide]
            })
        
        return recommendations
    
    def generate_migration_plan(self, changes: List[Change], dep_impacts: List[Dict]) -> List[Dict]:
        """生成迁移计划"""
        plan = []
        
        # 第一步：备份
        plan.append({
            "step": 1,
            "action": "备份当前配置",
            "command": "backup_config.sh",
            "rollback": "恢复备份"
        })
        
        # 第二步：检查依赖
        if dep_impacts:
            plan.append({
                "step": 2,
                "action": "检查第三方依赖兼容性",
                "details": [d["dependency"] for d in dep_impacts],
                "rollback": "暂缓升级"
            })
        
        # 第三步：执行迁移
        arch_changes = [c for c in changes if c.type == "architecture"]
        if arch_changes:
            plan.append({
                "step": 3,
                "action": "执行目录迁移",
                "details": [c.description for c in arch_changes[:2]],
                "rollback": "手动回滚目录"
            })
        
        # 第四步：验证
        plan.append({
            "step": 4,
            "action": "验证核心功能",
            "command": "verify_system.sh",
            "rollback": "回滚版本"
        })
        
        return plan

# ==================== Changelog获取器 ====================

class ChangelogFetcher:
    """获取OpenClaw Changelog"""
    
    def __init__(self):
        self.api_url = GITHUB_API
        self.cache_file = os.path.expanduser(CHANGELOG_CACHE)
    
    def fetch_latest_changelog(self, current_version: str) -> str:
        """获取最新版本的Changelog"""
        try:
            # 尝试从GitHub获取
            url = self.api_url.format(OPENCLAW_REPO) + "/releases"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                releases = response.json()
                
                # 解析release notes
                changelog_parts = []
                for release in releases[:5]:  # 最近5个版本
                    tag = release.get("tag_name", "")
                    body = release.get("body", "")
                    
                    if body:
                        changelog_parts.append(f"## [{tag}]\n\n{body}")
                
                return "\n\n".join(changelog_parts)
            
            return self._get_cached_changelog()
        
        except Exception as e:
            print(f"[WARN] 获取Changelog失败: {e}")
            return self._get_cached_changelog()
    
    def _get_cached_changelog(self) -> str:
        """获取缓存的Changelog"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file) as f:
                    return f.read()
        except:
            pass
        return ""

# ==================== 主函数 ====================

def main():
    """主函数"""
    print(f"[Impact Analyzer] 开始分析... {datetime.now().isoformat()}")
    
    analyzer = ImpactAnalyzer()
    fetcher = ChangelogFetcher()
    
    # 获取当前版本
    import subprocess
    try:
        result = subprocess.run(["openclaw", "--version"], capture_output=True, text=True)
        current_version = result.stdout.strip()
    except:
        current_version = "unknown"
    
    print(f"当前版本: {current_version}")
    
    # 获取Changelog
    print("获取Changelog...")
    changelog = fetcher.fetch_latest_changelog(current_version)
    
    if not changelog:
        print("[WARN] 无法获取Changelog，使用模拟数据")
        changelog = """
## [v2026.4.11]
- BREAKING: 目录结构重组，skills/ 迁移至 workspace/skills/
- FEATURE: 新增 capabilities 配置项
- API: /api/v2 接口变更
- DEPENDENCY: 升级 Python 要求至 3.12+
"""
    
    # 解析变更
    print("解析变更...")
    changes = analyzer.parse_changelog(changelog)
    
    print(f"发现 {len(changes)} 个变更")
    
    # 评估依赖影响
    print("评估第三方依赖影响...")
    dep_impacts = analyzer.assess_dependency_impact(changes)
    
    # 生成建议
    recommendations = analyzer.generate_recommendations(changes, dep_impacts)
    
    # 生成迁移计划
    migration_plan = analyzer.generate_migration_plan(changes, dep_impacts)
    
    # 风险汇总
    risk_summary = {
        "CRITICAL": len([c for c in changes if c.severity == RiskLevel.CRITICAL]),
        "HIGH": len([c for c in changes if c.severity == RiskLevel.HIGH]),
        "MEDIUM": len([c for c in changes if c.severity == RiskLevel.MEDIUM]),
        "LOW": len([c for c in changes if c.severity == RiskLevel.LOW]),
        "INFO": len([c for c in changes if c.severity == RiskLevel.INFO]),
    }
    
    # 构建报告
    report = ImpactReport(
        timestamp=datetime.now().isoformat(),
        current_version=current_version,
        target_version="2026.4.11",
        changes=[asdict(c) for c in changes],
        risk_summary=risk_summary,
        affected_dependencies=dep_impacts,
        recommendations=recommendations,
        migration_plan=migration_plan
    )
    
    # 输出报告
    print("\n" + "="*60)
    print("影响分析报告".center(50))
    print("="*60)
    
    print(f"\n📊 风险汇总:")
    for risk, count in risk_summary.items():
        if count > 0:
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "⚪"}.get(risk, "")
            print(f"  {icon} {risk}: {count}")
    
    if dep_impacts:
        print(f"\n📦 第三方依赖影响:")
        for dep in dep_impacts:
            icon = "🔴" if dep["overall_risk"] == RiskLevel.HIGH else "🟡"
            print(f"  {icon} {dep['dependency']}: {len(dep['impacts'])}个影响")
    
    if recommendations:
        print(f"\n💡 建议:")
        for rec in recommendations[:3]:
            print(f"  [{rec['priority']}] {rec['action']}: {rec['reason']}")
    
    # 保存JSON报告
    report_file = "~/.openclaw/.impact_report.json"
    os.makedirs(os.path.dirname(os.path.expanduser(report_file)), exist_ok=True)
    with open(os.path.expanduser(report_file), "w") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存到 {report_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
