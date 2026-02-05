# -*- coding: utf-8 -*-
"""
pytest配置文件
定义fixtures和钩子函数
"""
import os
import sys
from src.utils.yaml_loader import load_yaml_dict
from pathlib import Path
from src.utils.logger import log as logger

import pytest
import allure

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.client import create_client
from src.core.context import get_context, reset_context
from src.core.parser import TestParser
from src.core.validator import Validator
from src.utils.extractor import get_extractor


# ========================================
# 全局Fixtures
# ========================================

@pytest.fixture(scope="session", autouse=True)
def setup_session():
    """
    会话级fixture，在整个测试会话开始前执行一次
    """
    logger.info("=" * 60)
    logger.info("测试会话开始")
    logger.info("=" * 60)
    
    yield
    
    logger.info("=" * 60)
    logger.info("测试会话结束")
    logger.info("=" * 60)


@pytest.fixture(scope="function")
def test_context():
    """
    测试用例级fixture，每个用例都会创建新的上下文
    """
    # 重置上下文
    # 不清空extract_vars上，支持用例间数据传递
    # reset_context()
    context = get_context()

    yield context
    
    # 清空局部变量
    context.clear_local()


@pytest.fixture(scope="session")
def config():
    """
    配置fixture
    """
    config_file = Path("config/config.yaml")
    return load_yaml_dict(config_file, default={})


@pytest.fixture(scope="session")
def env_config(config):
    """
    环境配置fixture
    """
    env = os.environ.get('TEST_ENV', config.get('default_env', 'dev'))
    env_file = Path(f"config/env/{env}.yaml")
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


# ========================================
# Allure钩子
# ========================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Allure测试报告钩子
    """
    outcome = yield
    report = outcome.get_result()
    
    if report and report.when == "call":
        try:
            # 测试开始
            if report.passed:
                allure.attach(f"测试通过: {item.name}", name="测试结果", attachment_type=allure.attachment_type.TEXT)
            
            # 测试失败
            if report.failed:
                longrepr = str(report.longrepr) if report.longrepr else "无详细信息"
                allure.attach(longrepr, name="失败信息", attachment_type=allure.attachment_type.TEXT)
            
            # 测试跳过
            if report.skipped:
                longrepr = str(report.longrepr) if report.longrepr else "无跳过原因"
                allure.attach(longrepr, name="跳过原因", attachment_type=allure.attachment_type.TEXT)
        except Exception as e:
            logger.warning(f"生成测试报告时出错: {e}")


@pytest.fixture(autouse=True)
def attach_request_response(test_context):
    """
    自动附加请求和响应到Allure报告
    """
    yield
    
    try:
        # 获取最后一个响应
        response = test_context.get_last_response()
        
        if response and isinstance(response, dict):
            # 附加请求信息
            request = response.get('request', {}) or {}
            request_text = f"""
                        请求方法: {request.get('method', 'N/A')}
                        请求URL: {request.get('url', 'N/A')}
                        请求头: {request.get('headers', {})}
                        请求参数: {request.get('params', {})}
                        请求体: {request.get('body', 'N/A')}
                        """
            allure.attach(request_text, name="请求信息", attachment_type=allure.attachment_type.TEXT)
            
            # 附加响应信息
            headers = response.get('headers') or {}
            body = response.get('body')
            
            response_text = f"""
                        状态码: {response.get('status_code', 'N/A')}
                        响应头: {headers}
                        响应体: {body if body else 'N/A'}
                        耗时: {response.get('elapsed', 0):.3f}s
                        """
            allure.attach(response_text, name="响应信息", attachment_type=allure.attachment_type.TEXT)
            
            # 附加JSON响应
            if body is not None and isinstance(body, (dict, list)):
                import json
                try:
                    allure.attach(
                        json.dumps(body, ensure_ascii=False, indent=2),
                        name="响应JSON",
                        attachment_type=allure.attachment_type.JSON
                    )
                except Exception as e:
                    logger.warning(f"序列化JSON响应失败: {e}")
    except Exception as e:
        logger.warning(f"附加请求响应到Allure报告时出错: {e}")


# ========================================
# pytest钩子
# ========================================

def pytest_configure(config):
    """
    pytest配置钩子
    """
    try:
        # 添加自定义标记
        config.addinivalue_line("markers", "smoke: 冒烟测试")
        config.addinivalue_line("markers", "regression: 回归测试")
        config.addinivalue_line("markers", "daily: 每日巡检")
        config.addinivalue_line("markers", "p0: P0级用例")
        config.addinivalue_line("markers", "p1: P1级用例")
        config.addinivalue_line("markers", "p2: P2级用例")
        config.addinivalue_line("markers", "p3: P3级用例")
        config.addinivalue_line("markers", "slow: 慢速测试")
        config.addinivalue_line("markers", "skip: 跳过测试")
        config.addinivalue_line("markers", "xfail: 预期失败")
        config.addinivalue_line("markers", "positive: 正向测试")
        config.addinivalue_line("markers", "negative: 逆向测试")
        config.addinivalue_line("markers", "performance: 性能测试")
        config.addinivalue_line("markers", "database: 数据库测试")
        config.addinivalue_line("markers", "file: 文件上传测试")
        config.addinivalue_line("markers", "tag: 通用标记")
    except Exception as e:
        logger.warning(f"添加自定义标记时出错: {e}")


def pytest_collection_modifyitems(config, items):
    """
    修改测试用例集合
    可以在这里对用例进行排序、过滤等
    """
    # 根据优先级排序用例
    priority_order = {'p0': 0, 'p1': 1, 'p2': 2, 'p3': 3}
    
    def get_priority(item):
        for marker in item.iter_markers():
            if marker.name is not None and marker.name in priority_order:
                return priority_order[marker.name]
        return 999
    
    items.sort(key=get_priority)


# ========================================
# 辅助函数
# ========================================

def generate_test_data_from_yaml():
    """
    从YAML文件生成测试用例
    这是一个可选的动态测试生成器
    """
    parser = TestParser()
    test_data_dir = Path("test_data")
    
    if not test_data_dir.exists():
        return
    
    all_cases = parser.parse_dir()
    
    for module, cases in all_cases.items():
        for case in cases:
            # 这里可以动态生成pytest测试用例
            pass


# ========================================
# 示例测试用例
# ========================================

class TestExample:
    """示例测试类"""
    
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_example_smoke(self, http_client, env_config):
        """冒烟测试示例"""
        base_url = env_config.get('base_url', 'http://localhost:5000')
        
        response = http_client.request(
            method='GET',
            url=f'{base_url}/health'
        )
        
        assert response['status_code'] == 200
        assert response['body']['status'] == 'ok'
    
    @pytest.mark.regression
    @pytest.mark.p1
    def test_example_with_assertions(self, http_client, validator, env_config):
        """使用断言验证器的测试"""
        base_url = env_config.get('base_url', 'http://localhost:5000')
        
        response = http_client.request(
            method='GET',
            url=f'{base_url}/api/test'
        )
        
        # 使用验证器进行多元化断言
        assertions = [
            {'type': 'status_code', 'expected': 200},
            {'type': 'eq', 'path': 'body.code', 'expected': 0},
            {'type': 'not_none', 'path': 'body.data'}
        ]
        
        results = validator.validate(response, assertions)
        
        # 检查所有断言是否通过
        for result in results:
            assert result.passed, result.message
