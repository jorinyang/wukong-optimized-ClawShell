#!/usr/bin/env python3
"""
ClawShell 自发现引擎 (Self-Discovery Engine)
版本: v0.2.1-A
功能: 自动扫描系统能力、可用服务、接口
"""

import os
import json
import time
import subprocess
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict

# ============ 配置 ============

DISCOVERY_STATE_PATH = Path("~/.real/.discovery_state.json").expanduser()
SKILLS_DIR = Path("~/.real/skills").expanduser()
WORKSPACE_DIR = Path("~/.real/workspace").expanduser()
CONFIG_DIR = Path("~/.real/config").expanduser()
SCRIPTS_DIR = Path("~/.real/scripts").expanduser()


# ============ 数据结构 ============

@dataclass
class Capability:
    """能力描述"""
    name: str
    type: str  # skill, tool, script, agent, api, hook
    category: str  # 分组类别
    path: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = None
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "path": self.path,
            "description": self.description,
            "keywords": self.keywords,
            "metadata": self.metadata or {}
        }


@dataclass
class Interface:
    """接口描述"""
    name: str
    type: str  # mcp, webhook, api, cli
    endpoint: Optional[str] = None
    method: Optional[str] = None
    parameters: Optional[List[Dict]] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "endpoint": self.endpoint,
            "method": self.method,
            "parameters": self.parameters or [],
            "description": self.description
        }


@dataclass
class DiscoveryReport:
    """发现报告"""
    timestamp: float
    capabilities: List[Capability]
    interfaces: List[Interface]
    categories: Dict[str, int]  # 各类别能力数量
    total_count: int
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "interfaces": [i.to_dict() for i in self.interfaces],
            "categories": self.categories,
            "total_count": self.total_count
        }


# ============ 自发现引擎 ============

