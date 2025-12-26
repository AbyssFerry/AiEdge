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
            
            # 创建上传会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS upload_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'uploading',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
            
            # 创建上传分片表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS upload_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(task_id, chunk_index)
                )
            ''')
            
            # 创建上传相关索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_id ON upload_sessions(task_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_upload_chunks_task_id ON upload_chunks(task_id)
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
    
    # ========== 上传会话管理方法 ==========
    
    def create_upload_session(self, task_id: str, filename: str, file_size: int, 
                            total_chunks: int, expires_at: str) -> bool:
        """
        创建上传会话
        
        Args:
            task_id: 任务唯一标识
            filename: 文件名
            file_size: 文件大小（字节）
            total_chunks: 总分片数
            expires_at: 过期时间（ISO格式字符串）
            
        Returns:
            是否创建成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO upload_sessions (task_id, filename, file_size, total_chunks, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (task_id, filename, file_size, total_chunks, expires_at))
                conn.commit()
                return True
        except Exception as e:
            print(f"创建上传会话失败: {e}")
            return False
    
    def get_upload_session(self, task_id: str) -> Optional[Dict]:
        """
        获取上传会话信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            会话信息字典，不存在则返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT task_id, filename, file_size, total_chunks, status, 
                           created_at, expires_at
                    FROM upload_sessions
                    WHERE task_id = ?
                ''', (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'task_id': row['task_id'],
                        'filename': row['filename'],
                        'file_size': row['file_size'],
                        'total_chunks': row['total_chunks'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'expires_at': row['expires_at']
                    }
                return None
        except Exception as e:
            print(f"获取上传会话失败: {e}")
            return None
    
    def update_upload_session_status(self, task_id: str, status: str) -> bool:
        """
        更新上传会话状态
        
        Args:
            task_id: 任务ID
            status: 新状态（uploading/completed/failed）
            
        Returns:
            是否更新成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE upload_sessions
                    SET status = ?
                    WHERE task_id = ?
                ''', (status, task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新上传会话状态失败: {e}")
            return False
    
    def add_upload_chunk(self, task_id: str, chunk_index: int, file_path: str) -> bool:
        """
        记录已上传的分片
        
        Args:
            task_id: 任务ID
            chunk_index: 分片索引
            file_path: 分片文件路径
            
        Returns:
            是否记录成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO upload_chunks (task_id, chunk_index, file_path)
                    VALUES (?, ?, ?)
                ''', (task_id, chunk_index, file_path))
                conn.commit()
                return True
        except Exception as e:
            print(f"记录上传分片失败: {e}")
            return False
    
    def get_uploaded_chunks(self, task_id: str) -> List[int]:
        """
        获取已上传的分片索引列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            已上传的分片索引列表（排序后）
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT chunk_index
                    FROM upload_chunks
                    WHERE task_id = ?
                    ORDER BY chunk_index
                ''', (task_id,))
                rows = cursor.fetchall()
                return [row['chunk_index'] for row in rows]
        except Exception as e:
            print(f"获取已上传分片列表失败: {e}")
            return []
    
    def get_chunk_file_paths(self, task_id: str) -> List[str]:
        """
        获取所有分片的文件路径（按索引排序）
        
        Args:
            task_id: 任务ID
            
        Returns:
            分片文件路径列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT file_path
                    FROM upload_chunks
                    WHERE task_id = ?
                    ORDER BY chunk_index
                ''', (task_id,))
                rows = cursor.fetchall()
                return [row['file_path'] for row in rows]
        except Exception as e:
            print(f"获取分片文件路径失败: {e}")
            return []
    
    def delete_upload_session(self, task_id: str) -> bool:
        """
        删除上传会话及其所有分片记录
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 先删除分片记录
                cursor.execute('DELETE FROM upload_chunks WHERE task_id = ?', (task_id,))
                # 再删除会话
                cursor.execute('DELETE FROM upload_sessions WHERE task_id = ?', (task_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除上传会话失败: {e}")
            return False
    
    def get_expired_sessions(self) -> List[str]:
        """
        获取所有已过期的会话ID列表
        
        Returns:
            过期的任务ID列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT task_id
                    FROM upload_sessions
                    WHERE datetime(expires_at) < datetime('now')
                ''')
                rows = cursor.fetchall()
                return [row['task_id'] for row in rows]
        except Exception as e:
            print(f"获取过期会话列表失败: {e}")
            return []


# 全局数据库实例将在 config 中初始化
db = None
