"""
AiEdge 综合测试工具
提供交互式命令行界面测试所有功能
"""

import requests
import json
from core.config import config

# API 基础 URL
MAIN_URL = f"http://{config.MAIN_SERVER_HOST}:{config.MAIN_SERVER_PORT}"
MODEL_URL = f"http://{config.MODEL_SERVER_HOST}:{config.MODEL_SERVER_PORT}"


def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


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


# ============================================
# 主服务测试 (端口 23058)
# ============================================

def test_main_server_health():
    """测试主服务健康检查"""
    print_header("主服务健康检查")
    try:
        response = requests.get(f"{MAIN_URL}/health", timeout=5)
        print_response(response, "主服务状态")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 主服务连接失败: {str(e)}")
        return False


def test_download_model():
    """下载模型 - 从 .env 配置读取"""
    print_header("下载模型")
    
    models_from_config = config.MODELS_TO_DOWNLOAD
    
    if not models_from_config:
        print("⚠️  .env 文件中没有配置 MODELS_TO_DOWNLOAD")
        print("\n请在 .env 文件中添加要下载的模型")
        return False
    
    print(f"\n📦 .env 配置的模型:")
    for i, model in enumerate(models_from_config, 1):
        print(f"  [{i}] {model['filename']}")
        print(f"      仓库: {model['repo_id']}")
    
    print("\n选项:")
    print("  [all]    - 下载所有配置的模型")
    print(f"  [1-{len(models_from_config)}] - 下载指定的单个模型")
    print("  [q]      - 返回")
    
    choice = input("\n输入选择: ").strip().lower()
    
    if choice == 'q':
        return True
    
    models_to_download = []
    if choice == "all":
        models_to_download = models_from_config
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(models_from_config):
            models_to_download = [models_from_config[idx]]
        else:
            print("❌ 无效选择")
            return False
    else:
        print("❌ 无效选择")
        return False
    
    # 下载选中的模型
    for model_info in models_to_download:
        print(f"\n{'='*60}")
        print(f"⏳ 正在下载: {model_info['filename']}")
        print(f"{'='*60}")
        
        payload = {
            "repo_id": model_info["repo_id"],
            "filename": model_info["filename"]
        }
        
        print("⏳ 下载中，这可能需要较长时间，请耐心等待...")
        
        try:
            response = requests.post(
                f"{MAIN_URL}/models/download",
                json=payload,
                timeout=3600
            )
            
            print_response(response, f"下载结果 - {model_info['filename']}")
            
            if response.status_code == 200:
                print(f"✅ 下载成功！")
            else:
                print(f"❌ 下载失败")
                return False
                
        except Exception as e:
            print(f"❌ 下载出错: {str(e)}")
            return False
    
    return True


def test_list_models():
    """列出已下载的模型"""
    print_header("已下载的模型列表")
    
    try:
        response = requests.get(f"{MAIN_URL}/models/list")
        print_response(response, "模型列表")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 获取模型列表失败: {str(e)}")
        return False


def test_delete_model():
    """删除模型"""
    print_header("删除模型")
    
    try:
        list_response = requests.get(f"{MAIN_URL}/models/list")
        if list_response.status_code != 200:
            print("❌ 获取模型列表失败")
            return False
        
        data = list_response.json()
        files = data.get("files", [])
        
        if not files:
            print("⚠️  没有可删除的模型文件")
            return True
        
        print("\n已下载的模型:")
        for i, file_info in enumerate(files, 1):
            size_mb = file_info['size'] / (1024 * 1024) if file_info['size'] else 0
            print(f"  [{i}] {file_info['name']} ({size_mb:.2f} MB)")
        
        choice = input(f"\n选择要删除的模型 (1-{len(files)}, q=返回): ").strip()
        
        if choice.lower() == 'q':
            return True
        
        if not choice.isdigit() or not (1 <= int(choice) <= len(files)):
            print("❌ 无效选择")
            return False
        
        model_to_delete = files[int(choice)-1]["name"]
        
        confirm = input(f"⚠️  确认删除 '{model_to_delete}'? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消删除")
            return True
        
        payload = {"model_name": model_to_delete}
        response = requests.delete(f"{MAIN_URL}/models/delete", json=payload)
        
        print_response(response, "删除模型")
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 删除模型失败: {str(e)}")
        return False


# ============================================
# 子服务控制测试
# ============================================

def test_service_status():
    """查看子服务状态"""
    print_header("子服务状态")
    
    try:
        response = requests.get(f"{MAIN_URL}/service/status")
        print_response(response, "子服务状态")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 获取子服务状态失败: {str(e)}")
        return False


def test_start_service():
    """启动子服务"""
    print_header("启动子服务")
    
    try:
        response = requests.post(f"{MAIN_URL}/service/start")
        print_response(response, "启动结果")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ 子服务启动成功！")
                print(f"📍 推理服务地址: http://{config.MODEL_SERVER_HOST}:{config.MODEL_SERVER_PORT}")
                return True
        
        print("❌ 启动失败")
        return False
        
    except Exception as e:
        print(f"❌ 启动子服务失败: {str(e)}")
        return False


def test_stop_service():
    """停止子服务"""
    print_header("停止子服务")
    
    confirm = input("⚠️  确认停止子服务? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消停止")
        return True
    
    try:
        response = requests.post(f"{MAIN_URL}/service/stop")
        print_response(response, "停止结果")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 停止子服务失败: {str(e)}")
        return False


