# -*- coding: utf-8 -*-
"""
统一配置管理器
提供配置加载和缓存功能，避免重复加载配置文件
"""
from typing import Any, Dict, Optional
from pathlib import Path
from config import CONFIG_FILE, get_env_config_file
from src.utils.yaml_loader import load_yaml_dict
from src.utils.logger import logger


class ConfigManager:
    """配置管理器单例类"""

    _instance: Optional['ConfigManager'] = None
    _initialized: bool = False

    def __new__(cls) -> 'ConfigManager':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if not self._initialized:
            self._config_cache: Dict[str, Dict[str, Any]] = {}
            self._initialized = True
            logger.debug("配置管理器初始化完成")

    def get_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取主配置
        Args:
            force_reload: 是否强制重新加载
        Returns:
            Dict: 主配置字典
        """
        return self.load_config('main', CONFIG_FILE, force_reload)

    def get_env_config(self, env: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取环境配置
        Args:
            env: 环境名称，默认为 None，从主配置中读取
            force_reload: 是否强制重新加载
        Returns:
            Dict: 环境配置字典
        """
        if env is None:
            env = self.get_config().get('default_env', 'test')

        cache_key = f'env_{env}'
        env_file = get_env_config_file(env)

        return self.load_config(cache_key, env_file, force_reload)

    def load_config(self, cache_key: str, config_file: Path, force_reload: bool = False) -> Dict[str, Any]:
        """
        加载配置文件
        Args:
            cache_key: 缓存键
            config_file: 配置文件路径
            force_reload: 是否强制重新加载
        Returns:
            Dict: 配置字典
        """
        # 检查缓存
        if not force_reload and cache_key in self._config_cache:
            logger.debug(f"从缓存加载配置: {cache_key}")
            return self._config_cache[cache_key]

        # 加载配置
        if config_file.exists():
            config = load_yaml_dict(config_file, default={})
            self._config_cache[cache_key] = config
            logger.debug(f"已加载配置: {config_file}")
        else:
            logger.warning(f"配置文件不存在: {config_file}")
            config = {}
            self._config_cache[cache_key] = config

        return config

    def get(self, key: str, default: Any = None, env: Optional[str] = None) -> Any:
        """
        获取配置值
        优先从环境配置中获取，如果没有则从主配置中获取
        Args:
            key: 配置键（支持点号分隔，如 'http_client.timeout'）
            default: 默认值
            env: 环境名称
        Returns:
            Any: 配置值
        """
        env_config = self.get_env_config(env)
        config = self.get_config()

        # 优先从环境配置中获取
        value = self._get_nested_value(env_config, key)
        if value is not None:
            return value

        # 从主配置中获取
        value = self._get_nested_value(config, key)

        return value if value is not None else default

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], key: str) -> Any:
        """
        获取嵌套字典中的值
        Args:
            data: 数据字典
            key: 键（支持点号分隔）
        Returns:
            Any: 值
        """
        keys = key.split('.')
        value = data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value

    def reload(self):
        """清除所有缓存，强制重新加载"""
        self._config_cache.clear()
        logger.debug("已清除配置缓存")

    def clear_env_cache(self, env: str):
        """清除指定环境的缓存"""
        cache_key = f'env_{env}'
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
            logger.debug(f"已清除环境配置缓存: {env}")


# 全局实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    获取配置管理器实例
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
