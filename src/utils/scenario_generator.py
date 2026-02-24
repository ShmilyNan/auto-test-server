"""
场景生成器
从一个 cURL 生成多个测试场景（正向和逆向）
"""
from typing import Dict, List, Any
from loguru import logger
from dataclasses import dataclass

from src.utils.curl_parser import CurlRequest


@dataclass
class Scenario:
    """测试场景"""
    name: str  # 场景名称
    description: str  # 场景描述
    request: CurlRequest  # 请求对象
    expected_status: int = 200  # 期望状态码
    priority: str = "p1"  # 优先级
    tags: List[str] = None  # 标签


class ScenarioGenerator:
    """场景生成器"""

    def __init__(self):
        self.default_priority = "p1"
        self.default_tags = ["daily", "regression"]

    def generate_scenarios(
            self,
            request: CurlRequest,
            case_name: str,
            method: str = "POST",
            is_new: bool = False
    ) -> List[Scenario]:
        """
        从 cURL 请求生成多个测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            method: HTTP 方法
            is_new: 是否为新增类接口（决定是否添加 smoke 标签）

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 设置标签
        tags = self.default_tags.copy()
        if is_new:
            tags.append("smoke")

        # 1. 正向场景：正常流程
        normal_scenario = Scenario(
            name=f"{case_name}-正常流程",
            description=f"测试 {method} {case_name} 正常流程",
            request=request,
            expected_status=200,
            priority="p1",
            tags=tags.copy()
        )
        scenarios.append(normal_scenario)
        logger.debug(f"生成场景: {normal_scenario.name}")

        # 2. 根据方法生成不同的场景
        if method.upper() in ["POST", "PUT", "PATCH"]:
            # POST/PUT/PATCH 请求：参数校验场景
            scenarios.extend(self._generate_validation_scenarios(request, case_name, tags))
        elif method.upper() == "GET":
            # GET 请求：参数校验场景
            scenarios.extend(self._generate_get_scenarios(request, case_name, tags))
        elif method.upper() == "DELETE":
            # DELETE 请求：权限校验场景
            scenarios.extend(self._generate_delete_scenarios(request, case_name, tags))

        logger.info(f"用例 {case_name}: 生成 {len(scenarios)} 个场景")

        return scenarios

    def _generate_validation_scenarios(
            self,
            request: CurlRequest,
            case_name: str,
            tags: List[str]
    ) -> List[Scenario]:
        """
        生成参数校验场景（用于 POST/PUT/PATCH）

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 校验场景列表
        """
        scenarios = []

        if not request.data or not isinstance(request.data, dict):
            return scenarios

        # 找到关键字段用于生成测试场景
        key_fields = self._find_key_fields(request.data)

        # 生成必填参数缺失场景
        if key_fields:
            for field in key_fields[:2]:  # 最多生成 2 个必填参数缺失场景
                modified_data = request.data.copy()
                modified_data[field] = ""

                modified_request = CurlRequest(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    cookies=request.cookies,
                    data=modified_data,
                    params=request.params,
                    is_compressed=request.is_compressed,
                    insecure=request.insecure
                )

                scenario = Scenario(
                    name=f"{case_name}-{field}为空",
                    description=f"测试 {case_name} {field} 为空时的异常处理",
                    request=modified_request,
                    expected_status=200,  # 参数校验失败
                    priority="p2",
                    tags=tags.copy()
                )
                scenarios.append(scenario)
                logger.debug(f"生成场景: {scenario.name}")

        # 生成密码错误场景（如果是登录相关）
        if any(keyword in case_name.lower() for keyword in ["登录", "login", "auth", "认证"]):
            if request.data and isinstance(request.data, dict):
                password_field = None
                for field in ["password", "passwd", "pwd"]:
                    if field in request.data:
                        password_field = field
                        break

                if password_field:
                    modified_data = request.data.copy()
                    modified_data[password_field] = "wrong_password"

                    modified_request = CurlRequest(
                        method=request.method,
                        url=request.url,
                        headers=request.headers,
                        cookies=request.cookies,
                        data=modified_data,
                        params=request.params,
                        is_compressed=request.is_compressed,
                        insecure=request.insecure
                    )

                    scenario = Scenario(
                        name=f"{case_name}-密码错误",
                        description=f"测试 {case_name} 密码错误时的处理",
                        request=modified_request,
                        expected_status=401,  # 认证失败
                        priority="p2",
                        tags=tags.copy()
                    )
                    scenarios.append(scenario)
                    logger.debug(f"生成场景: {scenario.name}")

        return scenarios

    def _generate_get_scenarios(
            self,
            request: CurlRequest,
            case_name: str,
            tags: List[str]
    ) -> List[Scenario]:
        """
        生成 GET 请求的测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 生成参数错误场景
        if request.params:
            for param_name in list(request.params.keys())[:1]:  # 只生成 1 个参数错误场景
                modified_params = request.params.copy()
                modified_params[param_name] = "invalid_value"

                modified_request = CurlRequest(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    cookies=request.cookies,
                    data=request.data,
                    params=modified_params,
                    is_compressed=request.is_compressed,
                    insecure=request.insecure
                )

                scenario = Scenario(
                    name=f"{case_name}-参数错误",
                    description=f"测试 {case_name} 参数错误时的处理",
                    request=modified_request,
                    expected_status=200,
                    priority="p2",
                    tags=tags.copy()
                )
                scenarios.append(scenario)
                logger.debug(f"生成场景: {scenario.name}")

        return scenarios

    def _generate_delete_scenarios(
            self,
            request: CurlRequest,
            case_name: str,
            tags: List[str]
    ) -> List[Scenario]:
        """
        生成 DELETE 请求的测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 生成资源不存在场景
        modified_url = request.url
        if '?' in modified_url:
            modified_url = modified_url.split('?')[0]
        modified_url = modified_url.rstrip('/')
        modified_url = f"{modified_url}/999999"  # 使用不存在的 ID

        modified_request = CurlRequest(
            method=request.method,
            url=modified_url,
            headers=request.headers,
            cookies=request.cookies,
            data=request.data,
            params=request.params,
            is_compressed=request.is_compressed,
            insecure=request.insecure
        )

        scenario = Scenario(
            name=f"{case_name}-资源不存在",
            description=f"测试 {case_name} 删除不存在的资源",
            request=modified_request,
            expected_status=404,
            priority="p2",
            tags=tags.copy()
        )
        scenarios.append(scenario)
        logger.debug(f"生成场景: {scenario.name}")

        return scenarios

    def _find_key_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        找出关键字段（用于生成测试场景）

        Args:
            data: 数据字典

        Returns:
            List[str]: 关键字段列表
        """
        key_fields = []

        # 常见的必填字段
        common_fields = [
            "username", "user_name", "account",
            "password", "passwd", "pwd",
            "email", "phone", "mobile",
            "id", "name", "title",
            "pid", "product_id", "user_id"
        ]

        for field in common_fields:
            if field in data:
                key_fields.append(field)

        return key_fields


