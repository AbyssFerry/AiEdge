"""
AiEdge 综合测试工具
提供交互式命令行界面测试所有功能
"""

import requests
import json
import time
import os
import io
from pathlib import Path
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
    
    print("\n💡 提示：支持断点续传，下载中断后可重新启动继续下载")
    
    # 下载选中的模型
    for model_info in models_to_download:
        print(f"\n{'='*60}")
        print(f"⏳ 正在下载: {model_info['filename']}")
        print(f"{'='*60}")
        
        payload = {
            "repo_id": model_info["repo_id"],
            "filename": model_info["filename"]
        }
        
        try:
            # 启动异步下载任务
            print("📥 启动下载任务...")
            response = requests.post(
                f"{MAIN_URL}/models/download/start",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                print("❌ 启动下载失败")
                print_response(response, "错误详情")
                continue
            
            result = response.json()
            task_id = result.get('task_id')
            
            if not task_id:
                print("❌ 未获取到任务ID")
                continue
            
            print(f"✅ 任务已启动 (ID: {task_id[:8]}...)")
            print("⏳ 正在下载，请稍候...\n")
            
            # 轮询进度 - 每0.5秒查询一次
            last_status = ""
            last_percentage = -1
            
            while True:
                time.sleep(0.5)  # 0.5秒更新一次
                
                try:
                    status_resp = requests.get(
                        f"{MAIN_URL}/models/download/status/{task_id}",
                        timeout=5
                    )
                    
                    if status_resp.status_code != 200:
                        print("\n❌ 查询进度失败")
                        break
                    
                    progress = status_resp.json()
                    status = progress.get('status')
                    
                    if status == 'starting':
                        msg = progress.get('message', '准备中...')
                        if msg != last_status:
                            print(f"⏳ {msg}")
                            last_status = msg
                    
                    elif status == 'downloading':
                        percentage = progress.get('percentage', 0)
                        current_str = progress.get('current_str', '未知')
                        total_str = progress.get('total_str', '未知')
                        
                        # 只在进度变化时更新显示
                        if percentage != last_percentage:
                            # 创建进度条
                            bar_length = 40
                            filled = int(bar_length * percentage / 100)
                            bar = '█' * filled + '░' * (bar_length - filled)
                            
                            # 显示进度条
                            print(f"\r{bar} {percentage:.1f}% ({current_str}/{total_str})", 
                                  end='', flush=True)
                            last_percentage = percentage
                    
                    elif status == 'completed':
                        # 确保进度条显示100%
                        bar = '█' * 40
                        print(f"\r{bar} 100.0%")
                        print(f"\n✅ {progress.get('message', '下载完成')}")
                        break
                    
                    elif status == 'failed':
                        error_msg = progress.get('error', progress.get('message', '未知错误'))
                        print(f"\n❌ 下载失败: {error_msg}")
                        return False
                    
                    elif status == 'not_found':
                        print(f"\n❌ {progress.get('message', '任务不存在')}")
                        break
                
                except requests.RequestException as e:
                    print(f"\n❌ 网络错误: {str(e)}")
                    break
                except Exception as e:
                    print(f"\n❌ 查询进度出错: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"\n❌ 下载出错: {str(e)}")
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
# 系统信息测试
# ============================================

def test_disk_usage():
    """查询硬盘使用情况"""
    print_header("硬盘使用情况")
    
    try:
        response = requests.get(f"{MAIN_URL}/system/disk")
        print_response(response, "硬盘使用情况")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("\n📊 硬盘使用详情:")
                print(f"   总容量: {data['total_gb']:.2f} GB ({data['total']:,} 字节)")
                print(f"   已使用: {data['used_gb']:.2f} GB ({data['used']:,} 字节)")
                print(f"   可用空间: {data['free_gb']:.2f} GB ({data['free']:,} 字节)")
                print(f"   使用率: {data['percent']:.1f}%")
                
                # 显示使用率进度条
                bar_length = 40
                filled = int(bar_length * data['percent'] / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"   [{bar}] {data['percent']:.1f}%")
                
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ 查询硬盘信息失败: {str(e)}")
        return False


def test_memory_usage():
    """查询内存使用情况"""
    print_header("内存使用情况")
    
    try:
        response = requests.get(f"{MAIN_URL}/system/memory")
        print_response(response, "内存使用情况")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("\n📊 内存使用详情:")
                print(f"   总内存: {data['total_gb']:.2f} GB ({data['total']:,} 字节)")
                print(f"   已使用: {data['used_gb']:.2f} GB ({data['used']:,} 字节)")
                print(f"   可用内存: {data['available_gb']:.2f} GB ({data['available']:,} 字节)")
                print(f"   使用率: {data['percent']:.1f}%")
                
                # 显示使用率进度条
                bar_length = 40
                filled = int(bar_length * data['percent'] / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"   [{bar}] {data['percent']:.1f}%")
                
                # 显示 GPU 信息
                if data.get('gpu_memory_shared'):
                    print("\n🎮 GPU 显存信息:")
                    print(f"   内存与显存共享: 是")
                    
                    gpu_info = data.get('gpu_info')
                    if gpu_info:
                        print(f"   GPU 型号: {gpu_info.get('gpu_type', 'Unknown')}")
                        if 'gpu_usage_percent' in gpu_info:
                            print(f"   GPU 使用率: {gpu_info['gpu_usage_percent']}%")
                        if 'cuda_cores' in gpu_info:
                            print(f"   CUDA 核心数: {gpu_info['cuda_cores']}")
                        if 'cuda_version' in gpu_info:
                            print(f"   CUDA 版本: {gpu_info['cuda_version']}")
                    else:
                        print("   (无法获取详细 GPU 信息)")
                
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ 查询内存信息失败: {str(e)}")
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
        print(f"💡 请先通过主服务启动子服务 (选项 9)")
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
# 分片上传测试 (端口 23058)
# ============================================

def test_chunk_upload():
    """测试分片上传功能"""
    print_header("分片上传功能测试")
    
    # 子菜单
    print("""
📦 分片上传测试:
   [1] 完整上传流程测试（创建测试文件）
   [2] 断点续传测试
   [3] 查询上传进度
   
[q] 返回主菜单
""")
    
    choice = input("请选择测试: ").strip().lower()
    
    if choice == 'q':
        return True
    elif choice == '1':
        return test_chunk_upload_full_flow()
    elif choice == '2':
        return test_chunk_upload_resume()
    elif choice == '3':
        return test_chunk_upload_progress()
    else:
        print("❌ 无效选择")
        return False


def test_chunk_upload_full_flow():
    """完整上传流程测试"""
    print_header("完整上传流程测试")
    
    # 使用真实模型文件
    test_model_path = config.TEST_UPLOAD_MODEL_PATH
    
    if not test_model_path or not test_model_path.exists():
        print("❌ 未配置测试模型路径或文件不存在")
        print("💡 请在 .env 文件中配置 TEST_UPLOAD_MODEL_PATH")
        print(f"   当前配置: {test_model_path}")
        return False
    
    print(f"\n📝 使用真实模型文件: {test_model_path.name}")
    
    test_file_name = f"uploaded-{test_model_path.name}"
    test_file_size = test_model_path.stat().st_size
    chunk_size = config.CHUNK_SIZE  # 使用配置的分片大小
    total_chunks = (test_file_size + chunk_size - 1) // chunk_size
    
    print(f"   文件名: {test_file_name}")
    print(f"   原始路径: {test_model_path}")
    print(f"   大小: {test_file_size / (1024*1024):.1f} MB")
    print(f"   分片大小: {chunk_size / (1024*1024):.1f} MB")
    print(f"   总分片数: {total_chunks}")
    
    # 步骤1: 初始化上传会话
    print("\n" + "="*60)
    print("步骤 1: 初始化上传会话")
    print("="*60)
    
    init_payload = {
        "filename": test_file_name,
        "file_size": test_file_size,
        "total_chunks": total_chunks
    }
    
    try:
        response = requests.post(f"{MAIN_URL}/upload/init", json=init_payload, timeout=10)
        print_response(response, "初始化响应")
        
        if response.status_code != 200:
            print("❌ 初始化失败")
            return False
        
        result = response.json()
        task_id = result.get("task_id")
        
        if not task_id:
            print("❌ 未获取到 task_id")
            return False
        
        print(f"\n✅ 获得任务ID: {task_id}")
        
        # 步骤2: 上传分片
        print("\n" + "="*60)
        print("步骤 2: 上传分片")
        print("="*60)
        
        uploaded_count = 0
        with open(test_model_path, 'rb') as f:
            for chunk_idx in range(total_chunks):
                # 读取真实文件的分片
                f.seek(chunk_idx * chunk_size)
                chunk_data = f.read(chunk_size)
                
                # 准备上传数据
                files = {
                    'file': (f'chunk_{chunk_idx}', io.BytesIO(chunk_data), 'application/octet-stream')
                }
                data = {
                    'task_id': task_id,
                    'chunk_index': chunk_idx
                }
                
                # 上传分片
                try:
                    upload_response = requests.post(
                        f"{MAIN_URL}/upload/chunk",
                        files=files,
                        data=data,
                        timeout=30
                    )
                    
                    if upload_response.status_code == 200:
                        result = upload_response.json()
                        uploaded_count += 1
                        print(f"   ✅ 分片 {chunk_idx}/{total_chunks-1} 上传成功 - 进度: {result.get('progress', 0):.1f}%")
                    else:
                        print(f"   ❌ 分片 {chunk_idx} 上传失败: {upload_response.text}")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ 分片 {chunk_idx} 上传异常: {str(e)}")
                    return False
        
        print(f"\n✅ 所有分片上传完成 ({uploaded_count}/{total_chunks})")
        
        # 步骤3: 查询进度
        print("\n" + "="*60)
        print("步骤 3: 查询上传进度")
        print("="*60)
        
        progress_response = requests.get(f"{MAIN_URL}/upload/progress/{task_id}", timeout=10)
        print_response(progress_response, "进度查询")
        
        # 步骤4: 完成合并
        print("\n" + "="*60)
        print("步骤 4: 完成合并")
        print("="*60)
        
        complete_data = {
            'task_id': task_id
        }
        
        complete_response = requests.post(
            f"{MAIN_URL}/upload/complete",
            data=complete_data,
            timeout=60
        )
        print_response(complete_response, "合并响应")
        
        if complete_response.status_code == 200:
            result = complete_response.json()
            print(f"\n✅ 文件上传和合并成功!")
            print(f"   模型路径: {result.get('model_path')}")
            print(f"\n💡 提示: 使用选项 [11] 重启子服务来加载新模型")
            return True
        else:
            print("❌ 合并失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")
        return False


def test_chunk_upload_resume():
    """断点续传测试"""
    print_header("断点续传测试")
    
    # 使用真实模型文件
    test_model_path = config.TEST_UPLOAD_MODEL_PATH
    
    if not test_model_path or not test_model_path.exists():
        print("❌ 未配置测试模型路径或文件不存在")
        print("💡 请在 .env 文件中配置 TEST_UPLOAD_MODEL_PATH")
        return False
    
    print(f"\n📝 使用真实模型文件: {test_model_path.name}")
    
    test_file_name = f"resume-{test_model_path.name}"
    test_file_size = test_model_path.stat().st_size
    chunk_size = config.CHUNK_SIZE
    total_chunks = (test_file_size + chunk_size - 1) // chunk_size
    
    print(f"   文件名: {test_file_name}")
    print(f"   大小: {test_file_size / (1024*1024):.1f} MB")
    print(f"   总分片数: {total_chunks}")
    
    # 第一次上传：只上传一半
    print("\n" + "="*60)
    print("第一次上传：上传前一半分片")
    print("="*60)
    
    init_payload = {
        "filename": test_file_name,
        "file_size": test_file_size,
        "total_chunks": total_chunks
    }
    
    try:
        response = requests.post(f"{MAIN_URL}/upload/init", json=init_payload, timeout=10)
        result = response.json()
        task_id = result.get("task_id")
        
        print(f"✅ 任务ID: {task_id}")
        
        # 只上传一半分片
        half_chunks = total_chunks // 2
        print(f"\n上传前 {half_chunks} 个分片...")
        
        with open(test_model_path, 'rb') as f:
            for chunk_idx in range(half_chunks):
                f.seek(chunk_idx * chunk_size)
                chunk_data = f.read(chunk_size)
                
                files = {
                    'file': (f'chunk_{chunk_idx}', io.BytesIO(chunk_data), 'application/octet-stream')
                }
                data = {
                    'task_id': task_id,
                    'chunk_index': chunk_idx
                }
                
                requests.post(f"{MAIN_URL}/upload/chunk", files=files, data=data, timeout=30)
                print(f"   ✅ 分片 {chunk_idx} 已上传")
        
        print(f"\n✅ 已上传 {half_chunks}/{total_chunks} 个分片")
        
        # 模拟中断，重新初始化
        print("\n" + "="*60)
        print("模拟中断后重新初始化（断点续传）")
        print("="*60)
        
        response = requests.post(f"{MAIN_URL}/upload/init", json=init_payload, timeout=10)
        print_response(response, "断点续传初始化")
        
        result = response.json()
        resumed_task_id = result.get("task_id")
        uploaded_chunks = result.get("uploaded_chunks", [])
        
        print(f"\n✅ 检测到未完成的上传")
        print(f"   任务ID: {resumed_task_id}")
        print(f"   已上传分片: {len(uploaded_chunks)}/{total_chunks}")
        print(f"   分片列表: {uploaded_chunks}")
        
        # 继续上传剩余分片
        print("\n" + "="*60)
        print("继续上传剩余分片")
        print("="*60)
        
        with open(test_model_path, 'rb') as f:
            for chunk_idx in range(total_chunks):
                if chunk_idx in uploaded_chunks:
                    print(f"   ⏭️  分片 {chunk_idx} 已存在，跳过")
                    continue
                
                f.seek(chunk_idx * chunk_size)
                chunk_data = f.read(chunk_size)
                
                files = {
                    'file': (f'chunk_{chunk_idx}', io.BytesIO(chunk_data), 'application/octet-stream')
                }
                data = {
                    'task_id': resumed_task_id,
                    'chunk_index': chunk_idx
                }
                
                requests.post(f"{MAIN_URL}/upload/chunk", files=files, data=data, timeout=30)
                print(f"   ✅ 分片 {chunk_idx} 已上传")
        
        print(f"\n✅ 所有分片上传完成")
        
        # 完成合并
        print("\n" + "="*60)
        print("完成合并")
        print("="*60)
        
        complete_data = {'task_id': resumed_task_id}
        complete_response = requests.post(f"{MAIN_URL}/upload/complete", data=complete_data, timeout=60)
        print_response(complete_response, "合并响应")
        
        if complete_response.status_code == 200:
            print("\n✅ 断点续传测试成功!")
            print("💡 提示: 使用选项 [11] 重启子服务来加载新模型")
            return True
        else:
            print("❌ 合并失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")
        return False


def test_chunk_upload_progress():
    """查询上传进度"""
    print_header("查询上传进度")
    
    task_id = input("\n请输入任务ID: ").strip()
    
    if not task_id:
        print("❌ 任务ID不能为空")
        return False
    
    try:
        response = requests.get(f"{MAIN_URL}/upload/progress/{task_id}", timeout=10)
        print_response(response, "进度查询")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 查询失败: {str(e)}")
        return False


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

� 分片上传:
   [5] 分片上传测试

📊 系统信息:
   [6] 查询硬盘使用情况
   [7] 查询内存使用情况

🚀 子服务控制:
   [8] 查看子服务状态
   [9] 启动子服务
   [10] 停止子服务
   [11] 重启子服务

💬 推理测试:
   [12] 测试子服务连接
   [13] 聊天对话测试

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
                test_chunk_upload()
            elif choice == '6':
                test_disk_usage()
            elif choice == '7':
                test_memory_usage()
            elif choice == '8':
                test_service_status()
            elif choice == '9':
                test_start_service()
            elif choice == '10':
                test_stop_service()
            elif choice == '11':
                test_restart_service()
            elif choice == '12':
                test_model_service_health()
            elif choice == '13':
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
