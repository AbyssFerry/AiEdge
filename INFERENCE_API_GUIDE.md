# AiEdge 推理服务 API 指南

> 推理服务运行在端口 23059，提供 AI 对话能力

## 📖 快速说明

- **服务地址**: `http://localhost:23059`
- **核心接口**: `/v1/chat/completions` (POST)
- **模型列表**: `/v1/models` (GET)
- **前置条件**: 必须先通过管理服务（23058）启动

⚠️ 启动命令：`POST http://localhost:23058/service/start`

## 💬 对话接口

### 请求示例

```bash
POST http://localhost:23059/v1/chat/completions
Content-Type: application/json
```

```json
{
  "messages": [
    { "role": "user", "content": "你好" }
  ],
  "temperature": 0.7,
  "max_tokens": 2000,
  "stream": true
}
```

### 核心参数

| 参数          | 说明                 | 默认值     |
| ------------- | -------------------- | ---------- |
| `messages`    | 对话消息列表（必填） | -          |
| `model`       | 模型名称             | 第一个模型 |
| `stream`      | 是否流式输出         | false      |
| `temperature` | 随机度 (0-2)         | 0.8        |
| `max_tokens`  | 最大token数          | 2048       |

### 流式响应格式

```
data: {"choices":[{"delta":{"content":"你"}}]}
data: {"choices":[{"delta":{"content":"好"}}]}
data: [DONE]
```

## 🛠️ JavaScript 流式对话示例

```javascript
async function chatStream(message, onChunk) {
  const response = await fetch('http://localhost:23059/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: "user", content: message }],
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed === 'data: [DONE]') continue;

      const jsonStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed;
      try {
        const data = JSON.parse(jsonStr);
        const content = data.choices?.[0]?.delta?.content;
        if (content) onChunk(content);
      } catch (e) {}
    }
  }
}

// 使用
await chatStream("你好", (chunk) => process.stdout.write(chunk));
```

## 🧪 Python 测试代码（test.py）

### 1. 检查服务连接

```python
import requests

MODEL_URL = "http://localhost:23059"

def test_model_service_health():
    """测试子服务连接"""
    try:
        response = requests.get(f"{MODEL_URL}/v1/models", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"✅ 子服务运行正常")
            print(f"📚 已加载 {len(models)} 个模型:")
            for model in models:
                print(f"   - {model['id']}")
            return True
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 子服务未运行，请先通过管理服务启动")
        return False
```

### 2. 流式对话测试（完整）

```python
import json
import requests

def test_chat_completion():
    """流式聊天测试"""
    # 获取模型列表
    response = requests.get(f"{MODEL_URL}/v1/models")
    models = response.json().get("data", [])
    
    print(f"可用模型: {[m['id'] for m in models]}")
    selected_model = models[0]["id"]
    
    # 对话循环
    conversation_history = []
    
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() == 'q':
            break
        
        conversation_history.append({"role": "user", "content": user_input})
        
        payload = {
            "model": selected_model,
            "messages": conversation_history,
            "stream": True,
        }
        
        print("🤖 AI: ", end="", flush=True)
        assistant_message = ""
        
        with requests.post(
            f"{MODEL_URL}/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=120,
        ) as response:
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                
                line = raw_line.strip()
                if line.startswith("data: "):
                    line = line[6:].strip()
                
                if line == "[DONE]":
                    break
                
                try:
                    data = json.loads(line)
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        print(content, end="", flush=True)
                        assistant_message += content
                except:
                    continue
        
        conversation_history.append({"role": "assistant", "content": assistant_message})
        print()
```

### 3. Python 客户端封装

```python
class AiEdgeInferenceClient:
    def __init__(self, base_url: str = "http://localhost:23059"):
        self.base_url = base_url
    
    def chat_stream(self, messages, on_chunk):
        """流式聊天"""
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"messages": messages, "stream": True},
            stream=True
        )
        
        full_content = ""
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            
            line = raw_line.strip()
            if line.startswith("data: "):
                line = line[6:]
            if line == "[DONE]":
                break
            
            try:
                data = json.loads(line)
                content = data["choices"][0]["delta"].get("content")
                if content:
                    full_content += content
                    on_chunk(content)
            except:
                pass
        
        return full_content

# 使用
client = AiEdgeInferenceClient()
client.chat_stream(
    [{"role": "user", "content": "你好"}],
    lambda chunk: print(chunk, end="", flush=True)
)
```

---

完整测试代码请查看项目中的 `test.py` 文件。
