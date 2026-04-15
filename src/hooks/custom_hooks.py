# -*- coding: utf-8 -*-
"""
自定义钩子函数示例
"""
import time
from typing import Dict, Any
from src.core.context import get_context


def before_login():
    """
    登录前钩子
    清除旧的token
    """
    context = get_context()
    context.set_local('access_token', None)
    context.set_local('refresh_token', None)
    print("登录前钩子执行: 清除旧token")


def after_login(response: Dict[str, Any]):
    """
    登录后钩子
    自动保存token到缓存
    """
    context = get_context()

    if response.get('status_code') == 200:
        data = response.get('body', {}).get('data', {})
        token = data.get('token')

        if token:
            # 缓存token，有效期24小时
            context.set_cache('access_token', token, ttl=86400)
            print(f"登录后钩子执行: token已缓存")


def before_request():
    """
    请求前钩子
    记录请求开始时间
    """
    context = get_context()
    context.set_local('request_start_time', time.time())


def after_request(response: Dict[str, Any]):
    """
    请求后钩子
    记录响应时间
    """
    context = get_context()

    start_time = context.get_local('request_start_time')
    if start_time:
        elapsed = time.time() - start_time
        context.set_local('request_elapsed', elapsed)
        print(f"请求耗时: {elapsed:.3f}s")


def before_assertion():
    """
    断言前钩子
    """
    print("准备执行断言...")


def after_assertion(result: Dict[str, Any]):
    """
    断言后钩子
    """
    if result.get('passed'):
        print(f"断言通过: {result.get('message')}")
    else:
        print(f"断言失败: {result.get('message')}")


def on_test_failure(error: Exception):
    """
    测试失败钩子
    """
    print(f"测试失败: {str(error)}")
    # 可以在这里执行额外的错误处理逻辑
    # 例如：发送告警、记录日志等


def on_test_success():
    """
    测试成功钩子
    """
    print("测试成功")
    # 可以在这里执行成功后的处理逻辑


def on_test_skip(reason: str):
    """
    测试跳过钩子
    """
    print(f"测试跳过: {reason}")


def setup_suite():
    """
    测试套件设置钩子
    在整个测试套件开始前执行
    """
    print("测试套件开始")
    # 初始化测试数据
    # 准备测试环境


def teardown_suite():
    """
    测试套件清理钩子
    在整个测试套件结束后执行
    """
    print("测试套件结束")
    # 清理测试数据
    # 恢复测试环境


def before_database_query(sql: str):
    """
    数据库查询前钩子
    """
    print(f"执行SQL查询: {sql}")


def after_database_query(result: Any):
    """
    数据库查询后钩子
    """
    print(f"SQL查询结果: {result}")

# 更多自定义钩子可以根据需要添加
