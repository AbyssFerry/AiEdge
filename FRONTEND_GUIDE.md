# AiEdge - 前端开发指南

> 本文档面向使用 AiEdge 服务的前端开发人员，配合 `openapi.json` 使用

## 📖 服务概述

AiEdge 是一个边缘 AI 模型服务平台，为前端应用提供本地大语言模型（LLM）的管理和推理能力。

**核心价值**：
- ✅ 本地部署，数据隐私有保障
- ✅ 支持多模型切换和并发加载
- ✅ 提供完整的模型生命周期管理
- ✅ 异步操作，不阻塞用户界面

## 🏗️ 服务架构

AiEdge 提供两个独立的服务端点：

### 管理服务 (默认端口: 23058)
用于管理模型和控制推理服务，这是前端主要交互的服务。

**主要功能**：
- 模型下载和删除
- 查看可用模型列表
- 启动/停止/重启推理服务
- 系统资源监控
- 文件上传

### 推理服务 (默认端口: 23059)
独立运行的 AI 推理服务，用于实际的 AI 对话交互。

**主要功能**：
- AI 对话接口（兼容 llama.cpp 标准）
- 模型状态查询
- 健康检查

> ⚠️ **重要**: 推理服务需要先通过管理服务启动才能使用

## 🚀 快速开始

### 1. 基本工作流程

```
1. 下载模型 → 2. 启动推理服务 → 3. 开始对话
```

### 2. 典型使用场景

#### 场景一：首次使用

```javascript
// 步骤1: 下载模型
const downloadResponse = await fetch('http://localhost:23058/models/download/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    repo_id: 'google/gemma-2-2b-it-GGUF',
    filename: 'gemma-2-2b-it-Q4_K_M.gguf'
  })
});
const { task_id } = await downloadResponse.json();

// 步骤2: 轮询下载进度
const checkProgress = setInterval(async () => {
  const progress = await fetch(`http://localhost:23058/models/download/status/${task_id}`);
  const data = await progress.json();
  
  if (data.status === 'completed') {
    clearInterval(checkProgress);
    // 步骤3: 启动推理服务
    await fetch('http://localhost:23058/service/start', { method: 'POST' });
  }
}, 1000);
```

#### 场景二：使用现有模型

```javascript
// 1. 获取可用模型列表
const models = await fetch('http://localhost:23058/models/list')
  .then(r => r.json());

// 2. 如果有模型，直接启动服务
if (models.models && models.models.length > 0) {
  await fetch('http://localhost:23058/service/start', { method: 'POST' });
}

// 3. 开始对话
const response = await fetch('http://localhost:23059/v1/chat/completions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: '你好！' }
    ]
  })
});
```

## 🔑 核心概念

### 1. 模型管理

**支持的模型格式**: GGUF (量化后的大语言模型)

**模型来源**: Hugging Face 模型仓库

**关键参数**:
- `repo_id`: Hugging Face 仓库ID（如 `google/gemma-2-2b-it-GGUF`）
- `filename`: 具体的模型文件名（如 `gemma-2-2b-it-Q4_K_M.gguf`）

### 2. 异步下载机制

模型下载采用任务队列机制，避免阻塞：

1. 调用 `/models/download/start` 立即返回 `task_id`
2. 使用 `task_id` 查询 `/models/download/status/{task_id}` 获取进度
3. 下载状态：`pending` → `downloading` → `completed` / `failed`

**进度信息包含**:
- `percentage`: 下载百分比 (0-100)
- `downloaded_size`: 已下载大小（字节）
- `total_size`: 总大小（字节）
- `speed`: 下载速度（字节/秒）

### 3. 服务生命周期

```
[停止] → 启动 → [运行中] → 停止/重启 → [停止]
```

**服务状态**:
- `running`: 服务正在运行，可以进行推理
- `stopped`: 服务已停止，需要启动
- `starting`: 服务正在启动中
- `error`: 服务出错

### 4. 多模型支持

推理服务启动时会加载 `models/` 目录中的所有 GGUF 模型，可以在对话时指定使用哪个模型（通过 `model` 参数）。

## 💡 最佳实践

### 1. 用户体验优化

#### 下载进度展示
```javascript
async function downloadModelWithProgress(repo_id, filename, onProgress) {
  // 启动下载
  const { task_id } = await fetch('http://localhost:23058/models/download/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id, filename })
  }).then(r => r.json());

  // 轮询进度
  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      try {
        const status = await fetch(
          `http://localhost:23058/models/download/status/${task_id}`
        ).then(r => r.json());

        onProgress(status); // 回调更新 UI

        if (status.status === 'completed') {
          clearInterval(timer);
          resolve(status);
        } else if (status.status === 'failed') {
          clearInterval(timer);
          reject(new Error(status.error));
        }
      } catch (error) {
        clearInterval(timer);
        reject(error);
      }
    }, 1000);
  });
}

