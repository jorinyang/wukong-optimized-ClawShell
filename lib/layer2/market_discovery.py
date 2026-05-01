#!/usr/bin/env python3
"""
ClawShell 外部市场发现引擎 (External Market Discovery)
版本: v0.2.1-B-ext
功能: 发现并评估外部MCP/API/Skills资源，输出多维度对比报告
"""

import os
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import urllib.request
import urllib.error

# ============ 配置 ============

MARKET_CACHE_PATH = Path("~/.real/.market_discovery_cache.json").expanduser()
MARKET_CONFIG_PATH = Path("~/.real/.market_config.json").expanduser()


# ============ 数据结构 ============

class ResourceType(Enum):
    """资源类型"""
    MCP = "mcp"
    API = "api"
    SKILL = "skill"
    FUNCTION = "function"


class ChinaSuitability(Enum):
    """国内适用性"""
    EXCELLENT = "excellent"   # 原生支持
    GOOD = "good"            # 需配置
    LIMITED = "limited"       # 勉强可用
    NOT_AVAILABLE = "not_available"  # 不可用


@dataclass
class Resource:
    """资源"""
    id: str
    name: str
    type: ResourceType
    provider: str  # 来源平台
    description: str
    endpoint: Optional[str] = None
    pricing: Optional[str] = None  # 定价
    homepage: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    china_suitability: ChinaSuitability = ChinaSuitability.GOOD
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "provider": self.provider,
            "description": self.description,
            "endpoint": self.endpoint,
            "pricing": self.pricing,
            "homepage": self.homepage,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "china_suitability": self.china_suitability.value,
            "metadata": self.metadata
        }


@dataclass
class EvaluationCriteria:
    """评估标准"""
    quality_score: float = 0.0       # 优劣度 0-100
    cost_efficiency: float = 0.0     # 性价比 0-100
    functionality: float = 0.0       # 功能性 0-100
    china_suitability_score: float = 0.0  # 国内适用性 0-100
    overall_score: float = 0.0      # 综合评分 0-100
    
    def calculate_overall(self, weights: Dict[str, float] = None) -> float:
        """计算综合评分"""
        if weights is None:
            weights = {
                "quality": 0.25,
                "cost": 0.25,
                "functionality": 0.25,
                "china": 0.25
            }
        
        self.overall_score = (
            self.quality_score * weights["quality"] +
            self.cost_efficiency * weights["cost"] +
            self.functionality * weights["functionality"] +
            self.china_suitability_score * weights["china"]
        )
        return self.overall_score


@dataclass
class EvaluatedResource:
    """已评估资源"""
    resource: Resource
    evaluation: EvaluationCriteria
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    recommendation: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "resource": self.resource.to_dict(),
            "evaluation": {
                "quality": self.evaluation.quality_score,
                "cost_efficiency": self.evaluation.cost_efficiency,
                "functionality": self.evaluation.functionality,
                "china_suitability": self.evaluation.china_suitability_score,
                "overall": self.evaluation.overall_score
            },
            "pros": self.pros,
            "cons": self.cons,
            "recommendation": self.recommendation
        }


# ============ 市场发现器基类 ============

