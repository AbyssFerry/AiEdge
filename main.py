"""
AiEdge LLM Server - 主服务启动入口
启动管理服务，提供模型管理和子服务控制接口
"""

import uvicorn
from api.app import app
from core.config import config


if __name__ == "__main__":
    # 打印启动信息
    print("🚀 启动 AiEdge 主服务 (Management Server)...")
    print(f"📍 主服务地址: http://{config.MAIN_SERVER_HOST}:{config.MAIN_SERVER_PORT}")
    print(f"📍 子服务端口: {config.MODEL_SERVER_PORT}")
    print(f"📖 API文档: http://{config.MAIN_SERVER_HOST}:{config.MAIN_SERVER_PORT}/docs")
    print("")
    print("💡 使用说明:")
    print("   1. 访问 /docs 查看所有API接口")
    print("   2. 使用 /models/download/start 异步下载模型")
    print("   3. 使用 /service/start 启动模型推理服务")
    print("   4. 推理服务地址: http://{0}:{1}".format(config.MODEL_SERVER_HOST, config.MODEL_SERVER_PORT))
    print("")
    
    # 启动主服务
    uvicorn.run(
        app,
        host=config.MAIN_SERVER_HOST,
        port=config.MAIN_SERVER_PORT,
        log_level="info"
    )
