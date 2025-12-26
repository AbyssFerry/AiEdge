"""
模型管理业务逻辑
处理模型下载、删除和列表操作
"""

import shutil
import sys
import re
import time
from pathlib import Path
from typing import Optional, Dict
from llama_cpp import Llama
from core.config import config
from core.model_loader import model_loader


class ModelManager:
    """模型管理类，处理模型的下载、删除和列表操作"""
    
    _instance: Optional['ModelManager'] = None
    download_progress: Dict[str, dict]
    is_downloading: bool
    current_task_id: Optional[str]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.download_progress = {}  # 存储下载进度
            cls._instance.is_downloading = False  # 并发限制标志
            cls._instance.current_task_id = None  # 当前正在下载的任务ID
        return cls._instance
    
    def download_model(self, repo_id: str, filename: str, task_id: Optional[str] = None) -> dict:
        """
        从 Hugging Face 下载模型到本地 models 目录
        支持断点续传
        
        Args:
            repo_id: 模型仓库 ID
            filename: 要下载的模型文件名
            task_id: 任务ID，用于追踪进度（可选）
            
        Returns:
            包含操作结果的字典
        """
        try:
            # 检查是否已有下载任务在执行（限制并发为1）
            if task_id and self.is_downloading and self.current_task_id != task_id:
                return {
                    "success": False,
                    "message": f"已有下载任务正在进行中 (ID: {self.current_task_id})，请等待完成后再试",
                    "model_path": None,
                    "details": None
                }
            
            # 标记为正在下载
            if task_id:
                self.is_downloading = True
                self.current_task_id = task_id
                self.download_progress[task_id] = {
                    'status': 'starting',
                    'percentage': 0,
                    'current_str': '0B',
                    'total_str': '0B',
                    'message': '准备下载...'
                }
            
            # 准备下载参数
            local_dir = str(config.MODELS_DIR)
            
            # 捕获 tqdm 输出来获取进度
            class ProgressCapture:
                def __init__(self, task_id, manager):
                    self.task_id = task_id
                    self.manager = manager
                    # 匹配百分比和文件大小
                    self.pattern_full = re.compile(r'(\d+)%.*?(\d+\.?\d*[KMGT]?i?B)/(\d+\.?\d*[KMGT]?i?B)')
                    self.pattern_percent = re.compile(r'(\d+)%')
                    self.last_update = 0
                    self.buffer = ""  # 缓冲区累积文本
                
                def write(self, text):
                    # 累积文本到缓冲区
                    self.buffer += text
                    
                    if self.task_id:
                        current_time = time.time()
                        # 限制更新频率，避免过于频繁（每0.1秒最多更新一次）
                        if current_time - self.last_update >= 0.1:
                            # 先尝试匹配完整格式
                            match = self.pattern_full.search(self.buffer)
                            if match:
                                percentage = float(match.group(1))
                                current_str = match.group(2)
                                total_str = match.group(3)
                                
                                self.manager.download_progress[self.task_id] = {
                                    'status': 'downloading',
                                    'percentage': percentage,
                                    'current_str': current_str,
                                    'total_str': total_str,
                                    'message': f'下载中: {current_str}/{total_str}'
                                }
                                self.last_update = current_time
                                self.buffer = ""  # 清空缓冲区
                            else:
                                # 如果匹配不到完整格式，至少匹配百分比
                                match_percent = self.pattern_percent.search(self.buffer)
                                if match_percent:
                                    percentage = float(match_percent.group(1))
                                    
                                    self.manager.download_progress[self.task_id] = {
                                        'status': 'downloading',
                                        'percentage': percentage,
                                        'current_str': '未知',
                                        'total_str': '未知',
                                        'message': f'下载中: {percentage}%'
                                    }
                                    self.last_update = current_time
                                    # 保留部分缓冲区，可能需要更多文本才能匹配完整格式
                                    if len(self.buffer) > 500:
                                        self.buffer = self.buffer[-200:]
                    
                    # 同时输出到标准错误，保留原有日志，并立即刷新
                    if sys.__stderr__ is not None:
                        sys.__stderr__.write(text)
                        sys.__stderr__.flush()
                
                def flush(self):
                    if sys.__stderr__ is not None:
                        sys.__stderr__.flush()
            
            # 如果有 task_id，捕获进度
            if task_id:
                old_stderr = sys.stderr
                sys.stderr = ProgressCapture(task_id, self)
            
            try:
                # 使用 Llama.from_pretrained 下载模型
                # 支持断点续传（底层 huggingface_hub 自动支持）
                llm = Llama.from_pretrained(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=local_dir,
                    verbose=False
                )
            finally:
                # 恢复标准错误输出
                if task_id:
                    sys.stderr = old_stderr
            
            # 更新完成状态
            if task_id:
                self.download_progress[task_id] = {
                    'status': 'completed',
                    'percentage': 100,
                    'message': '下载完成'
                }
                self.is_downloading = False
                self.current_task_id = None
            
            # 下载成功后，添加到 models.txt
            model_loader.add_model(repo_id, filename)
            
            downloaded_info = {
                "repo_id": repo_id,
                "filename": filename,
                "local_dir": local_dir
            }
            
            return {
                "success": True,
                "message": f"模型下载成功: {filename}",
                "model_path": str(config.MODELS_DIR),
                "details": downloaded_info
            }
            
        except Exception as e:
            if task_id:
                self.download_progress[task_id] = {
                    'status': 'failed',
                    'percentage': 0,
                    'error': str(e),
                    'message': f'下载失败: {str(e)}'
                }
                self.is_downloading = False
                self.current_task_id = None
            
            return {
                "success": False,
                "message": f"下载模型失败: {str(e)}",
                "model_path": None,
                "details": None
            }
    
    def get_download_progress(self, task_id: str) -> dict:
        """
        获取下载进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            包含进度信息的字典
        """
        progress = self.download_progress.get(task_id)
        if progress:
            return progress
        else:
            return {
                'status': 'not_found',
                'message': '任务不存在或已过期'
            }
    
    def delete_model(self, model_name: str) -> dict:
        """
        删除本地 models 目录中的模型文件或文件夹
        
        Args:
            model_name: 要删除的模型文件名或目录名
            
        Returns:
            包含操作结果的字典
        """
        try:
            # 构建完整路径
            model_path = config.MODELS_DIR / model_name
            
            # 安全检查：确保路径在 models 目录内
            if not str(model_path.resolve()).startswith(str(config.MODELS_DIR.resolve())):
                return {
                    "success": False,
                    "message": "无效的模型路径，只能删除 models 目录下的文件",
                    "model_path": None,
                    "details": None
                }
            
            # 检查文件/目录是否存在
            if not model_path.exists():
                return {
                    "success": False,
                    "message": f"模型 '{model_name}' 不存在",
                    "model_path": None,
                    "details": None
                }
            
            # 删除文件或目录
            if model_path.is_file():
                model_path.unlink()
                deleted_type = "文件"
            elif model_path.is_dir():
                shutil.rmtree(model_path)
                deleted_type = "目录"
            else:
                return {
                    "success": False,
                    "message": f"无法删除 '{model_name}'，类型未知",
                    "model_path": None,
                    "details": None
                }
            
            # 从 models.txt 删除记录
            model_loader.remove_model(model_name)
            
            return {
                "success": True,
                "message": f"成功删除{deleted_type}: {model_name}",
                "model_path": str(model_path),
                "details": {
                    "deleted_type": deleted_type,
                    "deleted_path": str(model_path)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"删除模型时发生错误: {str(e)}",
                "model_path": None,
                "details": None
            }
    
    def list_models(self) -> dict:
        """
        列出 models 目录中的所有 GGUF 模型文件
        
        Returns:
            包含模型列表的字典
        """
        try:
            if not config.MODELS_DIR.exists():
                return {
                    "success": True,
                    "models_dir": str(config.MODELS_DIR),
                    "files": [],
                    "total_count": 0
                }
            
            files = []
            
            # 只读取 .gguf 结尾的文件
            for item in config.MODELS_DIR.iterdir():
                if item.is_file() and item.name.lower().endswith('.gguf'):
                    item_info = {
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size
                    }
                    files.append(item_info)
            
            return {
                "success": True,
                "models_dir": str(config.MODELS_DIR),
                "files": files,
                "total_count": len(files)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"列出模型时发生错误: {str(e)}",
                "models_dir": None,
                "files": [],
                "total_count": 0
            }


# 创建全局单例
model_manager = ModelManager()
