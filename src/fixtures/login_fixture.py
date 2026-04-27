# -*- coding: utf-8 -*-
"""
登录 Fixture - 统一登录版本
优化策略：只在测试用例实际需要时才执行登录（懒加载），避免全量登录
"""
import os
import pytest
import time
from enum import Enum
from typing import Dict, Optional
from loguru import logger
from src.utils.yaml_loader import load_yaml_dict
from src.fixtures.fixtures import env_config, http_client


class LoginStatus(Enum):
    """登录状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class LoginToken:
    """登录 Token 类"""

    def __init__(
        self,
        token: str,
        headers: Dict[str, str],
        expires_at: Optional[float] = None,
        status: LoginStatus = LoginStatus.SUCCESS,
        error_message: Optional[str] = None
    ):
        self.token = token
        self.headers = headers
        self.expires_at = expires_at
        self.status = status
        self.error_message = error_message

    @property
    def is_success(self) -> bool:
        """检查登录是否成功"""
        return self.status == LoginStatus.SUCCESS

    def __repr__(self):
        if self.is_success:
            token_preview = self.token[:20] if len(self.token) >= 20 else self.token
            return f"LoginToken(token={token_preview}..., expires_at={self.expires_at}, status={self.status.value})"
        else:
            return f"LoginToken(status={self.status.value}, error={self.error_message})"


# ========================================
# 全局登录缓存（session 级）
# ========================================
_login_cache: Dict[str, Optional[LoginToken]] = {}


def _get_login_cache_key(base_url_alias: str, env_name: str) -> str:
    """生成登录缓存的键"""
    return f"{env_name}:{base_url_alias}"


def _load_login_file(
    base_url_alias: str,
    env_name: str,
    env_config: Dict
) -> Optional[Dict]:
    """
    加载登录用例文件（混合文件方案）
    优先级：
    1. test_{service_type}.yaml（独立文件）
    2. test.yaml（通用文件）
    重要：所有匹配都使用别名（如 operation、dsp），不使用完整 URL
    Returns:
        登录用例字典，如果找不到则返回 None
    """
    login_dir = os.path.join("test_data", "login")

    # 尝试加载独立文件：test_{service_type}.yaml
    independent_file = os.path.join(login_dir, f"test_{base_url_alias}.yaml")
    if os.path.exists(independent_file):
        logger.info(f"✅ 找到独立登录文件: {independent_file}")
        test_cases = load_yaml_dict(independent_file, default={"test_cases": []})
        return test_cases.get("test_cases", [])

    # 尝试加载通用文件：test.yaml
    common_file = os.path.join(login_dir, "test.yaml")
    if os.path.exists(common_file):
        logger.info(f"✅ 找到通用登录文件: {common_file}")
        test_cases = load_yaml_dict(common_file, default={"test_cases": []})

        # 过滤出匹配 base_url 别名的用例（统一使用别名匹配）
        filtered_cases = []
        for case in test_cases.get("test_cases", []):
            case_base_url = case.get("base_url", "")
            # 统一使用别名匹配（如 operation、dsp）
            if case_base_url == base_url_alias:
                filtered_cases.append(case)
            # 如果使用的是完整 URL，也尝试匹配（向后兼容）
            else:
                base_urls = env_config.get('base_urls', {})
                base_url_value = base_urls.get(base_url_alias, '')
                if case_base_url == base_url_value:
                    logger.warning(f"⚠️  通用文件中使用完整 URL，建议改为别名: {base_url_alias}")
                    filtered_cases.append(case)

        if filtered_cases:
            logger.info(f"✅ 在通用文件中找到 {len(filtered_cases)} 个匹配的登录用例（别名: {base_url_alias}）")
            return filtered_cases
        else:
            logger.warning(f"⚠️  通用文件中没有找到匹配别名 {base_url_alias} 的登录用例")

    logger.warning(f"⚠️  未找到 {base_url_alias} 的登录用例文件")
    return None


def _perform_login(
    http_client,
    env_name: str,
    env_config: Dict,
    base_url_alias: str
) -> LoginToken:
    """
    执行单个服务的登录操作
    Args:
        http_client: HTTP 客户端
        env_name: 环境名称
        env_config: 环境配置
        base_url_alias: base_url 别名（如 operation、dsp）
    Returns:
        LoginToken 对象，包含登录状态和结果信息
    """
    # 获取重试配置
    auth_config = env_config.get('auth', {})
    retry_config = auth_config.get('retry', {})
    max_retries = retry_config.get('max_retries', 3)  # 默认重试3次
    retry_delay = retry_config.get('retry_delay', 2)  # 默认重试间隔2秒
    timeout = retry_config.get('timeout', 30)  # 默认超时30秒

    logger.info(f"开始为 {base_url_alias} 执行登录（最多重试 {max_retries} 次，间隔 {retry_delay} 秒，超时 {timeout} 秒）...")

    # 加载登录用例
    test_cases = _load_login_file(base_url_alias, env_name, env_config)
    if not test_cases:
        error_msg = f"未找到 {base_url_alias} 的登录用例"
        logger.error(error_msg)
        return LoginToken(
            token="",
            headers={},
            status=LoginStatus.FAILED,
            error_message=error_msg
        )

    # 执行第一个登录用例
    login_case = test_cases[0]
    logger.debug(f"登录用例: {login_case}")

    # 构建请求
    # 优先使用登录用例中的 base_url（如果是完整 URL），否则使用环境配置
    case_base_url = login_case.get("base_url", "")
    if case_base_url.startswith("http://") or case_base_url.startswith("https://"):
        base_url = case_base_url
    else:
        # 使用环境配置中的 base_url（通过别名获取）
        base_urls = env_config.get('base_urls', {})
        base_url = base_urls.get(base_url_alias, '')

    if not base_url or not base_url.strip():
        error_msg = f"未找到有效的 base_url，别名: {base_url_alias}"
        logger.error(error_msg)
        return LoginToken(
            token="",
            headers={},
            status=LoginStatus.FAILED,
            error_message=error_msg
        )

    method = login_case.get("method", "POST")

    # 支持 url 和 path 两种字段
    case_url = login_case.get("url", "")
    case_path = login_case.get("path", "")

    if case_url and (case_url.startswith("http://") or case_url.startswith("https://")):
        # 如果 url 字段是完整 URL（以 http:// 或 https:// 开头），直接使用
        url = case_url
    elif case_path:
        # 如果使用 path 字段（相对路径），拼接 base_url
        url = f"{base_url}{case_path}"
    elif case_url:
        # 如果 url 字段是相对路径（不以 http:// 或 https:// 开头），拼接 base_url
        url = f"{base_url}{case_url}"
    else:
        error_msg = f"登录用例未配置 url 或 path"
        logger.error(error_msg)
        return LoginToken(
            token="",
            headers={},
            status=LoginStatus.FAILED,
            error_message=error_msg
        )

    headers = login_case.get("headers", {"Content-Type": "application/json"})
    body = login_case.get("body", {})
    params = login_case.get("params", {})

    # 重试逻辑
    last_error = None
    for attempt in range(max_retries):
        try:
            logger.info(f"发送登录请求（第 {attempt + 1}/{max_retries} 次）: {method} {url}")
            logger.debug(f"请求体: {body}")

            # 发送请求
            response = http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                params=params,
                timeout=timeout
            )

            logger.info(f"登录响应状态码: {response.get('status_code')}")
            logger.info(f"登录响应体: {response.get('body')}")

            # 验证响应
            assertions = login_case.get("assertions", [])
            if assertions:
                from src.core.validator import Validator
                validator = Validator()
                results = validator.validate(response, assertions)

                logger.info(f"登录断言结果: 共 {len(results)} 个断言")

                # 检查是否所有断言都通过
                for result in results:
                    if not result.passed:
                        error_msg = f"登录断言失败: {result.message}"
                        logger.error(
                            f"  断言类型: {result.assertion_type}, 实际值: {result.actual}, 期望值: {result.expected}")
                        last_error = error_msg

                        # 如果不是最后一次重试，继续重试
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️  {base_url_alias} 登录断言失败，{retry_delay} 秒后重试...")
                            time.sleep(retry_delay)
                            break
                        else:
                            # 最后一次重试失败，返回失败状态
                            return LoginToken(
                                token="",
                                headers={},
                                status=LoginStatus.FAILED,
                                error_message=error_msg
                            )
                    else:
                        logger.info(f"登录断言通过: {result.message}")

            # 提取 token
            extractions = login_case.get("extractions", [])
            if not extractions:
                error_msg = f"登录用例未配置 extractions，无法提取 token"
                logger.error(error_msg)
                return LoginToken(
                    token="",
                    headers={},
                    status=LoginStatus.FAILED,
                    error_message=error_msg
                )

            # 从响应中提取 token
            from src.utils.extractor import Extractor
            extractor = Extractor()

            # 将 extractions 列表转换为字典格式
            extraction_dict = {}
            for item in extractions:
                name = item.get('name')
                extraction_type = item.get('type', 'jsonpath')
                expression = item.get('expression', '')
                if name:
                    extraction_dict[name] = {'type': extraction_type, 'expression': expression}

            extracted = extractor.extract(response, extraction_dict)

            logger.info(f"提取结果: {extracted}")

            token = extracted.get("auth_token")
            if not token or not token.strip():
                error_msg = f"未能从响应中提取到有效的 token"
                logger.error(error_msg)
                last_error = error_msg

                # 如果不是最后一次重试，继续重试
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️  {base_url_alias} 提取 token 失败，{retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    # 最后一次重试失败，返回失败状态
                    return LoginToken(
                        token="",
                        headers={},
                        status=LoginStatus.FAILED,
                        error_message=error_msg
                    )

            token_preview = token[:20] if len(token) >= 20 else token
            logger.info(f"✅ {base_url_alias} 登录成功，token: {token_preview}...")

            # 构建请求头
            auth_headers = headers.copy()
            auth_headers["Authorization"] = f"Bearer {token}"

            return LoginToken(
                token=token,
                headers=auth_headers,
                expires_at=None,
                status=LoginStatus.SUCCESS
            )

        except Exception as e:
            last_error = str(e)
            logger.exception(f"{base_url_alias} 登录过程中发生异常（第 {attempt + 1}/{max_retries} 次）")

            # 如果不是最后一次重试，继续重试
            if attempt < max_retries - 1:
                logger.warning(f"⚠️  {base_url_alias} 登录异常，{retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                # 最后一次重试失败，返回失败状态
                return LoginToken(
                    token="",
                    headers={},
                    status=LoginStatus.FAILED,
                    error_message=last_error
                )

    # 所有重试都失败
    error_msg = f"{base_url_alias} 登录失败，已重试 {max_retries} 次。最后错误: {last_error}"
    logger.error(error_msg)
    return LoginToken(
        token="",
        headers={},
        status=LoginStatus.FAILED,
        error_message=error_msg
    )


def get_service_headers(
    service_type: str,
    http_client,
    env_name: str,
    env_config: Dict,
    force_refresh: bool = False
) -> Dict[str, str]:
    """
    获取指定服务的请求头（懒加载 + 缓存）
    这是懒加载登录的核心函数：
    - 首次请求时执行登录
    - 后续请求从缓存中获取
    - 支持强制刷新缓存
    - 登录失败会缓存失败状态，避免重复尝试
    Args:
        service_type: 服务类型（如 operation、dsp）
        http_client: HTTP 客户端
        env_name: 环境名称
        env_config: 环境配置
        force_refresh: 是否强制刷新缓存
    Returns:
        请求头字典（登录成功返回带认证的 headers，失败返回默认 headers）
    """
    # 检查缓存
    cache_key = _get_login_cache_key(service_type, env_name)

    if not force_refresh and cache_key in _login_cache:
        login_token = _login_cache[cache_key]
        if login_token:
            if login_token.is_success:
                logger.info(f"✅ 从缓存获取 {service_type} 的请求头（登录成功）")
                return login_token.headers
            else:
                # 登录失败，记录警告并返回默认 headers
                logger.warning(f"⚠️  {service_type} 的登录已缓存但失败: {login_token.error_message}")
                logger.warning(f"⚠️  {service_type} 后续用例将被跳过")

    # 执行登录
    login_token = _perform_login(http_client, env_name, env_config, service_type)

    # 缓存结果（包括失败状态）
    _login_cache[cache_key] = login_token

    if login_token.is_success:
        return login_token.headers
    else:
        # 登录失败，返回默认 headers
        default_headers = env_config.get('headers', {
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        logger.error(f"❌ {service_type} 登录失败: {login_token.error_message}")
        logger.error(f"❌ {service_type} 后续用例将被跳过")
        return default_headers

def get_login_status(service_type: str, env_name: str) -> LoginStatus:
    """
    获取指定服务的登录状态
    Args:
        service_type: 服务类型（如 operation、dsp）
        env_name: 环境名称
    Returns:
        登录状态（SUCCESS/FAILED/PENDING）
    """
    cache_key = _get_login_cache_key(service_type, env_name)
    if cache_key in _login_cache:
        login_token = _login_cache[cache_key]
        if login_token:
            return login_token.status
    return LoginStatus.PENDING

def get_login_error_message(service_type: str, env_name: str) -> Optional[str]:
    """
    获取指定服务的登录失败错误信息
    Args:
        service_type: 服务类型（如 operation、dsp）
        env_name: 环境名称
    Returns:
        错误信息，如果登录成功或未登录则返回 None
    """
    cache_key = _get_login_cache_key(service_type, env_name)
    if cache_key in _login_cache:
        login_token = _login_cache[cache_key]
        if login_token and not login_token.is_success:
            return login_token.error_message
    return None


# ========================================
# Fixtures
# ========================================

@pytest.fixture(scope="session")
def login_cache():
    """
    登录缓存 fixture（session 级）
    功能：
    - 提供全局登录缓存
    - 在 session 结束时清空缓存
    Returns:
        登录缓存字典
    """
    global _login_cache
    _login_cache = {}

    yield _login_cache

    # 清空缓存
    logger.info("清空登录缓存")
    _login_cache.clear()


@pytest.fixture(scope="session")
def login_tokens(http_client, env_config, login_cache) -> Dict[str, Optional[LoginToken]]:
    """
    Token Fixture（兼容旧版）
    注意：此 fixture 为向后兼容保留，但不会执行实际登录
    实际登录由 get_service_headers 按需执行
    Returns:
        空的 token 字典（实际登录按需执行）
    """
    logger.info("=" * 60)
    logger.info("初始化懒加载登录机制（登录按需执行）")
    logger.info("=" * 60)

    return {}


@pytest.fixture(scope="session")
def service_headers(http_client, env_config, login_cache) -> Dict[str, Dict[str, str]]:
    """
    服务 Headers Fixture（兼容旧版）

    注意：此 fixture 为向后兼容保留
    实际推荐使用 auth_headers fixture

    Returns:
        空的 headers 字典（实际登录按需执行）
    """
    logger.info("=" * 60)
    logger.info("初始化懒加载服务 Headers（登录按需执行）")
    logger.info("=" * 60)

    base_urls = env_config.get('base_urls', {})
    return {alias: {} for alias in base_urls.keys()}


@pytest.fixture(scope="function")
def auth_headers(request, http_client, env_config, login_cache) -> Dict[str, str]:
    """
    请求头（根据用例的 base_url 自动选择并登录）
    功能：
    - 根据测试用例的 base_url 自动识别服务类型
    - 按需执行登录（首次需要时）
    - 使用缓存避免重复登录
    - 如果未找到对应服务或登录失败，使用默认 headers
    使用方式：
    在测试用例中添加 `auth_headers` 参数即可自动注入对应服务的 headers
    Returns:
        Dict[str, str]: headers
    """
    # 获取环境名称
    env_name = os.getenv('TEST_ENV', 'test')

    # 从测试用例中获取 base_url
    base_url = None
    service_type = None

    # 方法1: 从测试用例的属性中获取
    if hasattr(request, 'node') and hasattr(request.node, 'obj'):
        test_func = request.node.obj
        if hasattr(test_func, '_test_case'):
            base_url = test_func._test_case.get('base_url')

    # 方法2: 从用例的 markers 中获取
    if not base_url:
        for marker in request.node.iter_markers():
            if marker.name == 'parametrize' and 'base_url' in marker.kwargs:
                base_url = marker.kwargs['base_url']
                break

    # 方法3: 尝试从测试用例的参数中推断
    if not base_url:
        # 检查测试用例的参数中是否有 service_type 或 base_url 相关的字段
        # 这里需要根据实际用例结构进行调整
        logger.debug("无法从测试用例属性中获取 base_url")

    # 如果获取到了 base_url，推断 service_type（统一使用别名匹配）
    if base_url:
        base_urls = env_config.get('base_urls', {})

        # 方法1: 按 base_url 别名匹配（如 operation、dsp）
        if base_url in base_urls:
            service_type = base_url
        else:
            # 方法2: 按 base_url 值匹配（向后兼容）
            for alias, url in base_urls.items():
                if url == base_url or base_url.startswith(url):
                    logger.warning(f"⚠️  测试用例使用完整 URL，建议改为别名: {alias}")
                    service_type = alias
                    break

        logger.debug(f"base_url={base_url}, 推断的 service_type={service_type}")

    # 如果推断出了 service_type，获取对应的 headers（懒加载登录）
    if service_type:
        logger.info(f"按需获取 {service_type} 的请求头（如果尚未登录则会执行登录）")

        # 执行懒加载登录（移除 required_services 白名单检查，完全按需登录）
        headers = get_service_headers(
            service_type=service_type,
            http_client=http_client,
            env_name=env_name,
            env_config=env_config
        )
        return headers

    # 如果无法推断 service_type，使用默认 headers
    default_headers = env_config.get('headers', {
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    logger.warning(f"⚠️  无法推断 service_type，使用默认 headers")

    return default_headers


@pytest.fixture(scope="function")
def multi_service_headers(request, http_client, env_config, login_cache) -> Dict[str, Dict[str, str]]:
    """
    多服务请求头（支持一次请求多个服务的 headers）

    功能：
    - 根据测试用例中指定的服务类型列表，返回多个服务的 headers
    - 按需执行登录
    - 使用缓存避免重复登录

    使用方式：
    在测试用例中添加 `services=['operation', 'dsp']` 参数

    Returns:
        Dict[str, Dict[str, str]]: {service_type: headers}
    """
    # 获取环境名称
    env_name = os.getenv('TEST_ENV', 'test')

    # 从测试用例中获取需要的服务类型列表
    required_services = []

    if hasattr(request, 'node') and hasattr(request.node, 'obj'):
        test_func = request.node.obj
        if hasattr(test_func, '_test_case'):
            test_case = test_func._test_case
            # 支持从 test_case 中读取 services 字段
            required_services = test_case.get('services', [])

    # 如果没有指定服务，返回空字典（懒加载应由用例显式指定）
    if not required_services:
        logger.warning(f"⚠️  测试用例未指定 services 字段，返回空 headers 字典")
        return {}

    logger.info(f"需要获取 headers 的服务: {required_services}")

    headers_dict = {}
    for service_type in required_services:
        headers = get_service_headers(
            service_type=service_type,
            http_client=http_client,
            env_name=env_name,
            env_config=env_config
        )
        headers_dict[service_type] = headers

    return headers_dict
