"""
模型下载测试文件 - 测试正式下载模型功能
从 .env 配置文件读取要下载的模型
"""

import requests
import json
from core.config import config

# API 基础 URL（根据你的配置修改）
BASE_URL = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"


def print_response(response, title="响应"):
    """格式化打印响应"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    print(f"响应内容:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"{'='*60}\n")


def test_download_model():
    """测试正式下载模型 - 从 .env 配置文件读取"""
    print("\n⬇️  模型下载测试")
    
    # 从配置文件读取要下载的模型
    models_from_config = config.MODELS_TO_DOWNLOAD
    
    if not models_from_config:
        print("⚠️  .env 文件中没有配置 MODELS_TO_DOWNLOAD")
        print("\n请在 .env 文件中添加要下载的模型，格式如下:")
        print("MODELS_TO_DOWNLOAD=google/gemma-2-2b-it-GGUF|gemma-3-1b-it-f16.gguf,unsloth/Qwen2.5-VL-3B-Instruct-GGUF|Qwen2.5-VL-3B-Instruct-UD-Q8_K_XL.gguf")
        return False
    
    # 额外的可选模型（用户可以选择）
    additional_models = [
        {
            "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            "description": "Llama 3.2 3B 指令模型 (Q4量化)"
        },
        {
            "repo_id": "lmstudio-community/Phi-3.5-mini-instruct-GGUF",
            "filename": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
            "description": "Phi 3.5 Mini 指令模型"
        }
    ]
    
    print("\n📦 从 .env 配置的模型:")
    for i, model in enumerate(models_from_config, 1):
        print(f"  [{i}] {model['filename']}")
        print(f"      仓库: {model['repo_id']}")
    
    print("\n📦 额外可选模型:")
    for i, model in enumerate(additional_models, len(models_from_config) + 1):
        print(f"  [{i}] {model['description']}")
        print(f"      仓库: {model['repo_id']}")
        print(f"      文件: {model['filename']}")
    
    print("\n" + "="*60)
    print("选项:")
    print("  [config] - 下载 .env 配置的所有模型")
    print("  [all]    - 下载所有模型（包括配置和可选）")
    print(f"  [1-{len(models_from_config) + len(additional_models)}] - 下载指定的单个模型")
    print("  [q]      - 退出")
    
    choice = input("\n输入选择: ").strip().lower()
    
    if choice == 'q':
        print("👋 退出下载")
        return True
    
    models_to_download = []
    if choice == "config":
        models_to_download = models_from_config
    elif choice == "all":
        models_to_download = models_from_config + additional_models
    elif choice.isdigit():
        idx = int(choice) - 1
        all_models = models_from_config + additional_models
        if 0 <= idx < len(all_models):
            models_to_download = [all_models[idx]]
        else:
            print("❌ 无效选择")
            return False
    else:
        print("❌ 无效选择")
        return False
    
    # 下载选中的模型
    for model_info in models_to_download:
        print(f"\n{'='*60}")
        model_desc = model_info.get('description', model_info['filename'])
        print(f"⏳ 正在下载: {model_desc}")
        print(f"{'='*60}")
        
        payload = {
            "repo_id": model_info["repo_id"],
            "filename": model_info["filename"]
        }
        
        print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        print("⏳ 下载中，这可能需要较长时间，请耐心等待...")
        
        try:
            response = requests.post(
                f"{BASE_URL}/models/download",
                json=payload,
                timeout=3600  # 1小时超时
            )
            
            print_response(response, f"下载结果 - {model_desc}")
            
            if response.status_code != 200:
                print(f"❌ 下载失败")
                return False
            else:
                print(f"✅ 下载成功！")
                
        except requests.exceptions.Timeout:
            print("❌ 下载超时")
            return False
        except Exception as e:
            print(f"❌ 下载出错: {str(e)}")
            return False
    
    return True


def test_list_models():
    """测试列出已下载的模型"""
    print("\n📋 查看已下载的模型")
    
    try:
        response = requests.get(f"{BASE_URL}/models/list")
        print_response(response, "模型列表")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 获取模型列表失败: {str(e)}")
        return False


def test_delete_model():
    """测试删除模型"""
    print("\n🗑️  删除模型")
    
    # 先列出所有模型
    try:
        list_response = requests.get(f"{BASE_URL}/models/list")
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
        
        choice = input("\n选择要删除的模型 (1-{}): ".format(len(files))).strip()
        
        if not choice.isdigit() or not (1 <= int(choice) <= len(files)):
            print("❌ 无效选择")
            return False
        
        model_to_delete = files[int(choice)-1]["name"]
        
        confirm = input(f"⚠️  确认删除 '{model_to_delete}'? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消删除")
            return True
        
        payload = {"model_name": model_to_delete}
        response = requests.delete(f"{BASE_URL}/models/delete", json=payload)
        
        print_response(response, "删除模型")
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 删除模型失败: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AiEdge 模型管理工具")
    print("="*60)
    
    while True:
        print("\n请选择操作:")
        print("  [1] 下载模型")
        print("  [2] 列出已下载的模型")
        print("  [3] 删除模型")
        print("  [q] 退出")
        
        choice = input("\n输入选择: ").strip().lower()
        
        if choice == 'q':
            print("\n👋 再见！")
            break
        
        try:
            if choice == '1':
                test_download_model()
            elif choice == '2':
                test_list_models()
            elif choice == '3':
                test_delete_model()
            else:
                print("❌ 无效选择，请重新输入")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ 无法连接到服务器 {BASE_URL}")
            print("请确保 API 服务器正在运行 (运行 uv run ./main.py)")
            break
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
    
    print("\n" + "="*60 + "\n")
