"""
模型加载和管理逻辑
将模型相关的功能从 main.py 分离出来
"""

from pathlib import Path
from llama_cpp.server.settings import ModelSettings
from core.config import config


class ModelLoader:
    """模型加载器类，负责模型文件加载和数据库管理"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def read_models_list(self):
        """从数据库读取已下载的模型列表"""
        models = config.db.get_all_models()
        return [
            {
                'repo_id': model['repo_id'],
                'filename': model['filename']
            }
            for model in models
        ]
    
    def create_model_settings(self):
        """根据数据库中的模型列表创建 ModelSettings"""
        models_list = self.read_models_list()
        
        if not models_list:
            return []
        
        model_settings = []
        
        for model_info in models_list:
            filename = model_info['filename']
            model_path = config.MODELS_DIR / filename
            
            # 检查模型文件是否存在
            if not model_path.exists():
                print(f"⚠️  模型文件不存在，跳过: {model_path}")
                continue
            
            # 为模型生成别名（去掉文件扩展名）
            model_alias = filename.rsplit('.', 1)[0]
            
            # 创建模型配置
            settings = ModelSettings(
                model=str(model_path),
                model_alias=model_alias,
                n_gpu_layers=config.N_GPU_LAYERS,
                offload_kqv=True,
                # verbose=True,
            )
            
            model_settings.append(settings)
        
        return model_settings
    
    def add_model(self, repo_id: str, filename: str):
        """添加模型到数据库"""
        config.db.add_model(repo_id, filename)
    
    def remove_model(self, filename: str):
        """从数据库删除模型"""
        config.db.remove_model(filename)


# 创建全局单例
model_loader = ModelLoader()
