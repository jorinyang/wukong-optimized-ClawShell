#!/usr/bin/env python3
"""
悟空跨平台自适应适配层
功能：自动检测操作系统、适配路径、修复编码问题、搜索文件位置
作者：悟空(WuKong)
版本：v2.0
更新：2026-04-30 - 新增编码自动修复、跨平台路径适配
"""

import sys
import os
import re
import json
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# ==================== 跨平台编码配置 ====================
import locale
import platform

@dataclass
class PlatformConfig:
    """平台配置"""
    system: str
    encoding: str
    path_separator: str
    home_dir: Path
    temp_dir: Path
    workspace_patterns: List[str]
    clawshell_search_paths: List[Path]
    
    @classmethod
    def detect(cls) -> 'PlatformConfig':
        """自动检测当前平台配置"""
        system = platform.system()
        
        # Windows 配置
        if system == 'Windows':
            return cls(
                system='Windows',
                encoding='utf-8',
                path_separator='\\',
                home_dir=Path.home(),
                temp_dir=Path(os.environ.get('TEMP', 'C:\\Temp')),
                workspace_patterns=[
                    'C:\\Users\\*\\Documents\\wukong*',
                    'C:\\Users\\*\\.ClawShell',
                    'C:\\Users\\*\\.real\\users\\*\\workspace'
                ],
                clawshell_search_paths=[
                    Path.home() / '.ClawShell',
                    Path.home() / 'Documents' / 'wukong-optimized-ClawShell-tmp',
                    Path.home() / 'Documents' / 'wukong-optimized-ClawShell',
                    Path('C:/Program Files/ClawShell'),
                    Path.home() / '.ClawShell',
                ]
            )
        # Linux 配置
        elif system == 'Linux':
            return cls(
                system='Linux',
                encoding='utf-8',
                path_separator='/',
                home_dir=Path.home(),
                temp_dir=Path('/tmp'),
                workspace_patterns=[
                    '~/.wukong*',
                    '~/.clawshell*',
                    '~/.real/users/*/workspace'
                ],
                clawshell_search_paths=[
                    Path.home() / '.ClawShell',
                    Path.home() / 'wukong-optimized-ClawShell',
                    Path('/opt/ClawShell'),
                ]
            )
        # macOS 配置
        else:
            return cls(
                system='Darwin',
                encoding='utf-8',
                path_separator='/',
                home_dir=Path.home(),
                temp_dir=Path('/tmp'),
                workspace_patterns=[
                    '~/Library/Application Support/wukong*',
                    '~/.clawshell*',
                    '~/.real/users/*/workspace'
                ],
                clawshell_search_paths=[
                    Path.home() / '.ClawShell',
                    Path.home() / 'Library' / 'Application Support' / 'ClawShell',
                    Path('/Applications/ClawShell.app'),
                ]
            )