// 使用示例
await downloadModelWithProgress(
  'google/gemma-2-2b-it-GGUF',
  'gemma-2-2b-it-Q4_K_M.gguf',
  (status) => {
    console.log(`下载进度: ${status.percentage}%`);
    // 更新进度条
    updateProgressBar(status.percentage);
  }
);
```

#### 服务健康检查
```javascript
async function ensureServiceReady() {
  try {
    const status = await fetch('http://localhost:23058/service/status')
      .then(r => r.json());
    
    if (status.status !== 'running') {
      // 服务未运行，自动启动
      await fetch('http://localhost:23058/service/start', { method: 'POST' });
      
      // 等待服务就绪
      await waitForService();
    }
    
    return true;
  } catch (error) {
    console.error('服务检查失败:', error);
    return false;
  }
}

async function waitForService(maxAttempts = 30) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const health = await fetch('http://localhost:23059/health');
      if (health.ok) return true;
    } catch {}
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error('服务启动超时');
}
```

### 2. 错误处理

```javascript
async function safeApiCall(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '请求失败');
    }
    
    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError') {
      // 网络错误或服务不可用
      console.error('无法连接到服务器，请确保服务已启动');
    }
    throw error;
  }
}
```

### 3. 文件上传（大模型）

对于本地模型文件上传，使用分片上传机制：

```javascript
async function uploadLargeFile(file) {
  const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);
    
    const formData = new FormData();
    formData.append('file', chunk);
    formData.append('chunk_index', i);
    formData.append('total_chunks', totalChunks);
    formData.append('filename', file.name);
    
    await fetch('http://localhost:23058/upload/chunk', {
      method: 'POST',
      body: formData
    });
    
    // 更新上传进度
    updateUploadProgress((i + 1) / totalChunks * 100);
  }
}
```

### 4. 系统资源监控

```javascript
async function getSystemInfo() {
  const info = await fetch('http://localhost:23058/system/info')
    .then(r => r.json());
  
  return {
    disk: `${info.disk.used_gb.toFixed(2)} GB / ${info.disk.total_gb.toFixed(2)} GB`,
    memory: `${info.memory.used_gb.toFixed(2)} GB / ${info.memory.total_gb.toFixed(2)} GB`,
    gpu: info.gpu ? `${info.gpu.used_gb.toFixed(2)} GB / ${info.gpu.total_gb.toFixed(2)} GB` : '无',
  };
}

// 在下载前检查空间
async function checkSpaceBeforeDownload(estimatedSizeGB) {
  const info = await getSystemInfo();
  const availableGB = info.disk.total_gb - info.disk.used_gb;
  
  if (availableGB < estimatedSizeGB) {
    throw new Error(`磁盘空间不足，需要 ${estimatedSizeGB} GB，可用 ${availableGB.toFixed(2)} GB`);
  }
}
```

## ⚠️ 注意事项

### 1. 服务依赖关系
- 推理服务 **必须** 先启动管理服务才能使用
- 下载新模型后需要 **重启推理服务** 才能加载
- 删除模型前应先 **停止推理服务**

### 2. 性能考虑
- 模型文件通常较大（几百 MB 到几 GB），下载需要时间
- 首次加载模型到内存需要时间（根据模型大小，通常 10-30 秒）
- 推理速度取决于硬件性能（GPU > CPU）

### 3. 并发限制
- 同一时间只能有一个下载任务（后续任务会排队）
- 推理服务支持多个并发请求，但建议控制并发数

### 4. 错误恢复
```javascript
// 推荐的错误恢复策略
async function robustServiceStart() {
  try {
    await fetch('http://localhost:23058/service/start', { method: 'POST' });
  } catch (error) {
    // 如果启动失败，尝试先停止再启动
    try {
      await fetch('http://localhost:23058/service/stop', { method: 'POST' });
      await new Promise(r => setTimeout(r, 2000)); // 等待2秒
      await fetch('http://localhost:23058/service/start', { method: 'POST' });
    } catch (retryError) {
      console.error('服务启动失败:', retryError);
      throw retryError;
    }
  }
}
```

## 🔗 API 端点速查

详细的 API 定义请参考 `openapi.json` 文件，以下是常用端点：

### 管理服务 (23058)

| 功能         | 方法   | 端点                                |
| ------------ | ------ | ----------------------------------- |
| 下载模型     | POST   | `/models/download/start`            |
| 查询下载进度 | GET    | `/models/download/status/{task_id}` |
| 列出模型     | GET    | `/models/list`                      |
| 删除模型     | DELETE | `/models/delete`                    |
| 启动推理服务 | POST   | `/service/start`                    |
| 停止推理服务 | POST   | `/service/stop`                     |
| 重启推理服务 | POST   | `/service/restart`                  |
| 服务状态     | GET    | `/service/status`                   |
| 系统信息     | GET    | `/system/info`                      |
| 分片上传     | POST   | `/upload/chunk`                     |

### 推理服务 (23059)

| 功能     | 方法 | 端点                   |
| -------- | ---- | ---------------------- |
| 聊天对话 | POST | `/v1/chat/completions` |
| 模型列表 | GET  | `/v1/models`           |
| 健康检查 | GET  | `/health`              |

## 📱 示例应用流程

### 完整的聊天应用初始化流程

```javascript
class AiEdgeClient {
  constructor(managementUrl = 'http://localhost:23058', inferenceUrl = 'http://localhost:23059') {
    this.managementUrl = managementUrl;
    this.inferenceUrl = inferenceUrl;
  }

