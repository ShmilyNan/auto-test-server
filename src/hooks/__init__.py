# -*- coding: utf-8 -*-
"""
Hooks 包
包含框架级钩子和自定义业务钩子
"""
from src.hooks.allure_hooks import attach_request_response
from src.hooks.pytest_hooks import (
    pytest_configure,
    pytest_sessionfinish,
    pytest_collection_modifyitems,
)

__all__ = [
    # 框架级钩子
    "attach_request_response",
    "pytest_configure",
    "pytest_sessionfinish",
    "pytest_collection_modifyitems",
]
