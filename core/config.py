"""
配置管理类
使用 .env 文件管理环境变量
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from core.database import Database


class Config:
    """配置类，统一管理所有配置项"""
    
    def __init__(self):
        # 加载.env文件中的环境变量
        load_dotenv()
        
        # 项目根目录
        self.PROJECT_ROOT = Path(__file__).parent.parent
        
        # 模型和数据目录（使用项目内的目录）
        self.MODELS_DIR = self.PROJECT_ROOT / "models"
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        self.DB_PATH = self.DATA_DIR / "models.db"
        
        # 上传临时目录
        self.UPLOAD_TEMP_DIR = self.PROJECT_ROOT / "data" / "uploads"
        
        # 确保目录存在
        self.MODELS_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)
        self.UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.db = Database(str(self.DB_PATH))
        
        # 主服务配置（管理服务）
        self.MAIN_SERVER_HOST = os.getenv("MAIN_SERVER_HOST", "0.0.0.0")
        self.MAIN_SERVER_PORT = int(os.getenv("MAIN_SERVER_PORT", "23058"))
        
        # 子服务配置（模型推理服务）
        self.MODEL_SERVER_HOST = os.getenv("MODEL_SERVER_HOST", "0.0.0.0")
        self.MODEL_SERVER_PORT = int(os.getenv("MODEL_SERVER_PORT", "23059"))
        
        # GPU配置
        self.N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "-1"))  # -1 表示使用所有GPU层
        
        # API密钥（如果需要）
        self.API_KEY = os.getenv("API_KEY")
        
        # 上传配置
        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(10 * 1024 * 1024)))  # 默认10MB
        self.UPLOAD_SESSION_EXPIRE_HOURS = int(os.getenv("UPLOAD_SESSION_EXPIRE_HOURS", "24"))  # 默认24小时
        
        # 测试配置
        test_model_path = os.getenv("TEST_UPLOAD_MODEL_PATH", "")
        self.TEST_UPLOAD_MODEL_PATH = self.PROJECT_ROOT / test_model_path if test_model_path else None
        
        # 模型下载配置
        self.MODELS_TO_DOWNLOAD = self._parse_models_to_download()
    
    def _parse_models_to_download(self):
        """解析要下载的模型列表"""
        models_str = os.getenv("MODELS_TO_DOWNLOAD", "")
        if not models_str:
            return []
        
        models = []
        for model_str in models_str.split(','):
            model_str = model_str.strip()
            if '|' in model_str:
                parts = model_str.split('|', 1)
                if len(parts) == 2:
                    models.append({
                        'repo_id': parts[0].strip(),
                        'filename': parts[1].strip()
                    })
        return models
    
    @property
    def model_path(self):
        """获取模型目录路径"""
        return str(self.MODELS_DIR)
    
    def __repr__(self):
        return f"Config(main={self.MAIN_SERVER_HOST}:{self.MAIN_SERVER_PORT}, model={self.MODEL_SERVER_HOST}:{self.MODEL_SERVER_PORT})"


# 创建全局配置实例
config = Config()