  // 初始化应用
  async initialize() {
    // 1. 检查是否有可用模型
    const models = await this.getModels();
    
    if (models.length === 0) {
      throw new Error('没有可用模型，请先下载模型');
    }

    // 2. 检查推理服务状态
    const status = await this.getServiceStatus();
    
    if (status.status !== 'running') {
      // 3. 启动推理服务
      await this.startService();
      await this.waitForServiceReady();
    }

    return { ready: true, models };
  }

  // 获取模型列表
  async getModels() {
    const response = await fetch(`${this.managementUrl}/models/list`);
    const data = await response.json();
    return data.models || [];
  }

  // 获取服务状态
  async getServiceStatus() {
    const response = await fetch(`${this.managementUrl}/service/status`);
    return await response.json();
  }

  // 启动服务
  async startService() {
    await fetch(`${this.managementUrl}/service/start`, { method: 'POST' });
  }

  // 等待服务就绪
  async waitForServiceReady(maxAttempts = 30) {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await fetch(`${this.inferenceUrl}/health`);
        if (response.ok) return true;
      } catch {}
      await new Promise(r => setTimeout(r, 1000));
    }
    throw new Error('服务启动超时');
  }

  // 发送聊天消息
  async chat(messages, options = {}) {
    const response = await fetch(`${this.inferenceUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        stream: options.stream || false,
        temperature: options.temperature || 0.7,
        max_tokens: options.maxTokens || 2048,
      })
    });

    if (options.stream) {
      return response.body; // 返回流
    }

    const data = await response.json();
    return data.choices[0].message.content;
  }

  // 下载模型
  async downloadModel(repoId, filename, onProgress) {
    const response = await fetch(`${this.managementUrl}/models/download/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId, filename })
    });

    const { task_id } = await response.json();

    return new Promise((resolve, reject) => {
      const timer = setInterval(async () => {
        try {
          const statusResponse = await fetch(
            `${this.managementUrl}/models/download/status/${task_id}`
          );
          const status = await statusResponse.json();

          if (onProgress) onProgress(status);

          if (status.status === 'completed') {
            clearInterval(timer);
            resolve(status);
          } else if (status.status === 'failed') {
            clearInterval(timer);
            reject(new Error(status.error));
          }
        } catch (error) {
          clearInterval(timer);
          reject(error);
        }
      }, 1000);
    });
  }
}

// 使用示例
const client = new AiEdgeClient();

// 初始化
try {
  await client.initialize();
  console.log('✅ AiEdge 已就绪');
} catch (error) {
  if (error.message.includes('没有可用模型')) {
    // 下载模型
    await client.downloadModel(
      'google/gemma-2-2b-it-GGUF',
      'gemma-2-2b-it-Q4_K_M.gguf',
      (progress) => console.log(`下载进度: ${progress.percentage}%`)
    );
    
    // 重新初始化
    await client.initialize();
  }
}

// 开始对话
const reply = await client.chat([
  { role: 'user', content: '你好，请介绍一下你自己' }
]);
console.log('AI回复:', reply);
```

## 🎯 总结

AiEdge 为前端应用提供了完整的本地 AI 能力，关键要点：

1. **两个服务端点**: 管理服务（23058）+ 推理服务（23059）
2. **异步操作**: 下载和启动都是异步的，需要轮询状态
3. **服务依赖**: 推理前必须先启动服务，下载后需重启服务
4. **资源敏感**: 注意磁盘空间和内存使用
5. **错误处理**: 实现完善的重试和恢复机制

配合 `openapi.json` 中的详细 API 定义，你可以快速构建功能完整的 AI 应用前端！
