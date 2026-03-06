# -*- coding: utf-8 -*-
"""
测试用例管理API路由
"""

import json
from ruamel.yaml import YAML, YAMLError
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from server.models.database import get_db
from server.models.models import Project, TestCase, User
from server.auth.auth import require_permission
from server.schemas.schemas import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseListResponse,
    ResponseModel,
    PaginatedResponse,
    ImportRequest,
    ImportResponse
)


# 创建 YAML 实例
_yaml = YAML(typ='rt')
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


router = APIRouter(prefix="/api/testcases", tags=["测试用例管理"])


def test_case_to_response(test_case: TestCase) -> TestCaseResponse:
    """将TestCase模型转换为TestCaseResponse"""
    return TestCaseResponse(
        id=test_case.id,
        name=test_case.name,
        project_id=test_case.project_id,
        creator_id=test_case.creator_id,
        method=test_case.method,
        url=test_case.url,
        headers=json.loads(test_case.headers) if test_case.headers else None,
        params=json.loads(test_case.params) if test_case.params else None,
        body=json.loads(test_case.body) if test_case.body else None,
        assertions=json.loads(test_case.assertions) if test_case.assertions else None,
        extract=json.loads(test_case.extract) if test_case.extract else None,
        setup=json.loads(test_case.setup) if test_case.setup else None,
        teardown=json.loads(test_case.teardown) if test_case.teardown else None,
        timeout=test_case.timeout,
        retry=test_case.retry,
        tags=test_case.tags,
        category=test_case.category,
        priority=test_case.priority,
        description=test_case.description,
        source=test_case.source,
        is_active=test_case.is_active,
        last_run_at=test_case.last_run_at,
        last_run_status=test_case.last_run_status,
        created_at=test_case.created_at,
        updated_at=test_case.updated_at
    )


def check_project_access(project_id: int, current_user: User, db: Session) -> Project:
    """检查项目访问权限"""
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

    return project


@router.get("", response_model=PaginatedResponse, summary="获取测试用例列表")
def list_testcases(
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
        project_id: Optional[int] = Query(None, description="项目ID"),
        name: Optional[str] = Query(None, description="用例名称（模糊搜索）"),
        method: Optional[str] = Query(None, description="请求方法"),
        category: Optional[str] = Query(None, description="分类"),
        priority: Optional[int] = Query(None, ge=1, le=5, description="优先级"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user: User = Depends(require_permission("testcase:list")),
        db: Session = Depends(get_db)
):
    """
    获取测试用例列表（分页）
    需要权限：testcase:list
    """
    query = db.query(TestCase)

    # 数据隔离：非超级管理员只能看到自己项目的用例
    if not current_user.is_superuser:
        # 获取用户有权限的项目ID列表
        user_project_ids = db.query(Project.id).filter(
            Project.owner_id == current_user.id
        ).all()
        user_project_ids = [p[0] for p in user_project_ids]
        query = query.filter(TestCase.project_id.in_(user_project_ids))

    # 过滤条件
    if project_id:
        query = query.filter(TestCase.project_id == project_id)
    if name:
        query = query.filter(TestCase.name.like(f"%{name}%"))
    if method:
        query = query.filter(TestCase.method == method.upper())
    if category:
        query = query.filter(TestCase.category == category)
    if priority:
        query = query.filter(TestCase.priority == priority)
    if is_active is not None:
        query = query.filter(TestCase.is_active == is_active)

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    test_cases = query.order_by(TestCase.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[TestCaseListResponse.model_validate(tc) for tc in test_cases]
    )


@router.get("/{testcase_id}", response_model=TestCaseResponse, summary="获取测试用例详情")
def get_testcase(
        testcase_id: int,
        current_user: User = Depends(require_permission("testcase:read")),
        db: Session = Depends(get_db)
):
    """
    获取测试用例详情
    需要权限：testcase:read
    """
    test_case = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 权限检查
    check_project_access(test_case.project_id, current_user, db)

    return test_case_to_response(test_case)


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED, summary="创建测试用例（手工）")
def create_testcase(
        testcase_data: TestCaseCreate,
        current_user: User = Depends(require_permission("testcase:create")),
        db: Session = Depends(get_db)
):
    """
    手工创建测试用例
    需要权限：testcase:create
    """
    # 检查项目权限
    check_project_access(testcase_data.project_id, current_user, db)

    # 创建测试用例
    test_case = TestCase(
        name=testcase_data.name,
        project_id=testcase_data.project_id,
        creator_id=current_user.id,
        method=testcase_data.method,
        url=testcase_data.url,
        headers=json.dumps(testcase_data.headers) if testcase_data.headers else None,
        params=json.dumps(testcase_data.params) if testcase_data.params else None,
        body=json.dumps(testcase_data.body) if testcase_data.body else None,
        assertions=json.dumps(testcase_data.assertions) if testcase_data.assertions else None,
        extract=json.dumps(testcase_data.extract) if testcase_data.extract else None,
        setup=json.dumps(testcase_data.setup) if testcase_data.setup else None,
        teardown=json.dumps(testcase_data.teardown) if testcase_data.teardown else None,
        timeout=testcase_data.timeout,
        retry=testcase_data.retry,
        tags=testcase_data.tags,
        category=testcase_data.category,
        priority=testcase_data.priority,
        description=testcase_data.description,
        source='manual'
    )

    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    return test_case_to_response(test_case)


