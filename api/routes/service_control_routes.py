"""
子服务控制路由
提供启动、停止、重启和状态查询接口
"""

from fastapi import APIRouter, HTTPException
from core.service_manager import service_manager
from core.model_loader import model_loader
from core.config import config

router = APIRouter(prefix="/service", tags=["子服务控制"])


@router.post("/start")
async def start_service():
    """
    启动模型推理子服务
    
    子服务将加载 models 目录中的所有模型
    """
    # 检查是否有可用的模型
    models = model_loader.read_models_list()
    if not models:
        raise HTTPException(
            status_code=400,
            detail="没有可用的模型，请先下载模型"
        )
    
    result = service_manager.start()
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "port": config.MODEL_SERVER_PORT,
            "status": result["status"],
            "models": [m["filename"] for m in models]
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=result["message"]
        )


@router.post("/stop")
async def stop_service():
    """
    停止模型推理子服务
    
    优雅地关闭子服务并释放资源
    """
    result = service_manager.stop()
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "status": result["status"]
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=result["message"]
        )


@router.post("/restart")
async def restart_service():
    """
    重启模型推理子服务
    
    用于在下载新模型后重新加载所有模型
    """
    # 检查是否有可用的模型
    models = model_loader.read_models_list()
    if not models:
        raise HTTPException(
            status_code=400,
            detail="没有可用的模型，请先下载模型"
        )
    
    result = service_manager.restart()
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "port": config.MODEL_SERVER_PORT,
            "status": result["status"],
            "models": [m["filename"] for m in models]
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=result["message"]
        )


@router.get("/status")
async def get_service_status():
    """
    获取子服务状态
    
    返回子服务的运行状态、端口、PID 等信息
    """
    status = service_manager.get_status()
    models = model_loader.read_models_list()
    
    return {
        "status": status["status"],
        "port": status["port"],
        "pid": status["pid"],
        "uptime_seconds": status["uptime_seconds"],
        "available_models": [m["filename"] for m in models]
    }
