#!/usr/bin/env python3
"""
悟空定时健康检查 - 每日健康监测
功能：执行悟空及ClawShell的全链路健康检查，记录结果并生成报告
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ClawShell路径配置
CLAWSHELL_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(CLAWSHELL_PATH))

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "health_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "health_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WuKongHealthChecker:
    """悟空健康检查器"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "overall_score": 100,
            "checks": [],
            "issues": [],
            "recommendations": []
        }
        self.score = 100

    def check_python_environment(self) -> Dict:
        """检查Python环境"""
        check = {"name": "Python环境", "status": "pass", "details": {}}
        
        try:
            import python_version
            v = sys.version_info
            check["details"]["version"] = f"{v.major}.{v.minor}.{v.micro}"
            check["details"]["path"] = sys.executable
            
            if v.major < 3 or (v.major == 3 and v.minor < 8):
                check["status"] = "warning"
                self.score -= 10
                self.results["issues"].append({
                    "level": "warning",
                    "component": "Python",
                    "message": f"Python版本过低: {v.major}.{v.minor}"
                })
        except Exception as e:
            check["status"] = "fail"
            self.score -= 20
            self.results["issues"].append({
                "level": "error",
                "component": "Python",
                "message": str(e)
            })
            logger.error(f"Python环境检查失败: {e}")
        
        return check

    def check_clawshell_modules(self) -> Dict:
        """检查ClawShell模块导入"""
        check = {"name": "ClawShell模块", "status": "pass", "details": {}}
        
        modules_to_test = {
            "Layer1-健康监控": ("lib.layer1.health_check", "HealthMonitor"),
            "Layer2-自修复": ("lib.layer2.self_healing", "HealingAction"),
            "Layer3-任务市场": ("lib.layer3.task_market", "TaskMarket"),
            "Layer4-集群管理": ("lib.layer4.swarm", "NodeRegistry"),
            "Core-事件总线": ("lib.core.eventbus", "EventBus"),
            "Detector-检测器": ("lib.detector.dependency_checker", "DependencyChecker"),
        }
        
        success_count = 0
        failed_modules = []
        
        for module_name, (module_path, class_name) in modules_to_test.items():
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                check["details"][module_name] = "✓ 可用"
                success_count += 1
            except Exception as e:
                check["details"][module_name] = f"✗ {str(e)[:50]}"
                failed_modules.append(module_name)
                logger.warning(f"模块 {module_name} 导入失败: {e}")
        
        check["details"]["成功"] = f"{success_count}/{len(modules_to_test)}"
        
        if failed_modules:
            check["status"] = "warning" if len(failed_modules) <= 2 else "fail"
            self.score -= len(failed_modules) * 5
            self.results["issues"].append({
                "level": "warning" if len(failed_modules) <= 2 else "error",
                "component": "ClawShell模块",
                "message": f"以下模块导入失败: {', '.join(failed_modules)}"
            })
        
        return check

    def check_system_resources(self) -> Dict:
        """检查系统资源"""
        check = {"name": "系统资源", "status": "pass", "details": {}}
        
        try:
            import psutil
            
            # CPU使用率
            cpu = psutil.cpu_percent(interval=1)
            check["details"]["CPU使用率"] = f"{cpu}%"
            if cpu > 80:
                check["status"] = "warning"
                self.score -= 10
                self.results["issues"].append({
                    "level": "warning",
                    "component": "CPU",
                    "message": f"CPU使用率过高: {cpu}%"
                })
            
            # 内存使用率
            memory = psutil.virtual_memory()
            check["details"]["内存使用率"] = f"{memory.percent}%"
            check["details"]["内存总量"] = f"{memory.total / (1024**3):.1f}GB"
            if memory.percent > 85:
                check["status"] = "warning"
                self.score -= 15
                self.results["issues"].append({
                    "level": "warning",
                    "component": "内存",
                    "message": f"内存使用率过高: {memory.percent}%"
                })
            
            # 磁盘使用率
            disk = psutil.disk_usage('C:\\')
            check["details"]["磁盘使用率"] = f"{disk.percent}%"
            if disk.percent > 90:
                check["status"] = "warning"
                self.score -= 10
                self.results["issues"].append({
                    "level": "warning",
                    "component": "磁盘",
                    "message": f"磁盘使用率过高: {disk.percent}%"
                })
                
        except ImportError:
            check["details"]["psutil"] = "未安装"
            check["status"] = "warning"
        except Exception as e:
            check["status"] = "warning"
            check["details"]["error"] = str(e)
            logger.warning(f"系统资源检查异常: {e}")
        
        return check

    def check_network_connectivity(self) -> Dict:
        """检查网络连接"""
        check = {"name": "网络连接", "status": "pass", "details": {}}
        
        endpoints = [
            ("GitHub", "https://api.github.com"),
            ("钉钉", "https://oapi.dingtalk.com"),
        ]
        
        try:
            import urllib.request
            
            for name, url in endpoints:
                try:
                    req = urllib.request.Request(url, method='HEAD')
                    req.add_header('User-Agent', 'WuKong-HealthCheck/1.0')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        check["details"][name] = f"✓ {response.status}"
                except Exception as e:
                    check["details"][name] = f"✗ {str(e)[:30]}"
                    self.score -= 5
                    logger.warning(f"{name} 连接失败: {e}")
                    
        except Exception as e:
            check["status"] = "warning"
            check["details"]["error"] = str(e)
        
        return check

    def check_cron_tasks(self) -> Dict:
        """检查定时任务状态"""
        check = {"name": "定时任务", "status": "pass", "details": {}}
        
        cron_config_path = Path.home() / ".real" / "cron_tasks.json"
        
        if cron_config_path.exists():
            try:
                with open(cron_config_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    check["details"]["已配置任务"] = len(tasks.get("tasks", []))
                    
                    # 检查是否有最近执行的任务
                    recent_count = 0
                    for task in tasks.get("tasks", []):
                        if task.get("last_run"):
                            last_run = datetime.fromisoformat(task["last_run"])
                            if (datetime.now() - last_run).days < 1:
                                recent_count += 1
                    
                    check["details"]["最近执行"] = recent_count
            except Exception as e:
                check["details"]["读取错误"] = str(e)
        else:
            check["details"]["状态"] = "无配置文件"
            check["status"] = "info"
        
        return check

    def check_skills(self) -> Dict:
        """检查技能安装状态"""
        check = {"name": "技能安装", "status": "pass", "details": {}}
        
        skills_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / ".skills"
        
        if skills_dir.exists():
            skill_count = len(list(skills_dir.rglob("SKILL.md")))
            check["details"]["已安装技能"] = skill_count
            
            if skill_count == 0:
                check["status"] = "warning"
                self.score -= 5
                self.results["issues"].append({
                    "level": "warning",
                    "component": "Skills",
                    "message": "未安装任何技能"
                })
        else:
            check["details"]["状态"] = "技能目录不存在"
            check["status"] = "warning"
        
        return check

    def generate_recommendations(self):
        """生成修复建议"""
        issues_by_component = {}
        for issue in self.results["issues"]:
            component = issue["component"]
            if component not in issues_by_component:
                issues_by_component[component] = []
            issues_by_component[component].append(issue["message"])
        
        recommendations = {
            "Python": "建议升级到Python 3.10+以获得更好的性能支持",
            "ClawShell模块": "运行 'skills install local' 重新安装ClawShell-Debug技能",
            "CPU": "检查是否有后台进程占用大量CPU，必要时重启悟空",
            "内存": "清理不必要的进程，考虑增加物理内存",
            "磁盘": "清理磁盘空间，删除不必要的日志和缓存文件",
            "Skills": "安装必要的技能: 'skills install local' 或从技能市场安装"
        }
        
        for component, messages in issues_by_component.items():
            if component in recommendations:
                self.results["recommendations"].append(recommendations[component])

    def run(self) -> Dict:
        """执行完整健康检查"""
        logger.info("=" * 50)
        logger.info("悟空健康检查开始")
        logger.info("=" * 50)
        
        checks = [
            ("Python环境", self.check_python_environment),
            ("ClawShell模块", self.check_clawshell_modules),
            ("系统资源", self.check_system_resources),
            ("网络连接", self.check_network_connectivity),
            ("定时任务", self.check_cron_tasks),
            ("技能安装", self.check_skills),
        ]
        
        for name, check_func in checks:
            logger.info(f"检查 {name}...")
            try:
                result = check_func()
                self.results["checks"].append(result)
            except Exception as e:
                logger.error(f"{name} 检查失败: {e}")
                self.results["checks"].append({
                    "name": name,
                    "status": "error",
                    "details": {"error": str(e)}
                })
        
        # 计算最终评分
        self.results["overall_score"] = max(0, self.score)
        
        # 生成状态评估
        if self.score >= 90:
            self.results["overall_status"] = "healthy"
        elif self.score >= 70:
            self.results["overall_status"] = "warning"
        else:
            self.results["overall_status"] = "unhealthy"
        
        # 生成修复建议
        self.generate_recommendations()
        
        logger.info("=" * 50)
        logger.info(f"健康检查完成: {self.results['overall_status']}")
        logger.info(f"评分: {self.results['overall_score']}/100")
        logger.info(f"问题数: {len(self.results['issues'])}")
        logger.info("=" * 50)
        
        return self.results

    def save_report(self) -> Path:
        """保存检查报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON格式
        json_path = LOG_DIR / f"health_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        # 保存简洁摘要
        summary_path = LOG_DIR / f"health_summary_{timestamp}.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"悟空健康检查报告\n")
            f.write(f"时间: {self.results['timestamp']}\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"总体状态: {self.results['overall_status']}\n")
            f.write(f"评分: {self.results['overall_score']}/100\n")
            f.write(f"\n检查项目:\n")
            for check in self.results["checks"]:
                status_icon = {"pass": "✓", "warning": "⚠", "fail": "✗", "info": "ℹ"}.get(check["status"], "?")
                f.write(f"  {status_icon} {check['name']}: {check['status']}\n")
            
            if self.results["issues"]:
                f.write(f"\n发现问题:\n")
                for issue in self.results["issues"]:
                    f.write(f"  [{issue['level']}] {issue['component']}: {issue['message']}\n")
            
            if self.results["recommendations"]:
                f.write(f"\n修复建议:\n")
                for i, rec in enumerate(self.results["recommendations"], 1):
                    f.write(f"  {i}. {rec}\n")
        
        logger.info(f"报告已保存: {json_path}")
        logger.info(f"摘要已保存: {summary_path}")
        
        return json_path


def main():
    """主函数"""
    checker = WuKongHealthChecker()
    results = checker.run()
    report_path = checker.save_report()
    
    # 输出简洁摘要到控制台
    print(f"\n{'=' * 50}")
    print(f"悟空健康检查摘要")
    print(f"{'=' * 50}")
    print(f"状态: {results['overall_status']}")
    print(f"评分: {results['overall_score']}/100")
    print(f"问题数: {len(results['issues'])}")
    print(f"报告: {report_path}")
    
    return 0 if results['overall_status'] == 'healthy' else 1


if __name__ == "__main__":
    sys.exit(main())
