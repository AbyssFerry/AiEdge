"""
AiEdge LLM Server - 项目启动入口
使用 uvicorn 启动 FastAPI 服务，支持多模型同时加载
"""

import gc
import gc
import uvicorn
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ServerSettings
from core.config import config
from core.model_loader import create_model_settings_from_list


if __name__ == "__main__":
    # 读取模型配置
    model_settings = create_model_settings_from_list()
    
    if not model_settings:
        print("❌ 没有可用的模型，请先下载模型")
        print(f"📖 API文档: http://{config.SERVER_HOST}:{config.SERVER_PORT}/docs")
        print("   使用 /models/download 接口下载模型")
        print("   或运行 uv run ./test.py 来下载模型")
        
        # 即使没有模型也启动服务器，以便可以通过API下载模型
        from api.app import app
        uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)
    else:
        # 配置服务器设置
        server_settings = ServerSettings(
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            api_key=None,
            interrupt_requests=True,
        )
        
        # 创建支持多模型的FastAPI应用
        app = create_app(
            server_settings=server_settings,
            model_settings=model_settings,
        )
        
        # 打印启动信息
        print(f"🚀 启动多模型服务器...")
        print(f"📍 地址: http://{server_settings.host}:{server_settings.port}")
        print(f"📚 已加载 {len(model_settings)} 个模型:")
        for model in model_settings:
            print(f"   - {model.model_alias}: {model.model}")
        print(f"📖 API文档: http://{server_settings.host}:{server_settings.port}/docs")
        
        # 启动服务器，使用 try-finally 确保资源释放
        try:
            uvicorn.run(
                app,
                host=server_settings.host,
                port=server_settings.port,
            )
        finally:
            print("🛑 服务关闭，正在释放资源...")
            # 强制垃圾回收，释放 Python 对象内存
            gc.collect()
            
            # 释放 llama.cpp 资源（无需依赖 torch）
            try:
                # 优先关闭由 llama-cpp-python server 持有的当前模型
                from llama_cpp.server import app as llama_server_app  # type: ignore
                if hasattr(llama_server_app, "_llama_proxy") and getattr(llama_server_app, "_llama_proxy"):
                    try:
                        proxy = llama_server_app._llama_proxy
                        if hasattr(proxy, "close"):
                            proxy.close()
                        elif hasattr(proxy, "__del__"):
                            del llama_server_app._llama_proxy
                        print("✅ llama.cpp 当前模型已关闭")
                    except Exception as e:
                        print(f"⚠️ 关闭 llama.cpp 模型时出错: {e}")

                # 调用后端释放函数，归还底层资源（CUDA/BLAS/Metal 等）
                import llama_cpp
                try:
                    llama_cpp.llama_backend_free()
                    print("✅ llama.cpp 后端已释放")
                except Exception as e:
                    print(f"⚠️ 释放 llama.cpp 后端失败: {e}")
            except Exception as e:
                # 即使无法导入或调用，也不影响服务优雅退出
                print(f"⚠️ llama.cpp 清理过程出现异常: {e}")
            
            print("✅ 资源释放完成")