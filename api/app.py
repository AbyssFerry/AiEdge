"""
主服务应用 - 管理服务
提供模型下载、删除和子服务控制接口
不加载模型，仅作为管理层
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import config
from api.routes import router
from core.service_manager import service_manager
from core.upload_manager import upload_manager


async def cleanup_expired_uploads():
    """
    后台任务：定期清理过期的上传会话
    每小时执行一次
    """
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时执行一次
            print("\n🧹 执行定期清理任务...")
            upload_manager.cleanup_expired_sessions()
        except Exception as e:
            print(f"⚠️  清理任务出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理应用生命周期
    启动时执行初始化，关闭时清理资源
    """
    # 启动时
    print("🚀 主服务启动")
    
    # 启动后台清理任务
    cleanup_task = asyncio.create_task(cleanup_expired_uploads())
    
    yield
    
    # 关闭时 - 取消后台任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
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
        description="""
        ## AiEdge AI 边缘服务管理平台
        
        提供完整的本地大语言模型（LLM）管理和推理服务。
        
        ### 核心功能
        
        * 🤖 **模型管理**: 从 Hugging Face 下载、删除和管理 GGUF 格式模型
        * 🚀 **服务控制**: 启动/停止模型推理子服务，动态加载不同模型
        * 📁 **文件上传**: 支持大文件分块上传和断点续传
        * 💬 **智能对话**: 通过子服务提供 AI 对话能力
        
        ### 服务架构
        
        - **主服务** (端口 23058): 管理层，不加载模型，提供管理接口
        - **子服务** (端口 23059): 推理层，加载模型并提供对话接口
        
        ### 技术栈
        
        - FastAPI + llama-cpp-python
        - 支持 GGUF 量化模型
        - 异步文件上传和下载
        """,
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "模型管理",
                "description": "📦 模型下载、删除和查询。支持从 Hugging Face 下载 GGUF 格式的量化模型。"
            },
            {
                "name": "服务控制",
                "description": "🎮 控制模型推理子服务的启动、停止和状态查询。子服务负责加载模型并提供推理能力。"
            },
            {
                "name": "文件上传",
                "description": "📤 大文件分块上传功能，支持断点续传和进度查询。"
            }
        ],
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

