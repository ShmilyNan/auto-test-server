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

    # 设置环境变量
    os.environ.setdefault('DATABASE_URL', 'sqlite:///./test_platform.db')

    # 启动服务
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    start_server()
