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


@router.post(
    "/init",
    response_model=ChunkUploadInitResponse,
    summary="初始化上传会话",
    description="创建分块上传会话，支持断点续传",
    responses={
        200: {"description": "初始化成功"},
        400: {"description": "参数错误或文件格式不支持"}
    }
)
async def init_upload_session(request: ChunkUploadInitRequest):
    """
    ## 初始化分块上传会话
    
    创建一个大文件分块上传会话，返回任务ID和已上传的分块列表。
    
    ### 参数说明
    - **filename**: 文件名（必须以 `.gguf` 结尾）
    - **file_size**: 文件总大小（字节）
    - **total_chunks**: 总分块数（建议每块 10MB）
    
    ### 功能特性
    - ✅ **断点续传**: 如果之前上传中断，会返回已上传的分块列表
    - ✅ **磁盘空间检查**: 自动检查是否有足够空间
    - ✅ **会话管理**: 会话 24小时后自动过期
    
    ### 返回示例
    ```json
    {
      "success": true,
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "uploaded_chunks": [0, 1, 2, 5],
      "message": "继续之前的上传，已完成 4/512 个分块"
    }
    ```
    
    ### 使用流程
    1. 调用此接口初始化
    2. 使用返回的 `task_id` 上传分块
    3. 检查 `uploaded_chunks` 跳过已上传的分块
    4. 上传完成后调用合并接口
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


@router.post(
    "/chunk",
    summary="上传单个分块",
    description="上传文件的单个分块，支持幂等性",
    responses={
        200: {"description": "上传成功"},
        400: {"description": "参数错误或任务不存在"},
        500: {"description": "服务器内部错误"}
    }
)
async def upload_chunk(
    task_id: str = Form(..., description="上传任务ID（从 /upload/init 获取）"),
    chunk_index: int = Form(..., description="分块索引（从 0 开始）"),
    file: UploadFile = File(..., description="分块文件数据")
):
    """上传单个文件分块，支持幂等性和并行上传"""
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
