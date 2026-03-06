# -*- coding: utf-8 -*-
"""
数据库配置和会话管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from server.models.models import Base

# 数据库配置
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///./test_platform.db'  # 默认使用SQLite
)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {},
    echo=False,  # 是否打印SQL语句
    pool_pre_ping=True,  # 连接池预检查
    pool_recycle=3600,  # 连接回收时间
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    用于FastAPI的依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    创建所有表
    """
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def drop_db():
    """
    删除所有数据库表
    ⚠️ 谨慎使用
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️ 数据库表已删除")


def get_db_session() -> Session:
    """
    获取数据库会话（非依赖注入方式）
    用于脚本或其他场景
    """
    return SessionLocal()
