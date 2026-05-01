#!/usr/bin/env python3
"""
悟空版本监控器
功能：检测悟空及ClawShell的版本变化，及时发现依赖问题
作者：悟空(WuKong)
版本：v1.0
"""

import sys
import json
import logging
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 日志配置
LOG_DIR = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "version_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 版本检测清单
VERSION_CHECKS = {
    "Python": {
        "check": lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "min_version": "3.8",
        "recommended": "3.10+",
        "url": None
    },
    "ClawShell": {
        "repo": "jorinyang/wukong-optimized-ClawShell",
        "url": "https://api.github.com/repos/jorinyang/wukong-optimized-ClawShell/releases/latest",
        "check_local": lambda: "1.0.0"  # 从 __init__.py 或 package.json 读取
    },
    "psutil": {
        "module": "psutil",
        "min_version": "5.9.0",
        "url": "https://pypi.org/pypi/psutil/json"
    },
    "pyyaml": {
        "module": "yaml",
        "min_version": "6.0",
        "url": "https://pypi.org/pypi/PyYAML/json"
    },
    "requests": {
        "module": "requests",
        "min_version": "2.28.0",
        "url": "https://pypi.org/pypi/requests/json"
    }
}


class WuKongVersionMonitor:
    """悟空版本监控器"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "updates_available": [],
            "warnings": [],
            "all_ok": True
        }

    def check_python_version(self) -> Dict:
        """检查Python版本"""
        check = {"name": "Python", "status": "pass", "current": "", "latest": "", "message": ""}
        
        try:
            v = sys.version_info
            current = f"{v.major}.{v.minor}.{v.micro}"
            check["current"] = current
            
            # 解析最低版本要求
            min_parts = VERSION_CHECKS["Python"]["min_version"].split(".")
            min_v = tuple(int(x) for x in min_parts)
            
            current_v = (v.major, v.minor, v.micro)
            
            if current_v < min_v:
                check["status"] = "fail"
                check["message"] = f"低于最低要求 {VERSION_CHECKS['Python']['min_version']}"
                self.results["all_ok"] = False
            elif v.minor < 10:
                check["status"] = "warning"
                check["message"] = f"建议升级到 {VERSION_CHECKS['Python']['recommended']}"
                self.results["warnings"].append({
                    "component": "Python",
                    "message": check["message"],
                    "severity": "medium"
                })
            else:
                check["status"] = "pass"
                check["message"] = "版本正常"
                
        except Exception as e:
            check["status"] = "error"
            check["message"] = str(e)
            logger.error(f"Python版本检查失败: {e}")
        
        return check

    def check_module_version(self, module_name: str, import_name: str) -> Dict:
        """检查Python模块版本"""
        check = {"name": module_name, "status": "pass", "current": "", "latest": "", "message": ""}
        
        try:
            # 获取当前版本
            module = __import__(import_name)
            current = getattr(module, "__version__", "unknown")
            
            # 处理某些模块版本获取方式不同
            if current == "unknown" and module_name == "PIL":
                from PIL import Image
                current = Image.__version__
            elif current == "unknown" and module_name == "yaml":
                import yaml
                current = yaml.__version__
            
            check["current"] = current
            
            # 获取最新版本
            config = VERSION_CHECKS.get(module_name, {})
            url = config.get("url")
            
            if url:
                try:
                    req = urllib.request.Request(url)
                    req.add_header('User-Agent', 'WuKong-VersionMonitor/1.0')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        latest = data.get("info", {}).get("version", "unknown")
                        check["latest"] = latest
                        
                        # 版本比较
                        min_version = config.get("min_version", "0.0.0")
                        if self._compare_versions(current, min_version) < 0:
                            check["status"] = "fail"
                            check["message"] = f"低于最低要求 {min_version}"
                            self.results["all_ok"] = False
                            self.results["updates_available"].append({
                                "name": module_name,
                                "current": current,
                                "required": min_version,
                                "command": f"pip install {module_name}>= {min_version}"
                            })
                        elif self._compare_versions(current, latest) < 0:
                            check["status"] = "warning"
                            check["message"] = f"有新版本 {latest} 可用"
                            self.results["warnings"].append({
                                "component": module_name,
                                "message": f"有新版本 {latest} 可用",
                                "severity": "low"
                            })
                        else:
                            check["message"] = "已是最新版本"
                except Exception as e:
                    check["message"] = f"无法检查最新版本: {str(e)[:30]}"
            
        except ImportError:
            check["status"] = "fail"
            check["message"] = "模块未安装"
            self.results["all_ok"] = False
            self.results["updates_available"].append({
                "name": module_name,
                "current": "未安装",
                "command": f"pip install {module_name}"
            })
        except Exception as e:
            check["status"] = "error"
            check["message"] = str(e)
            logger.error(f"{module_name}版本检查失败: {e}")
        
        return check

    def check_clawshell_version(self) -> Dict:
        """检查ClawShell版本"""
        check = {"name": "ClawShell", "status": "pass", "current": "", "latest": "", "message": ""}
        
        try:
            # 读取本地版本
            clawshell_init = Path(__file__).parent.parent / "lib" / "__init__.py"
            if clawshell_init.exists():
                content = clawshell_init.read_text(encoding='utf-8')
                import re
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    check["current"] = match.group(1)
            
            if not check["current"]:
                check["current"] = "1.0.0"  # 默认版本
            
            # 检查GitHub最新版本
            url = VERSION_CHECKS["ClawShell"]["url"]
            try:
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'WuKong-VersionMonitor/1.0')
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    latest = data.get("tag_name", "").lstrip("v")
                    check["latest"] = latest
                    
                    if latest and self._compare_versions(check["current"], latest) < 0:
                        check["status"] = "warning"
                        check["message"] = f"有新版本 {latest} 可用"
                        self.results["updates_available"].append({
                            "name": "ClawShell",
                            "current": check["current"],
                            "latest": latest,
                            "url": "https://github.com/jorinyang/wukong-optimized-ClawShell"
                        })
                    else:
                        check["message"] = "已是最新版本"
            except Exception as e:
                check["message"] = f"无法检查最新版本"
                logger.warning(f"ClawShell版本检查失败: {e}")
                
        except Exception as e:
            check["status"] = "error"
            check["message"] = str(e)
            logger.error(f"ClawShell版本检查失败: {e}")
        
        return check

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，返回 -1, 0, 1"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            # 补齐长度
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            return 0
        except:
            return 0

    def check_all(self) -> Dict:
        """检查所有版本"""
        logger.info("开始版本检查...")
        
        # Python
        self.results["checks"].append(self.check_python_version())
        
        # ClawShell
        self.results["checks"].append(self.check_clawshell_version())
        
        # 依赖模块
        module_checks = [
            ("psutil", "psutil"),
            ("PyYAML", "yaml"),
            ("requests", "requests"),
        ]
        
        for name, import_name in module_checks:
            self.results["checks"].append(self.check_module_version(name, import_name))
        
        return self.results

    def generate_report(self) -> str:
        """生成报告"""
        status_icon = {"pass": "✅", "warning": "[WARN]️", "fail": "❌", "error": "[WARN]️"}
        
        report = f"""# 悟空版本检查报告

