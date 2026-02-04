# -*- coding: utf-8 -*-
"""
动态测试用例生成器
从 test_data 目录的 YAML/JSON 文件自动生成 pytest 测试用例
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.parser import TestParser, TestCase
from src.core.context import get_context, reset_context
from src.core.client import create_client
from src.core.validator import Validator
from src.utils.extractor import get_extractor
from loguru import logger


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

    def generate_pytest_functions(self):
        """
        动态生成 pytest 测试函数
        """
        if not self.test_cases:
            self.load_test_data()

        generated_functions = []

        for module_name, cases in self.test_cases.items():
            for idx, test_case in enumerate(cases):
                # 生成唯一的函数名
                func_name = self._generate_function_name(test_case, idx)

                # 创建测试函数
                test_func = self._create_test_function(test_case)

                # 设置函数名和文档字符串
                test_func.__name__ = func_name
                test_func.__doc__ = test_case.description or test_case.name
                test_func.__qualname__ = f"test_cases.{func_name}"

                # 添加 pytest 标记
                self._add_pytest_marks(test_func, test_case)

                generated_functions.append(test_func)

                # 将函数添加到当前模块
                globals()[func_name] = test_func

        logger.info(f"生成 {len(generated_functions)} 个测试函数")
        return generated_functions

    def _generate_function_name(self, test_case: TestCase, idx: int) -> str:
        """
        生成唯一的函数名

        Args:
            test_case: 测试用例
            idx: 索引

        Returns:
            str: 函数名
        """
        # 清理函数名，只保留字母、数字和下划线
        import re
        name = re.sub(r'[^\w]', '_', test_case.name)
        name = name.replace(' ', '_').strip('_')

        # 确保以 test_ 开头
        if not name.startswith('test_'):
            name = f'test_{name}'

        # 添加模块名和索引避免重复
        func_name = f"{name}_{idx}"

        return func_name

    def _create_test_function(self, test_case: TestCase):
        """
        创建测试函数

        Args:
            test_case: 测试用例

        Returns:
            Callable: 测试函数
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
            if test_case.skip:
                pytest.skip(test_case.skip_reason or "测试用例被标记为跳过")
                return

            # 设置用例开始时间
            start_time = time.time()

            try:
                # 执行前置处理
                if test_case.setup:
                    self._execute_setup(test_case.setup, test_context)

                # 准备请求参数
                request_data = self._prepare_request_data(test_case, test_context)

                # 构建完整URL
                url = self._build_url(test_case.url, test_context)

                # 发送请求
                logger.info(f"执行测试用例: {test_case.name}")
                logger.debug(f"请求: {test_case.method} {url}")

                response = http_client.request(
                    method=test_case.method,
                    url=url,
                    **request_data
                )

                # 保存响应到上下文
                test_context.set_last_response(response)

                # 提取数据
                if test_case.extract:
                    extracted_data = extractor.extract(response, test_case.extract)
                    for key, value in extracted_data.items():
                        test_context.set_extract(key, value)
                        logger.debug(f"提取变量: {key} = {value}")

                # 执行断言
                if test_case.validate:
                    results = validator.validate(response, test_case.validate)
                    failed_results = [r for r in results if not r.passed]

                    if failed_results:
                        error_messages = [r.message for r in failed_results]
                        pytest.fail(f"断言失败: {'; '.join(error_messages)}")

                # 执行后置处理
                if test_case.teardown:
                    self._execute_teardown(test_case.teardown, test_context)

                # 记录执行时间
                elapsed = time.time() - start_time
                logger.info(f"测试用例执行完成: {test_case.name}, 耗时: {elapsed:.3f}s")

            except AssertionError as e:
                logger.error(f"测试用例断言失败: {test_case.name}, 错误: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"测试用例执行失败: {test_case.name}, 错误: {str(e)}")
                raise

        return test_function

    def _prepare_request_data(self, test_case: TestCase, test_context):
        """
        准备请求数据

        Args:
            test_case: 测试用例
            test_context: 测试上下文

        Returns:
            Dict: 请求数据
        """
        request_data = {}

        # 请求头
        if test_case.headers:
            request_data['headers'] = test_context.replace_vars_dict(test_case.headers)

        # URL参数
        if test_case.params:
            request_data['params'] = test_context.replace_vars_dict(test_case.params)

        # 请求体
        if test_case.body is not None:
            request_data['body'] = test_context.replace_vars_dict(test_case.body)

        # 文件上传
        if test_case.files:
            request_data['files'] = test_case.files

        # 超时时间
        if test_case.timeout:
            request_data['timeout'] = test_case.timeout

        return request_data

    def _build_url(self, url: str, test_context) -> str:
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
        from src.utils.yaml_loader import load_yaml_dict

        config = load_yaml_dict("config/config.yaml", default={})
        default_env = config.get('default_env', 'dev')

        env_config = load_yaml_dict(f"config/env/{default_env}.yaml", default={})
        base_url = env_config.get('base_url', '')

        # 拼接完整URL
        if base_url and not url.startswith(('http://', 'https://')):
            if not url.startswith('/'):
                url = f'/{url}'
            url = f'{base_url}{url}'

        return url

    def _add_pytest_marks(self, test_func, test_case: TestCase):
        """
        添加 pytest 标记

        Args:
            test_func: 测试函数
            test_case: 测试用例
        """
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

        # 添加模块名标记
        module_mark = getattr(pytest.mark, f'module_{test_case.module}', pytest.mark.module)
        test_func = module_mark(test_func)

    def _execute_setup(self, setup_steps: List[Dict], test_context):
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
                # 可以在这里实现钩子调用
                logger.debug(f"调用钩子: {hook_name}")

    def _execute_teardown(self, teardown_steps: List[Dict], test_context):
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


# 导入 time
import time

# 创建生成器实例并生成测试用例
_generator = TestCaseGenerator()

# 在模块加载时生成测试用例
try:
    _generator.generate_pytest_functions()
    logger.info("动态测试用例生成成功")
except Exception as e:
    logger.error(f"动态测试用例生成失败: {str(e)}")
    import traceback

    traceback.print_exc()
