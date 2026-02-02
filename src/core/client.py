"""
HTTP客户端封装
支持 requests 和 httpx 两种方式，可平滑切换
"""

import time
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
from src.utils.logger import log as logger


class BaseHTTPClient(ABC):
    """HTTP客户端基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_interval = config.get('retry_interval', 1)
        
    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: 请求方法 GET/POST/PUT/DELETE/PATCH
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            Dict: 包含响应信息的字典
        """
        pass
    
    @abstractmethod
    def close(self):
        """关闭客户端连接"""
        pass


class RequestsClient(BaseHTTPClient):
    """Requests客户端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests库未安装，请运行: pip install requests")
        
        # 创建session
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_interval,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info("Requests客户端初始化成功")
    
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        json: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None,
        verify: bool = True,
        allow_redirects: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: 请求方法
            url: 请求URL
            headers: 请求头
            params: URL参数
            data: 请求体（表单/文本/二进制）
            json: 请求体（JSON）
            files: 上传文件
            timeout: 超时时间
            verify: 是否验证SSL证书
            allow_redirects: 是否允许重定向
            
        Returns:
            Dict: 响应信息
        """
        timeout = timeout or self.timeout
        request_time = time.time()
        
        try:
            logger.debug(f"发送请求: {method} {url}")
            logger.debug(f"请求头: {headers}")
            logger.debug(f"请求参数: {params}")
            logger.debug(f"请求体: {json or data}")
            
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                files=files,
                timeout=timeout,
                verify=verify,
                allow_redirects=allow_redirects,
                **kwargs
            )
            
            elapsed = time.time() - request_time
            
            # 尝试解析JSON响应
            try:
                response_json = response.json()
            except ValueError:
                response_json = response.text
            
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_json,
                'text': response.text,
                'elapsed': elapsed,
                'cookies': dict(response.cookies),
                'request': {
                    'method': method.upper(),
                    'url': url,
                    'headers': headers,
                    'params': params,
                    'body': json or data
                }
            }
            
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应耗时: {elapsed:.3f}s")
            logger.debug(f"响应体: {response_json}")
            
            return result
            
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {method} {url} - {str(e)}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接错误: {method} {url} - {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {method} {url} - {str(e)}")
            raise
    
    def close(self):
        """关闭Session"""
        self.session.close()
        logger.info("Requests客户端已关闭")


class HTTPXClient(BaseHTTPClient):
    """HTTPX客户端实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx库未安装，请运行: pip install httpx")
        
        # 创建异步和同步客户端
        limits = httpx.Limits(
            max_connections=config.get('max_connections', 100),
            max_keepalive_connections=config.get('max_keepalive_connections', 20)
        )
        
        # 同步客户端
        self.client = httpx.Client(
            timeout=self.timeout,
            limits=limits,
            verify=True
        )
        
        logger.info("HTTPX客户端初始化成功")
    
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        json: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None,
        verify: bool = True,
        allow_redirects: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: 请求方法
            url: 请求URL
            headers: 请求头
            params: URL参数
            data: 请求体
            json: 请求体（JSON）
            files: 上传文件
            timeout: 超时时间
            verify: 是否验证SSL证书
            allow_redirects: 是否允许重定向
            
        Returns:
            Dict: 响应信息
        """
        timeout = timeout or self.timeout
        request_time = time.time()
        
        try:
            logger.debug(f"发送请求: {method} {url}")
            logger.debug(f"请求头: {headers}")
            logger.debug(f"请求参数: {params}")
            logger.debug(f"请求体: {json or data}")
            
            response = self.client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                files=files,
                timeout=timeout,
                verify=verify,
                follow_redirects=allow_redirects,
                **kwargs
            )
            
            elapsed = time.time() - request_time
            
            # 尝试解析JSON响应
            try:
                response_json = response.json()
            except ValueError:
                response_json = response.text
            
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_json,
                'text': response.text,
                'elapsed': elapsed,
                'cookies': dict(response.cookies),
                'request': {
                    'method': method.upper(),
                    'url': url,
                    'headers': headers,
                    'params': params,
                    'body': json or data
                }
            }
            
            logger.debug(f"响应状态码: {response.status_code}")
            logger.debug(f"响应耗时: {elapsed:.3f}s")
            logger.debug(f"响应体: {response_json}")
            
            return result
            
        except httpx.TimeoutException as e:
            logger.error(f"请求超时: {method} {url} - {str(e)}")
            raise
        except httpx.ConnectError as e:
            logger.error(f"连接错误: {method} {url} - {str(e)}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP错误: {method} {url} - {str(e)}")
            raise
    
    def close(self):
        """关闭客户端"""
        self.client.close()
        logger.info("HTTPX客户端已关闭")


def create_client(client_type: str, config: Dict[str, Any]) -> BaseHTTPClient:
    """
    创建HTTP客户端工厂方法
    
    Args:
        client_type: 客户端类型 'requests' 或 'httpx'
        config: 配置字典
        
    Returns:
        BaseHTTPClient: HTTP客户端实例
        
    Raises:
        ValueError: 不支持的客户端类型
    """
    client_type = client_type.lower()
    
    if client_type == 'requests':
        return RequestsClient(config)
    elif client_type == 'httpx':
        return HTTPXClient(config)
    else:
        raise ValueError(f"不支持的客户端类型: {client_type}, 可选: requests, httpx")
