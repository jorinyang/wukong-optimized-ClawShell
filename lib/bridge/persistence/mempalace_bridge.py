"""
MemPalace Bridge - 记忆宫殿持久化
==================================

提供本地记忆宫殿的SQLite存储接口。
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List


class MemPalaceBridge:
    """MemPalace本地持久化桥接器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".claude" / "palace" / "memories.db"
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def save(self, key: str, value: str) -> bool:
        """保存记忆"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO memories (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"MemPalaceBridge save error: {e}")
            return False
    
    def load(self, key: str) -> Optional[str]:
        """加载记忆"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM memories WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            print(f"MemPalaceBridge load error: {e}")
            return None
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                'SELECT key, value FROM memories WHERE value LIKE ?',
                (f'%{query}%',)
            )
            rows = cursor.fetchall()
            conn.close()
            return [{'key': k, 'value': v} for k, v in rows]
        except Exception as e:
            print(f"MemPalaceBridge search error: {e}")
            return []