class PathResolver:
    """跨平台路径解析器"""
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def find_wukong_crons_dir(self) -> Optional[Path]:
        """搜索并定位 wukong-crons 目录
        
        搜索策略（按优先级）：
        1. 标准路径：wukong-optimized-ClawShell/wukong-crons
        2. 用户文档目录下的各种变体
        3. ClawShell 根目录
        4. 递归搜索 home 目录
        """
        search_patterns = [
            # 标准路径
            self.config.home_dir / 'Documents' / 'wukong-optimized-ClawShell-tmp' / 'wukong-crons',
            self.config.home_dir / 'Documents' / 'wukong-optimized-ClawShell' / 'wukong-crons',
            self.config.home_dir / '.ClawShell' / 'wukong-crons',
            # 搜索脚本所在目录
            Path(__file__).parent,
        ]
        
        for path in search_patterns:
            if path.exists() and (path / 'wukong_health_check.py').exists():
                self.logger.info(f"找到 wukong-crons: {path}")
                return path
        
        # 递归搜索（Windows 使用 dir 命令更高效）
        if self.config.system == 'Windows':
            result = subprocess.run(
                ['cmd', '/c', f'dir /s /b "{self.config.home_dir}\\wukong_health_check.py" 2>nul'],
                capture_output=True, text=True, encoding='utf-8'
            )
            if result.stdout.strip():
                found_path = Path(result.stdout.strip()).parent
                self.logger.info(f"递归搜索找到: {found_path}")
                return found_path
        else:
            import glob
            for pattern in self.config.workspace_patterns:
                expanded = os.path.expanduser(pattern)
                for match in glob.glob(f"{expanded}/**/wukong_health_check.py", recursive=True):
                    return Path(match).parent
        
        self.logger.warning("未找到 wukong-crons 目录")
        return None
    
    def find_clawshell_root(self) -> Optional[Path]:
        """定位 ClawShell 根目录"""
        for search_path in self.config.clawshell_search_paths:
            if search_path.exists() and (search_path / 'lib').exists():
                self.logger.info(f"找到 ClawShell: {search_path}")
                return search_path
        return None
    
    def normalize_path(self, path: str) -> Path:
        """规范化路径，处理跨平台差异"""
        path = os.path.expanduser(path)
        return Path(path).resolve()
    
    def get_workspace_dir(self) -> Path:
        """获取悟空工作区目录"""
        # 尝试多个可能的路径
        possible_paths = [
            self.config.home_dir / '.real' / 'users' / 'user-bd1b229d4eff8f6a45c456149072cb3b' / 'workspace',
            self.config.home_dir / '.real' / 'workspace',
            self.config.temp_dir / 'wukong-workspace',
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # 默认创建
        default = possible_paths[0]
        default.mkdir(parents=True, exist_ok=True)
        return default


class EncodingFixer:
    """编码问题检测与修复"""
    
    # 需要修复编码的文件模式
    FILE_PATTERNS = [
        '*.py', '*.json', '*.txt', '*.log', '*.md', '*.yaml', '*.yml'
    ]
    
    def __init__(self, config: PlatformConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.issues_found = []
        self.fixes_applied = []
    
    def detect_encoding_issues(self, file_path: Path) -> Dict[str, Any]:
        """检测文件编码问题"""
        issues = {'file': str(file_path), 'issues': []}
        
        try:
            # 尝试不同编码读取
            encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read()
                    issues['detected_encoding'] = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            # 检查 BOM 标记
            with open(file_path, 'rb') as f:
                first_bytes = f.read(3)
                if first_bytes == b'\xef\xbb\xbf':
                    issues['has_utf8_bom'] = True
                elif first_bytes == b'\xff\xfe':
                    issues['has_utf16_le_bom'] = True
                    
        except Exception as e:
            issues['error'] = str(e)
            
        return issues
    
    def fix_file_encoding(self, file_path: Path, target_encoding: str = 'utf-8') -> bool:
        """修复单个文件编码"""
        try:
            # 检测原始编码
            detected = self.detect_encoding_issues(file_path)
            original_encoding = detected.get('detected_encoding', 'utf-8')
            
            if original_encoding == target_encoding:
                self.logger.info(f"文件已是 {target_encoding}: {file_path.name}")
                return True
            
            # 读取并重写
            content = None
            for enc in [original_encoding, 'gbk', 'gb2312', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if content is None:
                self.logger.error(f"无法读取文件编码: {file_path}")
                return False
            
            # 移除 BOM（如果存在）
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # 写入 UTF-8
            with open(file_path, 'w', encoding=target_encoding) as f:
                f.write(content)
            
            self.fixes_applied.append({
                'file': str(file_path),
                'from': original_encoding,
                'to': target_encoding
            })
            self.logger.info(f"已修复编码: {file_path.name} ({original_encoding} → {target_encoding})")
            return True
            
        except Exception as e:
            self.logger.error(f"编码修复失败: {file_path} - {e}")
            self.issues_found.append({'file': str(file_path), 'error': str(e)})
            return False
    
    def fix_directory_encoding(self, directory: Path, recursive: bool = True) -> Dict:
        """批量修复目录内文件编码"""
        results = {'fixed': 0, 'failed': 0, 'skipped': 0}
        
        for pattern in self.FILE_PATTERNS:
            if recursive:
                files = list(directory.rglob(pattern))
            else:
                files = list(directory.glob(pattern))
            
            for file_path in files:
                # 跳过 __pycache__ 和 .git
                if '__pycache__' in str(file_path) or '.git' in str(file_path):
                    results['skipped'] += 1
                    continue
                    
                if self.fix_file_encoding(file_path):
                    results['fixed'] += 1
                else:
                    results['failed'] += 1
        
        return results
    
    def fix_log_handlers(self, file_path: Path) -> bool:
        """修复日志文件写入的编码问题（自动添加 encoding 参数）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已有 encoding 参数
            if 'encoding=' in content:
                self.logger.info(f"日志编码已配置: {file_path.name}")
                return True
            
            # 修复 FileHandler 缺少 encoding 的问题
            # 模式1: logging.FileHandler(path / "xxx.log")
            pattern1 = r'logging\.FileHandler\(([^)]+)\)'
            replacement1 = r'logging.FileHandler(\1, encoding=ENCODING)'
            
            # 添加 ENCODING 常量定义
            encoding_define = '''# 跨平台编码配置
import locale
import platform
ENCODING = 'utf-8' if platform.system() != 'Windows' else 'utf-8'

'''
            
            if 'FileHandler' in content:
                # 添加编码常量（如果还没有）
                if 'ENCODING' not in content:
                    content = content.replace(
                        'import logging',
                        'import logging\nimport locale\nimport platform\n\n# 跨平台编码配置\nENCODING = \'utf-8\''
                    )
                
                # 修复 FileHandler
                content = re.sub(
                    r'FileHandler\(([^,\)]+)\)',
                    r'FileHandler(\1, encoding=ENCODING)',
                    content
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append({
                    'file': str(file_path),
                    'fix': 'added_encoding_to_FileHandler'
                })
                self.logger.info(f"已修复日志编码: {file_path.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"日志编码修复失败: {file_path} - {e}")
            return False
        
        return True


class PlatformAdapter:
    """跨平台自适应主适配器"""
    
    def __init__(self):
        self.config = PlatformConfig.detect()
        self.path_resolver = PathResolver(self.config)
        self.encoding_fixer = EncodingFixer(self.config, logging.getLogger(__name__))
        
        # 初始化日志
        self._setup_logging()
    
    def _setup_logging(self):
        """配置日志"""
        workspace = self.path_resolver.get_workspace_dir()
        log_dir = workspace / 'adapter_logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'platform_adapter_{datetime.now().strftime("%Y%m%d")}.log'
        
        # 设置控制台输出编码
        if sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_full_adaptation(self) -> Dict:
        """执行完整的跨平台自适应适配"""
        self.logger.info("=" * 60)
        self.logger.info(f"悟空跨平台自适应适配 - {self.config.system}")
        self.logger.info("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'platform': self.config.system,
            'encoding': self.config.encoding,
            'detections': {},
            'fixes': [],
            'issues': []
        }
        
        # 1. 检测平台配置
        results['detections']['platform'] = {
            'system': self.config.system,
            'encoding': self.config.encoding,
            'home_dir': str(self.config.home_dir)
        }
        
        # 2. 定位关键目录
        crons_dir = self.path_resolver.find_wukong_crons_dir()
        clawshell_root = self.path_resolver.find_clawshell_root()
        
        results['detections']['directories'] = {
            'wukong_crons': str(crons_dir) if crons_dir else None,
            'clawshell_root': str(clawshell_root) if clawshell_root else None,
            'workspace': str(self.path_resolver.get_workspace_dir())
        }
        
        # 3. 修复编码问题
        if crons_dir:
            for py_file in crons_dir.glob('*.py'):
                if 'wukong_platform_adapter' not in py_file.name:  # 跳过自身
                    self.encoding_fixer.fix_log_handlers(py_file)
            
            encoding_results = self.encoding_fixer.fix_directory_encoding(crons_dir)
            results['fixes'].extend(self.encoding_fixer.fixes_applied)
            results['detections']['encoding_fixes'] = encoding_results
        
        # 4. 生成报告
        results['issues'] = self.encoding_fixer.issues_found
        
        self.logger.info("=" * 60)
        self.logger.info("自适应适配完成")
        self.logger.info(f"修复数量: {len(results['fixes'])}")
        self.logger.info(f"问题数量: {len(results['issues'])}")
        self.logger.info("=" * 60)
        
        return results
    
    def save_report(self, results: Dict) -> Path:
        """保存适配报告"""
        workspace = self.path_resolver.get_workspace_dir()
        report_dir = workspace / 'adapter_logs'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f'adaptation_report_{timestamp}.json'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"报告已保存: {report_path}")
        return report_path


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("悟空跨平台自适应适配层")
    print("=" * 60 + "\n")
    
    adapter = PlatformAdapter()
    results = adapter.run_full_adaptation()
    report_path = adapter.save_report(results)
    
    # 输出摘要
    print(f"\n{'=' * 60}")
    print("适配摘要")
    print(f"{'=' * 60}")
    print(f"平台: {results['platform']}")
    print(f"编码: {results['encoding']}")
    print(f"修复数量: {len(results['fixes'])}")
    print(f"问题数量: {len(results['issues'])}")
    print(f"\n详细报告: {report_path}")
    
    # 列出修复的文件
    if results['fixes']:
        print(f"\n已修复的文件:")
        for fix in results['fixes']:
            if 'file' in fix:
                print(f"  - {fix['file']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
