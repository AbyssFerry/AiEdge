"""
系统信息路由
提供硬盘、内存和 GPU 显存使用情况查询
"""

from fastapi import APIRouter, HTTPException
from api.models.system_info_models import DiskUsageResponse, MemoryUsageResponse
import psutil
from typing import Optional

router = APIRouter(
    prefix="/system",
    tags=["系统信息"]
)


def get_gpu_info() -> Optional[dict]:
    """
    获取 GPU 信息（针对 Jetson 设备）
    
    Returns:
        dict: GPU 信息字典，如果获取失败返回 None
    """
    try:
        from jtop import jtop
        
        with jtop() as jetson:
            if jetson.ok():
                gpu_info = {
                    "gpu_type": jetson.board.get("hardware", {}).get("Model", "Unknown"),
                    "shared_memory": True,
                    "gpu_usage_percent": jetson.stats.get("GPU", 0),
                    "total_memory_gb": round(jetson.memory.get("RAM", {}).get("tot", 0) / 1024, 2),
                    "used_memory_gb": round(jetson.memory.get("RAM", {}).get("used", 0) / 1024, 2),
                    "cuda_cores": jetson.board.get("hardware", {}).get("GPU", {}).get("CUDA Cores", "Unknown"),
                    "cuda_version": jetson.board.get("libraries", {}).get("CUDA", "Unknown"),
                }
                return gpu_info
    except ImportError:
        # jtop 不可用，可能不是 Jetson 设备
        pass
    except Exception as e:
        # 其他错误，记录但不中断
        print(f"获取 GPU 信息失败: {str(e)}")
    
    return None


@router.get(
    "/disk",
    response_model=DiskUsageResponse,
    summary="查询硬盘使用情况",
    description="查询系统根目录的硬盘使用情况，包括总容量、已使用、可用空间和使用百分比",
    responses={
        200: {"description": "成功返回硬盘使用情况"},
        500: {"description": "服务器内部错误"}
    }
)
async def get_disk_usage():
    """
    获取硬盘使用情况
    
    Returns:
        DiskUsageResponse: 包含硬盘使用详细信息的响应
    """
    try:
        # 获取根目录硬盘使用情况
        disk = psutil.disk_usage('/')
        
        return DiskUsageResponse(
            success=True,
            total=disk.total,
            used=disk.used,
            free=disk.free,
            percent=disk.percent,
            total_gb=round(disk.total / (1024**3), 2),
            used_gb=round(disk.used / (1024**3), 2),
            free_gb=round(disk.free / (1024**3), 2)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取硬盘信息失败: {str(e)}"
        )


@router.get(
    "/memory",
    response_model=MemoryUsageResponse,
    summary="查询内存使用情况",
    description="查询系统内存使用情况，包括总内存、可用内存、已使用内存和 GPU 显存信息（Jetson 设备内存与显存共享）",
    responses={
        200: {"description": "成功返回内存使用情况"},
        500: {"description": "服务器内部错误"}
    }
)
async def get_memory_usage():
    """
    获取内存使用情况（包含 GPU 显存信息）
    
    对于 Jetson 设备，内存和显存是共享的
    
    Returns:
        MemoryUsageResponse: 包含内存和 GPU 显存详细信息的响应
    """
    try:
        # 获取系统内存信息
        memory = psutil.virtual_memory()
        
        # 尝试获取 GPU 信息
        gpu_info = get_gpu_info()
        
        return MemoryUsageResponse(
            success=True,
            total=memory.total,
            available=memory.available,
            used=memory.used,
            percent=round(memory.percent, 1),
            total_gb=round(memory.total / (1024**3), 2),
            available_gb=round(memory.available / (1024**3), 2),
            used_gb=round(memory.used / (1024**3), 2),
            gpu_memory_shared=True,
            gpu_info=gpu_info
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取内存信息失败: {str(e)}"
        )
