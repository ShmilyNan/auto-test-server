# -*- coding: utf-8 -*-
"""
测试用例依赖管理钩子
实现 depends_on 功能：确保依赖的用例执行成功后才执行当前用例
"""
import os
import pytest
import time
from typing import Dict, List
from enum import Enum
from src.utils.logger import logger
from config.paths import get_env_config_file
from utils.yaml_loader import load_yaml_dict


def _get_dependency_wait_timeout() -> int:
    """
    从配置文件中获取依赖等待超时时间
    Returns:
        int: 超时时间（秒），默认 60 秒
    """
    try:
        # 从环境变量获取环境名称，默认为 test
        env = os.getenv('TEST_ENV', 'test')
        env_config_file = get_env_config_file(env)
        config = load_yaml_dict(env_config_file)

        # 从 dependency 配置中读取
        dependency_config = config.get('dependency', {})
        wait_timeout = dependency_config.get('wait_timeout', 60)

        logger.debug(f"从配置文件读取依赖等待超时: {wait_timeout}秒")
        return int(wait_timeout)
    except Exception as e:
        logger.warning(f"读取依赖等待超时配置失败，使用默认值: {e}")
        return 60


# 依赖等待超时时间（秒），从配置文件读取
DEPENDENCY_WAIT_TIMEOUT = _get_dependency_wait_timeout()


class TestStatus(Enum):
    """测试用例执行状态"""
    NOT_RUN = "not_run"      # 未执行
    PASSED = "passed"        # 通过
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过


# 全局测试结果存储（使用字典，key 为测试用例名称）
_test_results: Dict[str, TestStatus] = {}

# 测试用例名称映射表（nodeid -> 原始用例名称）
_test_name_mapping: Dict[str, str] = {}


def get_test_result(test_name: str) -> TestStatus:
    """
    获取测试用例的执行结果
    Args:
        test_name: 测试用例名称
    Returns:
        TestStatus: 测试执行状态
    """
    return _test_results.get(test_name, TestStatus.NOT_RUN)


def set_test_result(test_name: str, status: TestStatus):
    """
    设置测试用例的执行结果
    Args:
        test_name: 测试用例名称
        status: 测试执行状态
    """
    _test_results[test_name] = status
    logger.debug(f"设置测试结果: {test_name} = {status.value}")


def topological_sort(items: List) -> List:
    """
    根据依赖关系对测试用例进行拓扑排序
    Args:
        items: 测试用例列表
    Returns:
        List: 排序后的测试用例列表
    """
    # 构建依赖关系图
    dependency_map = {}  # {test_name: depends_on}
    name_to_item = {}    # {test_name: item}

    for item in items:
        # 获取原始用例名称
        test_case_info = getattr(item.obj, '_test_case', {})
        test_name = test_case_info.get('name', item.name)
        name_to_item[test_name] = item

        depends_on = getattr(item.obj, '_depends_on', None) or test_case_info.get('depends_on')

        if depends_on:
            dependency_map[test_name] = depends_on
            logger.debug(f"📌 发现依赖: {test_name} -> {depends_on}")

    # 执行拓扑排序（Kahn 算法）
    in_degree = {}     # 入度统计
    graph = {}         # 邻接表

    # 初始化
    for item in items:
        test_case_info = getattr(item.obj, '_test_case', {})
        test_name = test_case_info.get('name', item.name)
        in_degree[test_name] = 0
        graph[test_name] = []

    # 构建邻接表和入度
    for test_name, depends_on in dependency_map.items():
        if depends_on in name_to_item:
            graph[depends_on].append(test_name)
            in_degree[test_name] += 1
        else:
            logger.warning(f"⚠️  依赖的测试用例 '{depends_on}' 不存在，将被忽略")

    # 找到入度为0的节点
    queue = [test_name for test_name in in_degree if in_degree[test_name] == 0]
    sorted_items = []

    while queue:
        # 从队列中取出一个节点
        current = queue.pop(0)
        if current in name_to_item:
            sorted_items.append(name_to_item[current])

        # 减少邻居的入度
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # 检查是否存在循环依赖
    if len(sorted_items) != len(items):
        remaining = [name for name in in_degree if in_degree[name] > 0]
        logger.warning(f"⚠️  检测到循环依赖，涉及的测试用例: {remaining}")
        # 对于循环依赖的用例，保持原有顺序
        for item in items:
            test_case_info = getattr(item.obj, '_test_case', {})
            test_name = test_case_info.get('name', item.name)
            if test_name in remaining and item not in sorted_items:
                sorted_items.append(item)

    return sorted_items


