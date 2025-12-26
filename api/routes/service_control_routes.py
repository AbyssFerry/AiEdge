"""
子服务控制路由
提供启动、停止、重启和状态查询接口
"""

from fastapi import APIRouter, HTTPException
from core.service_manager import service_manager
from core.model_loader import model_loader
from core.config import config

router = APIRouter(prefix="/service", tags=["子服务控制"])


@router.post(
    "/start",
    summary="启动推理服务",
    description="启动模型推理子服务，加载所有可用模型",
    responses={
        200: {"description": "服务启动成功"},
        400: {"description": "没有可用的模型"},
        500: {"description": "服务启动失败"}
    }
)
async def start_service():
    """启动模型推理子服务，加载所有可用模型"""
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


@router.post(
    "/stop",
    summary="停止推理服务",
    description="优雅地停止模型推理子服务并释放资源",
    responses={
        200: {"description": "服务停止成功"},
        500: {"description": "服务停止失败"}
    }
)
async def stop_service():
    """停止模型推理子服务并释放资源"""
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


@router.post(
    "/restart",
    summary="重启推理服务",
    description="重启模型推理子服务，重新加载所有模型",
    responses={
        200: {"description": "服务重启成功"},
        400: {"description": "没有可用的模型"},
        500: {"description": "服务重启失败"}
    }
)
async def restart_service():
    """
    ## 重启模型推理子服务
    
    停止当前运行的服务并重新启动，重新加载所有模型。
    
    ### 主要用途
    - 🆕 **下载新模型后**：重启以加载新模型
    - 🔄 **切换模型**：删除旧模型后重启
    - 🛠️ **解决问题**：服务出现异常时重启
    
    ### 重启流程
    1. 停止当前服务
    2. 清理资源和缓存
    3. 扫描 models 目录
    4. 重新启动服务
    5. 加载所有模型
    
    ### 返回示例
    ```json
    {
      "success": true,
      "message": "子服务重启成功",
      "port": 5000,
      "status": "running",
      "models": ["new-model.gguf", "old-model.gguf"]
    }
    ```
    
    ### 注意事项
    - 重启过程需覀1-5分钟
    - 重启期间所有对话请求将不可用
    - 必须有至少一个模型才能重启
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
