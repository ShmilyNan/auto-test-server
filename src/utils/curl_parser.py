"""
cURL 解析器
将 cURL 命令解析为结构化数据
"""
import json
import shlex
from typing import Dict, List, Any
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from src.utils.logger import logger


@dataclass
class CurlRequest:
    """解析后的 cURL 请求数据"""
    method: str  # HTTP 方法: GET, POST, PUT, DELETE
    url: str  # 完整 URL
    headers: Dict[str, str]  # 请求头
    cookies: Dict[str, str]  # Cookies
    data: Any  # 请求体 (可以是 dict, str 或 None)
    params: Dict[str, Any]  # URL 参数
    is_compressed: bool  # 是否启用压缩
    insecure: bool  # 是否忽略 SSL 证书验证

    def get_path(self) -> str:
        """获取 URL 路径（不含域名）"""
        parsed = urlparse(self.url)
        return parsed.path

    def get_url_without_params(self) -> str:
        """获取不含查询参数的 URL"""
        parsed = urlparse(self.url)
        url_without_params = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return url_without_params


class CurlParser:
    """cURL 命令解析器"""

    def __init__(self):
        self._reset()

    def _reset(self):
        """重置解析状态"""
        self.method = "GET"
        self.url = None
        self.headers = {}
        self.cookies = {}
        self.data = None
        self.is_compressed = False
        self.insecure = False
        self._current_arg = None
        self._expect_data = False
        self._expect_header = False

    def parse(self, curl_command: str) -> CurlRequest:
        """
        解析 cURL 命令
        Args:
            curl_command: cURL 命令字符串
        Returns:
            CurlRequest: 解析后的请求对象
        Raises:
            ValueError: 命令格式错误
        """
        self._reset()

        # 移除续行符
        curl_command = curl_command.replace('\\\n', ' ').replace('\\\r\n', ' ')
        curl_command = curl_command.strip()

        # 提取命令参数
        try:
            # 使用 shlex.split 处理引号
            parts = shlex.split(curl_command)
        except ValueError:
            # 如果 shlex 失败，尝试简单分割
            parts = curl_command.split()

        if not parts or parts[0].lower() != 'curl':
            raise ValueError("不是有效的 cURL 命令")

        # 解析参数
        i = 1
        while i < len(parts):
            part = parts[i]

            # 处理选项
            if part.startswith('-'):
                self._parse_option(part, parts, i)
                i += 1
            # 处理 URL（非选项参数）
            elif self.url is None and (part.startswith('http://') or part.startswith('https://')):
                self.url = part

                i += 1
            else:
                i += 1

        # 验证必要信息
        if not self.url:
            raise ValueError("cURL 命令缺少 URL")

        # 确定 HTTP 方法
        if self.data is not None:
            self.method = "POST"

        # 解析 URL 参数
        parsed_url = urlparse(self.url)
        url_params = parse_qs(parsed_url.query)
        # 将列表参数转换为单值（取第一个）
        params = {k: v[0] if v else '' for k, v in url_params.items()}

        # 创建请求对象
        request = CurlRequest(
            method=self.method.upper(),
            url=self.url,
            headers=self.headers,
            cookies=self.cookies,
            data=self.data,
            params=params,
            is_compressed=self.is_compressed,
            insecure=self.insecure
        )

        logger.info(f"成功解析 cURL 命令: {self.method} {self.url}")

        return request

    def _parse_option(self, option: str, parts: List[str], index: int):
        """
        解析选项参数

        Args:
            option: 选项字符串
            parts: 所有参数列表
            index: 当前索引
        """
        # 长选项
        if option.startswith('--'):
            option_name = option[2:]

            if option_name == 'request':
                # 指定 HTTP 方法
                if index + 1 < len(parts):
                    self.method = parts[index + 1].upper()
            elif option_name == 'header':
                # 请求头
                if index + 1 < len(parts):
                    self._parse_header(parts[index + 1])
            elif option_name == 'data':
                # 请求体
                if index + 1 < len(parts):
                    self._parse_data(parts[index + 1])
            elif option_name == 'data-raw':
                # 请求体（raw）
                if index + 1 < len(parts):
                    self._parse_data(parts[index + 1])
            elif option_name == 'data-urlencode':
                # 请求体（URL 编码）
                if index + 1 < len(parts):
                    self._parse_data(parts[index + 1], is_urlencoded=True)
            elif option_name == 'cookie':
                # Cookie
                if index + 1 < len(parts):
                    self._parse_cookie(parts[index + 1])
            elif option_name == 'compressed':
                # 启用压缩
                self.is_compressed = True
            elif option_name == 'insecure':
                # 忽略 SSL 证书
                self.insecure = True
            elif option_name == 'user-agent':
                # User-Agent
                if index + 1 < len(parts):
                    self.headers['User-Agent'] = parts[index + 1]
            elif option_name == 'referer':
                # Referer
                if index + 1 < len(parts):
                    self.headers['Referer'] = parts[index + 1]
            elif option_name == 'user':
                # 认证用户名密码
                if index + 1 < len(parts):
                    self.headers['Authorization'] = parts[index + 1]

        # 短选项
        elif option.startswith('-'):
            option_name = option[1:]

            if option_name == 'X':
                # 指定 HTTP 方法
                if index + 1 < len(parts):
                    self.method = parts[index + 1].upper()
            elif option_name == 'H':
                # 请求头
                if index + 1 < len(parts):
                    self._parse_header(parts[index + 1])
            elif option_name == 'd':
                # 请求体
                if index + 1 < len(parts):
                    self._parse_data(parts[index + 1])
            elif option_name == 'b':
                # Cookie
                if index + 1 < len(parts):
                    self._parse_cookie(parts[index + 1])
            elif option_name == 'k':
                # 忽略 SSL 证书
                self.insecure = True
            elif option_name == 'A':
                # User-Agent
                if index + 1 < len(parts):
                    self.headers['User-Agent'] = parts[index + 1]
            elif option_name == 'e':
                # Referer
                if index + 1 < len(parts):
                    self.headers['Referer'] = parts[index + 1]

    def _parse_header(self, header_str: str):
        """
        解析请求头

        Args:
            header_str: 请求头字符串，格式: "key: value"
        """
        # 分割 key 和 value
        if ':' in header_str:
            parts = header_str.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
            # 标准化 header 名称（首字母大写）
            key = '-'.join(word.capitalize() for word in key.split('-'))
            self.headers[key] = value
            logger.debug(f"解析请求头: {key} = {value[:50]}...")

    def _parse_cookie(self, cookie_str: str):
        """
        解析 Cookie

        Args:
            cookie_str: Cookie 字符串，格式: "name=value; name2=value2"
        """
        # 分割多个 cookie
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.cookies[name.strip()] = value.strip()

        if self.cookies:
            logger.debug(f"解析 Cookies: {len(self.cookies)} 个")

    def _parse_data(self, data_str: str, is_urlencoded: bool = False):
        """
        解析请求体
        Args:
            data_str: 数据字符串
            is_urlencoded: 是否为 URL 编码数据
        """
        # 尝试解析为 JSON
        if not is_urlencoded:
            try:
                self.data = json.loads(data_str)
                logger.debug("请求体解析为 JSON 格式")
                return
            except json.JSONDecodeError:
                pass

        # URL 编码数据
        if is_urlencoded or '=' in data_str and data_str.count('=') > 1:
            params = {}
            for param in data_str.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    # 解码
                    import urllib.parse
                    params[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
            self.data = params
            logger.debug("请求体解析为表单格式")
        else:
            # 原始字符串
            self.data = data_str
            logger.debug("请求体解析为原始字符串")


def parse_curl_command(curl_command: str) -> CurlRequest:
    """
    便捷函数：解析 cURL 命令
    Args:
        curl_command: cURL 命令字符串
    Returns:
        CurlRequest: 解析后的请求对象
    """
    parser = CurlParser()
    return parser.parse(curl_command)


if __name__ == "__main__":
    # 测试用例
    get_curl = """curl 'https://dev-aly-us-ad-web.cdcicd.com/prod-api/report/template/list?templateType=1' \\
  -H 'accept: application/json, text/plain, */*' \\
  -H 'authorization: Bearer token123'"""

    post_curl = """curl 'https://dev-aly-us-ad-web.cdcicd.com/prod-api/offer/pid/add' \\
  -H 'content-type: application/json;charset=UTF-8' \\
  -H 'authorization: Bearer token123' \\
  --data-raw '{"pid":"test123","password":"test123"}'"""

    # 测试解析
    logger.info("=== 测试 GET 请求 ===")
    request1 = parse_curl_command(get_curl)
    logger.info(f"Method: {request1.method}")
    logger.info(f"URL: {request1.url}")
    logger.info(f"Path: {request1.get_path()}")
    logger.info(f"Headers: {request1.headers}")
    logger.info(f"Params: {request1.params}")

    logger.info("\n=== 测试 POST 请求 ===")
    request2 = parse_curl_command(post_curl)
    logger.info(f"Method: {request2.method}")
    logger.info(f"URL: {request2.url}")
    logger.info(f"Headers: {request2.headers}")
    logger.info(f"Data: {request2.data}")
