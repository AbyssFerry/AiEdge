"""
系统信息相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional


class DiskUsageResponse(BaseModel):
    """硬盘使用情况响应模型"""
    success: bool = Field(..., description="查询是否成功")
    total: int = Field(..., description="总硬盘容量（字节）")
    used: int = Field(..., description="已使用容量（字节）")
    free: int = Field(..., description="可用容量（字节）")
    percent: float = Field(..., description="使用百分比")
    total_gb: float = Field(..., description="总容量（GB）")
    used_gb: float = Field(..., description="已使用容量（GB）")
    free_gb: float = Field(..., description="可用容量（GB）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total": 500107862016,
                "used": 250053931008,
                "free": 250053931008,
                "percent": 50.0,
                "total_gb": 465.76,
                "used_gb": 232.88,
                "free_gb": 232.88
            }
        }


class MemoryUsageResponse(BaseModel):
    """内存使用情况响应模型（包含GPU共享内存信息）"""
    success: bool = Field(..., description="查询是否成功")
    
    # 系统总内存
    total: int = Field(..., description="系统总内存（字节）")
    available: int = Field(..., description="系统可用内存（字节）")
    used: int = Field(..., description="系统已使用内存（字节）")
    percent: float = Field(..., description="系统内存使用百分比")
    total_gb: float = Field(..., description="系统总内存（GB）")
    available_gb: float = Field(..., description="系统可用内存（GB）")
    used_gb: float = Field(..., description="系统已使用内存（GB）")
    
    # GPU内存（Jetson设备与系统共享）
    gpu_memory_shared: bool = Field(True, description="GPU与系统内存是否共享（Jetson设备为True）")
    gpu_info: Optional[dict] = Field(None, description="GPU内存详细信息（如果可用）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total": 34359738368,
                "available": 20401094656,
                "used": 13958643712,
                "percent": 40.6,
                "total_gb": 32.0,
                "available_gb": 19.0,
                "used_gb": 13.0,
                "gpu_memory_shared": True,
                "gpu_info": {
                    "type": "Jetson AGX Xavier",
                    "shared_memory": True,
                    "total_memory_gb": 32.0
                }
            }
        }
