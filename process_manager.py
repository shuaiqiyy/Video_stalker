import subprocess
import time

from config_loader import config


class ProcessManager:
    """管理目标进程的监控和等待"""
    
    @staticmethod
    def is_running(process_name):
        """检查进程是否正在运行"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                capture_output=True,
                text=True,
                creationflags=0x08000000
            )
            return process_name.lower() in result.stdout.lower()
        except Exception:
            return False
    
    @classmethod
    def wait_for_start(cls, process_name=None):
        """
        阻塞等待进程启动
        
        Args:
            process_name: 进程名，默认从配置读取
        """
        name = process_name or config.get('process.name')
        interval = config.get('process.wait_interval', 2)
        init_delay = config.get('process.init_delay', 1)
        while not cls.is_running(name):
            time.sleep(interval)
        time.sleep(init_delay)