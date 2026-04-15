# -*- coding: utf-8 -*-
"""
pytest配置文件
定义fixtures和钩子函数
"""
import pytest
import allure
from src.utils.logger import logger
from src.hooks.allure_hooks import attach_request_response

# 注册 pytest 插件
pytest_plugins = []

# ========================================
# 定义基础 Fixtures（在 conftest.py 中直接定义以确保可用性）
# ========================================
@pytest.fixture(scope="session")
def config():
    """
    配置fixture
    在 conftest.py 中定义以确保 pytest 能够正确识别
    """
    from config import CONFIG_FILE
    from src.utils.yaml_loader import load_yaml_dict
    return load_yaml_dict(CONFIG_FILE, default={})


# ========================================
# 导入其他 Fixtures
# ========================================
# 注意：config 已在上方定义，这里导入其他 fixtures
from src.fixtures.fixtures import (
    setup_session,
    test_context,
    env_config,
    http_client,
    validator,
    extractor,
    default_headers
)

logger.info("=" * 60)
logger.info("🚀 使用懒加载登录机制（统一版本）")
logger.info("   - 只在实际需要时才执行登录")
logger.info("   - 避免不必要的登录请求")
logger.info("   - 提升测试执行效率")
logger.info("=" * 60)

from src.fixtures.login_fixture import (
    login_cache,
    login_tokens,
    service_headers,
    auth_headers,
    multi_service_headers
)

# 附加 Allure 钩子
attach_request_response = pytest.fixture(autouse=True)(attach_request_response)

# ========================================
# 导入 Pytest 钩子
# ========================================
from src.hooks.pytest_hooks import (
    pytest_configure,
    pytest_sessionfinish,
    pytest_collection_modifyitems
)


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

                # 执行测试成功钩子
                from src.hooks.custom_hooks import on_test_success
                try:
                    on_test_success()
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"执行 on_test_success 钩子失败: {str(e)}")

            # 测试失败
            if report.failed:
                longrepr = str(report.longrepr) if report.longrepr else "无详细信息"
                allure.attach(longrepr, name="失败信息", attachment_type=allure.attachment_type.TEXT)

                # 执行测试失败钩子
                from src.hooks.custom_hooks import on_test_failure
                try:
                    on_test_failure(Exception(longrepr))
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"执行 on_test_failure 钩子失败: {str(e)}")

            # 测试跳过
            if report.skipped:
                longrepr = str(report.longrepr) if report.longrepr else "无跳过原因"
                allure.attach(longrepr, name="跳过原因", attachment_type=allure.attachment_type.TEXT)

                # 执行测试跳过钩子
                from src.hooks.custom_hooks import on_test_skip
                try:
                    on_test_skip(longrepr)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"执行 on_test_skip 钩子失败: {str(e)}")
        except Exception as e:
            logger.warning(f"生成测试报告时出错: {e}")
