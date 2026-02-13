# -*- coding: utf-8 -*-
"""
动态测试用例文件
从 test_data 目录的 YAML/JSON 文件自动生成 pytest 测试用例
"""
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.parser import TestParser, TestCase
from src.utils.yaml_loader import load_yaml_dict
from src.utils.logger import log as logger


class TestCaseGenerator:
    """测试用例生成器"""

    def __init__(self, test_data_dir: str = "test_data"):
        """
        初始化生成器
        Args:
            test_data_dir: 测试数据目录
        """
        self.test_data_dir = Path(test_data_dir)
        self.parser = TestParser(test_data_dir)
        self.test_cases: Dict[str, List[TestCase]] = {}

    def load_test_data(self) -> Dict[str, List[TestCase]]:
        """
        加载所有测试数据
        Returns:
            Dict[str, List[TestCase]]: {模块名: 测试用例列表}
        """
        logger.info(f"开始加载测试数据: {self.test_data_dir}")

        self.test_cases = self.parser.parse_dir()

        total_cases = sum(len(cases) for cases in self.test_cases.values())
        logger.info(f"加载完成: {len(self.test_cases)} 个模块, {total_cases} 个测试用例")

        return self.test_cases

    def generate_test_cases(self) -> List[Dict[str, Any]]:
        """
        生成参数化的测试用例数据
        Returns:
            List[Dict[str, Any]]: 测试用例数据列表（已按 order 排序）
        """
        if not self.test_cases:
            self.load_test_data()

        test_data_list = []

        for module_name, cases in self.test_cases.items():
            for idx, test_case in enumerate(cases):
                # 生成唯一的测试ID
                test_id = f"{module_name}_{test_case.name}_{idx}"

                test_data_list.append({
                    'test_id': test_id,
                    'test_case': test_case,
                    'module': module_name,
                    'index': idx
                })

        # 按 order 排序（跨模块排序）
        test_data_list.sort(key=lambda x: x['test_case'].order)

        logger.info(f"生成 {len(test_data_list)} 个参数化测试用例（已按 order 排序）")
        return test_data_list


# 创建生成器实例
_generator = TestCaseGenerator()
_test_data_list = _generator.generate_test_cases()


def _generate_function_name(test_case: TestCase, module: str, idx: int) -> str:
    """
    生成唯一的函数名
    Args:
        test_case: 测试用例
        module: 模块名称
        idx: 索引
    Returns:
        str: 函数名
    """
    import re
    name = re.sub(r'[^\w]', '_', test_case.name)
    name = name.replace(' ', '_').strip('_')

    # 确保以 test_ 开头
    if not name.startswith('test_'):
        name = f'test_{name}'

    # 添加模块名和索引避免重复，同时支持 -k 参数筛选
    function_name = f"{name}_{module}_{idx}"

    return function_name


def _build_url(url: str, test_context) -> str:
    """
    构建完整URL
    Args:
        url: URL路径
        test_context: 测试上下文
    Returns:
        str: 完整URL
    """
    # 替换URL中的变量
    url = test_context.replace_vars(url)

    # 获取基础URL
    config = load_yaml_dict("config/config.yaml", default={})
    default_env = config.get('default_env', 'test')

    env_config = load_yaml_dict(f"config/env/{default_env}.yaml", default={})
    base_url = env_config.get('base_url', '')

    # 拼接完整URL
    if base_url and not url.startswith(('http://', 'https://')):
        if not url.startswith('/'):
            url = f'/{url}'
        url = f'{base_url}{url}'

    return url


def _prepare_request_data(test_case: TestCase, test_context, http_client= None):
    """
    准备请求数据
    Args:
        test_case: 测试用例
        test_context: 测试上下文
        http_client: HTTP客户端（可选，用于全局登录）
    Returns:
        Dict: 请求数据
    """
    request_data = {}

    # 获取默认请求头（包括 Content-Type、Accept、User-Agent、Authorization）
    default_headers = test_context.get_default_headers()

    # 合并请求头：默认请求头 + 测试用例请求头
    # 测试用例请求头优先级更高，会覆盖默认请求头
    merged_headers = default_headers.copy()

    if test_case.headers:
        case_headers = test_context.replace_vars_dict(test_case.headers)
        merged_headers.update(case_headers)

    request_data['headers'] = merged_headers

    logger.debug(f"合并后的请求头: {merged_headers}")

    # URL参数
    if test_case.params:
        request_data['params'] = test_context.replace_vars_dict(test_case.params)

    # 请求体 - 需要根据请求头判断使用 json 还是 data
    if test_case.body is not None:
        body = test_context.replace_vars_dict(test_case.body)

        # 检查请求头中的 Content-Type
        content_type = None
        for key, value in merged_headers.items():
            if key.lower() == 'content-type':
                content_type = value
                break

        # 如果是 JSON 格式，使用 json 参数
        if content_type and 'application/json' in content_type.lower():
            request_data['json'] = body
        else:
            request_data['data'] = body

    # 文件上传
    if test_case.files:
        request_data['files'] = test_case.files

    # 超时时间
    if test_case.timeout:
        request_data['timeout'] = test_case.timeout

    return request_data


