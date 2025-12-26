"""
数据库管理模块
使用 SQLite 存储模型信息
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager


class Database:
    """数据库管理类，处理模型信息的持久化"""
    
    _instance = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        
        self.db_path = db_path
        self._initialized = True
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建模型表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id TEXT NOT NULL,
                    filename TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引以加快查询
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_filename ON models(filename)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_repo_id ON models(repo_id)
            ''')
            
            conn.commit()
    
    def add_model(self, repo_id: str, filename: str) -> bool:
        """
        添加模型到数据库
        
        Args:
            repo_id: 模型仓库 ID
            filename: 模型文件名
            
        Returns:
            是否添加成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO models (repo_id, filename)
                    VALUES (?, ?)
                ''', (repo_id, filename))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # 文件名已存在
            return False
        except Exception as e:
            print(f"添加模型到数据库失败: {e}")
            return False
    
    def remove_model(self, filename: str) -> bool:
        """
        从数据库删除模型
        
        Args:
            filename: 模型文件名
            
        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM models WHERE filename = ?', (filename,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"从数据库删除模型失败: {e}")
            return False
    
    def get_model(self, filename: str) -> Optional[Dict]:
        """
        获取单个模型信息
        
        Args:
            filename: 模型文件名
            
        Returns:
            模型信息字典，如果不存在则返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, repo_id, filename, created_at, updated_at
                    FROM models
                    WHERE filename = ?
                ''', (filename,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row['id'],
                        'repo_id': row['repo_id'],
                        'filename': row['filename'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                return None
        except Exception as e:
            print(f"获取模型信息失败: {e}")
            return None
    
    def get_all_models(self) -> List[Dict]:
        """
        获取所有模型列表
        
        Returns:
            模型信息列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, repo_id, filename, created_at, updated_at
                    FROM models
                    ORDER BY created_at DESC
                ''')
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row['id'],
                        'repo_id': row['repo_id'],
                        'filename': row['filename'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
    
    def model_exists(self, filename: str) -> bool:
        """
        检查模型是否存在
        
        Args:
            filename: 模型文件名
            
        Returns:
            模型是否存在
        """
        return self.get_model(filename) is not None


# 全局数据库实例将在 config 中初始化
db = None
