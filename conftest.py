# -*- coding: utf-8 -*-
"""
pytest配置文件
定义fixtures和钩子函数
"""
import os
import sys
import json
import pytest
import allure
import subprocess
import shutil
from pathlib import Path
from loguru import logger
from config import ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR, CONFIG_FILE, TEST_DATA_DIR, \
    get_env_config_file
from src.utils.yaml_loader import load_yaml_dict
from src.utils.logger import init_logger, get_logger
from src.core.client import create_client
from src.core.context import get_context
from src.core.parser import CaseDataParser
from src.core.validator import Validator
from src.utils.extractor import get_extractor
from src.utils.global_login import get_global_login


# ========================================
# 全局Fixtures
# ========================================
@pytest.fixture(scope="session", autouse=True)
def setup_session(http_client, env_config, default_headers, config):
    """
    会话级fixture，在整个测试会话开始前执行一次
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info("测试会话开始")
    logger.info(f"当前环境：{config.get('default_env', 'N/A')}")
    logger.info(f"当前环境: {env_config.get('base_url', 'N/A')}")
    logger.info("=" * 60)

    # 设置默认请求头到全局 context
    context = get_context()
    context.set_default_headers(default_headers)
    logger.info(f"已设置默认请求头: {default_headers}")

    # 执行全局登录（如果启用）
    global_login = get_global_login()
    if global_login.is_enabled():
        logger.info("检测到全局登录已启用，开始执行全局登录...")
        if global_login.login(http_client, env_config):
            logger.info("全局登录成功")
            # 更新默认请求头中的 Authorization
            auth_header = global_login.get_auth_header()
            if auth_header:
                updated_headers = context.get_default_headers()
                updated_headers['Authorization'] = auth_header
                context.set_default_headers(updated_headers)
                logger.info(f"已更新默认请求头中的 Authorization: {auth_header}")
        else:
            logger.warning("全局登录失败，后续测试可能收到影响")
    
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
    - Authorization（由全局登录自动添加）
    Returns:
        Dict: 默认请求头字典
    """
    logger = get_logger()
    headers = {}

    # 从 env 配置获取默认请求头
    env_headers = env_config.get('headers', {})

    # 默认请求头
    default_headers_map = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    }

    # 合并默认请求头，env 配置优先
    for key, default_value in default_headers_map.items():
        headers[key] = env_headers.get(key, default_value)

    # 其他 env 配置中的请求头
    for key, value in env_headers.items():
        if key not in headers and value:
            headers[key] = value

    logger.debug(f"默认请求头: {headers}")
    return headers


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

            # 附加请求JSON（如果请求体是JSON格式）
            request_body = request.get('body')
            if request_body is not None and isinstance(request_body, (dict, list)):
                try:
                    allure.attach(
                        json.dumps(request_body, ensure_ascii=False, indent=2),
                        name="请求JSON",
                        attachment_type=allure.attachment_type.JSON
                    )
                except Exception as e:
                    logger.warning(f"序列化请求JSON失败: {e}")

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
        # 初始化logger（确保日志配置生效）
        try:
            init_logger(
                log_dir="logs",
                log_level="INFO",
                console=True,
                file=True,
                rotation="10 MB",
                retention="7 days"
            )
        except Exception as e:
            # 如果初始化失败，继续执行（logger 可能已经被初始化）
            pass
        # 添加自定义标记
        config.addinivalue_line("markers", "smoke: 冒烟测试")
        config.addinivalue_line("markers", "regression: 回归测试")
        config.addinivalue_line("markers", "daily: 每日巡检")
        config.addinivalue_line("markers", "single: 单例测试")
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
        print(f"pytest_configure 出错: {e}")


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后自动生成 Allure 报告
    Args:
        session: pytest 会话对象
        exitstatus: 测试退出状态码
    """
    logger = get_logger()

    # 检查 allure 结果目录是否存在
    if not ALLURE_RESULTS_DIR.exists():
        logger.warning(f"Allure 结果目录不存在: {ALLURE_RESULTS_DIR}")
        return

    # 检查是否有测试结果
    result_files = list(ALLURE_RESULTS_DIR.glob("*.json"))
    if not result_files:
        logger.warning("Allure 结果目录中没有测试结果文件")
        return

    logger.info("=" * 60)
    logger.info("开始生成 Allure 测试报告...")
    logger.info(f"结果目录: {ALLURE_RESULTS_DIR}")
    logger.info(f"报告目录: {ALLURE_REPORT_DIR}")

    # 检查 allure 命令是否可用
    allure_cmd = _find_allure_command()

    if allure_cmd:
        # 使用 allure generate 命令生成报告
        _generate_allure_report_with_command(allure_cmd, ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR, logger)
    else:
        # 使用 Python 方式生成报告
        _generate_allure_report_with_python(ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR, logger)

    logger.info("=" * 60)


def _find_allure_command() -> str:
    """
    查找 allure 命令路径
    Returns:
        str: allure 命令路径，未找到返回空字符串
    """
    # Windows 下优先检查常见安装路径
    if sys.platform == "win32":
        # 检查 npm 全局安装路径
        npm_paths = [
            Path(os.environ.get("APPDATA", "")) / "npm" / "allure.cmd",
            Path(os.environ.get("LOCALAPPDATA", "")) / "npm" / "allure.cmd",
        ]
        for path in npm_paths:
            if path.exists():
                return str(path)

    # 检查 PATH 环境变量
    allure_cmd = shutil.which("allure")
    if allure_cmd:
        return allure_cmd
    return ""


def _generate_allure_report_with_command(allure_cmd: str, results_dir: Path, report_dir: Path, logger):
    """
    使用 allure 命令行工具生成报告
    Args:
        allure_cmd: allure 命令路径
        results_dir: 结果目录
        report_dir: 报告目录
        logger: 日志记录器
    """
    try:
        # 清理旧报告目录
        if report_dir.exists():
            shutil.rmtree(report_dir)

        # 构建命令：禁用 Google Analytics
        cmd = [
            allure_cmd,
            "generate",
            str(results_dir),
            "-o", str(report_dir),
            "--clean"
        ]

        # 设置环境变量禁用统计
        env = os.environ.copy()
        env["ALLURE_NO_ANALYTICS"] = "1"

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0:
            logger.info(f"✅ Allure 报告生成成功: {report_dir}")
            logger.info(f"   打开报告: {report_dir / 'index.html'}")
        else:
            logger.error(f"❌ Allure 报告生成失败: {result.stderr}")
            # 回退到 Python 方式
            _generate_allure_report_with_python(results_dir, report_dir, logger)

    except subprocess.TimeoutExpired:
        logger.error("❌ Allure 报告生成超时")
        _generate_allure_report_with_python(results_dir, report_dir, logger)
    except Exception as e:
        logger.error(f"❌ Allure 报告生成异常: {e}")
        _generate_allure_report_with_python(results_dir, report_dir, logger)


def _generate_allure_report_with_python(results_dir: Path, report_dir: Path, logger):
    """
    使用 Python 方式生成报告（作为 allure 命令不可用时的备选方案）
    Args:
        results_dir: 结果目录
        report_dir: 报告目录
        logger: 日志记录器
    """
    try:
        # 尝试安装并使用 allure-combine
        try:
            import allure_combine
        except ImportError:
            logger.info("正在安装 allure-combine...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "allure-combine", "-q"],
                capture_output=True
            )
            import allure_combine

        # 清理旧报告目录
        if report_dir.exists():
            shutil.rmtree(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        # 生成合并的 HTML 报告
        output_file = report_dir / "allure-report.html"
        allure_combine.combine(
            str(results_dir),
            output_file=str(output_file),
            ignore_errors=True
        )

        logger.info(f"✅ Allure 报告生成成功（Python 方式）: {output_file}")

    except ImportError:
        logger.warning("⚠️ allure-combine 安装失败")
        logger.info(f"💡 请手动安装 allure 命令行工具或 allure-combine:")
        logger.info("   - npm install -g allure-commandline")
        logger.info("   - pip install allure-combine")
        logger.info(f"   或手动执行: allure generate {results_dir} -o {report_dir} --clean")
    except Exception as e:
        logger.error(f"❌ Python 方式生成报告失败: {e}")
        logger.info(f"💡 请手动执行: allure generate {results_dir} -o {report_dir} --clean")


def pytest_collection_modifyitems(config, items):
    """
    修改测试用例集合
    可以在这里对用例进行排序、过滤等
    """
    # 根据优先级排序用例
    priority_order = {'p0': 1, 'p1': 2, 'p2': 3, 'p3': 4}
    
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
    parser = CaseDataParser()

    if not TEST_DATA_DIR.exists():
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
        base_url = env_config.get('base_url', 'http://localhost:8899')
        
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
        base_url = env_config.get('base_url', 'http://localhost:8899')
        
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