**检查时间**: {self.results['timestamp']}
**总体状态**: {"✅ 正常" if self.results["all_ok"] else "[WARN]️ 需要更新"}

---

## 版本检查结果

| 组件 | 当前版本 | 最新版本 | 状态 | 说明 |
|------|----------|----------|------|------|
"""
        
        for check in self.results["checks"]:
            icon = status_icon.get(check["status"], "❓")
            report += f"| {check['name']} | {check['current']} | {check['latest'] or '-'} | {icon} | {check['message']} |\n"
        
        # 可更新列表
        if self.results["updates_available"]:
            report += "\n## 需要更新的组件\n\n"
            for item in self.results["updates_available"]:
                report += f"### {item['name']}\n"
                report += f"- 当前版本: `{item['current']}`\n"
                if "required" in item:
                    report += f"- 最低要求: `{item['required']}`\n"
                    report += f"- 安装命令: ```bash\npip install {item['name']}>={item['required']}\n```\n"
                if "latest" in item:
                    report += f"- 最新版本: `{item['latest']}`\n"
                if "url" in item:
                    report += f"- 地址: {item['url']}\n"
                report += "\n"
        
        # 警告列表
        if self.results["warnings"]:
            report += "\n## 警告信息\n\n"
            for warning in self.results["warnings"]:
                report += f"- **[{warning['severity']}]** {warning['component']}: {warning['message']}\n"
        
        return report

    def save_report(self, content: str) -> Path:
        """保存报告"""
        output_dir = Path.home() / ".real" / "users" / "user-bd1b229d4eff8f6a45c456149072cb3b" / "workspace" / "version_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"version_check_{timestamp}.md"
        output_file = output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"报告已保存: {output_file}")
        return output_file

    def run(self) -> Dict:
        """执行检查"""
        logger.info("=" * 50)
        logger.info("悟空版本检查开始")
        logger.info("=" * 50)
        
        self.check_all()
        
        logger.info("=" * 50)
        logger.info(f"检查完成: {'✅ 正常' if self.results['all_ok'] else '[WARN]️ 需要更新'}")
        logger.info(f"需更新: {len(self.results['updates_available'])} 项")
        logger.info(f"警告: {len(self.results['warnings'])} 项")
        logger.info("=" * 50)
        
        return self.results


def main():
    """主函数"""
    monitor = WuKongVersionMonitor()
    results = monitor.run()
    
    content = monitor.generate_report()
    output_file = monitor.save_report(content)
    
    print(f"\n{'=' * 50}")
    print("版本检查结果")
    print(f"{'=' * 50}")
    print(f"状态: {'✅ 正常' if results['all_ok'] else '[WARN]️ 需要更新'}")
    print(f"需更新: {len(results['updates_available'])} 项")
    print(f"警告: {len(results['warnings'])} 项")
    print(f"\n详细报告: {output_file}")
    
    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