def check_dependencies(test_name: str, depends_on: str, wait_for_execution: bool = False) -> tuple[bool, str]:
    """
    检查测试用例的依赖关系
    Args:
        test_name: 当前测试用例名称
        depends_on: 依赖的测试用例名称
        wait_for_execution: 是否等待依赖用例执行完成
    Returns:
        tuple: (是否可以执行, 跳过原因)
    """
    if not depends_on:
        # 没有依赖，可以执行
        return True, ""

    # 如果配置了等待机制
    if wait_for_execution:
        logger.info(f"⏳ {test_name} 等待依赖用例 '{depends_on}' 执行完成...")

        start_time = time.time()
        timeout = DEPENDENCY_WAIT_TIMEOUT

        while time.time() - start_time < timeout:
            dependency_status = get_test_result(depends_on)

            if dependency_status != TestStatus.NOT_RUN:
                # 依赖用例已经执行，跳出等待循环
                break

            # 等待 0.5 秒后重试
            time.sleep(0.5)
        else:
            # 超时
            reason = f"等待依赖用例 '{depends_on}' 执行超时（{timeout}秒）"
            logger.error(f"❌ {test_name}: {reason}")
            return False, reason

    # 检查依赖的用例执行结果
    dependency_status = get_test_result(depends_on)

    if dependency_status == TestStatus.NOT_RUN:
        # 依赖的用例未执行（可能因为测试筛选等原因）
        reason = f"依赖的测试用例 '{depends_on}' 未执行"
        logger.warning(f"❌ {test_name}: {reason}")
        return False, reason

    elif dependency_status == TestStatus.FAILED:
        # 依赖的用例执行失败
        reason = f"依赖的测试用例 '{depends_on}' 执行失败"
        logger.warning(f"❌ {test_name}: {reason}")
        return False, reason

    elif dependency_status == TestStatus.SKIPPED:
        # 依赖的用例被跳过
        reason = f"依赖的测试用例 '{depends_on}' 被跳过"
        logger.warning(f"❌ {test_name}: {reason}")
        return False, reason

    # 依赖的用例执行成功，可以执行
    logger.debug(f"✅ {test_name}: 依赖检查通过")
    return True, ""


# ========================================
# Pytest 钩子函数
# ========================================


def pytest_collection_modifyitems(session, config, items):
    """
    测试收集完成后修改测试用例顺序
    根据依赖关系进行拓扑排序，确保依赖的用例先执行
    Args:
        session: 测试会话对象
        config: 配置对象
        items: 测试用例列表
    """
    logger.info("🔄 根据依赖关系重新排序测试用例...")

    # 执行拓扑排序
    sorted_items = topological_sort(items)

    # 替换原有序列
    items[:] = sorted_items

    logger.info(f"✅ 测试用例排序完成，总计 {len(items)} 个用例")


def pytest_runtest_setup(item):
    """
    测试用例执行前的钩子
    用于检查依赖关系
    Args:
        item: 测试用例对象
    """
    # 获取测试用例信息
    test_case_info = getattr(item.obj, '_test_case', {})

    # 存储测试用例名称映射（nodeid -> 原始用例名称）
    test_name = test_case_info.get('name', item.name)
    _test_name_mapping[item.nodeid] = test_name

    logger.debug(f"🔍 测试用例映射: {item.nodeid} -> {test_name}")

    # 获取 depends_on 信息
    depends_on = getattr(item.obj, '_depends_on', None) or test_case_info.get('depends_on')

    if depends_on:
        # 检查依赖关系（不再等待，因为已经排序）
        # 使用原始用例名称进行检查
        can_run, skip_reason = check_dependencies(test_name, depends_on, wait_for_execution=False)

        if not can_run:
            # 依赖不满足，跳过当前用例
            logger.info(f"⏭️  跳过测试用例: {test_name}")
            logger.info(f"   原因: {skip_reason}")
            pytest.skip(skip_reason)


def pytest_runtest_logreport(report):
    """
    测试用例执行后的钩子
    用于记录测试结果
    Args:
        report: 测试报告对象
    """
    # 只记录 call 阶段的结果
    if report.when != "call":
        return

    # 获取原始用例名称
    test_name = _test_name_mapping.get(report.nodeid, report.nodeid)

    # 根据测试结果设置状态
    if report.passed:
        set_test_result(test_name, TestStatus.PASSED)
    elif report.failed:
        set_test_result(test_name, TestStatus.FAILED)
    elif report.skipped:
        set_test_result(test_name, TestStatus.SKIPPED)

    logger.debug(f"📝 记录测试结果: {test_name} -> {report.when} -> {report.outcome}")


def pytest_sessionstart(session):
    """
    测试会话开始时的钩子
    初始化测试结果存储
    Args:
        session: 测试会话对象
    """
    global _test_results, _test_name_mapping
    _test_results.clear()
    _test_name_mapping.clear()
    logger.info("📋 测试依赖管理系统初始化完成")


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束时的钩子
    输出依赖关系统计
    Args:
        session: 测试会话对象
        exitstatus: 退出状态码
    """
    # 统计测试结果
    passed = sum(1 for status in _test_results.values() if status == TestStatus.PASSED)
    failed = sum(1 for status in _test_results.values() if status == TestStatus.FAILED)
    skipped = sum(1 for status in _test_results.values() if status == TestStatus.SKIPPED)

    logger.info(f"📊 测试依赖统计:")
    logger.info(f"   通过: {passed}")
    logger.info(f"   失败: {failed}")
    logger.info(f"   跳过: {skipped}")
    logger.info(f"   总计: {len(_test_results)}")
