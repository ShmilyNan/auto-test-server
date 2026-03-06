# -*- coding: utf-8 -*-
"""
用户管理API路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from server.models.database import get_db
from server.models.models import User, Role
from server.auth.auth import (
    get_password_hash,
    require_permission
)
from server.schemas.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    ResponseModel,
    PaginatedResponse
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", response_model=PaginatedResponse, summary="获取用户列表")
def list_users(
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
        username: Optional[str] = Query(None, description="用户名（模糊搜索）"),
        email: Optional[str] = Query(None, description="邮箱（模糊搜索）"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user: User = Depends(require_permission("user:list")),
        db: Session = Depends(get_db)
):
    """
    获取用户列表（分页）
    需要权限：user:list
    """
    query = db.query(User)

    # 过滤条件
    if username:
        query = query.filter(User.username.like(f"%{username}%"))
    if email:
        query = query.filter(User.email.like(f"%{email}%"))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserListResponse.model_validate(u) for u in users]
    )


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户详情")
def get_user(
        user_id: int,
        current_user: User = Depends(require_permission("user:read")),
        db: Session = Depends(get_db)
):
    """
    获取用户详情
    需要权限：user:read
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="创建用户")
def create_user(
        user_data: UserCreate,
        current_user: User = Depends(require_permission("user:create")),
        db: Session = Depends(get_db)
):
    """
    创建用户
    需要权限：user:create
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )

    # 分配角色
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        user.roles = roles

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户")
def update_user(
        user_id: int,
        user_data: UserUpdate,
        current_user: User = Depends(require_permission("user:update")),
        db: Session = Depends(get_db)
):
    """
    更新用户信息
    需要权限：user:update
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新字段
    if user_data.email is not None:
        # 检查邮箱是否被其他用户使用
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    # 更新角色
    if user_data.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        user.roles = roles

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=ResponseModel, summary="删除用户")
def delete_user(
        user_id: int,
        current_user: User = Depends(require_permission("user:delete")),
        db: Session = Depends(get_db)
):
    """
    删除用户
    需要权限：user:delete
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )

    # 不能删除超级管理员
    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除超级管理员"
        )

    db.delete(user)
    db.commit()

    return ResponseModel(message="用户删除成功")


@router.put("/{user_id}/reset-password", response_model=ResponseModel, summary="重置用户密码")
def reset_user_password(
        user_id: int,
        new_password: str = Query(..., min_length=6, max_length=50, description="新密码"),
        current_user: User = Depends(require_permission("user:update")),
        db: Session = Depends(get_db)
):
    """
    重置用户密码（管理员操作）
    需要权限：user:update
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    user.hashed_password = get_password_hash(new_password)
    db.commit()

    return ResponseModel(message="密码重置成功")
