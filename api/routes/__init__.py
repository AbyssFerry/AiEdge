"""
路由处理器 - API 端点实现
"""

from fastapi import APIRouter
import os
from core.config import config
from api.routes.model_manager import router as model_router

# 创建路由器
router = APIRouter()

# 引入模型管理路由
router.include_router(model_router)


@router.get("/health")
async def health_check():
    """
    健康检查接口
    返回服务状态和配置信息
    """
    return {
        "status": "ok",
        "service": "AiEdge LLM Server",
        "model": os.path.basename(config.model_path),
        "host": config.SERVER_HOST,
        "port": config.SERVER_PORT,
        "gpu_layers": config.N_GPU_LAYERS
    }


@router.get("/")
async def root():
    """
    根路径，返回服务信息
    """
    return {
        "message": "AiEdge LLM Server is running",
        "docs": "/docs",
        "health": "/health"
    }
