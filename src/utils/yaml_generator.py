"""
YAML 生成器
将 CurlRequest 对象转换为 YAML 格式的测试数据文件
"""
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from urllib.parse import urlparse
from loguru import logger
from src.utils.curl_parser import CurlRequest
from src.utils.scenario_generator import Scenario

# 创建 YAML 实例
_yaml = YAML(typ='rt')
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


class YamlGenerator:
    """YAML 测试数据文件生成器"""

    def __init__(self):
        pass

    def generate(
        self,
        request: CurlRequest,
        module_name: Optional[str] = None,
        module_description: Optional[str] = None,
        test_case_name: Optional[str] = None,
        test_case_description: Optional[str] = None,
        priority: str = "p2",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成 YAML 数据结构
        Args:
            request: CurlRequest 对象
            module_name: 模块名称（默认从 URL 提取）
            module_description: 模块描述
            test_case_name: 测试用例名称
            test_case_description: 测试用例描述
            priority: 优先级
            tags: 标签列表
        Returns:
            Dict: YAML 数据字典
        """
        # 从 URL 提取模块名称
        if not module_name:
            module_name = self._extract_module_name(request.url)

        if not module_description:
            module_description = f"{module_name} 模块的测试用例（从 cURL 转换）"

        # 生成测试用例名称
        if not test_case_name:
            test_case_name = f"{request.method} {self._extract_endpoint(request.url)}"

        if not test_case_description:
            test_case_description = f"测试 {request.method} 请求：{request.get_path()}"

        # 默认标签
        if not tags:
            tags = ["smoke", "positive"]

        # 准备全局配置
        config = self._generate_config(request)

        # 准备测试用例
        test_case = self._generate_test_case(
            request,
            test_case_name,
            test_case_description,
            priority,
            tags
        )

        # 构建完整的 YAML 结构（使用 CommentedMap 保持顺序）
        yaml_data = CommentedMap()
        yaml_data['module'] = CommentedMap()
        yaml_data['module']['name'] = module_name
        yaml_data['module']['version'] = '1.0.0'
        yaml_data['module']['description'] = module_description
        yaml_data['module']['author'] = '从cURL转换'
        yaml_data['config'] = config
        yaml_data['test_cases'] = [test_case]

        logger.info(f"生成 YAML 数据: 模块={module_name}, 用例={test_case_name}")

        return yaml_data

    def _extract_module_name(self, url: str) -> str:
        """
        从 URL 提取模块名称

        Args:
            url: URL 字符串

        Returns:
            str: 模块名称
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        # 通常第二个路径段是模块名
        if len(path_parts) >= 2:
            return path_parts[1].replace('-', '_')

        return "test_module"

    def _extract_endpoint(self, url: str) -> str:
        """
        从 URL 提取端点名称

        Args:
            url: URL 字符串

        Returns:
            str: 端点名称
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        # 提取最后一段路径作为端点名
        if path:
            parts = path.split('/')
            return parts[-1]

        return "endpoint"

    def _generate_config(self, request: CurlRequest) -> CommentedMap:
        """
        生成全局配置
        Args:
            request: CurlRequest 对象
        Returns:
            CommentedMap: 配置字典（保持字段顺序
        """
        config = CommentedMap()
        config['headers'] = CommentedMap()
        config['timeout'] = 30

        # 从请求头中提取有用的默认请求头
        important_headers = ['Content-Type', 'Accept', 'Authorization']

        for header in important_headers:
            if header in request.headers:
                config['headers'][header] = request.headers[header]

        # 如果没有 Content-Type，设置默认值
        if 'Content-Type' not in config['headers'] and request.method.upper() == 'POST':
            config['headers']['Content-Type'] = 'application/json'

        if 'Accept' not in config['headers']:
            config['headers']['Accept'] = 'application/json'

        return config

    def _generate_test_case(
        self,
        request: CurlRequest,
        name: str,
        description: str,
        priority: str,
        tags: List[str]
    ) -> CommentedMap:
        """
        生成测试用例
        Args:
            request: CurlRequest 对象
            name: 用例名称
            description: 用例描述
            priority: 优先级
            tags: 标签列表
        Returns:
            CommentedMap: 测试用例字典
        """
        # 按照 user_module.yaml 的字段顺序构建（使用 CommentedMap 保持顺序）
        test_case = CommentedMap()

        # 1. name (必填)
        test_case['name'] = name

        # 2. description (必填)
        test_case['description'] = description

        # 3. order (可选，暂时不设置)
        # test_case['order'] = 0

        # 4. priority (必填)
        test_case['priority'] = priority

        # 5. tags (必填)
        test_case['tags'] = tags

        # 6. method (必填)
        test_case['method'] = request.method.upper()

        # 7. url (必填)
        test_case['url'] = request.get_path()

        # 8. headers (可选)
        config_headers = self._generate_config(request)['headers']
        case_headers = {}

        for key, value in request.headers.items():
            # 如果 header 值与全局配置不同，或者包含敏感信息，则添加到用例级别
            if key not in config_headers or config_headers[key] != value:
                # 过滤掉一些浏览器相关的 header
                if not self._is_browser_header(key):
                    case_headers[key] = value

        if case_headers:
            test_case['headers'] = case_headers

        # params 参数
        if request.params:
            test_case['params'] = request.params

        # 添加请求体
        if request.data is not None:
            test_case['body'] = request.data

        # validate (必填)
        test_case['validate'] = [
            {
                'type': 'status_code',
                'expected': 200
            }
        ]

        # 如果有 JSON 响应，添加断言
        if request.headers.get('Accept', '').lower() == 'application/json':
            # 添加通用的 JSON 断言
            test_case['validate'].append({
                'type': 'eq',
                'path': 'body.code',
                'expected': 0
            })

        # 12. extract (可选，暂时不添加)
        # 13. metadata (可选，暂时不添加)
        # 14. depends_on (可选，暂时不添加)

        return test_case

    def _is_browser_header(self, header_name: str) -> bool:
        """
        判断是否为浏览器相关的 header（通常不需要在测试中保留）

        Args:
            header_name: header 名称

        Returns:
            bool: 是否为浏览器 header
        """
        browser_headers = [
            'User-Agent',
            'Referer',
            'Origin',
            'Sec-Ch-Ua',
            'Sec-Ch-Ua-Mobile',
            'Sec-Ch-Ua-Platform',
            'Sec-Fetch-Dest',
            'Sec-Fetch-Mode',
            'Sec-Fetch-Site',
            'Sec-Fetch-User',
            'Priority'
        ]

        return header_name.lower() in [h.lower() for h in browser_headers]

    def save_to_file(
        self,
        yaml_data: Dict[str, Any],
        output_dir: str = "test_data",
        filename: Optional[str] = None
    ) -> str:
        """
        将 YAML 数据保存到文件
        Args:
            yaml_data: YAML 数据字典
            output_dir: 输出目录
            filename: 文件名（不包含扩展名）
        Returns:
            str: 保存的文件路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        if not filename:
            module_name = yaml_data['module']['name']
            filename = f"{module_name}_module"

        # 添加时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{filename}_{timestamp}"

        file_path = output_path / f"{filename_with_timestamp}.yaml"

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 从 cURL 转换的测试数据文件\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(yaml_data, f)

        logger.info(f"YAML 文件已保存: {file_path}")

        return str(file_path)

    def append_to_file(
        self,
        request: CurlRequest,
        file_path: str,
        test_case_name: Optional[str] = None,
        test_case_description: Optional[str] = None,
        priority: str = "p2",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        将测试用例追加到已有的 YAML 文件中
        Args:
            request: CurlRequest 对象
            file_path: 目标 YAML 文件路径
            test_case_name: 测试用例名称
            test_case_description: 测试用例描述
            priority: 优先级
            tags: 标签列表
        Returns:
            str: 文件路径
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        yaml_path = Path(file_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取现有文件
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        # 解析 YAML
        existing_data = _yaml.load(yaml_content) if yaml_content.strip() else None

        if not existing_data:
            raise ValueError(f"无法解析 YAML 文件: {file_path}")

        if 'test_cases' not in existing_data:
            existing_data['test_cases'] = []

        # 生成测试用例名称和描述
        if not test_case_name:
            test_case_name = f"{request.method} {self._extract_endpoint(request.url)}"

        if not test_case_description:
            test_case_description = f"测试 {request.method} 请求：{request.get_path()}"

        # 默认标签
        if not tags:
            tags = ["smoke", "positive"]

        # 生成新的测试用例
        new_test_case = self._generate_test_case(
            request,
            test_case_name,
            test_case_description,
            priority,
            tags
        )

        # 追加到 test_cases 列表
        existing_data['test_cases'].append(new_test_case)

        # 备份原文件
        backup_path = yaml_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        yaml_path.rename(backup_path)
        logger.debug(f"原文件已备份到: {backup_path}")

        # 写回文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 测试数据文件（追加模式）\n")
            f.write(f"# 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(existing_data, f)

        logger.info(f"测试用例已追加到文件: {file_path}")
        logger.info(f"文件中共有 {len(existing_data['test_cases'])} 个测试用例")

        return str(file_path)

    def append_scenarios_to_file(
        self,
        scenarios: List[Scenario],
        file_path: str,
        module_name: Optional[str] = None,
        module_description: Optional[str] = None
    ) -> Tuple[str, int, int]:
        """
        将多个场景追加到已有的 YAML 文件中（智能去重）

        Args:
            scenarios: 场景列表
            file_path: 目标 YAML 文件路径
            module_name: 模块名称（如果文件不存在）
            module_description: 模块描述

        Returns:
            Tuple[str, int, int]: (文件路径, 添加的场景数, 跳过的场景数)
        """
        yaml_path = Path(file_path)

        # 获取已存在的用例名称
        existing_cases = set()
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    existing_data = _yaml.load(f)

                if existing_data and 'test_cases' in existing_data:
                    existing_cases = {case.get('name', '') for case in existing_data['test_cases']}
            except Exception as e:
                logger.warning(f"读取现有 YAML 文件失败: {e}")

        # 准备要添加的场景（过滤已存在的）
        new_scenarios = []
        skipped_count = 0

        for scenario in scenarios:
            if scenario.name in existing_cases:
                logger.debug(f"场景已存在，跳过: {scenario.name}")
                skipped_count += 1
            else:
                new_scenarios.append(scenario)

        if not new_scenarios:
            logger.info(f"所有场景已存在，无需追加")
            return str(yaml_path), 0, skipped_count

        # 如果文件不存在，创建新文件
        if not yaml_path.exists():
            if not module_name:
                module_name = yaml_path.stem

            if not module_description:
                module_description = f"{module_name} 模块的测试用例"

            # 生成全局配置（使用第一个场景的请求）
            first_scenario = new_scenarios[0]
            config = self._generate_config(first_scenario.request)

            # 使用 CommentedMap 保持字段顺序
            yaml_data = CommentedMap()
            yaml_data['module'] = CommentedMap()
            yaml_data['module']['name'] = module_name
            yaml_data['module']['version'] = '1.0.0'
            yaml_data['module']['description'] = module_description
            yaml_data['module']['author'] = '从cURL转换'
            yaml_data['config'] = config
            yaml_data['test_cases'] = []
        else:
            # 读取现有文件
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

            existing_data = _yaml.load(yaml_content) if yaml_content.strip() else None

            if not existing_data:
                raise ValueError(f"无法解析 YAML 文件: {file_path}")

            if 'test_cases' not in existing_data:
                existing_data['test_cases'] = []

            yaml_data = existing_data

        # 将场景转换为测试用例
        for scenario in new_scenarios:
            test_case = self._generate_test_case(
                scenario.request,
                scenario.name,
                scenario.description,
                scenario.priority,
                scenario.tags
            )

            # 修改期望状态码
            for validate in test_case['validate']:
                if validate['type'] == 'status_code':
                    validate['expected'] = scenario.expected_status

            yaml_data['test_cases'].append(test_case)

        # 备份原文件（如果文件已存在）
        if yaml_path.exists():
            backup_path = yaml_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            yaml_path.rename(backup_path)
            logger.debug(f"原文件已备份到: {backup_path}")

        # 确保目录存在
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        # 写回文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 测试数据文件（批量追加模式）\n")
            f.write(f"# 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(yaml_data, f)

        logger.info(f"已追加 {len(new_scenarios)} 个场景到文件: {file_path}")
        logger.info(f"跳过 {skipped_count} 个已存在的场景")
        logger.info(f"文件中共有 {len(yaml_data['test_cases'])} 个测试用例")

        return str(yaml_path), len(new_scenarios), skipped_count


def convert_curl_to_yaml(
    curl_command: str,
    output_dir: str = "test_data",
    filename: Optional[str] = None,
    module_name: Optional[str] = None,
    module_description: Optional[str] = None,
    test_case_name: Optional[str] = None,
    test_case_description: Optional[str] = None,
    priority: str = "p2",
    tags: Optional[List[str]] = None
) -> str:
    """
    便捷函数：将 cURL 命令转换为 YAML 文件

    Args:
        curl_command: cURL 命令字符串
        output_dir: 输出目录
        filename: 文件名（不包含扩展名）
        module_name: 模块名称
        module_description: 模块描述
        test_case_name: 测试用例名称
        test_case_description: 测试用例描述
        priority: 优先级
        tags: 标签列表

    Returns:
        str: 生成的 YAML 文件路径
    """
    from src.utils.curl_parser import CurlParser

    # 解析 cURL
    parser = CurlParser()
    request = parser.parse(curl_command)

    # 生成 YAML 数据
    generator = YamlGenerator()
    yaml_data = generator.generate(
        request,
        module_name=module_name,
        module_description=module_description,
        test_case_name=test_case_name,
        test_case_description=test_case_description,
        priority=priority,
        tags=tags
    )

    # 保存到文件
    file_path = generator.save_to_file(yaml_data, output_dir, filename)

    return file_path


def append_curl_to_yaml(
    curl_command: str,
    file_path: str,
    test_case_name: Optional[str] = None,
    test_case_description: Optional[str] = None,
    priority: str = "p2",
    tags: Optional[List[str]] = None
) -> str:
    """
    便捷函数：将 cURL 命令追加到已有的 YAML 文件

    Args:
        curl_command: cURL 命令字符串
        file_path: 目标 YAML 文件路径
        test_case_name: 测试用例名称
        test_case_description: 测试用例描述
        priority: 优先级
        tags: 标签列表

    Returns:
        str: 文件路径

    Raises:
        FileNotFoundError: 文件不存在
    """
    from src.utils.curl_parser import CurlParser

    # 解析 cURL
    parser = CurlParser()
    request = parser.parse(curl_command)

    # 追加到文件
    generator = YamlGenerator()
    return generator.append_to_file(
        request,
        file_path,
        test_case_name=test_case_name,
        test_case_description=test_case_description,
        priority=priority,
        tags=tags
    )


if __name__ == "__main__":
    # 测试用例
    get_curl = """curl 'https://dev-aly-us-ad-web.cdcicd.com/prod-api/report/template/list?templateType=1' \\
  -H 'accept: application/json, text/plain, */*' \\
  -H 'authorization: Bearer token123'"""

    post_curl = """curl 'https://dev-aly-us-ad-web.cdcicd.com/prod-api/offer/pid/add' \\
  -H 'content-type: application/json;charset=UTF-8' \\
  -H 'authorization: Bearer token123' \\
  --data-raw '{"pid":"test123","password":"test123"}'"""

    # 测试转换
    logger.info("=== 测试 GET 请求转换 ===")
    file_path1 = convert_curl_to_yaml(get_curl, output_dir="/tmp/test_data")
    logger.info(f"生成的文件: {file_path1}")

    logger.info("\n=== 测试 POST 请求转换 ===")
    file_path2 = convert_curl_to_yaml(post_curl, output_dir="/tmp/test_data")
    logger.info(f"生成的文件: {file_path2}")
