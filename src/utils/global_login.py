# -*- coding: utf-8 -*-
"""
全局登录工具
支持全局前置登录、Token 管理
Token 过期时自动重新登录
"""
import time
from typing import Dict, Any, Optional
from src.utils.logger import log as logger
from src.core.client import BaseHTTPClient
from src.utils.yaml_loader import load_yaml_dict
from src.utils.extractor import get_extractor


class GlobalLogin:
    """全局登录管理器"""

    _instance = None
    _token = None
    _token_expire_time = 0
    _config = None
    _env_config = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取全局登录配置
        Returns:
            Dict[str, Any]: 配置字典
        """
        if cls._config is None:
            config = load_yaml_dict("config/config.yaml", default={})
            cls._config = config.get('global_login', {})
        return cls._config

    @classmethod
    def set_env_config(cls, env_config: Dict[str, Any]):
        """
        设置环境配置
        Args:
            env_config: 环境配置字典
        """
        cls._env_config = env_config

    @classmethod
    def get_env_config(cls) -> Dict[str, Any]:
        """
        获取环境配置
        Returns:
            Dict[str, Any]: 环境配置字典
        """
        return cls._env_config or {}

    @classmethod
    def is_enabled(cls) -> bool:
        """
        检查是否启用全局登录
        Returns:
            bool: 是否启用
        """
        config = cls.get_config()
        return config.get('enable', False)

    @classmethod
    def get_token(cls) -> Optional[str]:
        """
        获取当前的 Token
        Returns:
            Optional[str]: Token 字符串
        """
        return cls._token

    @classmethod
    def get_auth_header(cls) -> Optional[str]:
        """
        获取 Authorization header 值
        Returns:
            Optional[str]: Authorization header 值，如 "Bearer xxx"
        """
        if cls._token is None:
            return None

        config = cls.get_config()
        token_type = config.get('token_type', 'Bearer')
        return f"{token_type} {cls._token}"

    @classmethod
    def is_token_expired(cls) -> bool:
        """
        检查 Token 是否过期
        Returns:
            bool: 是否过期
        """
        if cls._token is None:
            return True

        config = cls.get_config()
        token_ttl = config.get('token_ttl', 0)

        if token_ttl == 0:
            # 永不过期
            return False

        return time.time() > cls._token_expire_time

    @classmethod
    def login(cls, client: BaseHTTPClient, env_config: Optional[Dict[str, Any]] =  None) -> bool:
        """
        执行全局登录
        Args:
            client: HTTP 客户端
            env_config: 环境配置（包含base_url 和 auth 配置）
        Returns:
            bool: 是否登录成功
        """
        config = cls.get_config()

        # 设置环境配置
        if env_config:
            cls.set_env_config(env_config)
        else:
            env_config = cls.get_env_config()

        if not config.get('enable', False):
            logger.info("全局登录未启用")
            return False

        try:
            # 从 env 配置获取基础配置
            base_url = env_config.get('base_url', '')
            auth_config = env_config.get('auth', {})

            # 从 env 配置获取登录信息（优先级高于 config.yaml）
            login_url = config.get('login_url', '/prod-api/login')
            request_method = config.get('request_method', 'POST').upper()
            request_body_type = config.get('request_body_type', 'json')

            # 优先使用 env 配置中的 auth 信息
            username = auth_config.get('username') or config.get('username', 'Lee')
            password = auth_config.get('password') or config.get('password', 'Working@1130')

            headers = config.get('headers', {})
            body_template = config.get('body_template', '')

            # 构建完整的登录 URL
            if base_url and not login_url.startswith(('http://', 'https://')):
                if not login_url.startswith('/'):
                    login_url = f'/{login_url}'
                login_url = f'{base_url}{login_url}'

            # 构建请求体
            body_str = body_template.replace('${username}', username).replace('${password}', password)

            if request_body_type == 'json':
                import json
                body = json.loads(body_str)
            else:
                body = body_str

            # 发送登录请求
            logger.info(f"开始全局登录: {request_method} {login_url}")
            logger.debug(f"登录用户: {username}")

            response = client.request(
                method=request_method,
                url=login_url,
                headers=headers,
                json=body if request_body_type == 'json' else None,
                data=body if request_body_type != 'json' else None
            )

            # 检查响应
            if response.get('status_code') != 200:
                logger.error(f"全局登录失败: 状态码 {response.get('status_code')}")
                logger.error(f"响应内容: {response.get('body', {})}")
                return False

            response_body = response.get('body', {})

            # 提取 Token
            token_path = config.get('token_path', '$.token')
            extractor = get_extractor()

            try:
                extracted = extractor.extract(response_body, {'token': {'expression': token_path}})
                token = extracted.get('token')

                if not token:
                    logger.error("全局登录失败: 无法提取 Token")
                    logger.error(f"Token 提取路径: {token_path}")
                    logger.error(f"响应内容: {response_body}")
                    return False

                # 保存 Token
                cls._token = token
                cls._token_expire_time = time.time() + config.get('token_ttl', 0)

                logger.info(f"全局登录成功: Token 有效期 {config.get('token_ttl', 0)} 秒")
                return True

            except Exception as e:
                logger.error(f"全局登录失败: Token 提取错误 - {str(e)}")
                return False

        except Exception as e:
            logger.error(f"全局登录失败: {str(e)}")
            return False

    @classmethod
    def ensure_token(cls, client: BaseHTTPClient) -> bool:
        """
        确保 Token 有效（如果不存在或已过期，则重新登录）
        Args:
            client: HTTP 客户端
        Returns:
            bool: 是否成功获取有效 Token
        """
        # 检查是否启用全局登录
        if not cls.is_enabled():
            return True

        # 检查 Token 是否存在且未过期
        if cls._token is not None and not cls.is_token_expired():
            return True

        # Token 不存在或已过期，重新登录
        logger.info("Token 不存在或已过期，重新登录")
        return cls.login(client)

    @classmethod
    def logout(cls):
        """登出（清除 Token）"""
        logger.info("执行全局登出")
        cls._token = None
        cls._token_expire_time = 0


def get_global_login() -> GlobalLogin:
    """
    获取全局登录实例
    Returns:
        GlobalLogin: 全局登录实例
    """
    return GlobalLogin()
