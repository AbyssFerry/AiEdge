"""
配置管理类
使用 .env 文件管理环境变量
"""

import os
from dotenv import load_dotenv


class Config:
    """配置类，统一管理所有配置项"""
    
    def __init__(self):
        # 加载.env文件中的环境变量
        load_dotenv()
        # load_dotenv(override=True)  # 强制覆盖现有系统环境变量
        
        # 模型配置
        self.MODEL_DIR = os.getenv("MODEL_DIR", "/home/abyss/models")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gemma-3-1b-it-f16.gguf")
        
        # 服务器配置
        self.SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
        self.SERVER_PORT = int(os.getenv("SERVER_PORT", "23058"))
        
        # GPU配置
        self.N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "-1"))  # -1 表示使用所有GPU层
        
        # API密钥（如果需要）
        self.API_KEY = os.getenv("API_KEY")
    
    @property
    def model_path(self):
        """获取完整的模型路径"""
        return os.path.join(self.MODEL_DIR, self.MODEL_NAME)
    
    def __repr__(self):
        return f"Config(host={self.SERVER_HOST}, port={self.SERVER_PORT}, model={self.MODEL_NAME})"


# 创建全局配置实例
config = Config()
