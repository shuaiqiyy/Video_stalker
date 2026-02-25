import json
import os
from pathlib import Path


class Config:
    """配置管理类 - 单例模式"""
    
    _instance = None
    _config_data = None
    
    def __new__(cls, config_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path or cls._default_path())
        return cls._instance
    
    @staticmethod
    def _default_path():
        """获取默认配置文件路径（与脚本同目录）"""
        return Path(__file__).parent / "config.json"
    
    def _load(self, path):
        """加载JSON配置文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        self._config_data = self._expand_env_vars(raw_data)
    
    @staticmethod
    def _expand_env_vars(obj):
        """递归展开环境变量（如 %USERPROFILE%）"""
        if isinstance(obj, dict):
            return {k: Config._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Config._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return os.path.expandvars(obj)
        return obj
    
    def get(self, key_path, default=None):
        """
        获取配置值，支持点号路径如 'process.name'
        
        Args:
            key_path: 配置键路径，如 "log.directory"
            default: 默认值
        """
        keys = key_path.split('.')
        value = self._config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def __getitem__(self, key):
        """支持 config['key'] 访问"""
        return self._config_data[key]
    
    @property
    def raw(self):
        """获取原始配置字典"""
        return self._config_data.copy()


# 全局配置实例（首次导入时加载）
config = Config()