def test_restart_service():
    """重启子服务"""
    print_header("重启子服务")
    
    print("💡 提示: 下载新模型后需要重启子服务才能加载")
    confirm = input("确认重启子服务? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消重启")
        return True
    
    try:
        response = requests.post(f"{MAIN_URL}/service/restart")
        print_response(response, "重启结果")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ 子服务重启成功！")
                return True
        
        print("❌ 重启失败")
        return False
        
    except Exception as e:
        print(f"❌ 重启子服务失败: {str(e)}")
        return False


# ============================================
# 推理服务测试 (端口 23059)
# ============================================

def test_model_service_health():
    """测试子服务连接"""
    print_header("子服务连接测试")
    
    try:
        # 使用 /v1/models 端点测试连接（llama.cpp 原生端点）
        response = requests.get(f"{MODEL_URL}/v1/models", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"✅ 子服务运行正常")
            print(f"📍 地址: {MODEL_URL}")
            print(f"📚 已加载 {len(models)} 个模型:")
            for model in models:
                print(f"   - {model['id']}")
            return True
        else:
            print_response(response, "子服务响应")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 子服务未运行")
        print(f"💡 请先通过主服务启动子服务 (选项 6)")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False


def list_available_models():
    """列出可用的推理模型"""
    try:
        response = requests.get(f"{MODEL_URL}/v1/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            return models
        return []
    except Exception:
        return []


def test_chat_completion():
    """测试聊天功能（流式）"""
    print_header("聊天测试")
    
    # 外层循环：选择模型
    while True:
        print("\n📋 正在获取可用模型...")
        models = list_available_models()
        
        if not models:
            print("❌ 没有可用的模型")
            print("💡 请先确保子服务已启动并加载了模型")
            return False
        
        print(f"\n✅ 找到 {len(models)} 个可用模型:")
        for i, model in enumerate(models, 1):
            print(f"  [{i}] {model['id']}")
        
        choice = input(f"\n选择模型 (1-{len(models)}, q=返回主菜单): ").strip()
        
        if choice.lower() == 'q':
            return True
        
        if not choice.isdigit() or not (1 <= int(choice) <= len(models)):
            print("❌ 无效选择")
            continue
        
        selected_model = models[int(choice) - 1]["id"]
        print(f"\n✅ 已选择模型: {selected_model}")
        
        # 进入对话模式
        print(f"\n💬 与模型对话 (输入 'q' 返回选择模型)")
        print("="*60)
        
        conversation_history = []
        
        # 内层循环：对话
        while True:
            user_input = input("\n你: ").strip()
            
            if user_input.lower() in ["q", "quit", "exit"]:
                print("👋 结束对话，返回模型选择\n")
                break
            
            if not user_input:
                continue
            
            conversation_history.append({"role": "user", "content": user_input})
            
            payload = {
                "model": selected_model,
                "messages": conversation_history,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": True,
            }
            
            print("\n🤖 模型: ", end="", flush=True)
            
            assistant_message = ""
            try:
                with requests.post(
                    f"{MODEL_URL}/v1/chat/completions",
                    json=payload,
                    stream=True,
                    timeout=120,
                ) as response:
                    if response.status_code != 200:
                        print(f"\n❌ 请求失败: {response.status_code}")
                        continue
                    
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
                        except Exception:
                            continue
                        
                        choices = data.get("choices") or []
                        if not choices:
                            continue
                        
                        chunk = choices[0]
                        delta = chunk.get("delta") or {}
                        content = delta.get("content")
                        
                        if content is None:
                            content = chunk.get("text")
                        
                        if content:
                            print(content, end="", flush=True)
                            assistant_message += content
            
            except requests.exceptions.Timeout:
                print("\n❌ 请求超时")
            except Exception as e:
                print(f"\n❌ 发生错误: {str(e)}")
            
            if assistant_message:
                conversation_history.append({"role": "assistant", "content": assistant_message})
            print()
        
        # 对话循环结束后，继续外层循环让用户选择其他模型


# ============================================
# 主菜单
# ============================================

def print_main_menu():
    """打印主菜单"""
    print_header("AiEdge 测试工具")
    print(f"""
📍 服务地址:
   主服务 (管理): http://{config.MAIN_SERVER_HOST}:{config.MAIN_SERVER_PORT}
   子服务 (推理): http://{config.MODEL_SERVER_HOST}:{config.MODEL_SERVER_PORT}

🔧 主服务管理:
   [1] 健康检查
   [2] 下载模型 (从 .env 配置)
   [3] 查看已下载的模型
   [4] 删除模型

🚀 子服务控制:
   [5] 查看子服务状态
   [6] 启动子服务
   [7] 停止子服务
   [8] 重启子服务

💬 推理测试:
   [9] 测试子服务连接
   [10] 聊天对话测试

[0] 退出
""")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  🚀 AiEdge 综合测试工具")
    print("="*60)
    
    while True:
        print_main_menu()
        choice = input("请选择操作: ").strip()
        
        try:
            if choice == '0':
                print("\n👋 再见！")
                break
            elif choice == '1':
                test_main_server_health()
            elif choice == '2':
                test_download_model()
            elif choice == '3':
                test_list_models()
            elif choice == '4':
                test_delete_model()
            elif choice == '5':
                test_service_status()
            elif choice == '6':
                test_start_service()
            elif choice == '7':
                test_stop_service()
            elif choice == '8':
                test_restart_service()
            elif choice == '9':
                test_model_service_health()
            elif choice == '10':
                test_chat_completion()
            else:
                print("❌ 无效选择，请重新输入")
            
            input("\n按 Enter 继续...")
            
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ 连接失败: {str(e)}")
            print(f"💡 请确保主服务正在运行: python main.py")
            input("\n按 Enter 继续...")
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
            input("\n按 Enter 继续...")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
