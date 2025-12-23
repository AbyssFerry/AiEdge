from llama_cpp.server.app import create_app
from llama_cpp.server.settings import ServerSettings, ModelSettings
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import config
from api import router

# 配置服务器和模型
server_settings = ServerSettings(host=config.SERVER_HOST, port=config.SERVER_PORT)
model_settings = ModelSettings(model=config.model_path, n_gpu_layers=config.N_GPU_LAYERS)

# 创建应用
app = create_app(server_settings=server_settings, model_settings=[model_settings])

# 配置CORS，允许浏览器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 引入自定义API路由
app.include_router(router)

if __name__ == "__main__":
    print(f"🚀 启动服务器: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"📊 健康检查: http://{config.SERVER_HOST}:{config.SERVER_PORT}/health")
    print(f"📖 API文档: http://{config.SERVER_HOST}:{config.SERVER_PORT}/docs")
    print(f"📦 模型路径: {config.model_path}")
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)