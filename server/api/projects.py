# -*- coding: utf-8 -*-
"""
项目管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from server.models.database import get_db
from server.models.models import Project, Environment, User
from server.auth.auth import (
    get_current_user,
    require_permission
)
from server.schemas.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    EnvironmentCreate,
    EnvironmentResponse,
    ResponseModel,
    PaginatedResponse
)

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


@router.get("", response_model=PaginatedResponse, summary="获取项目列表")
def list_projects(
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
        name: Optional[str] = Query(None, description="项目名称（模糊搜索）"),
        code: Optional[str] = Query(None, description="项目代码"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user: User = Depends(require_permission("project:list")),
        db: Session = Depends(get_db)
):
    """
    获取项目列表（分页）
    需要权限：project:list
    """
    query = db.query(Project)

    # 数据隔离：非超级管理员只能看到自己创建的项目
    if not current_user.is_superuser:
        query = query.filter(Project.owner_id == current_user.id)

    # 过滤条件
    if name:
        query = query.filter(Project.name.like(f"%{name}%"))
    if code:
        query = query.filter(Project.code == code)
    if is_active is not None:
        query = query.filter(Project.is_active == is_active)

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    projects = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ProjectResponse.model_validate(p) for p in projects]
    )


@router.get("/all", response_model=List[ProjectResponse], summary="获取所有项目（不分页）")
def list_all_projects(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    获取所有项目（用于下拉选择等场景）
    """
    query = db.query(Project).filter(Project.is_active == True)

    # 数据隔离
    if not current_user.is_superuser:
        query = query.filter(Project.owner_id == current_user.id)

    projects = query.all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
def get_project(
        project_id: int,
        current_user: User = Depends(require_permission("project:read")),
        db: Session = Depends(get_db)
):
    """
    获取项目详情
    需要权限：project:read
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 数据隔离检查
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该项目"
        )

    return ProjectResponse.model_validate(project)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="创建项目")
def create_project(
        project_data: ProjectCreate,
        current_user: User = Depends(require_permission("project:create")),
        db: Session = Depends(get_db)
):
    """
    创建项目
    需要权限：project:create
    """
    # 检查项目代码是否已存在
    if db.query(Project).filter(Project.code == project_data.code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目代码已存在"
        )

    # 创建项目
    project = Project(
        name=project_data.name,
        code=project_data.code,
        description=project_data.description,
        base_url=project_data.base_url,
        owner_id=current_user.id
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse, summary="更新项目")
def update_project(
        project_id: int,
        project_data: ProjectUpdate,
        current_user: User = Depends(require_permission("project:update")),
        db: Session = Depends(get_db)
):
    """
    更新项目信息
    需要权限：project:update
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 数据隔离检查
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改该项目"
        )

    # 更新字段
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.base_url is not None:
        project.base_url = project_data.base_url
    if project_data.is_active is not None:
        project.is_active = project_data.is_active

    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=ResponseModel, summary="删除项目")
def delete_project(
        project_id: int,
        current_user: User = Depends(require_permission("project:delete")),
        db: Session = Depends(get_db)
):
    """
    删除项目
    需要权限：project:delete
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 数据隔离检查
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除该项目"
        )

    db.delete(project)
    db.commit()

    return ResponseModel(message="项目删除成功")


# ==================== 环境管理 ====================

@router.get("/{project_id}/environments", response_model=List[EnvironmentResponse], summary="获取项目环境列表")
def list_environments(
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    获取项目的环境配置列表
    """
    # 检查项目权限
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该项目"
        )

    environments = db.query(Environment).filter(
        Environment.project_id == project_id
    ).all()

    return [EnvironmentResponse.model_validate(e) for e in environments]


@router.post("/{project_id}/environments", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED,
             summary="创建环境配置")
def create_environment(
        project_id: int,
        env_data: EnvironmentCreate,
        current_user: User = Depends(require_permission("project:update")),
        db: Session = Depends(get_db)
):
    """
    创建环境配置
    需要权限：project:update
    """
    # 检查项目权限
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该项目"
        )

    # 检查环境代码是否已存在
    existing = db.query(Environment).filter(
        Environment.project_id == project_id,
        Environment.code == env_data.code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该环境代码已存在"
        )

    # 创建环境
    import json
    environment = Environment(
        name=env_data.name,
        code=env_data.code,
        project_id=project_id,
        base_url=env_data.base_url,
        headers=json.dumps(env_data.headers) if env_data.headers else None,
        variables=json.dumps(env_data.variables) if env_data.variables else None
    )

    db.add(environment)
    db.commit()
    db.refresh(environment)

    return EnvironmentResponse.model_validate(environment)
