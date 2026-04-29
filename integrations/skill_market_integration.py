"""
ClawShell Skill Market - 悟空专属技能市场
基于 TaskMarket 基础设施构建技能分发平台
"""

import sys
sys.path.insert(0, r'C:\Users\Aorus\.ClawShell')

from lib.layer4.swarm import NodeRegistry, Node, NodeType, NodeStatus
from lib.layer3.task_market import TaskMarket, TaskMatcher, TaskPriority
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Skill:
    """技能定义"""
    skill_id: str
    name: str
    description: str
    version: str
    author: str
    category: str
    tags: list
    capabilities: list
    dependencies: list
    install_path: str

class WuKongSkillMarket:
    """悟空技能市场"""
    
    def __init__(self):
        self.node_registry = NodeRegistry()
        self.market = TaskMarket(node_registry=self.node_registry)
        self.matcher = TaskMatcher(node_registry=self.node_registry)
        self.skills = {}  # skill_id -> Skill
        
    def register_skill(self, skill: Skill):
        """注册技能到市场"""
        self.skills[skill.skill_id] = skill
        
        # 注册技能节点
        skill_node = Node(
            node_id=f'skill-{skill.skill_id}',
            node_type=NodeType.SERVICE,
            name=f'Skill: {skill.name}',
            status=NodeStatus.ACTIVE,
            capabilities=skill.capabilities
        )
        self.node_registry.register(skill_node)
        
        return skill_node
    
    def search_skills(self, query=None, category=None, tags=None):
        """搜索技能"""
        results = list(self.skills.values())
        
        if query:
            query_lower = query.lower()
            results = [s for s in results 
                      if query_lower in s.name.lower() 
                      or query_lower in s.description.lower()]
        
        if category:
            results = [s for s in results if s.category == category]
        
        if tags:
            results = [s for s in results 
                      if any(tag in s.tags for tag in tags)]
        
        return results
    
    def get_skill(self, skill_id):
        """获取技能详情"""
        return self.skills.get(skill_id)
    
    def list_categories(self):
        """列出所有分类"""
        return list(set(s.category for s in self.skills.values()))
    
    def get_skill_dependencies(self, skill_id):
        """获取技能依赖"""
        skill = self.get_skill(skill_id)
        if not skill:
            return []
        
        deps = []
        for dep_id in skill.dependencies:
            dep = self.get_skill(dep_id)
            if dep:
                deps.append(dep)
        return deps
    
    def request_skill_execution(self, skill_id, task_params):
        """请求技能执行"""
        skill = self.get_skill(skill_id)
        if not skill:
            return {'success': False, 'error': 'Skill not found'}
        
        # 提交技能执行任务
        task = self.market.submit_task(
            task_type=f'skill:{skill_id}',
            description=f"Execute skill: {skill.name}",
            priority=TaskPriority.NORMAL,
            required_capabilities=skill.capabilities
        )
        
        return {
            'success': True,
            'task_id': task.task_id,
            'skill': skill.name
        }


# 预注册悟空核心技能
CORE_SKILLS = [
    Skill(
        skill_id='clawshell-debug',
        name='ClawShell-Debug',
        description='ClawShell插件安装及调试',
        version='2.0',
        author='WuKong',
        category='development',
        tags=['clawshell', 'debug', 'development'],
        capabilities=['module_testing', 'import_validation'],
        dependencies=[],
        install_path='.skills/clawshell-debug'
    ),
    Skill(
        skill_id='clawshell-cicd',
        name='ClawShell-CICD',
        description='全自动化CI/CD部署',
        version='2.0',
        author='WuKong',
        category='devops',
        tags=['cicd', 'deployment', 'automation'],
        capabilities=['deployment', 'integration'],
        dependencies=[],
        install_path='.skills/clawshell-cicd-deploy'
    ),
]


# 集成示例
if __name__ == '__main__':
    market = WuKongSkillMarket()
    
    # 注册核心技能
    for skill in CORE_SKILLS:
        market.register_skill(skill)
    
    print(f"已注册 {len(market.skills)} 个核心技能")
    print(f"分类: {market.list_categories()}")
    
    # 搜索技能
    results = market.search_skills(query='clawshell')
    print(f"\n搜索 'clawshell' 结果: {len(results)}")
    for s in results:
        print(f"  - {s.name} ({s.version})")
