# -*- coding: utf-8 -*-
"""
数据库配置和会话管理
"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator


# 数据库配置
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://autotest_user:776462@localhost:5432/autotest_db'
)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False
)

# PostgreSQL 时区设置
@event.listens_for(engine, "connect")
def set_timezone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'Asia/Shanghai'")
    cursor.close()

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
