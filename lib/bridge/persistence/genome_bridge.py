"""
Genome Bridge - 知识传承持久化
==============================

提供知识传承的数据持久化接口。
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json


class GenomeBridge:
    """Genome持久化桥接器"""
    
    def __init__(self, genome_path: Optional[Path] = None):
        self.genome_path = genome_path or Path.home() / ".openclaw" / "genome"
    
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """保存知识条目"""
        try:
            file_path = self.genome_path / f"{key}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"GenomeBridge save error: {e}")
            return False
    
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """加载知识条目"""
        try:
            file_path = self.genome_path / f"{key}.json"
            if not file_path.exists():
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"GenomeBridge load error: {e}")
            return None
    
    def exists(self, key: str) -> bool:
        """检查知识条目是否存在"""
        return (self.genome_path / f"{key}.json").exists()
    
    def delete(self, key: str) -> bool:
        """删除知识条目"""
        try:
            file_path = self.genome_path / f"{key}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False
