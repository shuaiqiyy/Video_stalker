import os
import re
import time
from datetime import datetime

from config_loader import config
from toast_notifier import ToastNotifier


class LogMonitor:
    """日志监控器 - 定期读取模式"""
    
    def __init__(self, log_path, notifier=None):
        self.log_path = log_path
        self.notifier = notifier or ToastNotifier()
        self._notified_events = set()
        self._last_position = 0
        self._last_size = 0
        self._running = False
        
        # 从配置加载参数
        self._check_interval = config.get('monitor.check_interval', 0.2)
        self._file_wait = config.get('monitor.file_wait_interval', 3)
        
        # 编译正则表达式
        patterns = config.get('patterns', {})
        self._re_create = re.compile(patterns.get('channel_create', 
            r'Create Channel PeerCid is (\d+), ServiceID is \d+, ChanId\[(\d+)\]'))
        self._re_end = re.compile(patterns.get('channel_end',
            r'PeerCid is (\d+).*?ChanId\[(\d+)\]'))
        self._end_keywords = patterns.get('end_keywords', ['TEARDOWN_REQ', 'Channel Closed'])
        
        # 通知模板
        self._notify_title = config.get('notification.title', '请注意')
    
    def _read_new_lines(self):
        """原子读取新增内容"""
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self._last_position)
                lines = f.readlines()
                self._last_position = f.tell()
                return lines
        except PermissionError:
            time.sleep(0.5)
            return []
        except Exception as e:
            return []
    
    def _handle_rotation(self, current_size):
        """处理日志轮转"""
        if current_size < self._last_size:
            self._last_position = 0
            self._notified_events.clear()
            return True
        return False
    
    def _process_line(self, line):
        """处理单行日志"""
        line = line.strip()
        if not line:
            return
        
        # 检测观看开始
        match = self._re_create.search(line)
        if match:
            cid = match.group(1)
            channel_id = match.group(2)
            event_key = f"{cid}_{channel_id}"
            
            if event_key not in self._notified_events:
                self._notified_events.add(event_key)
                time_str = datetime.now().strftime("%H:%M:%S")
                short_cid = cid[-4:] if len(cid) > 4 else cid
                

            return
    def _check_cycle(self):
        """单次检查周期"""
        if not os.path.exists(self.log_path):
            time.sleep(self._file_wait)
            return
        
        current_size = os.path.getsize(self.log_path)
        self._handle_rotation(current_size)
        self._last_size = current_size
        
        if current_size > self._last_position:
            for line in self._read_new_lines():
                self._process_line(line)
        
        time.sleep(self._check_interval)
    