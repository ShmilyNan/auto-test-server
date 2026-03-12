# -*- coding: utf-8 -*-
"""
认证模块 - JWT Token生成和验证
"""
# import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
# from server.models.database import get_db
# from server.models.models import User
from server.infrastructure.persistence.database import get_db, SessionLocal
from server.infrastructure.persistence.models import User
from common.config import get_env_int, get_env_str


# 配置
# SECRET_KEY = "your-secret-key-here-change-in-production"  # 生产环境需要修改
SECRET_KEY = get_env_str("SECRET_KEY", "$argon2id$v=19$m=65536,t=3,p=4$+J8zxrj3XgtBKIWwdq51Tg$YYRakdBUHQqPMOvV5P6C2gQ6nniYkMO1KZbT3/5YiRs")
DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_HOURS = 24
ACCESS_TOKEN_EXPIRE_HOURS = get_env_int("ACCESS_TOKEN_EXPIRE_HOURS", 24)

# 密码加密 - 使用Argon2 更安全且无长度限制
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__parallelism=4,
    argon2__memory_cost=2 ** 16
)

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def validate_secret_key() -> None:
    """校验JWT密钥配置，避免使用不安全默认值"""
    if not SECRET_KEY or SECRET_KEY == DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY 未正确配置，请通过环境变量设置高强度密钥"
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    Returns:
        JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码访问令牌
    Args:
        token: JWT token
    Returns:
        解码后的数据，失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    """
    获取当前用户
    用于FastAPI依赖注入
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return user


def get_current_user_from_token(token: str) -> User:
    """
    从 Token 字符串获取用户（用于 WebSocket 等非 Depends 场景）
    Args:
        token: JWT token 字符串
    Returns:
        User: 用户对象
    Raises:
        HTTPException: Token 无效或用户不存在
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据"
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        return user
    finally:
        db.close()

def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return current_user


def check_permission(user: User, permission_code: str) -> bool:
    """
    检查用户是否有指定权限
    Args:
        user: 用户对象
        permission_code: 权限代码
    Returns:
        是否有权限
    """
    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True

    # 检查用户的角色是否包含该权限
    for role in user.roles:
        for permission in role.permissions:
            if permission.code == permission_code:
                return True

    return False


def require_permission(permission_code: str):
    """
    权限装饰器
    用于API接口权限控制
    Args:
        permission_code: 权限代码
    Returns:
        依赖函数
    """

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有权限: {permission_code}"
            )
        return current_user

    return permission_checker
