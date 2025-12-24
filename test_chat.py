"""
聊天功能测试文件 - 仅交互式对话（流式返回）
"""

import requests
import json
from core.config import config

# API 基础 URL（从配置读取）
BASE_URL = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"


def print_response(response, title="响应"):
    """格式化打印响应"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"{'='*60}\n")


def list_available_models():
    """列出可用的模型"""
    try:
        response = requests.get(f"{BASE_URL}/v1/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            return models
        return []
    except Exception as e:
        print(f"❌ 获取模型列表失败: {str(e)}")
        return []


def test_chat_completion(model_id: str):
    """与指定模型进行交互式对话（流式返回）。"""
    print(f"\n💬 与模型 '{model_id}' 对话")
    print("提示: 输入 'quit' 或 'exit' 退出对话\n")

    # 对话历史
    conversation_history = []

    while True:
        user_input = input("你: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 结束对话")
            break

        if not user_input:
            continue

        # 追加用户消息
        conversation_history.append({"role": "user", "content": user_input})

        # 构建请求（开启流式）
        payload = {
            "model": model_id,
            "messages": conversation_history,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,
        }

        print("\n🤖 模型: ", end="", flush=True)

        assistant_message = ""
        try:
            with requests.post(
                f"{BASE_URL}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=120,
            ) as response:
                if response.status_code != 200:
                    print(f"\n❌ 请求失败: {response.status_code}")
                    try:
                        print(response.text)
                    except Exception:
                        pass
                    print()
                    continue

                # 逐行读取 SSE/NDJSON 数据
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith("data: "):
                        line = line[6:].strip()

                    if line == "[DONE]":
                        break

                    # 解析块
                    try:
                        data = json.loads(line)
                    except Exception:
                        # 非 JSON 块，忽略
                        continue

                    choices = data.get("choices") or []
                    if not choices:
                        continue

                    chunk = choices[0]
                    delta = chunk.get("delta") or {}
                    # OpenAI 风格：delta.content
                    content = delta.get("content")
                    # 某些实现可能直接给 text
                    if content is None:
                        content = chunk.get("text")

                    if content:
                        print(content, end="", flush=True)
                        assistant_message += content

        except requests.exceptions.Timeout:
            print("\n❌ 请求超时")
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")

        # 结束当前回答并入历史
        if assistant_message:
            conversation_history.append({"role": "assistant", "content": assistant_message})
        print("\n")


# 移除简单补全测试，专注交互式对话（流式）


def main():
    print("\n" + "="*60)
    print("🚀 AiEdge 聊天功能测试")
    print("="*60)

    while True:
        # 每次返回菜单时重新拉取模型列表
        print("\n📋 正在获取可用模型...")
        models = list_available_models()

        if not models:
            print("❌ 没有可用的模型")
            print("请先运行服务器并确保已下载模型")
            return

        print(f"\n✅ 找到 {len(models)} 个可用模型:")
        for i, model in enumerate(models, 1):
            print(f"  [{i}] {model['id']}")

        # 选择模型并直接进入对话；支持 q 退出
        print("\n" + "="*60)
        choice = input(f"选择模型 (1-{len(models)}，或 q 退出): ").strip()

        if choice.lower() in ["q", "quit", "exit"]:
            break

        if not choice.isdigit() or not (1 <= int(choice) <= len(models)):
            print("❌ 无效选择")
            continue

        selected_model = models[int(choice) - 1]["id"]
        print(f"\n✅ 已选择模型: {selected_model}")

        # 直接进入交互式对话（流式）；对话结束后返回选择菜单
        test_chat_completion(selected_model)

    print("\n" + "="*60)
    print("👋 已退出，测试结束")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到服务器 {BASE_URL}")
        print("请确保 API 服务器正在运行 (运行 uv run ./main.py)")
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
