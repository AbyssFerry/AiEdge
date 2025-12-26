"""
上传管理器模块
处理模型文件的分片上传、合并和断点续传
"""

import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.config import config
from core.model_loader import model_loader


class UploadManager:
    """上传管理器，处理分片上传和文件合并"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db = config.db
        self.temp_dir = config.UPLOAD_TEMP_DIR
        self.models_dir = config.MODELS_DIR
        self.expire_hours = config.UPLOAD_SESSION_EXPIRE_HOURS
        self._initialized = True
    
    def init_upload_session(self, filename: str, file_size: int, total_chunks: int) -> Dict:
        """
        初始化上传会话
        
        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            total_chunks: 总分片数
            
        Returns:
            包含 success、task_id、uploaded_chunks、message 的字典
        """
        try:
            # 检查文件名是否已存在于模型目录
            model_path = self.models_dir / filename
            if model_path.exists():
                return {
                    "success": False,
                    "message": f"模型文件 {filename} 已存在"
                }
            
            # 检查磁盘空间（需要1.5倍文件大小的空间）
            required_space = int(file_size * 1.5)
            stat = os.statvfs(str(self.temp_dir))
            available_space = stat.f_bavail * stat.f_frsize
            
            if available_space < required_space:
                return {
                    "success": False,
                    "message": f"磁盘空间不足。需要: {self._format_size(required_space)}, "
                              f"可用: {self._format_size(available_space)}"
                }
            
            # 检查是否有相同文件名的未完成上传（断点续传）
            existing_sessions = self._find_existing_session(filename, file_size, total_chunks)
            
            if existing_sessions:
                # 返回现有会话，支持断点续传
                task_id = existing_sessions['task_id']
                uploaded_chunks = self.db.get_uploaded_chunks(task_id)
                
                print(f"📋 发现未完成的上传会话: {task_id}")
                print(f"   已上传分片: {len(uploaded_chunks)}/{total_chunks}")
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "uploaded_chunks": uploaded_chunks,
                    "message": f"继续之前的上传，已完成 {len(uploaded_chunks)}/{total_chunks} 个分片"
                }
            
            # 创建新的上传会话
            task_id = str(uuid.uuid4())
            expires_at = (datetime.now() + timedelta(hours=self.expire_hours)).isoformat()
            
            # 创建任务专用的临时目录
            task_temp_dir = self.temp_dir / task_id
            task_temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存到数据库
            success = self.db.create_upload_session(
                task_id=task_id,
                filename=filename,
                file_size=file_size,
                total_chunks=total_chunks,
                expires_at=expires_at
            )
            
            if not success:
                return {
                    "success": False,
                    "message": "创建上传会话失败"
                }
            
            print(f"✅ 创建新上传会话: {task_id}")
            print(f"   文件名: {filename}")
            print(f"   大小: {self._format_size(file_size)}")
            print(f"   分片数: {total_chunks}")
            print(f"   过期时间: {expires_at}")
            
            return {
                "success": True,
                "task_id": task_id,
                "uploaded_chunks": [],
                "message": "上传会话已创建"
            }
            
        except Exception as e:
            print(f"❌ 初始化上传会话失败: {e}")
            return {
                "success": False,
                "message": f"初始化失败: {str(e)}"
            }
    
    def save_chunk(self, task_id: str, chunk_index: int, chunk_data: bytes) -> Dict:
        """
        保存分片数据
        
        Args:
            task_id: 任务ID
            chunk_index: 分片索引
            chunk_data: 分片数据
            
        Returns:
            包含 success、progress、uploaded_chunks、total_chunks、message 的字典
        """
        try:
            # 验证会话
            session = self.db.get_upload_session(task_id)
            if not session:
                return {
                    "success": False,
                    "message": "上传会话不存在或已过期"
                }
            
            if session['status'] == 'completed':
                return {
                    "success": False,
                    "message": "上传已完成，无法继续上传分片"
                }
            
            # 验证分片索引
            if chunk_index < 0 or chunk_index >= session['total_chunks']:
                return {
                    "success": False,
                    "message": f"分片索引无效: {chunk_index}"
                }
            
            # 检查分片是否已上传（幂等性处理）
            uploaded_chunks = self.db.get_uploaded_chunks(task_id)
            if chunk_index in uploaded_chunks:
                progress = (len(uploaded_chunks) / session['total_chunks']) * 100
                return {
                    "success": True,
                    "progress": round(progress, 2),
                    "uploaded_chunks": len(uploaded_chunks),
                    "total_chunks": session['total_chunks'],
                    "message": f"分片 {chunk_index} 已存在，跳过"
                }
            
            # 保存分片文件
            task_temp_dir = self.temp_dir / task_id
            chunk_file_path = task_temp_dir / f"chunk_{chunk_index:06d}"
            
            # 流式写入分片数据
            with open(chunk_file_path, 'wb') as f:
                f.write(chunk_data)
            
            # 记录到数据库
            self.db.add_upload_chunk(task_id, chunk_index, str(chunk_file_path))
            
            # 更新进度
            uploaded_chunks = self.db.get_uploaded_chunks(task_id)
            progress = (len(uploaded_chunks) / session['total_chunks']) * 100
            
            print(f"📦 分片 {chunk_index} 已保存 ({len(uploaded_chunks)}/{session['total_chunks']})")
            
            return {
                "success": True,
                "progress": round(progress, 2),
                "uploaded_chunks": len(uploaded_chunks),
                "total_chunks": session['total_chunks'],
                "message": f"分片 {chunk_index} 上传成功"
            }
            
        except Exception as e:
            print(f"❌ 保存分片失败: {e}")
            return {
                "success": False,
                "message": f"保存分片失败: {str(e)}"
            }
    
    def merge_chunks(self, task_id: str) -> Dict:
        """
        合并所有分片成完整文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            包含 success、message、model_path 的字典
        """
        try:
            # 验证会话
            session = self.db.get_upload_session(task_id)
            if not session:
                return {
                    "success": False,
                    "message": "上传会话不存在或已过期"
                }
            
            # 检查是否已完成
            if session['status'] == 'completed':
                model_path = self.models_dir / session['filename']
                if model_path.exists():
                    return {
                        "success": True,
                        "message": "文件已合并完成",
                        "model_path": str(model_path)
                    }
            
            # 验证所有分片完整性
            uploaded_chunks = self.db.get_uploaded_chunks(task_id)
            total_chunks = session['total_chunks']
            
            if len(uploaded_chunks) != total_chunks:
                missing_chunks = set(range(total_chunks)) - set(uploaded_chunks)
                return {
                    "success": False,
                    "message": f"分片不完整，缺少: {sorted(list(missing_chunks))[:10]}"
                }
            
            # 检查分片是否连续
            if uploaded_chunks != list(range(total_chunks)):
                return {
                    "success": False,
                    "message": "分片索引不连续"
                }
            
            print(f"🔗 开始合并分片: {session['filename']}")
            print(f"   总分片数: {total_chunks}")
            
            # 获取所有分片文件路径（已排序）
            chunk_paths = self.db.get_chunk_file_paths(task_id)
            
            # 合并到最终文件
            final_path = self.models_dir / session['filename']
            merged_size = 0
            
            with open(final_path, 'wb') as outfile:
                for i, chunk_path in enumerate(chunk_paths):
                    if not os.path.exists(chunk_path):
                        # 清理已写入的部分
                        if final_path.exists():
                            final_path.unlink()
                        return {
                            "success": False,
                            "message": f"分片文件不存在: {chunk_path}"
                        }
                    
                    # 流式读取并写入
                    with open(chunk_path, 'rb') as infile:
                        chunk_data = infile.read()
                        outfile.write(chunk_data)
                        merged_size += len(chunk_data)
                    
                    # 显示进度
                    if (i + 1) % 10 == 0 or (i + 1) == total_chunks:
                        progress = ((i + 1) / total_chunks) * 100
                        print(f"   合并进度: {i + 1}/{total_chunks} ({progress:.1f}%)")
            
            # 验证文件大小
            if merged_size != session['file_size']:
                print(f"⚠️  文件大小不匹配: 期望 {session['file_size']}, 实际 {merged_size}")
                # 不删除文件，允许用户检查
                self.db.update_upload_session_status(task_id, 'failed')
                return {
                    "success": False,
                    "message": f"文件大小验证失败: 期望 {session['file_size']}, 实际 {merged_size}"
                }
            
            print(f"✅ 文件合并成功: {final_path}")
            print(f"   最终大小: {self._format_size(merged_size)}")
            
            # 添加到模型数据库（使用空的 repo_id，因为是手动上传）
            model_loader.add_model("manual_upload", session['filename'])
            
            # 更新会话状态
            self.db.update_upload_session_status(task_id, 'completed')
            
            # 清理临时文件
            self._cleanup_temp_files(task_id)
            
            return {
                "success": True,
                "message": "文件合并成功",
                "model_path": str(final_path)
            }
            
        except Exception as e:
            print(f"❌ 合并分片失败: {e}")
            # 标记为失败但不删除临时文件，允许重试
            self.db.update_upload_session_status(task_id, 'failed')
            return {
                "success": False,
                "message": f"合并失败: {str(e)}"
            }
    
    def get_upload_progress(self, task_id: str) -> Dict:
        """
        获取上传进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            包含进度信息的字典
        """
        try:
            session = self.db.get_upload_session(task_id)
            if not session:
                return {
                    "success": False,
                    "status": "not_found",
                    "message": "上传会话不存在"
                }
            
            uploaded_chunks = self.db.get_uploaded_chunks(task_id)
            progress = (len(uploaded_chunks) / session['total_chunks']) * 100
            
            return {
                "success": True,
                "status": session['status'],
                "progress": round(progress, 2),
                "uploaded_chunks": len(uploaded_chunks),
                "total_chunks": session['total_chunks'],
                "filename": session['filename'],
                "file_size": session['file_size'],
                "message": f"进度: {len(uploaded_chunks)}/{session['total_chunks']}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取进度失败: {str(e)}"
            }
    
    def cleanup_expired_sessions(self) -> Dict:
        """
        清理过期的上传会话和临时文件
        
        Returns:
            包含清理结果的字典
        """
        try:
            expired_task_ids = self.db.get_expired_sessions()
            
            if not expired_task_ids:
                print("🧹 没有过期的上传会话")
                return {
                    "success": True,
                    "cleaned_count": 0,
                    "message": "没有过期会话需要清理"
                }
            
            print(f"🧹 开始清理 {len(expired_task_ids)} 个过期会话...")
            
            cleaned_count = 0
            for task_id in expired_task_ids:
                try:
                    # 清理临时文件
                    self._cleanup_temp_files(task_id)
                    
                    # 删除数据库记录
                    self.db.delete_upload_session(task_id)
                    
                    cleaned_count += 1
                    print(f"   ✅ 已清理: {task_id}")
                    
                except Exception as e:
                    print(f"   ⚠️  清理失败 {task_id}: {e}")
            
            print(f"✅ 清理完成，共清理 {cleaned_count} 个会话")
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "message": f"已清理 {cleaned_count} 个过期会话"
            }
            
        except Exception as e:
            print(f"❌ 清理过期会话失败: {e}")
            return {
                "success": False,
                "message": f"清理失败: {str(e)}"
            }
    
    def _find_existing_session(self, filename: str, file_size: int, total_chunks: int) -> Optional[Dict]:
        """查找相同文件的未完成上传会话"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT task_id, filename, file_size, total_chunks, status, created_at, expires_at
                    FROM upload_sessions
                    WHERE filename = ? AND file_size = ? AND total_chunks = ? 
                          AND status = 'uploading'
                          AND datetime(expires_at) > datetime('now')
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (filename, file_size, total_chunks))
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
            print(f"查找现有会话失败: {e}")
            return None
    
    def _cleanup_temp_files(self, task_id: str):
        """清理任务的临时文件"""
        try:
            task_temp_dir = self.temp_dir / task_id
            if task_temp_dir.exists():
                shutil.rmtree(task_temp_dir)
                print(f"🗑️  已删除临时目录: {task_temp_dir}")
        except Exception as e:
            print(f"⚠️  删除临时文件失败: {e}")
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# 创建全局上传管理器实例
upload_manager = UploadManager()
