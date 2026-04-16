# -*- coding: utf-8 -*-
"""
Pytest 钩子模块
处理 pytest 核心钩子函数
"""
from src.utils.logger import init_logger
from src.allure_helpers.report_generator import generate_allure_report


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
        except Exception:
            # 如果初始化失败，继续执行（logger 可能已经被初始化）
            pass

        # 添加自定义标记
        _register_markers(config)
    except Exception as e:
        print(f"pytest_configure 出错: {e}")


def _register_markers(config):
    """
    注册 pytest 自定义标记
    """
    markers = [
        "smoke: 冒烟测试",
        "regression: 回归测试",
        "daily: 每日巡检",
        "single: 单例测试",
        "p0: P0级用例",
        "p1: P1级用例",
        "p2: P2级用例",
        "p3: P3级用例",
        "slow: 慢速测试",
        "skip: 跳过测试",
        "xfail: 预期失败",
        "positive: 正向测试",
        "negative: 逆向测试",
        "performance: 性能测试",
        "database: 数据库测试",
        "file: 文件上传测试",
        "tag: 通用标记",
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后自动生成 Allure 报告
    Args:
        session: pytest 会话对象
        exitstatus: 测试退出状态码
    """
    generate_allure_report()


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
