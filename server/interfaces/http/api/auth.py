# -*- coding: utf-8 -*-
"""
认证API路由
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from server.infrastructure.persistence.database import get_db
from server.infrastructure.persistence.models import User
from server.auth.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_HOURS
)
from server.schemas.schemas import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    ChangePasswordRequest,
    ResponseModel
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    Returns:
        JWT token和用户信息
    """
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()

    # 验证用户
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    # 创建token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    """
    return UserResponse.model_validate(current_user)


@router.put("/change-password", response_model=ResponseModel, summary="修改密码")
def change_password(
        request: ChangePasswordRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    修改密码
    """
    # 验证旧密码
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 更新密码
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return ResponseModel(message="密码修改成功")


@router.post("/logout", response_model=ResponseModel, summary="用户登出")
def logout(current_user: User = Depends(get_current_user)):
    """
    用户登出
    注：JWT token无法在服务端失效，客户端需要删除token
    """
    return ResponseModel(message="登出成功")
