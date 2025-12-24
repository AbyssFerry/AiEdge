# AiEdge - 边缘 AI 模型服务器

一个轻量级的边缘 AI 模型服务器，支持多模型并发运行，基于 llama-cpp-python。

## 📁 项目结构

```
AiEdge/
├── main.py                 # 服务器启动入口
├── test.py                 # 模型下载测试工具
├── test_chat.py            # 聊天功能测试工具
├── .env                    # 环境配置文件
├── requirements.txt        # 依赖包
├── core/                   # 核心模块
│   ├── config.py           # 配置管理
│   └── model_loader.py     # 模型加载逻辑
├── api/                    # API 路由
│   ├── app.py              # FastAPI 应用
│   ├── models/             # 数据模型
│   └── routes/             # 路由处理
├── data/                   # 数据目录
│   └── models.txt          # 已下载模型记录
└── models/                 # 模型文件存储
```

## 🚀 快速开始

### 1. 配置环境变量

编辑 `.env` 文件：

```env
# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=23058

# GPU配置
N_GPU_LAYERS=-1  # -1表示全部使用GPU

# 模型下载配置（格式: repo_id|filename，多个模型用逗号分隔）
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf
```

### 2. 下载模型

使用测试工具下载模型：

```bash
uv run ./test.py
```

选项：
- `[config]` - 下载 .env 中配置的所有模型
- `[all]` - 下载所有可用模型
- `[1-N]` - 下载指定编号的模型

### 3. 启动服务器

```bash
uv run ./main.py
```

服务器会自动加载 `data/models.txt` 中记录的所有已下载模型。

### 4. 测试聊天功能

```bash
uv run ./test_chat.py
```

## 📖 API 文档

启动服务器后访问: http://0.0.0.0:23058/docs

### 主要接口

- `GET /v1/models` - 列出可用模型
- `POST /v1/chat/completions` - 聊天补全
- `POST /models/download` - 下载模型
- `DELETE /models/delete` - 删除模型
- `GET /models/list` - 列出已下载模型

## 🔧 配置说明

### .env 配置项

| 配置项               | 说明              | 默认值    |
| -------------------- | ----------------- | --------- |
| `SERVER_HOST`        | 服务器监听地址    | `0.0.0.0` |
| `SERVER_PORT`        | 服务器端口        | `23058`   |
| `N_GPU_LAYERS`       | GPU层数 (-1=全部) | `-1`      |
| `MODELS_TO_DOWNLOAD` | 要下载的模型列表  | -         |

### 模型配置格式

```env
# 单个模型
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf

# 多个模型（用逗号分隔）
MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf,unsloth/Qwen2.5-VL-3B-Instruct-GGUF|Qwen2.5-VL-3B-Instruct-UD-Q8_K_XL.gguf
```

## 📦 依赖管理

```bash
# 安装依赖
pip install -r requirements.txt

# 更新依赖
pip freeze > requirements.txt
```

## 📝 注意事项

1. **模型存储**: 所有模型存储在项目的 `models/` 目录下
2. **GPU 支持**: 需要支持 CUDA 的显卡才能启用 GPU 加速
3. **内存需求**: 确保有足够内存加载多个模型

---

Made with ❤️ by AiEdge Team