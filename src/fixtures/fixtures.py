# -*- coding: utf-8 -*-
"""
基础 Fixtures 模块
提供测试会话、上下文、客户端等基础 fixtures
"""
import os
import pytest
from config import CONFIG_FILE, get_env_config_file
from src.utils.yaml_loader import load_yaml_dict
from src.utils.logger import logger
from src.core.client import create_client
from src.core.context import get_context
from src.core.validator import Validator
from src.utils.extractor import get_extractor


@pytest.fixture(scope="session", autouse=True)
def setup_session(http_client, env_config, default_headers, config):
    """
    会话级fixture，在整个测试会话开始前执行一次
    """
    logger.info("=" * 60)
    logger.info("测试会话开始")
    logger.info(f"当前环境：{config.get('default_env', 'N/A')}")
    base_urls = env_config.get('base_urls', {})
    logger.info(f"可用 base_url: {list(base_urls.keys()) if base_urls else '无'}")
    logger.info("=" * 60)

    # 注意：全局登录逻辑已移除
    # 登录功能现在通过 auth_token fixture 实现
    # 登录配置从 test_data/login/{env_name}.yaml 读取
    # 测试用例可以选择是否使用登录 token

    # 设置默认请求头到全局 context
    context = get_context()
    context.set_default_headers(default_headers)
    logger.info(f"已设置默认请求头: {default_headers}")

    yield

    logger.info("=" * 60)
    logger.info("测试会话结束")
    logger.info("=" * 60)


@pytest.fixture(scope="function")
def test_context():
    """
    测试用例级fixture，每个用例都会创建新的上下文
    """
    context = get_context()

    yield context

    # 清空局部变量
    context.clear_local()


@pytest.fixture(scope="session")
def config():
    """
    配置fixture
    """
    return load_yaml_dict(CONFIG_FILE, default={})


@pytest.fixture(scope="session")
def env_config(config):
    """
    环境配置fixture
    """
    env = os.environ.get('TEST_ENV', config.get('default_env', 'test'))
    env_file = get_env_config_file(env)
    return load_yaml_dict(env_file, default={})


@pytest.fixture(scope="session")
def http_client(config):
    """
    HTTP客户端fixture
    """
    http_config = config.get('http_client', {})
    client_type = http_config.get('type', 'requests')

    client = create_client(client_type, http_config)

    yield client

    # 清理
    client.close()


@pytest.fixture
def validator():
    """
    断言验证器fixture
    """
    return Validator()


@pytest.fixture
def extractor():
    """
    数据提取器fixture
    """
    return get_extractor()


@pytest.fixture(scope="session")
def default_headers(env_config):
    """
    默认请求头fixture
    从 env 配置中获取默认请求头，包括：
    - Content-Type
    - Accept
    - User-Agent
    注意：Authorization 不再自动添加，需要测试用例通过 auth_token fixture 获取
    Returns:
        Dict: 默认请求头字典
    """
    headers = {}

    # 从 env 配置获取默认请求头
    env_headers = env_config.get('headers', {})

    # 默认请求头
    default_headers_map = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    }

    # 合并默认请求头（env 配置优先）
    headers.update(default_headers_map)
    headers.update(env_headers)

    logger.debug(f"默认请求头: {headers}")

    return headers
