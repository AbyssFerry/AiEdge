"""
模型管理路由 - 提供模型下载和删除功能
"""

from fastapi import APIRouter, HTTPException
from api.models.model_manager_models import (
    ModelDownloadRequest,
    ModelDeleteRequest,
    ModelResponse
)
from core.model_manager import model_manager

router = APIRouter(prefix="/models", tags=["模型管理"])


@router.post("/download", response_model=ModelResponse)
async def download_model(request: ModelDownloadRequest):
    """
    使用 llama-cpp-python 从 Hugging Face 下载模型到本地 models 目录
    
    - **repo_id**: 模型仓库 ID（必填）
    - **filename**: 要下载的模型文件名（必填）
    """
    result = model_manager.download_model(request.repo_id, request.filename)
    
    if result["success"]:
        return ModelResponse(**result)
    else:
        raise HTTPException(
            status_code=400 if "失败" in result["message"] else 500,
            detail=result["message"]
        )


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
