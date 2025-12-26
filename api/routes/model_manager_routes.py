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


@router.post("/download", response_model=ModelResponse)
async def download_model(request: ModelDownloadRequest):
    """
    使用 llama-cpp-python 从 Hugging Face 下载模型到本地 models 目录（同步方式）
    
    - **repo_id**: 模型仓库 ID（必填）
    - **filename**: 要下载的模型文件名（必填）
    
    注意：此接口会阻塞直到下载完成，建议使用 /download/start 启动异步下载
    """
    result = model_manager.download_model(request.repo_id, request.filename)
    
    if result["success"]:
        return ModelResponse(**result)
    else:
        raise HTTPException(
            status_code=400 if "失败" in result["message"] else 500,
            detail=result["message"]
        )


@router.post("/download/start", response_model=DownloadTaskResponse)
async def start_download(request: ModelDownloadRequest):
    """
    异步启动模型下载任务（推荐使用）
    
    - **repo_id**: 模型仓库 ID（必填）
    - **filename**: 要下载的模型文件名（必填）
    
    返回任务ID，可通过 /download/status/{task_id} 查询下载进度
    
    支持断点续传：如果下载中断，重新启动相同的模型下载将自动从断点继续
    """
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


@router.get("/download/status/{task_id}", response_model=DownloadProgressResponse)
async def get_download_status(task_id: str):
    """
    查询下载任务进度
    
    - **task_id**: 任务ID（从 /download/start 接口获取）
    
    返回下载状态：
    - starting: 准备下载
    - downloading: 下载中
    - completed: 下载完成
    - failed: 下载失败
    - not_found: 任务不存在或已过期
    """
    progress = model_manager.get_download_progress(task_id)
    return DownloadProgressResponse(**progress)


@router.delete("/delete", response_model=ModelResponse)
async def delete_model(request: ModelDeleteRequest):
    """
    删除本地 models 目录中的模型文件或文件夹
    
    - **model_name**: 要删除的模型文件名或目录名（必填）
    """
    result = model_manager.delete_model(request.model_name)
    
    if result["success"]:
        return ModelResponse(**result)
    else:
        status_code = 404 if "不存在" in result["message"] else 400 if "无效" in result["message"] else 500
        raise HTTPException(
            status_code=status_code,
            detail=result["message"]
        )


@router.get("/list", response_model=dict)
async def list_models():
    """
    列出 models 目录中的所有 GGUF 模型文件
    """
    result = model_manager.list_models()
    
    if result["success"]:
        return result
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "列出模型时发生错误")
        )