@router.put("/{testcase_id}", response_model=TestCaseResponse, summary="更新测试用例")
def update_testcase(
        testcase_id: int,
        testcase_data: TestCaseUpdate,
        current_user: User = Depends(require_permission("testcase:update")),
        db: Session = Depends(get_db)
):
    """
    更新测试用例
    需要权限：testcase:update
    """
    test_case = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 权限检查
    check_project_access(test_case.project_id, current_user, db)

    # 更新字段
    update_data = testcase_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in ['headers', 'params', 'body', 'assertions', 'extract', 'setup', 'teardown']:
            setattr(test_case, field, json.dumps(value) if value else None)
        else:
            setattr(test_case, field, value)

    db.commit()
    db.refresh(test_case)

    return test_case_to_response(test_case)


@router.delete("/{testcase_id}", response_model=ResponseModel, summary="删除测试用例")
def delete_testcase(
        testcase_id: int,
        current_user: User = Depends(require_permission("testcase:delete")),
        db: Session = Depends(get_db)
):
    """
    删除测试用例
    需要权限：testcase:delete
    """
    test_case = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 权限检查
    check_project_access(test_case.project_id, current_user, db)

    db.delete(test_case)
    db.commit()

    return ResponseModel(message="测试用例删除成功")


# ==================== 导入功能 ====================

