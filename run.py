#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
接口自动化测试平台 - 运行入口
"""
import sys
import os
import argparse
import time
import pytest
from config import CONFIG_FILE, ALLURE_RESULTS_DIR, get_env_config_file
from src.utils.yaml_loader import load_yaml
from src.utils.logger import logger
from src.utils.notifier import NotificationManager


def load_config() -> dict:
    """
    加载配置文件
    Returns:
        dict: 配置字典
    """
    if not CONFIG_FILE.exists():
        logger.warning(f"配置文件不存在: {CONFIG_FILE}，使用默认配置")
        return {}

    config = load_yaml(CONFIG_FILE)

    logger.info(f"加载配置文件: {CONFIG_FILE}")
    return config


def load_env_config(env: str = "test") -> dict:
    """
    加载环境配置
    Args:
        env: 环境名称 (test/prod)
    Returns:
        dict: 环境配置字典
    """
    env_file = get_env_config_file(env)
    if not env_file.exists():
        logger.warning(f"环境配置文件不存在: {env_file}")
        return {}

    env_config = load_yaml(env_file)

    logger.info(f"加载环境配置: {env}")
    return env_config


def run_tests(
        env: str = "test",
        test_dir: str = "src/api",
        markers: str = None,
        verbose: bool = True,
        workers: int = None,
        report: bool = True
) -> int:
    """
    运行测试
    Args:
        env: 环境名称
        test_dir: 测试目录
        markers: pytest markers
        verbose: 是否详细输出
        workers: 并发worker数
        report: 是否生成报告
    Returns:
        int: 退出码
    """
    start_time = time.time()

    # 加载配置
    config = load_config()
    env_config = load_env_config(env)

    # 注意：日志初始化已移至 conftest.py 的 pytest_configure 钩子中
    # 使用 logger 时确保先调用 pytest_configure 或通过 pytest 运行

    try:
        logger.info(f"=" * 60)
        logger.info(f"接口自动化测试平台启动")
        logger.info(f"环境: {env}")
        logger.info(f"测试目录: {test_dir}")
        logger.info(f"=" * 60)
    except:
        # logger 可能尚未初始化，使用 print
        print(f"=" * 60)
        print(f"接口自动化测试平台启动")
        print(f"环境: {env}")
        print(f"测试目录: {test_dir}")
        print(f"=" * 60)

    # 设置环境变量（供测试用例使用）
    os.environ['TEST_ENV'] = env

    # 构建pytest参数
    pytest_args = [test_dir, '-v']

    if verbose:
        pytest_args.append('-s')

    if markers:
        pytest_args.extend(['-m', markers])

    # 并发执行
    if workers:
        pytest_args.extend(['-n', str(workers)])

    # Allure报告
    if report:
        pytest_args.extend([f'--alluredir={ALLURE_RESULTS_DIR}', '--clean-alluredir'])

    # 其他pytest参数
    pytest_args.extend([
        '--tb=short',
        '--strict-markers'
    ])

    logger.info(f"pytest参数: {' '.join(pytest_args)}")

    try:
        # 运行测试
        exit_code = pytest.main(pytest_args)

        # 计算耗时
        duration = time.time() - start_time

        logger.info(f"=" * 60)
        logger.info(f"测试执行完成，耗时: {duration:.2f}s")
        logger.info(f"退出码: {exit_code}")
        logger.info(f"=" * 60)

        # 生成测试报告
        if report:
            logger.info(f"Allure报告已生成到: {ALLURE_RESULTS_DIR}")
            logger.info("查看报告: allure serve reports/allure")

        # 发送通知
        notification_config = config.get('notification', {})
        if notification_config.get('enable', False):
            notifier = NotificationManager(notification_config)

            # 构造报告数据（简化版）
            report_data = {
                'env': env,
                'duration': duration,
                'exit_code': exit_code,
                'success': exit_code == 0
            }

            # 根据退出码判断通知级别
            notify_level = notification_config.get('level', 'failed')
            if notify_level == 'all' or (notify_level == 'failed' and exit_code != 0):
                notifier.send_test_report(report_data)

        return exit_code

    except Exception as e:
        logger.error(f"测试执行异常: {str(e)}")
        return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='接口自动化测试平台')

    parser.add_argument(
        '--env',
        type=str,
        default='test',
        choices=['test', 'prod'],
        help='测试环境 (默认: test)'
    )

    parser.add_argument(
        '--test-dir',
        type=str,
        default='src/api',
        help='测试目录 (默认: src/api)'
    )

    parser.add_argument(
        '-m',
        '--markers',
        type=str,
        # default='single',
        default=None,
        help='pytest markers'
    )

    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=True,
        help='详细输出'
    )

    parser.add_argument(
        '-n',
        '--workers',
        type=int,
        default=None,
        help='并发worker数'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='不生成报告'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='仅生成报告，不运行测试'
    )

    args = parser.parse_args()

    # 仅生成报告
    if args.report_only:
        os.system(f'allure generate {ALLURE_RESULTS_DIR} -o reports/html --clean')
        logger.info("HTML报告已生成到: reports/html")
        return 0

    # 运行测试
    exit_code = run_tests(
        env=args.env,
        test_dir=args.test_dir,
        markers=args.markers,
        verbose=args.verbose,
        workers=args.workers,
        report=not args.no_report
    )

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
