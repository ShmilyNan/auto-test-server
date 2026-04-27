# -*- coding: utf-8 -*-
"""
测试用例依赖管理钩子
实现 depends_on 功能：确保依赖的用例执行成功后才执行当前用例
"""
import pytest
from typing import Dict, Set
from enum import Enum
from src.utils.logger import logger


class TestStatus(Enum):
    """测试用例执行状态"""
    NOT_RUN = "not_run"      # 未执行
    PASSED = "passed"        # 通过
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过


# 全局测试结果存储（使用字典，key 为测试用例名称）
_test_results: Dict[str, TestStatus] = {}


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


def get_dependency_graph() -> Dict[str, Set[str]]:
    """
    获取依赖关系图
    Returns:
        Dict: {测试用例名称: 依赖的用例名称集合}
    """
    dependency_graph = {}

    # 遍历所有收集到的测试用例
    for item in pytest.Session.items:
        # 获取 depends_on 信息（如果存在）
        depends_on = getattr(item.obj, '_depends_on', None) or \
                     getattr(item.obj, '_test_case', {}).get('depends_on')

        if depends_on:
            test_name = item.name
            if test_name not in dependency_graph:
                dependency_graph[test_name] = set()
            dependency_graph[test_name].add(depends_on)

    return dependency_graph


def check_dependencies(test_name: str, depends_on: str) -> tuple[bool, str]:
    """
    检查测试用例的依赖关系
    Args:
        test_name: 当前测试用例名称
        depends_on: 依赖的测试用例名称
    Returns:
        tuple: (是否可以执行, 跳过原因)
    """
    if not depends_on:
        # 没有依赖，可以执行
        return True, ""

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


def pytest_runtest_setup(item):
    """
    测试用例执行前的钩子
    用于检查依赖关系
    Args:
        item: 测试用例对象
    """
    # 获取 depends_on 信息
    depends_on = getattr(item.obj, '_depends_on', None) or \
                 getattr(item.obj, '_test_case', {}).get('depends_on')

    if depends_on:
        # 检查依赖关系
        can_run, skip_reason = check_dependencies(item.name, depends_on)

        if not can_run:
            # 依赖不满足，跳过当前用例
            logger.info(f"⏭️  跳过测试用例: {item.name}")
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

    test_name = report.nodeid

    # 根据测试结果设置状态
    if report.passed:
        set_test_result(test_name, TestStatus.PASSED)
    elif report.failed:
        set_test_result(test_name, TestStatus.FAILED)
    elif report.skipped:
        set_test_result(test_name, TestStatus.SKIPPED)


def pytest_sessionstart(session):
    """
    测试会话开始时的钩子
    初始化测试结果存储
    Args:
        session: 测试会话对象
    """
    global _test_results
    _test_results.clear()
    logger.info("📋 测试依赖管理系统初始化完成")


def pytest_session_finish(session, exitstatus):
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


# ========================================
# 工具函数
# ========================================


def get_all_dependencies() -> Dict[str, Set[str]]:
    """
    获取所有测试用例的依赖关系
    Returns:
        Dict: {测试用例名称: 依赖的用例名称集合}
    """
    dependency_graph = {}

    # 遍历当前 session 的所有测试用例
    session = pytest.Session if hasattr(pytest, 'Session') else None
    if session:
        for item in pytest.Session.items:
            depends_on = getattr(item.obj, '_depends_on', None) or \
                         getattr(item.obj, '_test_case', {}).get('depends_on')

            if depends_on:
                test_name = item.name
                if test_name not in dependency_graph:
                    dependency_graph[test_name] = set()
                dependency_graph[test_name].add(depends_on)

    return dependency_graph


def validate_dependency_graph() -> list[str]:
    """
    验证依赖关系图，检查是否存在循环依赖
    Returns:
        list: 循环依赖的错误信息列表
    """
    errors = []

    # 获取依赖关系图
    dependency_graph = get_all_dependencies()

    # 使用 DFS 检测循环依赖
    def dfs(node, visited, rec_stack):
        if node in rec_stack:
            # 发现循环依赖
            cycle = list(rec_stack) + [node]
            errors.append(f"发现循环依赖: {' -> '.join(cycle)}")
            return True

        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        # 检查所有依赖
        if node in dependency_graph:
            for dep in dependency_graph[node]:
                if dfs(dep, visited, rec_stack):
                    return True

        rec_stack.remove(node)
        return False

    # 对每个节点执行 DFS
    visited = set()
    for node in dependency_graph:
        if node not in visited:
            dfs(node, visited, set())

    return errors
