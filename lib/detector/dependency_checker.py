"""
Dependency Checker - Python依赖检测
===================================

检测Python环境和依赖包可用性。
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Dependency:
    """依赖项"""
    name: str
    required_version: Optional[str] = None
    installed: bool = False
    current_version: Optional[str] = None
    satisfies: bool = False


class DependencyChecker:
    """Python依赖检测器"""
    
    # 系统级依赖
    SYSTEM_DEPS = ['curl', 'jq', 'git']
    
    # Python依赖 (package_name: (min_version, import_name))
    PYTHON_DEPS = {
        'psutil': ('5.9.0', 'psutil'),
        'pyyaml': ('6.0', 'yaml'),
        'requests': ('2.28.0', 'requests'),
        'aiohttp': ('3.8.0', 'aiohttp'),
        'httpx': ('0.24.0', 'httpx'),
    }
    
    def __init__(self):
        self.python_version = sys.version_info
    
    def check_python_version(self) -> Tuple[bool, str]:
        """检查Python版本"""
        version = f"{self.python_version.major}.{self.python_version.minor}"
        if self.python_version.major >= 3 and self.python_version.minor >= 8:
            return True, version
        return False, version
    
    def check_system_deps(self) -> List[Dependency]:
        """检查系统依赖"""
        results = []
        
        for dep in self.SYSTEM_DEPS:
            installed = self._command_exists(dep)
            results.append(Dependency(
                name=dep,
                installed=installed,
                satisfies=installed
            ))
        
        return results
    
    def check_python_deps(self) -> List[Dependency]:
        """检查Python依赖"""
        results = []
        
        for pkg_name, (min_ver, import_name) in self.PYTHON_DEPS.items():
            installed, current_ver = self._check_package(pkg_name, import_name)
            satisfies = installed and self._version_satisfies(current_ver, min_ver)
            
            results.append(Dependency(
                name=pkg_name,
                required_version=min_ver,
                installed=installed,
                current_version=current_ver,
                satisfies=satisfies
            ))
        
        return results
    
    def check_all(self) -> Dict:
        """检查所有依赖"""
        python_ok, python_ver = self.check_python_version()
        
        return {
            'python_version': {'ok': python_ok, 'version': python_ver},
            'system_deps': self.check_system_deps(),
            'python_deps': self.check_python_deps(),
            'all_satisfied': python_ok and all(d.satisfies for d in self.check_python_deps())
        }
    
    def get_missing_deps(self) -> List[str]:
        """获取缺失的依赖列表"""
        missing = []
        
        for dep in self.check_python_deps():
            if not dep.installed:
                missing.append(dep.name)
            elif not dep.satisfies:
                missing.append(f"{dep.name}>={dep.required_version}")
        
        for dep in self.check_system_deps():
            if not dep.installed:
                missing.append(dep.name)
        
        return missing
    
    def _command_exists(self, cmd: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _check_package(self, pkg_name: str, import_name: str) -> Tuple[bool, Optional[str]]:
        """检查Python包是否已安装"""
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', None)
            if version is None:
                # 尝试从 pip 获取版本
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'show', pkg_name],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Version:'):
                            version = line.split(':', 1)[1].strip()
                            break
            return True, version
        except ImportError:
            return False, None
    
    def _version_satisfies(self, current: Optional[str], required: str) -> bool:
        """检查版本是否满足要求"""
        if current is None:
            return False
        
        try:
            from packaging import version
            return version.parse(current) >= version.parse(required)
        except Exception:
            # 如果无法解析版本，保守返回True
            return True
