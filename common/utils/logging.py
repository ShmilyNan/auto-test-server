"""统一日志工具。
- 使用 src 侧既有依赖 loguru 作为统一日志实现。
- 为 server 与 src 提供低耦合的统一入口。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _logger

_INITIALIZED = False


class _InterceptHandler(logging.Handler):
    """将标准 logging 转发到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def init_logging(
    log_dir: str | Path = "logs",
    log_level: str = "INFO",
    console: bool = True,
    file: bool = True,
    rotation: str = "10 MB",
    retention: str = "7 days",
    format_str: Optional[str] = None,
) -> None:
    """初始化全局日志配置（幂等）。"""
    global _INITIALIZED
    if _INITIALIZED:
        return

    if format_str is None:
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    target_log_dir = Path(log_dir)
    target_log_dir.mkdir(parents=True, exist_ok=True)

    _logger.remove()

    if console:
        _logger.add(
            sys.stdout,
            level=log_level,
            format=format_str,
            colorize=True,
            enqueue=True,
        )

    if file:
        _logger.add(
            target_log_dir / "app_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            format=format_str,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
        )
        _logger.add(
            target_log_dir / "error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format=format_str,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
        )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    _INITIALIZED = True


def get_logger(name: Optional[str] = None):
    """获取 logger；按需初始化默认配置。"""
    if not _INITIALIZED:
        init_logging()
    if name:
        return _logger.bind(name=name)
    return _logger