class DiscoveryEngine:
    """自发现引擎"""
    
    def __init__(self):
        self.capabilities: List[Capability] = []
        self.interfaces: List[Interface] = []
        self._load_state()
    
    def _load_state(self):
        """加载上次发现状态"""
        if DISCOVERY_STATE_PATH.exists():
            try:
                with open(DISCOVERY_STATE_PATH) as f:
                    data = json.load(f)
                    # 可以恢复上次发现的能力列表
            except:
                pass
    
    def _save_state(self):
        """保存发现状态"""
        state = {
            "last_discovery": time.time(),
            "capabilities_count": len(self.capabilities)
        }
        with open(DISCOVERY_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    
    # ---- 能力发现 ----
    
    def discover_capabilities(self) -> List[Capability]:
        """发现系统能力"""
        capabilities = []
        
        # 1. 发现Skills
        capabilities.extend(self._discover_skills())
        
        # 2. 发现MCPs
        capabilities.extend(self._discover_mcps())
        
        # 3. 发现Agents
        capabilities.extend(self._discover_agents())
        
        # 4. 发现Scripts
        capabilities.extend(self._discover_scripts())
        
        # 5. 发现Hooks
        capabilities.extend(self._discover_hooks())
        
        # 6. 发现Crons
        capabilities.extend(self._discover_crons())
        
        self.capabilities = capabilities
        return capabilities
    
    def _discover_skills(self) -> List[Capability]:
        """发现Skills"""
        capabilities = []
        
        if not SKILLS_DIR.exists():
            return capabilities
        
        for skill_path in SKILLS_DIR.rglob("SKILL.md"):
            try:
                skill_dir = skill_path.parent
                rel_path = skill_dir.relative_to(SKILLS_DIR)
                
                # 解析SKILL.md获取描述
                description = self._extract_skill_description(skill_path)
                
                # 提取关键词
                keywords = self._extract_keywords(skill_path)
                
                # 扫描脚本
                scripts = list(skill_dir.glob("*.sh")) + list(skill_dir.glob("*.py"))
                
                capability = Capability(
                    name=skill_dir.name,
                    type="skill",
                    category=f"skill/{rel_path.parts[0]}" if len(rel_path.parts) > 1 else "skill",
                    path=str(skill_dir),
                    description=description,
                    keywords=keywords,
                    metadata={
                        "script_count": len(scripts),
                        "has_readme": (skill_dir / "README.md").exists()
                    }
                )
                capabilities.append(capability)
            except Exception as e:
                print(f"发现Skill失败 {skill_path}: {e}")
        
        return capabilities
    
    def _extract_skill_description(self, skill_md_path: Path) -> str:
        """提取Skill描述"""
        try:
            content = skill_md_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # 取第一段非空非标题内容作为描述
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line[:200]  # 最多200字符
        except:
            pass
        return ""
    
    def _extract_keywords(self, skill_md_path: Path) -> List[str]:
        """提取关键词"""
        keywords = []
        try:
            content = skill_md_path.read_text(encoding='utf-8')
            
            # 提取代码块中的命令
            import re
            commands = re.findall(r'`([^`]+)`', content)
            keywords.extend([c.strip() for c in commands if len(c) < 50])
            
            # 提取工具名
            tools = re.findall(r'(?:tool|skill|script):\s*[`"]?([\w-]+)[`"]?', content, re.IGNORECASE)
            keywords.extend(tools)
            
            # 去重
            keywords = list(set(keywords))[:20]  # 最多20个
        except:
            pass
        return keywords
    
    def _discover_mcps(self) -> List[Capability]:
        """发现MCP服务"""
        capabilities = []
        
        mcp_configs = [
            CONFIG_DIR / "mcp.json",
            CONFIG_DIR / "mcp_settings.json",
            Path("~/.claude/mcp.json").expanduser(),
        ]
        
        for config_path in mcp_configs:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        data = json.load(f)
                    
                    servers = data.get("mcpServers", {}) or data.get("servers", {})
                    
                    for name, config in servers.items():
                        if isinstance(config, dict):
                            command = config.get("command", "")
                            description = config.get("description", "")
                        else:
                            command = str(config)
                            description = ""
                        
                        capability = Capability(
                            name=name,
                            type="mcp",
                            category="mcp",
                            description=description,
                            keywords=[command.split('/')[-1] if '/' in command else command],
                            metadata={"config_path": str(config_path)}
                        )
                        capabilities.append(capability)
                except Exception as e:
                    print(f"解析MCP配置失败 {config_path}: {e}")
        
        return capabilities
    
    def _discover_agents(self) -> List[Capability]:
        """发现Agents"""
        capabilities = []
        
        agents_dir = Path("~/.real/agents").expanduser()
        if not agents_dir.exists():
            return capabilities
        
        for agent_file in agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text(encoding='utf-8')
                
                # 提取名称和描述
                name = agent_file.stem
                description = ""
                keywords = []
                
                for line in content.split('\n')[:50]:
                    if line.startswith('# '):
                        name = line[2:].strip()
                    elif line.startswith('**') and '**' in line[2:]:
                        desc_match = line.match(r'\*\*([^*]+)\*\*')
                        if desc_match:
                            description = desc_match.group(1)
                    elif '```' not in line:
                        keywords.extend([w for w in line.split() if len(w) > 3])
                
                capability = Capability(
                    name=name,
                    type="agent",
                    category="agent",
                    path=str(agent_file),
                    description=description[:200] if description else "",
                    keywords=list(set(keywords))[:10]
                )
                capabilities.append(capability)
            except Exception as e:
                print(f"发现Agent失败 {agent_file}: {e}")
        
        return capabilities
    
    def _discover_scripts(self) -> List[Capability]:
        """发现Scripts"""
        capabilities = []
        
        if not SCRIPTS_DIR.exists():
            return capabilities
        
        # 关键脚本
        critical_patterns = [
            "*version*", "*impact*", "*adapt*",
            "*graph*", "*knowledge*", "*hermes*",
            "*n8n*", "*verify*", "*update*"
        ]
        
        for pattern in critical_patterns:
            for script_path in SCRIPTS_DIR.glob(pattern):
                if script_path.is_file():
                    capability = Capability(
                        name=script_path.name,
                        type="script",
                        category="script",
                        path=str(script_path),
                        description=self._get_script_description(script_path),
                        keywords=[script_path.stem.split('_')[0]]
                    )
                    capabilities.append(capability)
        
        return capabilities
    
    def _get_script_description(self, script_path: Path) -> str:
        """获取脚本描述"""
        try:
            content = script_path.read_text(encoding='utf-8')
            lines = content.split('\n')[:20]
            
            # 查找docstring或注释
            for line in lines:
                line = line.strip()
                if line.startswith('"""') or line.startswith("'''"):
                    # 多行docstring
                    continue
                elif line.startswith('#'):
                    return line[1:].strip()[:100]
                elif line.startswith('"""') or line.startswith("'''"):
                    return line[3:-3].strip()[:100]
        except:
            pass
        return ""
    
    def _discover_hooks(self) -> List[Capability]:
        """发现Hooks"""
        capabilities = []
        
        hooks_dir = Path("~/.real/hooks").expanduser()
        if not hooks_dir.exists():
            return capabilities
        
        for hook_file in hooks_dir.rglob("*.py"):
            try:
                content = hook_file.read_text(encoding='utf-8')
                
                # 检查是否是hook文件
                if "hook" in content.lower() or "on_" in content:
                    capability = Capability(
                        name=hook_file.stem,
                        type="hook",
                        category="hook",
                        path=str(hook_file),
                        description="事件钩子"
                    )
                    capabilities.append(capability)
            except:
                pass
        
        return capabilities
    
    def _discover_crons(self) -> List[Capability]:
        """发现Cron任务"""
        capabilities = []
        
        cron_dir = Path("~/.real/cron").expanduser()
        if not cron_dir.exists():
            return capabilities
        
        for cron_file in cron_dir.glob("*.json"):
            try:
                with open(cron_file) as f:
                    data = json.load(f)
                
                name = data.get("name", cron_file.stem)
                schedule = data.get("schedule", "")
                description = data.get("description", "")
                
                capability = Capability(
                    name=name,
                    type="cron",
                    category="cron",
                    path=str(cron_file),
                    description=description or f"定时任务: {schedule}",
                    metadata={"schedule": schedule}
                )
                capabilities.append(capability)
            except:
                pass
        
        return capabilities
    
    # ---- 接口发现 ----
    
    def discover_interfaces(self) -> List[Interface]:
        """发现接口"""
        interfaces = []
        
        # 1. 发现Webhook接口
        interfaces.extend(self._discover_webhooks())
        
        # 2. 发现MCP接口
        interfaces.extend(self._discover_mcp_interfaces())
        
        # 3. 发现API接口
        interfaces.extend(self._discover_api_interfaces())
        
        self.interfaces = interfaces
        return interfaces
    
    def _discover_webhooks(self) -> List[Interface]:
        """发现Webhook接口"""
        interfaces = []
        
        # 扫描N8N工作流
        n8n_workflows_dir = Path("~/n8n/workflows").expanduser()
        if n8n_workflows_dir.exists():
            for wf_file in n8n_workflows_dir.glob("*.json"):
                try:
                    with open(wf_file) as f:
                        data = json.load(f)
                    
                    name = data.get("name", wf_file.stem)
                    webhooks = data.get("nodes", [])
                    
                    for node in webhooks:
                        if node.get("type") == "n8n-nodes-base.webhook":
                            path = node.get("parameters", {}).get("path", "")
                            method = node.get("parameters", {}).get("httpMethod", "GET")
                            
                            interfaces.append(Interface(
                                name=f"{name}/{path}",
                                type="webhook",
                                endpoint=path,
                                method=method,
                                description=f"N8N工作流: {name}"
                            ))
                except:
                    pass
        
        return interfaces
    
    def _discover_mcp_interfaces(self) -> List[Interface]:
        """发现MCP接口"""
        interfaces = []
        
        mcp_configs = [
            CONFIG_DIR / "mcp.json",
            CONFIG_DIR / "mcp_settings.json",
        ]
        
        for config_path in mcp_configs:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        data = json.load(f)
                    
                    servers = data.get("mcpServers", {}) or data.get("servers", {})
                    
                    for name, config in servers.items():
                        if isinstance(config, dict):
                            # MCP服务可能定义了自己的接口
                            capabilities = config.get("capabilities", [])
                            for cap in capabilities:
                                interfaces.append(Interface(
                                    name=f"{name}/{cap.get('name', 'unknown')}",
                                    type="mcp",
                                    endpoint=cap.get("endpoint"),
                                    method=cap.get("method", "POST"),
                                    parameters=cap.get("parameters", []),
                                    description=cap.get("description", "")
                                ))
                except:
                    pass
        
        return interfaces
    
    def _discover_api_interfaces(self) -> List[Interface]:
        """发现API接口"""
        interfaces = []
        
        # 扫描知识库中的API文档
        api_docs_dir = WORKSPACE_DIR / "docs"
        if api_docs_dir.exists():
            for doc_file in api_docs_dir.rglob("*.md"):
                if "api" in doc_file.name.lower():
                    try:
                        content = doc_file.read_text(encoding='utf-8')
                        
                        # 简单的URL提取
                        import re
                        urls = re.findall(r'(?:https?://[^\s]+|/[a-zA-Z0-9_/{}?-]+)', content)
                        
                        for url in urls[:5]:  # 最多5个
                            if url.startswith('/'):
                                interfaces.append(Interface(
                                    name=doc_file.stem,
                                    type="api",
                                    endpoint=url,
                                    description=f"API文档: {doc_file.name}"
                                ))
                    except:
                        pass
        
        return interfaces
    
    # ---- 全局发现 ----
    
    def discover_all(self) -> DiscoveryReport:
        """执行全局发现"""
        now = time.time()
        
        # 发现能力
        capabilities = self.discover_capabilities()
        
        # 发现接口
        interfaces = self.discover_interfaces()
        
        # 生成分类统计
        categories = defaultdict(int)
        for cap in capabilities:
            categories[cap.category] += 1
        
        # 保存状态
        self._save_state()
        
        return DiscoveryReport(
            timestamp=now,
            capabilities=capabilities,
            interfaces=interfaces,
            categories=dict(categories),
            total_count=len(capabilities) + len(interfaces)
        )
    
    def search_capabilities(self, query: str, type_filter: Optional[str] = None) -> List[Capability]:
        """搜索能力"""
        if not self.capabilities:
            self.discover_capabilities()
        
        query_lower = query.lower()
        results = []
        
        for cap in self.capabilities:
            if type_filter and cap.type != type_filter:
                continue
            
            # 匹配名称、描述、关键词
            if (query_lower in cap.name.lower() or
                query_lower in cap.description.lower() or
                any(query_lower in kw.lower() for kw in cap.keywords)):
                results.append(cap)
        
        return results
    
    def get_capability_map(self) -> Dict[str, List[str]]:
        """获取能力地图"""
        if not self.capabilities:
            self.discover_capabilities()
        
        capability_map = defaultdict(list)
        for cap in self.capabilities:
            capability_map[cap.category].append(cap.name)
        
        return dict(capability_map)


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 自发现引擎")
    parser.add_argument("--format", choices=["json", "text", "tree"], default="text")
    parser.add_argument("--search", type=str, help="搜索能力")
    parser.add_argument("--type", type=str, choices=["skill", "mcp", "agent", "script", "hook", "cron"], help="按类型筛选")
    parser.add_argument("--capabilities", action="store_true", help="只显示能力")
    parser.add_argument("--interfaces", action="store_true", help="只显示接口")
    args = parser.parse_args()
    
    engine = DiscoveryEngine()
    
    if args.search:
        capabilities = engine.search_capabilities(args.search, args.type)
        
        if args.format == "json":
            print(json.dumps([c.to_dict() for c in capabilities], indent=2, ensure_ascii=False))
        else:
            print(f"搜索结果: '{args.search}' ({len(capabilities)}个)")
            for cap in capabilities:
                print(f"  [{cap.type}] {cap.name}")
                if cap.description:
                    print(f"      {cap.description[:80]}")
    else:
        if args.capabilities:
            report = engine.discover_capabilities()
            capabilities = report if isinstance(report, list) else engine.capabilities
            categories = engine.get_capability_map()
            
            if args.format == "tree":
                print("能力地图:")
                for cat, caps in sorted(categories.items()):
                    print(f"  {cat}/")
                    for cap in caps:
                        print(f"    └── {cap}")
            elif args.format == "json":
                print(json.dumps([c.to_dict() for c in capabilities], indent=2, ensure_ascii=False))
            else:
                print(f"发现 {len(capabilities)} 个能力:")
                for cat, caps in sorted(categories.items()):
                    print(f"  [{cat}] {len(caps)}个")
        
        elif args.interfaces:
            interfaces = engine.discover_interfaces()
            
            if args.format == "json":
                print(json.dumps([i.to_dict() for i in interfaces], indent=2, ensure_ascii=False))
            else:
                print(f"发现 {len(interfaces)} 个接口:")
                for iface in interfaces:
                    method = iface.method or "ANY"
                    print(f"  [{iface.type}] {method:6} {iface.endpoint or iface.name}")
        
        else:
            report = engine.discover_all()
            
            if args.format == "json":
                print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            else:
                print("=" * 60)
                print("ClawShell 自发现引擎 v0.2.1-A")
                print("=" * 60)
                print(f"发现时间: {report.timestamp}")
                print()
                
                print("能力统计:")
                for cat, count in sorted(report.categories.items()):
                    print(f"  {cat}: {count}")
                print(f"  接口: {len(report.interfaces)}")
                print(f"  总计: {report.total_count}")
                
                if args.format == "tree":
                    print()
                    print("能力地图:")
                    capability_map = engine.get_capability_map()
                    for cat, caps in sorted(capability_map.items()):
                        print(f"  {cat}/")
                        for cap in caps[:10]:  # 最多显示10个
                            print(f"    └── {cap}")
                        if len(caps) > 10:
                            print(f"    └── ... (+{len(caps) - 10} more)")


if __name__ == "__main__":
    main()
