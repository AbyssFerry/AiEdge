"""
子服务进程管理器
管理模型推理服务的启动、停止和重启
"""

import subprocess
import sys
import time
from pathlib import Path
from core.config import config


class ServiceManager:
    """管理子服务进程的单例类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.process = None
        self.start_time = None
        self._initialized = True
    
    def is_running(self) -> bool:
        """检查子服务是否正在运行"""
        if self.process is None:
            return False
        
        # 检查进程是否还存在
        return self.process.poll() is None
    
    def get_status(self) -> dict:
        """获取子服务状态"""
        if self.is_running():
            uptime = int(time.time() - self.start_time) if self.start_time else 0
            return {
                "status": "running",
                "pid": self.process.pid,
                "port": config.MODEL_SERVER_PORT,
                "uptime_seconds": uptime
            }
        else:
            return {
                "status": "stopped",
                "pid": None,
                "port": config.MODEL_SERVER_PORT,
                "uptime_seconds": 0
            }
    
    def start(self) -> dict:
        """启动子服务"""
        if self.is_running():
            return {
                "success": False,
                "message": "子服务已经在运行中",
                "status": self.get_status()
            }
        
        try:
            # 获取 model_service.py 的路径
            project_root = Path(__file__).parent.parent
            model_service_script = project_root / "model_service.py"
            
            if not model_service_script.exists():
                return {
                    "success": False,
                    "message": f"找不到子服务启动脚本: {model_service_script}",
                    "status": self.get_status()
                }
            
            # 启动子进程
            self.process = subprocess.Popen(
                [sys.executable, str(model_service_script)]
            )
            
            self.start_time = time.time()
            
            # 等待子进程启动
            time.sleep(2)
            
            # 检查进程是否成功启动
            if not self.is_running():
                return {
                    "success": False,
                    "message": "子服务启动失败",
                    "status": self.get_status()
                }
            
            return {
                "success": True,
                "message": "子服务启动成功",
                "status": self.get_status()
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"启动子服务时发生错误: {str(e)}",
                "status": self.get_status()
            }
    
    def stop(self, timeout: int = 30) -> dict:
        """停止子服务"""
        if not self.is_running():
            return {
                "success": True,
                "message": "子服务未运行",
                "status": self.get_status()
            }
        
        try:
            pid = self.process.pid
            
            # 尝试优雅关闭
            self.process.terminate()
            
            try:
                # 等待进程结束
                self.process.wait(timeout=timeout)
                self.process = None
                self.start_time = None
                
                return {
                    "success": True,
                    "message": f"子服务已停止 (PID: {pid})",
                    "status": self.get_status()
                }
                
            except subprocess.TimeoutExpired:
                # 超时则强制杀死
                self.process.kill()
                self.process.wait()
                self.process = None
                self.start_time = None
                
                return {
                    "success": True,
                    "message": f"子服务已强制停止 (PID: {pid}, 超时后强制终止)",
                    "status": self.get_status()
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"停止子服务时发生错误: {str(e)}",
                "status": self.get_status()
            }
    
    def restart(self) -> dict:
        """重启子服务"""
        # 先停止
        stop_result = self.stop()
        
        if not stop_result["success"]:
            return {
                "success": False,
                "message": f"重启失败: 停止服务时出错 - {stop_result['message']}",
                "status": self.get_status()
            }
        
        # 等待一小段时间确保资源释放
        time.sleep(2)
        
        # 再启动
        start_result = self.start()
        
        if start_result["success"]:
            return {
                "success": True,
                "message": "子服务重启成功",
                "status": self.get_status()
            }
        else:
            return {
                "success": False,
                "message": f"重启失败: 启动服务时出错 - {start_result['message']}",
                "status": self.get_status()
            }


# 创建全局单例
service_manager = ServiceManager()
