"""
模型管理业务逻辑
处理模型下载、删除和列表操作
"""

import shutil
from pathlib import Path
from llama_cpp import Llama
from core.config import config
from core.model_loader import model_loader


class ModelManager:
    """模型管理类，处理模型的下载、删除和列表操作"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def download_model(self, repo_id: str, filename: str) -> dict:
        """
        从 Hugging Face 下载模型到本地 models 目录
        
        Args:
            repo_id: 模型仓库 ID
            filename: 要下载的模型文件名
            
        Returns:
            包含操作结果的字典
        """
        try:
            # 准备下载参数
            local_dir = str(config.MODELS_DIR)
            
            # 使用 Llama.from_pretrained 下载模型
            llm = Llama.from_pretrained(
                repo_id=repo_id,
                filename=filename,
                local_dir=local_dir,
                verbose=False  # 减少输出信息
            )
            
            # 下载成功后，添加到 models.txt
            model_loader.add_model(repo_id, filename)
            
            # 获取下载的文件信息
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
            return {
                "success": False,
                "message": f"下载模型失败: {str(e)}",
                "model_path": None,
                "details": None
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
