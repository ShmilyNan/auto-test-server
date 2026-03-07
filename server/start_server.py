#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动后端API服务
"""
import os
import uvicorn


def start_server():
    """启动API服务"""
    print("\n" + "=" * 60)
    print("🚀 启动接口自动化测试平台API服务")
    print("=" * 60)

    # 数据库连接（默认 PostgreSQL，可通过环境变量覆盖）
    # 如需使用 SQLite，设置环境变量：DATABASE_URL=sqlite:///./test_platform.db
    db_url = os.getenv('DATABASE_URL', 'postgresql://autotest_user:776462@localhost:5432/autotest_db')
    print(f"📦 数据库: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    # 启动服务
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8899,
        reload=True,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    start_server()
