"""
External Detector - 外部工具检测
================================

检测外部服务和工具的可用性（N8N/Docker/阿里云等）。
"""

import os
import subprocess
import socket
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ExternalTool:
    """外部工具"""
    name: str
    command: Optional[str] = None
    port: Optional[int] = None
    available: bool = False
    healthy: bool = False
    details: str = ""


class ExternalDetector:
    """外部工具检测器"""
    
    EXTERNAL_TOOLS = {
        'n8n': {
            'name': 'N8N',
            'command': 'n8n',
            'port': 5678,
            'health_endpoint': 'http://localhost:5678'
        },
        'docker': {
            'name': 'Docker',
            'command': 'docker',
            'version_cmd': ['docker', '--version']
        },
        'redis': {
            'name': 'Redis',
            'command': 'redis-cli',
            'port': 6379
        },
        'aliyun': {
            'name': '阿里云CLI',
            'command': 'aliyun',
            'env_vars': ['ALIYUN_ACCESS_KEY_ID', 'ALIYUN_ACCESS_KEY_SECRET']
        },
        'github': {
            'name': 'GitHub CLI',
            'command': 'gh',
            'env_vars': ['GITHUB_TOKEN']
        },
        'node': {
            'name': 'Node.js',
            'command': 'node',
            'version_cmd': ['node', '--version']
        },
        'npm': {
            'name': 'NPM',
            'command': 'npm',
            'version_cmd': ['npm', '--version']
        }
    }
    
    def __init__(self):
        pass
    
    def detect_all(self) -> List[ExternalTool]:
        """检测所有外部工具"""
        detected = []
        
        for tool_id, config in self.EXTERNAL_TOOLS.items():
            tool = self._detect_tool(tool_id, config)
            detected.append(tool)
        
        return detected
    
    def get_available_tools(self) -> List[str]:
        """获取可用的工具名称列表"""
        return [tool.name for tool in self.detect_all() if tool.available]
    
    def _detect_tool(self, tool_id: str, config: Dict) -> ExternalTool:
        """检测单个工具"""
        name = config['name']
        command = config.get('command')
        
        # 命令存在性检测
        if command:
            available = self._command_exists(command)
        else:
            available = False
        
        # 版本检测
        version_cmd = config.get('version_cmd')
        version = None
        if available and version_cmd:
            version = self._get_version(version_cmd)
        
        # 端口检测
        port = config.get('port')
        healthy = False
        if port and available:
            healthy = self._check_port(port)
        
        # 环境变量检测
        env_vars = config.get('env_vars', [])
        env_configured = all(os.environ.get(var) for var in env_vars) if env_vars else False
        
        details = ""
        if version:
            details += f"版本: {version}; "
        if port:
            details += f"端口: {port}; "
        if env_vars:
            details += f"环境变量: {'已配置' if env_configured else '未配置'}"
        
        return ExternalTool(
            name=name,
            command=command,
            port=port,
            available=available,
            healthy=healthy,
            details=details.strip('; ')
        )
    
    def _command_exists(self, cmd: str) -> bool:
        """检查命令是否存在"""
        try:
            result = subprocess.run(
                ['which', cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_version(self, cmd: List[str]) -> Optional[str]:
        """获取工具版本"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    def _check_port(self, port: int, host: str = 'localhost') -> bool:
        """检查端口是否开放"""
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def detect_http_services(self) -> Dict[str, bool]:
        """检测HTTP服务健康状态"""
        services = {
            'n8n': 'http://localhost:5678',
        }
        
        results = {}
        for name, url in services.items():
            try:
                import urllib.request
                response = urllib.request.urlopen(url, timeout=2)
                results[name] = response.status == 200
            except Exception:
                results[name] = False
        
        return results
