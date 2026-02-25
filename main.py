import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from config_loader import Config, config
from process_manager import ProcessManager
from log_finder import LogFinder
from toast_notifier import ToastNotifier, ToastManager


# 全局变量
_notifier = None
_app = None


def parse_cli_args():
    """解析命令行参数"""
    args = {
        'process_name': config.get('process.name'),
        'log_dir': config.get('log.directory'),
        'config_path': None
    }
    
    if len(sys.argv) >= 2:
        args['process_name'] = sys.argv[1]
    if len(sys.argv) >= 3:
        args['log_dir'] = sys.argv[2]
    if len(sys.argv) >= 4:
        args['config_path'] = sys.argv[3]
        Config(args['config_path'])
    
    return args


def interactive_input():
    """交互式获取日志路径"""
    path = input("请手动输入路径: ").strip().strip('"')
    if not os.path.isfile(path):
        sys.exit(1)
    return path


class MonitorWorker(QThread):
    """
    监控工作线程 - 使用 QThread 确保与 Qt 兼容
    """
    log_line_signal = pyqtSignal(str)  # 发送日志行到主线程处理
    
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path
        self._running = True
        self._paused = False
        
    def run(self):
        """监控循环"""
        import re
        import time
        from datetime import datetime
        
        # 编译正则
        patterns = config.get('patterns', {})
        re_create = re.compile(patterns.get('channel_create', 
            r'Create Channel PeerCid is (\d+), ServiceID is \d+, ChanId\[(\d+)\]'))
        re_end = re.compile(patterns.get('channel_end',
            r'PeerCid is (\d+).*?ChanId\[(\d+)\]'))
        end_keywords = patterns.get('end_keywords', ['TEARDOWN_REQ', 'Channel Closed'])
        
        check_interval = config.get('monitor.check_interval', 0.2)
        file_wait = config.get('monitor.file_wait_interval', 3)
        
        notified_events = set()
        last_position = 0
        last_size = 0
        
        # 发送启动信号
        self.log_line_signal.emit("__STARTUP__")
        
        while self._running:
            try:
                if not os.path.exists(self.log_path):
                    time.sleep(file_wait)
                    continue
                
                current_size = os.path.getsize(self.log_path)
                
                if current_size < last_size:
                    last_position = 0
                    notified_events.clear()
                
                last_size = current_size
                
                if current_size > last_position:
                    try:
                        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()
                        
                        for line in new_lines:
                            line_stripped = line.strip()
                            if not line_stripped:
                                continue
                            
                            # 发送到主线程处理（避免线程安全问题）
                            self.log_line_signal.emit(line_stripped)
                            
                    except PermissionError:
                        time.sleep(0.5)
                        continue
                
                time.sleep(check_interval)
                
            except Exception as e:
                time.sleep(3)
    
    def stop(self):
        self._running = False


class MainController:
    """
    主控制器 - 在主线程运行，处理所有 GUI 操作
    """
    
    def __init__(self, log_path):
        self.log_path = log_path
        self.notifier = ToastNotifier()
        self.worker = MonitorWorker(log_path)
        self.worker.log_line_signal.connect(self._on_log_line)
        
        # 状态
        self.notified_events = set()
        import re
        patterns = config.get('patterns', {})
        self.re_create = re.compile(patterns.get('channel_create', 
            r'Create Channel PeerCid is (\d+), ServiceID is \d+, ChanId\[(\d+)\]'))
        self.re_end = re.compile(patterns.get('channel_end',
            r'PeerCid is (\d+).*?ChanId\[(\d+)\]'))
        self.end_keywords = patterns.get('end_keywords', ['TEARDOWN_REQ', 'Channel Closed'])
        
    def _on_log_line(self, line):
        """在主线程处理日志行"""
        if line == "__STARTUP__":
            self.notifier.show("启动", "", "")
            return
            
        from datetime import datetime
        
        # 检测观看开始
        match = self.re_create.search(line)
        if match:
            cid = match.group(1)
            channel_id = match.group(2)
            event_key = f"{cid}_{channel_id}"
            
            if event_key not in self.notified_events:
                self.notified_events.add(event_key)
                time_str = datetime.now().strftime("%H:%M:%S")
                short_cid = cid[-4:] if len(cid) > 4 else cid
                self.notifier.show("系统更新提醒", 
                    f"设备版本 {short_cid} 将更新", cid)
            return
        
        # 检测观看结束
        has_end = any(kw in line for kw in self.end_keywords)
        if has_end:
            match_end = self.re_end.search(line)
            if match_end:
                ended_key = f"{match_end.group(1)}_{match_end.group(2)}"
                if ended_key in self.notified_events:
                    self.notified_events.remove(ended_key)
    
    def start(self):
        """启动"""
        self.worker.start()
        
    def stop(self):
        """停止"""
        self.worker.stop()
        self.worker.wait(2000)


def main():
    """主流程"""
    global _app, _notifier
    
    args = parse_cli_args()
    
    # 等待进程
    ProcessManager.wait_for_start(args['process_name'])
    
    # 查找日志
    finder = LogFinder()
    log_path = finder.find_with_fallback(args['log_dir'])
    
    if not log_path:
        log_path = interactive_input()
    
    # 创建 Qt 应用（必须在主线程）
    _app = QApplication.instance() or QApplication(sys.argv)
    
    # 创建控制器（初始化 ToastNotifier）
    controller = MainController(log_path)
    controller.start()
    
    # 启动 Qt 事件循环
    try:
        sys.exit(_app.exec_())
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()