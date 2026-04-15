"""
统一日志模块 - 基于 loguru
本模块提供统一的日志管理功能，使用 loguru 作为日志库，并拦截第三方库的 logging 输出。
功能特性：
1. 基于 loguru 的高性能日志记录
2. 支持控制台彩色输出和文件输出
3. 自动日志文件轮转（按大小）
4. 拦截第三方库的 logging 输出并统一管理
5. 向后兼容接口
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List
from loguru import logger


# ============================================================================
# 拦截器类：将标准 logging 输出转发到 loguru
# ============================================================================

class InterceptHandler(logging.Handler):
    """
    标准日志拦截器
    将 logging 标准库的输出拦截并转发到 loguru，实现统一管理。
    """

    @staticmethod
    def get_loguru_level(record: logging.LogRecord) -> int:
        """将 logging 级别转换为 loguru 级别"""
        try:
            return logger.level(record.levelname).no
        except ValueError:
            return 10  # 默认 DEBUG 级别

    def emit(self, record: logging.LogRecord) -> None:
        """拦截并转发日志记录"""
        try:
            # 获取对应的 loguru 级别名称
            try:
                level_name = logger.level(record.levelname).name
            except ValueError:
                level_name = record.levelname

            # 构造日志消息，包含原始的模块信息
            # 格式: "module_name:function_name:line_number - message"
            frame_info = f"{record.name}:{record.funcName}:{record.lineno}"

            # 使用 loguru 记录日志，使用 depth=2 跳过 emit 方法和日志框架
            logger.opt(depth=2, exception=record.exc_info).log(
                level_name, f"{frame_info} - {record.getMessage()}"
            )

        except Exception:
            # 防止拦截器本身出错，使用 logging 的默认错误处理
            self.handleError(record)


# ============================================================================
# 全局 logger 实例
# ============================================================================

# 创建默认 logger 实例
logger = logger

# 移除默认的处理器
logger.remove()

# 添加默认控制台处理器（在 init_logging 中会被替换）
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)


# ============================================================================
# 日志初始化函数
# ============================================================================

def init_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    console: bool = True,
    file: bool = True,
    rotation: str = "10 MB",
    retention: str = "10 days",
    compression: str = "zip",
    log_format: Optional[str] = None,
    intercept_logging: bool = True,
    intercept_modules: Optional[List[str]] = None
) -> None:
    """
    初始化日志配置
    Args:
        log_dir: 日志文件目录
        log_level: 日志级别（TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL）
        console: 是否输出到控制台
        file: 是否输出到文件
        rotation: 日志轮转策略（如 "10 MB"、"500 MB"、"00:00"、"1 week"）
        retention: 日志保留时间（如 "10 days"、"1 month"、"2 months"）
        compression: 压缩格式（"zip"、"gz"、"tar"）
        log_format: 自定义日志格式（loguru 格式）
        intercept_logging: 是否拦截标准 logging 输出
        intercept_modules: 需要拦截的模块列表（None 表示拦截所有）
    Examples:
        >>> init_logging(log_dir="logs", log_level="INFO")
        >>> init_logging(log_dir="logs", log_level="DEBUG", intercept_logging=True)
    """
    # 移除所有现有处理器
    logger.remove()

    # 默认日志格式
    if log_format is None:
        log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # 控制台处理器（带彩色）
    if console:
        logger.add(
            sys.stdout,
            format=log_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )

    # 文件处理器（所有日志级别）
    if file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 所有日志文件
        logger.add(
            log_path / "app.log",
            format=log_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )

        # 错误日志文件（只记录 ERROR 和 CRITICAL）
        logger.add(
            log_path / "error.log",
            format=log_format,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )

    # 拦截标准 logging 输出
    if intercept_logging:
        intercept_std_logging(intercept_modules)


def intercept_std_logging(modules: Optional[List[str]] = None) -> None:
    """
    拦截标准 logging 输出到 loguru
    Args:
        modules: 需要拦截的模块列表
                - None: 拦截所有模块（包括根 logger）
                - ["urllib3", "requests"]: 只拦截指定模块
    Examples:
        >>> # 拦截所有 logging 输出
        >>> intercept_std_logging()

        >>> # 只拦截特定模块
        >>> intercept_std_logging(["urllib3", "requests", "httpx"])
    """
    # 创建拦截器
    intercept_handler = InterceptHandler()
    intercept_handler.setLevel(0)  # 拦截所有级别

    if modules is None:
        # 拦截所有 logging 输出
        # 配置根 logger 使用拦截器
        logging.root.handlers = [intercept_handler]
        logging.root.setLevel(0)

        # 禁用第三方库的 propagate，避免重复日志
        _disable_third_party_propagate()

    else:
        # 只拦截指定模块
        for module_name in modules:
            try:
                module_logger = logging.getLogger(module_name)
                module_logger.handlers = [intercept_handler]
                module_logger.setLevel(0)
                module_logger.propagate = False
            except Exception as e:
                logger.warning(f"无法拦截模块 {module_name} 的日志: {e}")


def _disable_third_party_propagate() -> None:
    """
    禁用常见第三方库的默认 handlers，避免重复日志
    这些库通常有自己的 logging 配置，会输出重复的日志。
    我们需要清空它们的 handlers，让日志通过 propagate 传播到根 logger 的拦截器。
    """
    third_party_loggers = [
        # HTTP 客户端
        "urllib3",
        "requests",
        "httpx",
        "httpcore",
        "aiohttp",
        "http.client",

        # 数据库
        "sqlalchemy",
        "psycopg2",
        "pymysql",

        # 异步框架
        "asyncio",

        # 测试框架
        "pytest",
        "allure",

        # 其他常用库
        "uvicorn",
        "fastapi",
        "botocore",
        "boto3",
    ]

    for logger_name in third_party_loggers:
        try:
            lib_logger = logging.getLogger(logger_name)
            # 清空现有 handlers，避免重复输出
            lib_logger.handlers.clear()
            # 确保 propagate 为 True，让日志传播到根 logger 的拦截器
            lib_logger.propagate = True
        except Exception:
            pass


def init_logger(*args, **kwargs) -> None:
    """
    init_logging 的别名（向后兼容）
    保持向后兼容性，旧代码可以继续使用 init_logger 函数
    """
    init_logging(*args, **kwargs)


def get_logger(name: str):
    """
    获取命名的 logger 实例
    Args:
        name: logger 名称（通常使用 __name__）
    Returns:
        loguru logger 实例
    Examples:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    """
    return logger.bind(name=name)


# ============================================================================
# 模块级函数（直接使用全局 logger）
# ============================================================================

def debug(message: str, *args, **kwargs) -> None:
    """记录 DEBUG 级别日志"""
    logger.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    """记录 INFO 级别日志"""
    logger.info(message, *args, **kwargs)


def success(message: str, *args, **kwargs) -> None:
    """记录 SUCCESS 级别日志"""
    logger.success(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    """记录 WARNING 级别日志"""
    logger.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    """记录 ERROR 级别日志"""
    logger.error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    """记录 CRITICAL 级别日志"""
    logger.critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs) -> None:
    """记录异常日志（自动捕获当前异常）"""
    logger.exception(message, *args, **kwargs)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "logger",
    "init_logging",
    "init_logger",
    "get_logger",
    "intercept_std_logging",
    "InterceptHandler",
    # 便捷函数
    "debug",
    "info",
    "success",
    "warning",
    "error",
    "critical",
    "exception",
]
