"""
主服务应用 - 管理服务
提供模型下载、删除和子服务控制接口
不加载模型，仅作为管理层
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import config
from api.routes import router
from api.service_manager import service_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理应用生命周期
    启动时执行初始化，关闭时清理资源
    """
    # 启动时
    print("🚀 主服务启动")
    
    yield
    
    # 关闭时 - 自动停止子服务
    print("\n🛑 主服务关闭中...")
    if service_manager.is_running():
        print("📌 正在停止子服务...")
        result = service_manager.stop()
        if result["success"]:
            print("✅ 子服务已停止")
        else:
            print(f"⚠️  停止子服务时出现问题: {result['message']}")
    print("✅ 主服务已关闭")


def create_application():
    """
    创建并配置主服务 FastAPI 应用
    """
    # 创建 FastAPI 应用，传入生命周期管理
    app = FastAPI(
        title="AiEdge LLM Management Server",
        description="主服务 - 提供模型管理和子服务控制",
        version="2.0.0",
        lifespan=lifespan
    )

    # 配置CORS，允许浏览器跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
        allow_credentials=True,
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有请求头
    )

    # 引入所有管理路由
    app.include_router(router)
    
    return app


# 创建应用实例
app = create_application()