@router.post("/import/yaml", response_model=ImportResponse, summary="从YAML文件导入")
async def import_from_yaml(
        project_id: int = Query(..., description="项目ID"),
        file: UploadFile = File(..., description="YAML文件"),
        current_user: User = Depends(require_permission("testcase:import")),
        db: Session = Depends(get_db)
):
    """
    从YAML文件导入测试用例
    需要权限：testcase:import
    """
    # 检查项目权限
    check_project_access(project_id, current_user, db)

    # 读取文件内容
    content = await file.read()

    try:
        # 解析YAML
        data = _yaml.load(content)

        # 支持单个用例和多个用例
        if isinstance(data, dict):
            data = {'test_cases': [data]}

        test_cases_data = data.get('test_cases', [])

        imported_cases = []
        errors = []

        for case_data in test_cases_data:
            try:
                test_case = TestCase(
                    name=case_data.get('name', '未命名用例'),
                    project_id=project_id,
                    creator_id=current_user.id,
                    method=case_data.get('method', 'GET'),
                    url=case_data.get('url', ''),
                    headers=json.dumps(case_data.get('headers')),
                    params=json.dumps(case_data.get('params')),
                    body=json.dumps(case_data.get('body')),
                    assertions=json.dumps(case_data.get('assertions')),
                    extract=json.dumps(case_data.get('extract')),
                    setup=json.dumps(case_data.get('setup')),
                    teardown=json.dumps(case_data.get('teardown')),
                    timeout=case_data.get('timeout', 30),
                    retry=case_data.get('retry', 0),
                    tags=case_data.get('tags'),
                    category=case_data.get('category'),
                    priority=case_data.get('priority', 3),
                    description=case_data.get('description'),
                    source='yaml',
                    source_file=file.filename
                )

                db.add(test_case)
                db.flush()
                imported_cases.append(test_case)

            except Exception as e:
                errors.append(f"用例 '{case_data.get('name', '未知')}' 导入失败: {str(e)}")

        db.commit()

        return ImportResponse(
            success_count=len(imported_cases),
            failed_count=len(errors),
            test_cases=[TestCaseListResponse.model_validate(tc) for tc in imported_cases],
            errors=errors
        )

    except YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"YAML解析失败: {str(e)}"
        )


@router.post("/import/json", response_model=ImportResponse, summary="从JSON文件导入")
async def import_from_json(
        project_id: int = Query(..., description="项目ID"),
        file: UploadFile = File(..., description="JSON文件"),
        current_user: User = Depends(require_permission("testcase:import")),
        db: Session = Depends(get_db)
):
    """
    从JSON文件导入测试用例
    需要权限：testcase:import
    """
    # 检查项目权限
    check_project_access(project_id, current_user, db)

    # 读取文件内容
    content = await file.read()

    try:
        # 解析JSON
        data = json.loads(content)

        # 支持单个用例和多个用例
        if isinstance(data, dict) and 'test_cases' not in data:
            data = {'test_cases': [data]}

        test_cases_data = data.get('test_cases', [])

        imported_cases = []
        errors = []

        for case_data in test_cases_data:
            try:
                test_case = TestCase(
                    name=case_data.get('name', '未命名用例'),
                    project_id=project_id,
                    creator_id=current_user.id,
                    method=case_data.get('method', 'GET'),
                    url=case_data.get('url', ''),
                    headers=json.dumps(case_data.get('headers')),
                    params=json.dumps(case_data.get('params')),
                    body=json.dumps(case_data.get('body')),
                    assertions=json.dumps(case_data.get('assertions')),
                    extract=json.dumps(case_data.get('extract')),
                    setup=json.dumps(case_data.get('setup')),
                    teardown=json.dumps(case_data.get('teardown')),
                    timeout=case_data.get('timeout', 30),
                    retry=case_data.get('retry', 0),
                    tags=case_data.get('tags'),
                    category=case_data.get('category'),
                    priority=case_data.get('priority', 3),
                    description=case_data.get('description'),
                    source='json',
                    source_file=file.filename
                )

                db.add(test_case)
                db.flush()
                imported_cases.append(test_case)

            except Exception as e:
                errors.append(f"用例 '{case_data.get('name', '未知')}' 导入失败: {str(e)}")

        db.commit()

        return ImportResponse(
            success_count=len(imported_cases),
            failed_count=len(errors),
            test_cases=[TestCaseListResponse.model_validate(tc) for tc in imported_cases],
            errors=errors
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JSON解析失败: {str(e)}"
        )


