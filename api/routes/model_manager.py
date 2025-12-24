"""
模型管理路由 - 提供模型下载和删除功能
"""

from fastapi import APIRouter, HTTPException
from api.models.model_manager import (
    ModelDownloadRequest,
    ModelDeleteRequest,
    ModelResponse
)
import shutil
from llama_cpp import Llama
from core.config import config
from core.model_loader import add_model_to_list, remove_model_from_list

router = APIRouter(prefix="/models", tags=["模型管理"])


@router.post("/download", response_model=ModelResponse)
async def download_model(request: ModelDownloadRequest):
    """
    使用 llama-cpp-python 从 Hugging Face 下载模型到本地 models 目录
    
    - **repo_id**: 模型仓库 ID（必填）
    - **filename**: 要下载的模型文件名（必填）
    """
    try:
        # 准备下载参数
        local_dir = str(config.MODELS_DIR)
        
        try:
            # 使用 Llama.from_pretrained 下载模型
            llm = Llama.from_pretrained(
                repo_id=request.repo_id,
                filename=request.filename,
                local_dir=local_dir,
                verbose=False  # 减少输出信息
            )
            
            # 下载成功后，添加到 models.txt
            add_model_to_list(request.repo_id, request.filename)
            
            # 获取下载的文件信息
            downloaded_info = {
                "repo_id": request.repo_id,
                "filename": request.filename,
                "local_dir": local_dir
            }
            
            return ModelResponse(
                success=True,
                message=f"模型下载成功: {request.filename}",
                model_path=str(config.MODELS_DIR),
                details=downloaded_info
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"下载模型失败: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"下载模型时发生错误: {str(e)}"
        )


@router.delete("/delete", response_model=ModelResponse)
async def delete_model(request: ModelDeleteRequest):
    """
    删除本地 models 目录中的模型文件或文件夹
    
    - **model_name**: 要删除的模型文件名或目录名（必填）
    """
    try:
        # 构建完整路径
        model_path = config.MODELS_DIR / request.model_name
        
        # 安全检查：确保路径在 models 目录内
        if not str(model_path.resolve()).startswith(str(config.MODELS_DIR.resolve())):
            raise HTTPException(
                status_code=400,
                detail="无效的模型路径，只能删除 models 目录下的文件"
            )
        
        # 检查文件/目录是否存在
        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"模型 '{request.model_name}' 不存在"
            )
        
        # 删除文件或目录
        if model_path.is_file():
            model_path.unlink()
            deleted_type = "文件"
        elif model_path.is_dir():
            shutil.rmtree(model_path)
            deleted_type = "目录"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"无法删除 '{request.model_name}'，类型未知"
            )
        
        # 从 models.txt 删除记录
        remove_model_from_list(request.model_name)
        
        return ModelResponse(
            success=True,
            message=f"成功删除{deleted_type}: {request.model_name}",
            model_path=str(model_path),
            details={
                "deleted_type": deleted_type,
                "deleted_path": str(model_path)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除模型时发生错误: {str(e)}"
        )


@router.get("/list", response_model=dict)
async def list_models():
    """
    列出 models 目录中的所有文件和文件夹
    """
    try:
        if not config.MODELS_DIR.exists():
            return {
                "success": True,
                "models_dir": str(config.MODELS_DIR),
                "files": [],
                "directories": [],
                "total_count": 0
            }
        
        files = []
        directories = []
        
        for item in config.MODELS_DIR.iterdir():
            item_info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size if item.is_file() else None
            }
            
            if item.is_file():
                files.append(item_info)
            elif item.is_dir():
                directories.append(item_info)
        
        return {
            "success": True,
            "models_dir": str(config.MODELS_DIR),
            "files": files,
            "directories": directories,
            "total_count": len(files) + len(directories)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出模型时发生错误: {str(e)}"
        )