class BaseMarketDiscoverer:
    """市场发现器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.resources: List[Resource] = []
        self.last_fetch = 0
        self.cache_ttl = 3600  # 1小时缓存
    
    def fetch(self, force: bool = False) -> List[Resource]:
        """获取资源列表"""
        now = time.time()
        
        if not force and now - self.last_fetch < self.cache_ttl and self.resources:
            return self.resources
        
        self.resources = self._do_fetch()
        self.last_fetch = now
        return self.resources
    
    def _do_fetch(self) -> List[Resource]:
        """执行获取（子类实现）"""
        raise NotImplementedError
    
    def _make_request(self, url: str, timeout: int = 10) -> Optional[str]:
        """发送HTTP请求"""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "ClawShell-Market-Discovery/0.2")
            req.add_header("Accept", "application/json, text/html")
            
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            print(f"Request failed {url}: {e}")
            return None


# ============ 钉钉AIHub MCP发现器 ============

class DingTalkAIHubDiscoverer(BaseMarketDiscoverer):
    """钉钉AIHub MCP市场发现器"""
    
    def __init__(self):
        super().__init__("钉钉AIHub")
        self.base_url = "https://aihub.dingtalk.com"
        self.mcp_url = "https://aihub.dingtalk.com/api/mcp/v1/markets"
    
    def _do_fetch(self) -> List[Resource]:
        """获取钉钉AIHub MCP列表"""
        resources = []
        
        # 尝试获取MCP市场数据
        try:
            # 直接抓取页面
            content = self._make_request(self.base_url + "/#/mcp")
            if content:
                resources.extend(self._parse_dingtalk_mcp(content))
        except Exception as e:
            print(f"Failed to fetch DingTalk AIHub: {e}")
        
        # 添加预配置的已知MCP
        resources.extend(self._get_known_mcps())
        
        return resources
    
    def _parse_dingtalk_mcp(self, content: str) -> List[Resource]:
        """解析钉钉MCP页面"""
        resources = []
        
        # 预配置的钉钉生态MCP
        known_mcps = [
            {
                "id": "dingtalk-calendar",
                "name": "钉钉日历",
                "description": "钉钉日历MCP服务，支持日程CRUD",
                "endpoint": "https://mcp-gw.dingtalk.com/server/8358166daf75692b8bb17f8f3a48d5413c0749cbac774ce546dcebb65161f71d",
                "pricing": "免费",
                "tags": ["日历", "日程", "钉钉"],
                "capabilities": ["日程创建", "日程查询", "日程修改", "日程删除"]
            },
            {
                "id": "dingtalk-contacts",
                "name": "钉钉通讯录",
                "description": "钉钉通讯录MCP服务",
                "endpoint": "https://mcp-gw.dingtalk.com/contacts",
                "pricing": "免费",
                "tags": ["通讯录", "用户", "钉钉"],
                "capabilities": ["用户查询", "部门查询"]
            },
            {
                "id": "dingtalk-docs",
                "name": "钉钉文档",
                "description": "钉钉文档MCP服务",
                "endpoint": "https://mcp-gw.dingtalk.com/docs",
                "pricing": "免费",
                "tags": ["文档", "知识库", "钉钉"],
                "capabilities": ["文档创建", "文档查询", "文档更新"]
            },
            {
                "id": "dingtalk-todo",
                "name": "钉钉待办",
                "description": "钉钉待办任务MCP服务",
                "endpoint": "https://mcp-gw.dingtalk.com/todo",
                "pricing": "免费",
                "tags": ["待办", "任务", "钉钉"],
                "capabilities": ["待办创建", "待办查询", "待办完成"]
            }
        ]
        
        for mcp in known_mcps:
            resources.append(Resource(
                id=mcp["id"],
                name=mcp["name"],
                type=ResourceType.MCP,
                provider="钉钉AIHub",
                description=mcp["description"],
                endpoint=mcp["endpoint"],
                pricing=mcp.get("pricing"),
                homepage=self.base_url + "/#/mcp",
                tags=mcp.get("tags", []),
                capabilities=mcp.get("capabilities", []),
                china_suitability=ChinaSuitability.EXCELLENT,
                metadata={"source": "dingtalk_aihub"}
            ))
        
        return resources
    
    def _get_known_mcps(self) -> List[Resource]:
        """获取已知MCP列表"""
        return []  # 已在_parse_dingtalk_mcp中包含


# ============ 阿里云云市场发现器 ============

class AliyunMarketDiscoverer(BaseMarketDiscoverer):
    """阿里云云市场发现器"""
    
    def __init__(self):
        super().__init__("阿里云云市场")
        self.base_url = "https://market.aliyun.com"
        self.api_category = "/products"
    
    def _do_fetch(self) -> List[Resource]:
        """获取阿里云API列表"""
        resources = []
        
        # 已知阿里云API类别
        known_apis = [
            {
                "id": "aliyun-ecs",
                "name": "ECS云服务器",
                "description": "弹性计算服务API",
                "endpoint": "https://ecs.aliyuncs.com",
                "pricing": "按量付费",
                "tags": ["云服务器", "计算", "ECS"],
                "capabilities": ["实例管理", "快照", "安全组"]
            },
            {
                "id": "aliyun-rds",
                "name": "RDS数据库",
                "description": "关系型数据库服务API",
                "endpoint": "https://rds.aliyuncs.com",
                "pricing": "包年包月/按量",
                "tags": ["数据库", "MySQL", "PostgreSQL"],
                "capabilities": ["实例管理", "备份", "监控"]
            },
            {
                "id": "aliyun-oss",
                "name": "OSS对象存储",
                "description": "对象存储服务API",
                "endpoint": "https://oss.aliyuncs.com",
                "pricing": "按量付费",
                "tags": ["存储", "对象存储", "OSS"],
                "capabilities": ["上传下载", "存储管理", "生命周期"]
            },
            {
                "id": "aliyun-sls",
                "name": "SLS日志服务",
                "description": "日志服务API",
                "endpoint": "https://sls.aliyuncs.com",
                "pricing": "按量付费",
                "tags": ["日志", "监控", "SLS"],
                "capabilities": ["日志采集", "日志查询", "仪表盘"]
            },
            {
                "id": "aliyun-fc",
                "name": "函数计算",
                "description": "Serverless函数计算服务API",
                "endpoint": "https://fc.aliyuncs.com",
                "pricing": "按调用次数/时长",
                "tags": ["Serverless", "函数计算", "FC"],
                "capabilities": ["函数部署", "函数调用", "触发器"]
            },
            {
                "id": "aliyun-dingtalk",
                "name": "钉钉开放平台",
                "description": "钉钉企业级API",
                "endpoint": "https://oapi.dingtalk.com",
                "pricing": "基础免费",
                "tags": ["钉钉", "企业", "IM"],
                "capabilities": ["消息推送", "用户管理", "审批"],
                "china_suitability": ChinaSuitability.EXCELLENT
            }
        ]
        
        for api in known_apis:
            resources.append(Resource(
                id=api["id"],
                name=api["name"],
                type=ResourceType.API,
                provider="阿里云",
                description=api["description"],
                endpoint=api["endpoint"],
                pricing=api.get("pricing"),
                homepage=self.base_url,
                tags=api.get("tags", []),
                capabilities=api.get("capabilities", []),
                china_suitability=api.get("china_suitability", ChinaSuitability.EXCELLENT),
                metadata={"source": "aliyun_market"}
            ))
        
        return resources


# ============ Clawd Skills Hub发现器 ============

class ClawdMarketDiscoverer(BaseMarketDiscoverer):
    """Clawd Skills市场发现器"""
    
    def __init__(self):
        super().__init__("Clawd Skills Hub")
        self.base_url = "https://clawd.org.cn"
        self.market_url = self.base_url + "/market"
    
    def _do_fetch(self) -> List[Resource]:
        """获取Clawd Skills列表"""
        resources = []
        
        try:
            content = self._make_request(self.market_url)
            if content:
                resources.extend(self._parse_clawd_skills(content))
        except Exception as e:
            print(f"Failed to fetch Clawd: {e}")
        
        # 补充已知Skills
        resources.extend(self._get_known_skills())
        
        return resources
    
    def _parse_clawd_skills(self, content: str) -> List[Resource]:
        """解析Clawd页面"""
        # 预留解析逻辑
        return []
    
    def _get_known_skills(self) -> List[Resource]:
        """获取已知Skills"""
        known_skills = [
            {
                "id": "clawd-trip-planner",
                "name": "行程规划助手",
                "description": "智能行程规划与分析，支持车次/航班/酒店查询",
                "pricing": "免费",
                "tags": ["出行", "行程", "规划"],
                "capabilities": ["车次查询", "航班搜索", "酒店推荐", "行程报告"]
            },
            {
                "id": "clawd-weather",
                "name": "天气预报助手",
                "description": "实时天气查询与预报",
                "pricing": "免费",
                "tags": ["天气", "预报", "出行"],
                "capabilities": ["当前天气", "未来预报", "空气质量"]
            },
            {
                "id": "clawd-translation",
                "name": "翻译助手",
                "description": "多语言翻译服务",
                "pricing": "免费",
                "tags": ["翻译", "语言", "文字"],
                "capabilities": ["文本翻译", "语言检测"]
            }
        ]
        
        resources = []
        for skill in known_skills:
            resources.append(Resource(
                id=skill["id"],
                name=skill["name"],
                type=ResourceType.SKILL,
                provider="Clawd",
                description=skill["description"],
                pricing=skill.get("pricing"),
                homepage=self.market_url,
                tags=skill.get("tags", []),
                capabilities=skill.get("capabilities", []),
                china_suitability=ChinaSuitability.EXCELLENT,
                metadata={"source": "clawd_market"}
            ))
        
        return resources


# ============ 资源评估器 ============

class ResourceEvaluator:
    """资源评估器"""
    
    def __init__(self):
        self.weights = {
            "quality": 0.25,
            "cost": 0.25,
            "functionality": 0.25,
            "china": 0.25
        }
    
    def evaluate(self, resource: Resource) -> EvaluatedResource:
        """评估单个资源"""
        eval_criteria = EvaluationCriteria()
        
        # 1. 优劣度评估
        eval_criteria.quality_score = self._evaluate_quality(resource)
        
        # 2. 性价比评估
        eval_criteria.cost_efficiency = self._evaluate_cost(resource)
        
        # 3. 功能性评估
        eval_criteria.functionality = self._evaluate_functionality(resource)
        
        # 4. 国内适用性评估
        eval_criteria.china_suitability_score = self._evaluate_china_suitability(resource)
        
        # 计算综合评分
        eval_criteria.calculate_overall(self.weights)
        
        # 生成优缺点
        pros, cons = self._generate_pros_cons(resource, eval_criteria)
        
        # 生成建议
        recommendation = self._generate_recommendation(resource, eval_criteria)
        
        return EvaluatedResource(
            resource=resource,
            evaluation=eval_criteria,
            pros=pros,
            cons=cons,
            recommendation=recommendation
        )
    
    def _evaluate_quality(self, resource: Resource) -> float:
        """评估优劣度"""
        score = 70.0  # 基础分
        
        # 来源加成
        if resource.provider in ["钉钉AIHub", "阿里云", "Clawd"]:
            score += 15
        elif "github" in resource.homepage.lower():
            score += 10
        
        # 标签加分
        quality_tags = ["官方", "enterprise", "production", "stable"]
        for tag in quality_tags:
            if tag.lower() in " ".join(resource.tags).lower():
                score += 5
        
        # 能力数量
        score += min(len(resource.capabilities) * 2, 10)
        
        return min(score, 100)
    
    def _evaluate_cost(self, resource: Resource) -> float:
        """评估性价比"""
        pricing = (resource.pricing or "").lower()
        
        if "免费" in pricing:
            return 100.0
        elif "按量" in pricing:
            return 80.0
        elif "包年" in pricing or "订阅" in pricing:
            return 60.0
        elif "企业" in pricing or "商业" in pricing:
            return 40.0
        else:
            return 50.0  # 未知定价
    
    def _evaluate_functionality(self, resource: Resource) -> float:
        """评估功能性"""
        score = 50.0  # 基础分
        
        # 能力数量
        score += min(len(resource.capabilities) * 5, 30)
        
        # 能力类型加成
        advanced_caps = ["AI", "ML", "分析", "智能", "自动"]
        for cap in resource.capabilities:
            for adv in advanced_caps:
                if adv in cap:
                    score += 5
                    break
        
        return min(score, 100)
    
    def _evaluate_china_suitability(self, resource: Resource) -> float:
        """评估国内适用性"""
        mapping = {
            ChinaSuitability.EXCELLENT: 100.0,
            ChinaSuitability.GOOD: 75.0,
            ChinaSuitability.LIMITED: 40.0,
            ChinaSuitability.NOT_AVAILABLE: 10.0
        }
        return mapping.get(resource.china_suitability, 50.0)
    
    def _generate_pros_cons(self, resource: Resource, eval: EvaluationCriteria) -> Tuple[List[str], List[str]]:
        """生成优缺点"""
        pros = []
        cons = []
        
        # 优点
        if eval.china_suitability_score >= 90:
            pros.append("国内原生支持，访问稳定")
        if eval.cost_efficiency >= 80:
            pros.append("定价合理或免费")
        if eval.functionality >= 70:
            pros.append("功能丰富，覆盖场景广")
        if len(resource.capabilities) >= 5:
            pros.append(f"提供{len(resource.capabilities)}种能力")
        
        # 缺点
        if eval.china_suitability_score < 60:
            cons.append("国内访问可能受限")
        if eval.cost_efficiency < 50:
            cons.append("定价较高")
        if eval.functionality < 50:
            cons.append("功能相对简单")
        if not resource.endpoint:
            cons.append("无明确接入端点")
        
        return pros, cons
    
    def _generate_recommendation(self, resource: Resource, eval: EvaluationCriteria) -> str:
        """生成建议"""
        if eval.overall_score >= 80:
            return f"⭐ 强烈推荐：{resource.name} 综合表现优秀"
        elif eval.overall_score >= 60:
            return f"✅ 推荐使用：{resource.name} 性价比较高"
        elif eval.overall_score >= 40:
            return f"⚠️ 谨慎选择：{resource.name} 需评估后使用"
        else:
            return f"❌ 不推荐：{resource.name} 国内适用性差或性价比低"


# ============ 市场发现引擎 ============

class MarketDiscoveryEngine:
    """外部市场发现引擎"""
    
    def __init__(self):
        self.discoverers: Dict[str, BaseMarketDiscoverer] = {
            "dingtalk": DingTalkAIHubDiscoverer(),
            "aliyun": AliyunMarketDiscoverer(),
            "clawd": ClawdMarketDiscoverer()
        }
        self.evaluator = ResourceEvaluator()
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存"""
        if MARKET_CACHE_PATH.exists():
            try:
                with open(MARKET_CACHE_PATH) as f:
                    cache = json.load(f)
                    # 恢复各发现器的资源
                    for name, discoverer in self.discoverers.items():
                        if name in cache.get("resources", {}):
                            # 缓存数据可在force刷新时使用
                            pass
            except:
                pass
    
    def _save_cache(self):
        """保存缓存"""
        cache = {
            "last_update": time.time(),
            "resources": {
                name: [r.to_dict() for r in d.resources]
                for name, d in self.discoverers.items()
            }
        }
        with open(MARKET_CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=2)
    
    def discover_all(self, force: bool = False) -> List[Resource]:
        """发现所有外部资源"""
        all_resources = []
        
        for name, discoverer in self.discoverers.items():
            try:
                resources = discoverer.fetch(force=force)
                all_resources.extend(resources)
            except Exception as e:
                print(f"Discoverer {name} failed: {e}")
        
        self._save_cache()
        return all_resources
    
    def discover_by_type(self, resource_type: ResourceType, force: bool = False) -> List[Resource]:
        """按类型发现资源"""
        all_resources = self.discover_all(force=force)
        return [r for r in all_resources if r.type == resource_type]
    
    def discover_by_provider(self, provider: str, force: bool = False) -> List[Resource]:
        """按提供商发现资源"""
        all_resources = self.discover_all(force=force)
        return [r for r in all_resources if provider.lower() in r.provider.lower()]
    
    def evaluate_all(self, resources: Optional[List[Resource]] = None) -> List[EvaluatedResource]:
        """评估所有资源"""
        if resources is None:
            resources = self.discover_all()
        
        evaluated = []
        for resource in resources:
            try:
                evaluated.append(self.evaluator.evaluate(resource))
            except Exception as e:
                print(f"Evaluate {resource.name} failed: {e}")
        
        # 按综合评分排序
        evaluated.sort(key=lambda x: x.evaluation.overall_score, reverse=True)
        return evaluated
    
    def get_comparison_report(self) -> Dict:
        """获取对比报告"""
        resources = self.discover_all()
        evaluated = self.evaluate_all(resources)
        
        report = {
            "timestamp": time.time(),
            "total_resources": len(resources),
            "by_type": {},
            "by_provider": {},
            "top_recommendations": [],
            "evaluated_resources": []
        }
        
        # 分类统计
        for r in resources:
            t = r.type.value
            report["by_type"][t] = report["by_type"].get(t, 0) + 1
            
            p = r.provider
            report["by_provider"][p] = report["by_provider"].get(p, 0) + 1
        
        # Top推荐
        for e in evaluated[:5]:
            report["top_recommendations"].append(e.to_dict())
        
        # 完整评估列表
        report["evaluated_resources"] = [e.to_dict() for e in evaluated]
        
        return report


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell 外部市场发现引擎")
    parser.add_argument("--discover", action="store_true", help="发现资源")
    parser.add_argument("--type", choices=["mcp", "api", "skill"], help="按类型筛选")
    parser.add_argument("--provider", help="按提供商筛选")
    parser.add_argument("--evaluate", action="store_true", help="评估资源")
    parser.add_argument("--report", action="store_true", help="生成对比报告")
    parser.add_argument("--force", action="store_true", help="强制刷新缓存")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()
    
    engine = MarketDiscoveryEngine()
    
    if args.discover:
        if args.type:
            rt = ResourceType(args.type)
            resources = engine.discover_by_type(rt, force=args.force)
        elif args.provider:
            resources = engine.discover_by_provider(args.provider, force=args.force)
        else:
            resources = engine.discover_all(force=args.force)
        
        print(f"发现 {len(resources)} 个资源:")
        for r in resources:
            print(f"  [{r.type.value}] {r.name} ({r.provider})")
            print(f"      {r.description[:60]}...")
    
    elif args.evaluate:
        evaluated = engine.evaluate_all()
        
        print("=" * 80)
        print("资源评估结果")
        print("=" * 80)
        
        for e in evaluated:
            print(f"\n【{e.resource.name}】({e.resource.provider})")
            print(f"  综合评分: {e.evaluation.overall_score:.1f}/100")
            print(f"    - 优劣度: {e.evaluation.quality_score:.1f}")
            print(f"    - 性价比: {e.evaluation.cost_efficiency:.1f}")
            print(f"    - 功能性: {e.evaluation.functionality:.1f}")
            print(f"    - 国内适用: {e.evaluation.china_suitability_score:.1f}")
            print(f"  优点: {', '.join(e.pros) if e.pros else '无明显优点'}")
            print(f"  缺点: {', '.join(e.cons) if e.cons else '无明显缺点'}")
            print(f"  建议: {e.recommendation}")
    
    elif args.report:
        report = engine.get_comparison_report()
        
        if args.format == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("=" * 80)
            print("外部资源对比报告")
            print("=" * 80)
            print(f"生成时间: {time.ctime(report['timestamp'])}")
            print(f"资源总数: {report['total_resources']}")
            print()
            
            print("按类型统计:")
            for t, count in report["by_type"].items():
                print(f"  {t}: {count}")
            print()
            
            print("按提供商统计:")
            for p, count in report["by_provider"].items():
                print(f"  {p}: {count}")
            print()
            
            print("Top 5 推荐:")
            for i, rec in enumerate(report["top_recommendations"], 1):
                r = rec["resource"]
                e = rec["evaluation"]
                print(f"  {i}. {r['name']} ({r['provider']}) - 评分: {e['overall']:.1f}")
                print(f"     {rec['recommendation']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
