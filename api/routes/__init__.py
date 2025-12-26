"""
路由处理器 - API 端点实现
"""

from fastapi import APIRouter
from core.config import config
from core.model_loader import model_loader
from api.routes.model_manager_routes import router as model_router
from api.routes.service_control_routes import router as service_router
from api.routes.upload_routes import router as upload_router

# 创建路由器
router = APIRouter()

# 引入模型管理路由
router.include_router(model_router)

# 引入子服务控制路由
router.include_router(service_router)

# 引入分片上传路由
router.include_router(upload_router, prefix="/upload", tags=["分片上传"])


@router.get("/health")
async def health_check():
    """
    健康检查接口
    返回主服务状态和配置信息
    """
    models = model_loader.read_models_list()
    return {
        "status": "ok",
        "service": "AiEdge LLM Management Server",
        "version": "2.0.0",
        "main_server": {
            "host": config.MAIN_SERVER_HOST,
            "port": config.MAIN_SERVER_PORT
        },
        "model_server": {
            "host": config.MODEL_SERVER_HOST,
            "port": config.MODEL_SERVER_PORT
        },
        "available_models": len(models),
        "gpu_layers": config.N_GPU_LAYERS
    }


@router.get("/")
async def root():
    """
    根路径，返回服务信息
    """
    return {
        "message": "AiEdge LLM Management Server",
        "version": "2.0.0",
        "description": "主服务 - 提供模型管理和子服务控制",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "models": "/models/*",
            "service": "/service/*"
        }
    }

