#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动后端API服务
"""
import uvicorn
from common.config import get_env_str, get_env_int
from common.utils.logging import get_logger, init_logging


def start_server():
    """启动API服务"""
    init_logging()
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("🚀 启动接口自动化测试平台API服务")
    logger.info("=" * 60)

    # 数据库连接（默认 PostgreSQL，可通过环境变量覆盖）
    # 如需使用 SQLite，设置环境变量：DATABASE_URL=sqlite:///./test_platform.db
    db_url = get_env_str('DATABASE_URL', 'postgresql://autotest_user:776462@localhost:5432/autotest_db')
    logger.info(f"📦 数据库: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    # 启动服务
    uvicorn.run(
        "server.main:app",
        host=get_env_str('SERVER_BIND', '0.0.0.0'),
        port=get_env_int('SERVER_PORT', 8899),
        reload=get_env_str('SERVER_RELOAD', 'true').lower() == 'true',
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    start_server()