def generate_scenarios(
        request: CurlRequest,
        case_name: str,
        method: str = "POST",
        is_new: bool = False
) -> List[Scenario]:
    """
    便捷函数：生成测试场景

    Args:
        request: cURL 请求对象
        case_name: 用例名称
        method: HTTP 方法
        is_new: 是否为新增类接口

    Returns:
        List[Scenario]: 测试场景列表
    """
    generator = ScenarioGenerator()
    return generator.generate_scenarios(request, case_name, method, is_new)


if __name__ == "__main__":
    # 测试场景生成
    from src.utils.curl_parser import CurlParser

    # 测试登录接口
    login_curl = """curl 'https://api.example.com/login' -H 'content-type: application/json' --data-raw '{"username":"test","password":"test123"}'"""

    parser = CurlParser()
    request = parser.parse(login_curl)

    generator = ScenarioGenerator()
    scenarios = generator.generate_scenarios(request, "用户登录", "POST", is_new=True)

    print(f"生成 {len(scenarios)} 个场景:")
    for scenario in scenarios:
        print(f"  - {scenario.name}")
        print(f"    描述: {scenario.description}")
        print(f"    期望状态码: {scenario.expected_status}")
        print(f"    优先级: {scenario.priority}")
        print(f"    标签: {scenario.tags}")
