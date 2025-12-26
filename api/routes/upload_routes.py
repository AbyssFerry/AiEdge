"""
分片上传路由
处理模型文件的分片上传、进度查询和合并
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from api.models.model_manager_models import (
    ChunkUploadInitRequest,
    ChunkUploadInitResponse,
    ChunkUploadProgressResponse,
    ChunkUploadCompleteResponse
)
from core.upload_manager import upload_manager


router = APIRouter()


@router.post("/init", response_model=ChunkUploadInitResponse)
async def init_upload_session(request: ChunkUploadInitRequest):
    """
    初始化分片上传会话
    
    - 生成唯一的任务ID
    - 检查磁盘空间
    - 支持断点续传（返回已上传的分片列表）
    """
    # 验证文件名格式
    if not request.filename.lower().endswith('.gguf'):
        raise HTTPException(status_code=400, detail="只支持 .gguf 格式的模型文件")
    
    # 初始化上传会话
    result = upload_manager.init_upload_session(
        filename=request.filename,
        file_size=request.file_size,
        total_chunks=request.total_chunks
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ChunkUploadInitResponse(
        success=True,
        task_id=result["task_id"],
        uploaded_chunks=result.get("uploaded_chunks", []),
        message=result["message"]
    )


@router.post("/chunk")
async def upload_chunk(
    task_id: str = Form(..., description="上传任务ID"),
    chunk_index: int = Form(..., description="分片索引（从0开始）"),
    file: UploadFile = File(..., description="分片文件数据")
):
    """
    上传单个分片
    
    - 支持幂等性（重复上传同一分片直接返回成功）
    - 返回实时上传进度
    """
    try:
        # 读取分片数据
        chunk_data = await file.read()
        
        # 保存分片
        result = upload_manager.save_chunk(
            task_id=task_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {
            "success": True,
            "progress": result["progress"],
            "uploaded_chunks": result["uploaded_chunks"],
            "total_chunks": result["total_chunks"],
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传分片失败: {str(e)}")


@router.get("/progress/{task_id}", response_model=ChunkUploadProgressResponse)
async def get_upload_progress(task_id: str):
    """
    查询上传进度
    
    - 返回已上传的分片数和百分比
    - 返回会话状态（uploading/completed/failed）
    """
    result = upload_manager.get_upload_progress(task_id)
    
    if not result["success"]:
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ChunkUploadProgressResponse(
        success=True,
        status=result["status"],
        progress=result["progress"],
        uploaded_chunks=result["uploaded_chunks"],
        total_chunks=result["total_chunks"],
        filename=result.get("filename"),
        file_size=result.get("file_size"),
        message=result["message"]
    )


@router.post("/complete", response_model=ChunkUploadCompleteResponse)
async def complete_upload(task_id: str = Form(..., description="上传任务ID")):
    """
    完成上传并合并分片
    
    - 验证所有分片完整性
    - 按顺序合并分片成完整文件
    - 验证文件大小
    - 保存到模型目录并更新数据库
    - 清理临时文件
    """
    result = upload_manager.merge_chunks(task_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ChunkUploadCompleteResponse(
        success=True,
        message=result["message"],
        model_path=result.get("model_path")
    )
