"""
模型管理路由 - 提供模型下载和删除功能
"""

import uuid
import threading
from fastapi import APIRouter, HTTPException
from api.models.model_manager_models import (
    ModelDownloadRequest,
    ModelDeleteRequest,
    ModelResponse,
    DownloadTaskResponse,
    DownloadProgressResponse
)
from core.model_manager import model_manager

router = APIRouter(prefix="/models", tags=["模型管理"])


@router.post(
    "/download/start",
    response_model=DownloadTaskResponse,
    summary="下载模型",
    description="在后台启动模型下载任务，立即返回任务ID，支持断点续传",
    response_description="返回任务ID用于查询进度",
    responses={
        200: {"description": "任务启动成功"},
        400: {"description": "参数错误"},
        500: {"description": "服务器内部错误"}
    }
)
async def start_download(request: ModelDownloadRequest):
    """启动模型下载任务，立即返回任务ID"""
    # 生成唯一任务ID
    task_id = str(uuid.uuid4())
    
    # 在后台线程执行下载
    def download_task():
        model_manager.download_model(request.repo_id, request.filename, task_id)
    
    thread = threading.Thread(target=download_task, daemon=True)
    thread.start()
    
    return DownloadTaskResponse(
        success=True,
        task_id=task_id,
        message="下载任务已启动，支持断点续传"
    )


@router.get(
    "/download/status/{task_id}",
    response_model=DownloadProgressResponse,
    summary="查询下载进度",
    description="根据任务ID查询模型下载的实时进度",
    responses={
        200: {"description": "成功返回进度信息"},
        404: {"description": "任务不存在"}
    }
)
async def get_download_status(task_id: str):
    """查询下载任务的实时进度"""
    progress = model_manager.get_download_progress(task_id)
    return DownloadProgressResponse(**progress)


@router.delete(
    "/delete",
    response_model=ModelResponse,
    summary="删除模型文件",
    description="从本地 models 目录删除指定的模型文件或文件夹",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "模型不存在"},
        400: {"description": "参数错误或模型名称无效"},
        500: {"description": "服务器内部错误"}
    }
)
async def delete_model(request: ModelDeleteRequest):
    """删除本地模型文件或目录"""
    result = model_manager.delete_model(request.model_name)
    
    if result["success"]:
        return ModelResponse(**result)
    else:
        status_code = 404 if "不存在" in result["message"] else 400 if "无效" in result["message"] else 500
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )


@router.get(
    "/list",
    response_model=dict,
    summary="列出所有模型",
    description="获取 models 目录中所有可用的 GGUF 模型文件列表",
    responses={
        200: {"description": "成功返回模型列表"},
        500: {"description": "服务器内部错误"}
    }
)
async def list_models():
    """列出 models 目录中的所有 GGUF 模型"""
    result = model_manager.list_models()
    
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "列出模型时发生错误")
        )
