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