@router.post("/import/curl", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED, summary="从CURL导入")
async def import_from_curl(
        project_id: int = Query(..., description="项目ID"),
        curl_command: str = Query(..., description="CURL命令"),
        name: Optional[str] = Query(None, description="用例名称"),
        current_user: User = Depends(require_permission("testcase:import")),
        db: Session = Depends(get_db)
):
    """
    从CURL命令导入测试用例
    需要权限：testcase:import
    """
    # 检查项目权限
    check_project_access(project_id, current_user, db)

    try:
        # 解析CURL命令
        from src.utils.curl_parser import parse_curl

        parsed = parse_curl(curl_command)

        # 创建测试用例
        test_case = TestCase(
            name=name or f"CURL导入_{parsed.get('url', '')[:50]}",
            project_id=project_id,
            creator_id=current_user.id,
            method=parsed.get('method', 'GET'),
            url=parsed.get('url', ''),
            headers=json.dumps(parsed.get('headers')),
            body=json.dumps(parsed.get('data')),
            timeout=30,
            source='curl'
        )

        db.add(test_case)
        db.commit()
        db.refresh(test_case)

        return test_case_to_response(test_case)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CURL解析失败: {str(e)}"
        )


@router.post("/import/swagger", response_model=ImportResponse, summary="从Swagger导入")
async def import_from_swagger(
        import_request: ImportRequest,
        current_user: User = Depends(require_permission("testcase:import")),
        db: Session = Depends(get_db)
):
    """
    从Swagger文档导入测试用例
    需要权限：testcase:import
    """
    # 检查项目权限
    check_project_access(import_request.project_id, current_user, db)

    try:
        import requests

        # 获取Swagger文档
        response = requests.get(import_request.file_url, timeout=30)
        response.raise_for_status()

        swagger_data = response.json()

        # 解析Swagger文档
        imported_cases = []
        errors = []

        # OpenAPI 3.0 格式
        paths = swagger_data.get('paths', {})
        base_url = swagger_data.get('servers', [{}])[0].get('url', '')

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    try:
                        test_case = TestCase(
                            name=details.get('summary', f"{method.upper()} {path}"),
                            project_id=import_request.project_id,
                            creator_id=current_user.id,
                            method=method.upper(),
                            url=base_url + path if base_url else path,
                            description=details.get('description'),
                            tags=','.join(details.get('tags', [])),
                            source='swagger'
                        )

                        db.add(test_case)
                        db.flush()
                        imported_cases.append(test_case)

                    except Exception as e:
                        errors.append(f"接口 {method.upper()} {path} 导入失败: {str(e)}")

        db.commit()

        return ImportResponse(
            success_count=len(imported_cases),
            failed_count=len(errors),
            test_cases=[TestCaseListResponse.model_validate(tc) for tc in imported_cases],
            errors=errors
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Swagger导入失败: {str(e)}"
        )


# ==================== 导出功能 ====================

@router.get("/{testcase_id}/export/yaml", summary="导出为YAML")
def export_to_yaml(
        testcase_id: int,
        current_user: User = Depends(require_permission("testcase:export")),
        db: Session = Depends(get_db)
):
    """
    导出测试用例为YAML格式
    需要权限：testcase:export
    """
    test_case = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="测试用例不存在"
        )

    # 权限检查
    check_project_access(test_case.project_id, current_user, db)

    # 构建导出数据
    export_data = {
        'name': test_case.name,
        'method': test_case.method,
        'url': test_case.url,
        'headers': json.loads(test_case.headers) if test_case.headers else None,
        'params': json.loads(test_case.params) if test_case.params else None,
        'body': json.loads(test_case.body) if test_case.body else None,
        'assertions': json.loads(test_case.assertions) if test_case.assertions else None,
        'extract': json.loads(test_case.extract) if test_case.extract else None,
        'setup': json.loads(test_case.setup) if test_case.setup else None,
        'teardown': json.loads(test_case.teardown) if test_case.teardown else None,
        'timeout': test_case.timeout,
        'retry': test_case.retry,
        'tags': test_case.tags,
        'category': test_case.category,
        'priority': test_case.priority,
        'description': test_case.description
    }

    # 移除None值
    export_data = {k: v for k, v in export_data.items() if v is not None}

    return export_data
