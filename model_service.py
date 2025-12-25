"""
模型推理服务 - 子服务启动脚本
加载所有模型并提供原生 llama.cpp API
"""

import uvicorn
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ServerSettings
from core.config import config
from core.model_loader import create_model_settings_from_list


if __name__ == "__main__":
    # 读取并创建所有模型配置
    model_settings = create_model_settings_from_list()
    
    if not model_settings:
        print("❌ 没有可用的模型，请先通过主服务下载模型")
        print(f"📖 主服务地址: http://{config.MAIN_SERVER_HOST}:{config.MAIN_SERVER_PORT}")
        print("   使用 POST /models/download 接口下载模型")
        exit(1)
    
    # 配置子服务设置
    server_settings = ServerSettings(
        host=config.MODEL_SERVER_HOST,
        port=config.MODEL_SERVER_PORT,
        api_key=None,
        interrupt_requests=True,
    )
    
    # 创建原生 llama.cpp 应用（不添加任何自定义路由）
    app = create_app(
        server_settings=server_settings,
        model_settings=model_settings,
    )
    
    # 打印启动信息
    print(f"🚀 启动模型推理服务...")
    print(f"📍 地址: http://{server_settings.host}:{server_settings.port}")
    print(f"📚 已加载 {len(model_settings)} 个模型:")
    for model in model_settings:
        print(f"   - {model.model_alias}: {model.model}")
    print(f"📖 API文档: http://{server_settings.host}:{server_settings.port}/docs")
    
    # 启动服务
    uvicorn.run(
        app,
        host=server_settings.host,
        port=server_settings.port,
        log_level="info"
    )
