"""
模型加载和管理逻辑
将模型相关的功能从 main.py 分离出来
"""

from pathlib import Path
from llama_cpp.server.settings import ModelSettings
from core.config import config


class ModelLoader:
    """模型加载器类，负责模型文件加载和 models.txt 管理"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def read_models_list(self):
        """从 data/models.txt 读取已下载的模型列表"""
        if not config.MODELS_TXT.exists():
            print("⚠️  未找到 data/models.txt 文件，将不加载任何模型")
            return []
        
        models = []
        with open(config.MODELS_TXT, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析格式: repo_id|filename
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        models.append({
                            'repo_id': parts[0].strip(),
                            'filename': parts[1].strip()
                        })
        
        return models
    
    def create_model_settings(self):
        """根据 models.txt 中的模型列表创建 ModelSettings"""
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
        """添加模型到 models.txt"""
        # 先读取现有模型，避免重复
        existing_models = self.read_models_list()
        for model in existing_models:
            if model['repo_id'] == repo_id and model['filename'] == filename:
                return  # 已存在，不重复添加
        
        # 追加到文件
        with open(config.MODELS_TXT, 'a', encoding='utf-8') as f:
            f.write(f"{repo_id}|{filename}\n")
    
    def remove_model(self, filename: str):
        """从 models.txt 删除模型"""
        if not config.MODELS_TXT.exists():
            return
        
        # 读取所有行
        with open(config.MODELS_TXT, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉要删除的模型
        with open(config.MODELS_TXT, 'w', encoding='utf-8') as f:
            for line in lines:
                # 保留注释和空行
                if line.strip().startswith('#') or not line.strip():
                    f.write(line)
                    continue
                
                # 检查是否是要删除的模型
                if '|' in line:
                    parts = line.strip().split('|', 1)
                    if len(parts) == 2 and parts[1].strip() != filename:
                        f.write(line)


# 创建全局单例
model_loader = ModelLoader()
