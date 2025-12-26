# AiEdge - 边缘 AI 模型服务器

一个轻量级的边缘 AI 模型服务器，支持多模型并发运行，基于 llama-cpp-python。

## 🏗️ 架构设计

AiEdge 采用**主服务 + 子服务**的双层架构：

- **主服务 (Management Server)** - 端口 23058
  - 模型管理（下载、删除、列表）
  - 子服务控制（启动、停止、重启）
  - 健康检查和状态查询
  
- **子服务 (Model Service)** - 端口 23059
  - 独立进程运行
  - 加载所有模型并提供推理服务
  - 原生 llama.cpp API
  - 支持热重启（下载新模型后重启即可加载）

## �� 项目结构

```
AiEdge/
├── main.py                      # 主服务启动入口
├── model_service.py             # 子服务启动脚本（独立进程）
├── test_chat.py                 # 聊天功能测试工具
├── test_download.py             # 模型下载测试工具
├── .env                         # 环境配置文件
├── requirements.txt             # 依赖包
├── core/                        # 核心模块
│   ├── config.py                # 配置管理
│   └── model_loader.py          # 模型加载逻辑
├── api/                         # API 路由
│   ├── app.py                   # 主服务应用
│   ├── service_manager.py       # 子进程管理器
│   ├── models/                  # 数据模型
│   └── routes/                  # 路由处理
│       ├── model_manager.py     # 模型管理路由
│       └── service_control.py   # 子服务控制路由
├── data/                        # 数据目录
│   └── models.txt               # 已下载模型记录
└── models/                      # 模型文件存储
```

## 🚀 快速开始

### 1. 配置环境变量

编辑 `.env` 文件：

```env
# 主服务配置（管理服务）
MAIN_SERVER_HOST=0.0.0.0
MAIN_SERVER_PORT=23058

# 子服务配置（模型推理服务）
MODEL_SERVER_HOST=0.0.0.0
MODEL_SERVER_PORT=23059

# GPU配置
N_GPU_LAYERS=-1  # -1表示全部使用GPU

# 模型下载配置（格式: repo_id|filename，多个模型用逗号分隔）
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf
```

### 2. 启动主服务

```bash
python main.py
# 或
uv run ./main.py
```

主服务启动后访问: http://localhost:23058/docs

### 3. 下载模型

通过主服务 API 异步下载模型：

```bash
# 启动下载任务
curl -X POST http://localhost:23058/models/download/start \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "google/gemma-2-2b-it-GGUF",
    "filename": "gemma-3-1b-it-f16.gguf"
  }'

# 查询下载进度（使用返回的task_id）
curl http://localhost:23058/models/download/status/{task_id}
```

或使用测试工具：

```bash
uv run ./test_download.py
```

### 4. 启动子服务（加载所有模型）

```bash
curl -X POST http://localhost:23058/service/start
```

返回示例：
```json
{
  "success": true,
  "message": "子服务启动成功",
  "port": 23059,
  "models": ["gemma-3-1b-it-f16.gguf", "Qwen2.5-VL-3B-Instruct-UD-Q8_K_XL.gguf"]
}
```

### 5. 使用推理服务

直接向子服务发送请求：

```bash
curl -X POST http://localhost:23059/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-3-1b-it-f16.gguf",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

或使用测试工具：

```bash
uv run ./test_chat.py
```

### 6. 下载新模型后重启子服务

```bash
# 1. 下载新模型
curl -X POST http://localhost:23058/models/download ...

