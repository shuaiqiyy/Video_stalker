import os
import re
import glob
from pathlib import Path

from config_loader import config


class LogFinder:
    """查找和管理日志文件路径"""
    
    def __init__(self):
        self._pattern = config.get('log.pattern', 'ich_run_*.log')
        self._number_regex = re.compile(r'ich_run_(\d+)\.log')
    
    def find_latest(self, log_dir=None):
        """
        查找目录中数字最大的日志文件
        
        Args:
            log_dir: 日志目录，默认从配置读取
        """
        directory = log_dir or config.get('log.directory')
        
        if not os.path.exists(directory):
            return None
        
        search_pattern = os.path.join(directory, self._pattern)
        log_files = glob.glob(search_pattern)
        
        if not log_files:
            return None
        
        def _extract_number(filepath):
            filename = os.path.basename(filepath)
            match = self._number_regex.search(filename)
            return int(match.group(1)) if match else 0
        
        log_files.sort(key=_extract_number, reverse=True)
        return log_files[0]
    
    def find_with_fallback(self, log_dir=None):
        """
        查找日志，支持备用路径回退
        """
        # 先尝试主目录
        latest = self.find_latest(log_dir)
        if latest:
            return latest
        
        # 尝试备用路径
        backup_paths = config.get('log.backup_paths', [])
        for path in backup_paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    @staticmethod
    def validate_path(path):
        """验证路径是否为有效文件"""
        return path and os.path.isfile(path)