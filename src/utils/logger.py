"""日志记录器封装（兼容层）。
统一委托到 common.utils.logging，供 src 与 server 共用。
"""
from common.utils.logging import get_logger as _get_logger
from common.utils.logging import init_logging


class TestLogger:
    """兼容旧接口：提供 get_logger。"""

    def __init__(self, **kwargs):
        init_logging(**kwargs)

    @staticmethod
    def get_logger():
        return _get_logger()

def init_logger(**kwargs):
    """兼容旧函数名。"""
    init_logging(**kwargs)

def get_logger():
    """获取全局logger。"""
    return _get_logger()

logger = get_logger()
__all__ = ["logger", "init_logger", "get_logger", "TestLogger"]