# 2. 重启子服务加载新模型
curl -X POST http://localhost:23058/service/restart
```

## 📖 API 文档

### 主服务接口 (端口 23058)

#### 模型管理

- `POST /models/download/start` - 异步下载模型
  ```json
  {
    "repo_id": "google/gemma-2-2b-it-GGUF",
    "filename": "gemma-3-1b-it-f16.gguf"
  }
  ```

- `GET /models/download/status/{task_id}` - 查询下载进度

- `DELETE /models/delete` - 删除模型
  ```json
  {
    "model_name": "gemma-3-1b-it-f16.gguf"
  }
  ```

- `GET /models/list` - 列出已下载模型

#### 子服务控制

- `POST /service/start` - 启动子服务（加载所有模型）
- `POST /service/stop` - 停止子服务
- `POST /service/restart` - 重启子服务（用于加载新下载的模型）
- `GET /service/status` - 查看子服务状态

#### 其他

- `GET /health` - 健康检查
- `GET /` - 服务信息

### 子服务接口 (端口 23059)

子服务提供原生 llama.cpp API，参考: http://localhost:23059/docs

主要接口：
- `GET /v1/models` - 列出可用模型
- `POST /v1/chat/completions` - 聊天补全（支持流式）
- `POST /v1/completions` - 文本补全
- `POST /v1/embeddings` - 生成嵌入向量

## 🔧 配置说明

### .env 配置项

| 配置项               | 说明               | 默认值    |
| -------------------- | ------------------ | --------- |
| `MAIN_SERVER_HOST`   | 主服务监听地址     | `0.0.0.0` |
| `MAIN_SERVER_PORT`   | 主服务端口         | `23058`   |
| `MODEL_SERVER_HOST`  | 子服务监听地址     | `0.0.0.0` |
| `MODEL_SERVER_PORT`  | 子服务端口         | `23059`   |
| `N_GPU_LAYERS`       | GPU 层数 (-1=全部) | `-1`      |
| `MODELS_TO_DOWNLOAD` | 要下载的模型列表   | -         |

### 模型配置格式

```env
# 单个模型
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf

# 多个模型（用逗号分隔）
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf,unsloth/Qwen2.5-VL-3B-Instruct-GGUF|Qwen2.5-VL-3B-Instruct-UD-Q8_K_XL.gguf
```

## 💡 使用场景

### 场景 1: 初次部署

```bash
# 1. 启动主服务
python main.py

# 2. 下载模型
curl -X POST http://localhost:23058/models/download/start -d '{...}'

# 3. 启动子服务
curl -X POST http://localhost:23058/service/start

# 4. 使用推理服务
curl http://localhost:23059/v1/chat/completions -d '{...}'
```

### 场景 2: 添加新模型

```bash
# 1. 下载新模型（主服务继续运行）
curl -X POST http://localhost:23058/models/download/start -d '{...}'

# 2. 重启子服务加载新模型
curl -X POST http://localhost:23058/service/restart

# 3. 新模型立即可用
```

### 场景 3: 资源管理

```bash
# 停止子服务释放显存
curl -X POST http://localhost:23058/service/stop

# 删除不需要的模型
curl -X DELETE http://localhost:23058/models/delete -d '{"model_name": "..."}'

# 重新启动子服务
curl -X POST http://localhost:23058/service/start
```

## 📝 注意事项

1. **端口占用**: 确保 23058 和 23059 端口未被占用
2. **模型存储**: 所有模型存储在项目的 `models/` 目录下
3. **GPU 支持**: 需要支持 CUDA 的显卡才能启用 GPU 加速
4. **内存需求**: 确保有足够内存和显存加载多个模型
5. **资源释放**: 停止子服务会优雅释放显存和内存
6. **热更新**: 下载新模型后需要重启子服务才能加载

## 🔍 故障排查

### 子服务启动失败
- 检查是否有可用模型：`curl http://localhost:23058/models/list`
- 查看子服务状态：`curl http://localhost:23058/service/status`
- 检查端口占用：`lsof -i:23059`

### 模型加载失败
- 确认模型文件完整下载
- 检查显存是否足够
- 查看 `data/models.txt` 是否正确记录

## 📦 依赖管理

```bash
# 安装依赖
pip install -r requirements.txt

# 或使用 uv
uv pip install -r requirements.txt
```

---

Made with ❤️ by AiEdge Team
