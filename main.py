import os
import re
import time
import subprocess
import threading
import glob
import sys
import ctypes
from datetime import datetime
from pathlib import Path


class Toast:
    """使用PowerShell发送Windows通知"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.last_time = {}
        
    def show(self, title, msg, cid="default"):
        """发送通知，每个设备独立冷却"""
        with self.lock:
            now = time.time()
            if now - self.last_time.get(cid, 0) < 3:
                return
            self.last_time[cid] = now
        
        title_clean = title.replace('"', '`"').replace('$', '`$')
        msg_clean = msg.replace('"', '`"').replace('$', '`$')
        
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = "{title_clean}"
$notify.BalloonTipText = "{msg_clean}"
$notify.BalloonTipIcon = "Info"
$notify.Visible = $true
$notify.ShowBalloonTip(5000)
Start-Sleep -Milliseconds 6000
$notify.Dispose()
'''
        
        def run():
            try:
                subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000
                )
            except:
                pass
        
        threading.Thread(target=run, daemon=True).start()


def find_latest_log(log_dir):
    """查找log文件夹中数字最大的ich_run_X.log文件"""
    if not os.path.exists(log_dir):
        return None
    
    pattern = os.path.join(log_dir, "ich_run_*.log")
    log_files = glob.glob(pattern)
    
    if not log_files:
        return None
    
    def extract_number(filepath):
        filename = os.path.basename(filepath)
        match = re.search(r'ich_run_(\d+)\.log', filename)
        return int(match.group(1)) if match else 0
    
    log_files.sort(key=extract_number, reverse=True)
    return log_files[0]


def is_process_running(process_name):
    """检查进程是否正在运行"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )
        return process_name.lower() in result.stdout.lower()
    except:
        return False


def wait_for_process(process_name):
    """等待进程启动"""
    while not is_process_running(process_name):
        time.sleep(3)
    time.sleep(2)


def monitor(log_path):
    """监控日志"""
    toast = Toast()
    notified_events = set()
    last_position = 0
    last_size = 0
    
    toast.show("监控启动", "等待设备连接...", "startup")
    
    while True:
        try:
            if not os.path.exists(log_path):
                time.sleep(3)
                continue
            
            current_size = os.path.getsize(log_path)
            
            if current_size < last_size:
                last_position = 0
                notified_events.clear()
            
            last_size = current_size
            
            if current_size > last_position:
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                    
                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        match = re.search(r'Create Channel PeerCid is (\d+), ServiceID is \d+, ChanId\[(\d+)\]', line)
                        if match:
                            cid = match.group(1)
                            channel_id = match.group(2)
                            event_key = f"{cid}_{channel_id}"
                            
                            if event_key not in notified_events:
                                notified_events.add(event_key)
                                toast.show("请注意", f"设备 {cid[-4:]} 通道{channel_id} 开始观看", cid)
                        
                        if 'TEARDOWN_REQ' in line or 'Channel Closed' in line:
                            match_end = re.search(r'PeerCid is (\d+).*?ChanId\[(\d+)\]', line)
                            if match_end:
                                ended_key = f"{match_end.group(1)}_{match_end.group(2)}"
                                if ended_key in notified_events:
                                    notified_events.remove(ended_key)
                    
                except PermissionError:
                    time.sleep(0.5)
                    continue
                except:
                    pass
            
            time.sleep(0.2)
            
        except KeyboardInterrupt:
            raise
        except:
            time.sleep(3)


def add_to_startup():
    """添加到开机启动"""
    try:
        import winreg
        exe_path = sys.executable
        script_path = os.path.abspath(__file__)
        startup_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, startup_key, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "LogMonitor", 0, winreg.REG_SZ, f'"{exe_path}" "{script_path}"')
        winreg.CloseKey(key)
        return True
    except:
        return False


def hide_console():
    """隐藏控制台窗口"""
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass


if __name__ == "__main__":
    # 隐藏控制台
    hide_console()
    
    # 默认配置
    PROCESS_NAME = "AtHomeVideoStreamer.exe"
    LOG_DIR = r"d:\AtHomeVideoStreamer\log"
    
    # 检查命令行参数
    if len(sys.argv) >= 2:
        PROCESS_NAME = sys.argv[1]
    if len(sys.argv) >= 3:
        LOG_DIR = sys.argv[2]
    
    # 等待进程启动
    wait_for_process(PROCESS_NAME)
    
    # 查找最新的日志文件
    log_path = find_latest_log(LOG_DIR)
    
    if not log_path:
        backup_paths = [
            r"d:\AtHomeVideoStreamer\ich_run_0.log",
            r"c:\AtHomeVideoStreamer\log\ich_run_0.log",
        ]
        for p in backup_paths:
            if os.path.isfile(p):
                log_path = p
                break
    
    if not log_path or not os.path.isfile(log_path):
        exit(1)
    
    try:
        monitor(log_path)
    except KeyboardInterrupt:
        pass
    except:
        pass