"""
日志记录器封装
基于loguru实现
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


class TestLogger:
    """测试日志记录器"""
    
    def __init__(
        self,
        log_dir: str = "logs",
        log_level: str = "INFO",
        console: bool = True,
        file: bool = True,
        rotation: str = "10 MB",
        retention: str = "7 days",
        format_str: Optional[str] = None
    ):
        """
        初始化日志记录器
        
        Args:
            log_dir: 日志目录
            log_level: 日志级别
            console: 是否控制台输出
            file: 是否文件输出
            rotation: 日志轮转大小
            retention: 日志保留时间
            format_str: 自定义格式
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认格式
        if format_str is None:
            format_str = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )
        
        # 移除默认处理器
        logger.remove()
        
        # 控制台输出
        if console:
            logger.add(
                sys.stdout,
                level=log_level,
                format=format_str,
                colorize=True,
                enqueue=True
            )
        
        # 文件输出 - 所有日志
        if file:
            logger.add(
                self.log_dir / "app_{time:YYYY-MM-DD}.log",
                level="DEBUG",
                format=format_str,
                rotation=rotation,
                retention=retention,
                encoding="utf-8",
                enqueue=True
            )
        
        # 错误日志单独记录
        if file:
            logger.add(
                self.log_dir / "error_{time:YYYY-MM-DD}.log",
                level="ERROR",
                format=format_str,
                rotation=rotation,
                retention=retention,
                encoding="utf-8",
                enqueue=True
            )
        
        logger.info(f"日志记录器初始化完成，日志目录: {self.log_dir.absolute()}")
    
    def get_logger(self):
        """获取logger实例"""
        return logger


# 全局日志实例
_test_logger = None


def init_logger(**kwargs):
    """
    初始化全局日志记录器
    
    Args:
        **kwargs: 配置参数
    """
    global _test_logger
    
    if _test_logger is None:
        _test_logger = TestLogger(**kwargs)


def get_logger():
    """
    获取全局日志记录器
    
    Returns:
        Logger: loguru logger实例
    """
    global _test_logger
    
    if _test_logger is None:
        _test_logger = TestLogger()
    
    return logger

# 为了方便使用，直接导出logger
log = get_logger()
