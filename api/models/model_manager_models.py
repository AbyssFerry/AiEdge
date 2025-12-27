"""
模型管理相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ModelDownloadRequest(BaseModel):
    """模型下载请求模型"""
    repo_id: str = Field(..., description="模型仓库的 ID，例如: 'meta-llama/Llama-2-7b-hf'")
    filename: str = Field(..., description="要下载的模型文件名（必填）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "repo_id": "TheBloke/Llama-2-7B-GGUF",
                "filename": "llama-2-7b.Q4_K_M.gguf"
            }
        }


class ModelDeleteRequest(BaseModel):
    """模型删除请求模型"""
    model_name: str = Field(..., description="要删除的模型文件名或目录名")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "llama-2-7b.Q4_K_M.gguf"
            }
        }


class ModelResponse(BaseModel):
    """模型操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    model_path: Optional[str] = Field(None, description="模型的本地路径")
    details: Optional[dict] = Field(None, description="额外的详细信息")


class DownloadTaskResponse(BaseModel):
    """下载任务启动响应模型"""
    success: bool = Field(..., description="任务启动是否成功")
    task_id: str = Field(..., description="任务唯一ID")
    message: str = Field(..., description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "task_id": "abc123-def456-ghi789",
                "message": "下载任务已启动"
            }
        }


class DownloadProgressResponse(BaseModel):
    """下载进度响应模型"""
    status: str = Field(..., description="下载状态: starting/downloading/completed/failed/not_found")
    percentage: float = Field(0, description="下载百分比 (0-100)")
    current_str: Optional[str] = Field(None, description="已下载大小（字符串格式，如 '1.2GB'）")
    total_str: Optional[str] = Field(None, description="总大小（字符串格式，如 '2.4GB'）")
    message: str = Field(..., description="状态描述信息")
    error: Optional[str] = Field(None, description="错误信息（仅在 failed 状态时有值）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "downloading",
                "percentage": 45.6,
                "current_str": "1.2GB",
                "total_str": "2.4GB",
                "message": "下载中: 1.2GB/2.4GB"
            }
        }


# ========== 分片上传相关数据模型 ==========

class ChunkUploadInitRequest(BaseModel):
    """分片上传初始化请求"""
    filename: str = Field(..., description="文件名（必须是 .gguf 格式）")
    file_size: int = Field(..., description="文件总大小（字节）", gt=0)
    total_chunks: int = Field(..., description="总分片数", gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "llama-3-8b-instruct-q4.gguf",
                "file_size": 5368709120,
                "total_chunks": 512
            }
        }


class ChunkUploadInitResponse(BaseModel):
    """分片上传初始化响应"""
    success: bool = Field(..., description="是否成功")
    task_id: Optional[str] = Field(None, description="上传任务唯一标识")
    uploaded_chunks: List[int] = Field(default_factory=list, description="已上传的分片索引列表（用于断点续传）")
    message: str = Field(..., description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "uploaded_chunks": [0, 1, 2, 5, 8],
                "message": "继续之前的上传，已完成 5/512 个分片"
            }
        }


class ChunkUploadProgressResponse(BaseModel):
    """分片上传进度响应"""
    success: bool = Field(..., description="是否成功")
    status: str = Field(..., description="上传状态: uploading/completed/failed/not_found")
    progress: float = Field(0, description="上传进度百分比 (0-100)")
    uploaded_chunks: int = Field(0, description="已上传的分片数量")
    total_chunks: int = Field(0, description="总分片数")
    filename: Optional[str] = Field(None, description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    message: str = Field(..., description="状态描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status": "uploading",
                "progress": 65.4,
                "uploaded_chunks": 335,
                "total_chunks": 512,
                "filename": "llama-3-8b-instruct-q4.gguf",
                "file_size": 5368709120,
                "message": "进度: 335/512"
            }
        }


class ChunkUploadCompleteResponse(BaseModel):
    """分片上传完成响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    model_path: Optional[str] = Field(None, description="合并后的模型文件路径")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "文件合并成功",
                "model_path": "/home/user/AiEdge/models/llama-3-8b-instruct-q4.gguf"
            }
        }

