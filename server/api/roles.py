# -*- coding: utf-8 -*-
"""
角色和权限管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from server.models.database import get_db
from server.models.models import Role, Permission
from server.auth.auth import (
    get_current_user,
    User,
    require_permission
)
from server.schemas.schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    PermissionCreate,
    PermissionResponse,
    ResponseModel,
    PaginatedResponse
)

router = APIRouter(prefix="/api", tags=["角色权限管理"])


# ==================== 角色管理 ====================

@router.get("/roles", response_model=PaginatedResponse, summary="获取角色列表")
def list_roles(
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
        name: Optional[str] = Query(None, description="角色名称（模糊搜索）"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user: User = Depends(require_permission("role:list")),
        db: Session = Depends(get_db)
):
    """
    获取角色列表（分页）
    需要权限：role:list
    """
    query = db.query(Role)

    # 过滤条件
    if name:
        query = query.filter(Role.name.like(f"%{name}%"))
    if is_active is not None:
        query = query.filter(Role.is_active == is_active)

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    roles = query.order_by(Role.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[RoleListResponse.model_validate(r) for r in roles]
    )


@router.get("/roles/all", response_model=List[RoleListResponse], summary="获取所有角色（不分页）")
def list_all_roles(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    获取所有角色（用于下拉选择等场景）
    """
    roles = db.query(Role).filter(Role.is_active == True).all()
    return [RoleListResponse.model_validate(r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse, summary="获取角色详情")
def get_role(
        role_id: int,
        current_user: User = Depends(require_permission("role:read")),
        db: Session = Depends(get_db)
):
    """
    获取角色详情
    需要权限：role:read
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    return RoleResponse.model_validate(role)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, summary="创建角色")
def create_role(
        role_data: RoleCreate,
        current_user: User = Depends(require_permission("role:create")),
        db: Session = Depends(get_db)
):
    """
    创建角色
    需要权限：role:create
    """
    # 检查角色名是否已存在
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色名已存在"
        )

    # 检查角色代码是否已存在
    if db.query(Role).filter(Role.code == role_data.code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色代码已存在"
        )

    # 创建角色
    role = Role(
        name=role_data.name,
        code=role_data.code,
        description=role_data.description
    )

    # 分配权限
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        role.permissions = permissions

    db.add(role)
    db.commit()
    db.refresh(role)

    return RoleResponse.model_validate(role)


@router.put("/roles/{role_id}", response_model=RoleResponse, summary="更新角色")
def update_role(
        role_id: int,
        role_data: RoleUpdate,
        current_user: User = Depends(require_permission("role:update")),
        db: Session = Depends(get_db)
):
    """
    更新角色信息
    需要权限：role:update
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 不能修改超级管理员角色
    if role.code == 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改超级管理员角色"
        )

    # 更新字段
    if role_data.name is not None:
        existing = db.query(Role).filter(
            Role.name == role_data.name,
            Role.id != role_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色名已存在"
            )
        role.name = role_data.name

    if role_data.code is not None:
        existing = db.query(Role).filter(
            Role.code == role_data.code,
            Role.id != role_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色代码已存在"
            )
        role.code = role_data.code

    if role_data.description is not None:
        role.description = role_data.description

    if role_data.is_active is not None:
        role.is_active = role_data.is_active

    # 更新权限
    if role_data.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        role.permissions = permissions

    db.commit()
    db.refresh(role)

    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}", response_model=ResponseModel, summary="删除角色")
def delete_role(
        role_id: int,
        current_user: User = Depends(require_permission("role:delete")),
        db: Session = Depends(get_db)
):
    """
    删除角色
    需要权限：role:delete
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 不能删除系统角色
    if role.code in ['admin', 'project_admin', 'tester', 'user']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除系统角色"
        )

    # 检查是否有用户在使用该角色
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该角色正在被 {len(role.users)} 个用户使用，不能删除"
        )

    db.delete(role)
    db.commit()

    return ResponseModel(message="角色删除成功")


# ==================== 权限管理 ====================

@router.get("/permissions", response_model=List[PermissionResponse], summary="获取权限列表")
def list_permissions(
        resource: Optional[str] = Query(None, description="资源类型"),
        current_user: User = Depends(require_permission("permission:list")),
        db: Session = Depends(get_db)
):
    """
    获取权限列表
    需要权限：permission:list
    """
    query = db.query(Permission)

    if resource:
        query = query.filter(Permission.resource == resource)

    permissions = query.order_by(Permission.resource, Permission.action).all()

    return [PermissionResponse.model_validate(p) for p in permissions]


@router.get("/permissions/{permission_id}", response_model=PermissionResponse, summary="获取权限详情")
def get_permission(
        permission_id: int,
        current_user: User = Depends(require_permission("permission:read")),
        db: Session = Depends(get_db)
):
    """
    获取权限详情
    需要权限：permission:read
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="权限不存在"
        )

    return PermissionResponse.model_validate(permission)


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED, summary="创建权限")
def create_permission(
        perm_data: PermissionCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    创建权限（仅超级管理员）
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可以创建权限"
        )

    # 检查权限代码是否已存在
    if db.query(Permission).filter(Permission.code == perm_data.code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="权限代码已存在"
        )

    permission = Permission(**perm_data.model_dump())
    db.add(permission)
    db.commit()
    db.refresh(permission)

    return PermissionResponse.model_validate(permission)


@router.post("/roles/{role_id}/permissions", response_model=RoleResponse, summary="为角色分配权限")
def assign_permissions(
        role_id: int,
        permission_ids: List[int],
        current_user: User = Depends(require_permission("permission:assign")),
        db: Session = Depends(get_db)
):
    """
    为角色分配权限
    需要权限：permission:assign
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 获取权限
    permissions = db.query(Permission).filter(
        Permission.id.in_(permission_ids)
    ).all()

    role.permissions = permissions
    db.commit()
    db.refresh(role)

    return RoleResponse.model_validate(role)