def _execute_setup(setup_steps: List[Dict], test_context):
    """
    执行前置处理

    Args:
        setup_steps: 前置处理步骤
        test_context: 测试上下文
    """
    for step in setup_steps:
        action = step.get('action')

        if action == 'set_var':
            name = step.get('name')
            value = step.get('value')
            test_context.set_local(name, value)
            logger.debug(f"设置局部变量: {name} = {value}")

        elif action == 'set_global':
            name = step.get('name')
            value = step.get('value')
            test_context.set_global(name, value)
            logger.debug(f"设置全局变量: {name} = {value}")

        elif action == 'call_hook':
            hook_name = step.get('hook')
            logger.debug(f"调用钩子: {hook_name}")


def _execute_teardown(teardown_steps: List[Dict], test_context):
    """
    执行后置处理
    Args:
        teardown_steps: 后置处理步骤
        test_context: 测试上下文
    """
    for step in teardown_steps:
        action = step.get('action')

        if action == 'clear_local':
            test_context.clear_local()
            logger.debug("清空局部变量")

        elif action == 'call_hook':
            hook_name = step.get('hook')
            logger.debug(f"调用钩子: {hook_name}")


# 为每个测试用例动态生成测试函数
for test_data in _test_data_list:
    test_case = test_data['test_case']
    idx = test_data['index']
    module_name = test_data['module']

    # 生成函数名
    func_name = _generate_function_name(test_case, module_name, idx)


    # 创建测试函数
    def _create_test_function(tc=test_case):
        """
        动态生成的测试函数
        """

        def test_function(http_client, validator, extractor, test_context):
            """
            动态生成的测试函数

            Args:
                http_client: HTTP客户端fixture
                validator: 验证器fixture
                extractor: 提取器fixture
                test_context: 测试上下文fixture
            """
            # 检查是否跳过
            if tc.skip:
                pytest.skip(tc.skip_reason or "测试用例被标记为跳过")
                return

            # 设置用例开始时间
            start_time = time.time()

            try:
                # 执行前置处理
                if tc.setup:
                    _execute_setup(tc.setup, test_context)

                # 准备请求参数
                request_data = _prepare_request_data(tc, test_context, http_client)

                # 构建完整URL
                url = _build_url(tc.url, test_context)

                # 发送请求
                logger.info(f"执行测试用例: {tc.name}")
                logger.debug(f"请求: {tc.method} {url}")

                response = http_client.request(
                    method=tc.method,
                    url=url,
                    **request_data
                )

                # 保存响应到上下文
                test_context.set_last_response(response)

                # 提取数据
                if tc.extract:
                    extracted_data = extractor.extract(response, tc.extract)
                    for key, value in extracted_data.items():
                        test_context.set_extract(key, value)
                        logger.debug(f"提取变量: {key} = {value}")

                # 执行断言
                if tc.validate:
                    results = validator.validate(response, tc.validate)
                    failed_results = [r for r in results if not r.passed]

                    if failed_results:
                        error_messages = [r.message for r in failed_results]
                        pytest.fail(f"断言失败: {'; '.join(error_messages)}")

                # 执行后置处理
                if tc.teardown:
                    _execute_teardown(tc.teardown, test_context)

                # 执行数据清洗
                if tc.cleanup:
                    try:
                        from src.utils.cleaner import get_cleaner
                        cleaner = get_cleaner()
                        success = cleaner.cleanup(tc.cleanup)
                        if success:
                            logger.debug(f"数据清洗成功: {tc.name}")
                        else:
                            logger.warning(f"数据清洗失败: {tc.name}")
                    except Exception as e:
                        logger.error(f"数据清洗异常: {tc.name}, 错误: {str(e)}")
                        # 数据清洗失败不影响测试用例结果

                # 记录执行时间
                elapsed = time.time() - start_time
                logger.info(f"测试用例执行成功: {tc.name}, 耗时: {elapsed:.3f}s")

            except AssertionError as e:
                logger.error(f"测试用例断言失败: {tc.name}, 错误: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"测试用例执行失败: {tc.name}, 错误: {str(e)}")
                raise

        return test_function


    # 创建实际的测试函数
    test_func = _create_test_function(test_case)
    test_func.__name__ = func_name
    test_func.__doc__ = test_case.description or test_case.name
    test_func.__qualname__ = f"test_dynamic.{func_name}"

    # 添加 pytest 标记

    # 添加执行顺序标记（优先级最高）
    if test_case.order is not None:
        try:
            # 使用 pytest-order 插件的标记
            test_func = pytest.mark.order(test_case.order)(test_func)
        except:
            pass

    # 添加优先级标记
    priority_map = {
        'p0': pytest.mark.p0,
        'p1': pytest.mark.p1,
        'p2': pytest.mark.p2,
        'p3': pytest.mark.p3
    }
    if test_case.priority in priority_map:
        test_func = priority_map[test_case.priority](test_func)

    # 添加标签
    for tag in test_case.tags:
        try:
            mark = getattr(pytest.mark, tag, pytest.mark.tag)
            test_func = mark(test_func)
        except:
            pass

    # 添加模块名标记（已通过函数名支持 -k 参数筛选）
    # 函数名格式：test_用例名_模块名_索引
    # 例如：test_用户登录_正常流程_user_module_0
    # 可以通过 -k "user_module" 筛选所有用户模块的测试用例

    # 将函数添加到模块的命名空间
    globals()[func_name] = test_func

logger.info(f"动态生成 {len(_test_data_list)} 个测试用例函数")
