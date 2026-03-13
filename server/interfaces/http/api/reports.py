# -*- coding: utf-8 -*-
"""测试报告API"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from server.auth.auth import get_current_user
from server.infrastructure.persistence.database import get_db
from server.infrastructure.persistence.models import Project, TestReport, TestRun, User
from server.schemas.schemas import (
    PaginatedResponse,
    ReportCreateRequest,
    ReportDetailResponse,
    ReportListItem,
)

router = APIRouter(prefix="/api/reports", tags=["测试报告"])


@router.post("/generate", response_model=ReportDetailResponse, summary="基于执行计划生成测试报告")
def generate_report(
        request: ReportCreateRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    runs = db.query(TestRun).filter(TestRun.batch_id == request.batch_id).all()
    if not runs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行批次不存在")

    project_id = runs[0].project_id
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该项目")

    total = len(runs)
    passed = sum(1 for item in runs if item.status == "passed")
    failed = sum(1 for item in runs if item.status == "failed")
    error = sum(1 for item in runs if item.status == "error")
    pass_rate = (passed / total) if total else 0

    report_name = request.name or runs[0].run_name or f"测试报告-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    summary = {
        "batch_id": request.batch_id,
        "generated_from": "test_runs",
        "run_name": runs[0].run_name,
    }

    report = TestReport(
        name=report_name,
        batch_id=request.batch_id,
        project_id=project_id,
        creator_id=current_user.id,
        total=total,
        passed=passed,
        failed=failed,
        error=error,
        pass_rate=f"{pass_rate * 100:.2f}%",
        status="passed" if (failed == 0 and error == 0) else "failed",
        allure_report_path=f"reports/allure-report/{request.batch_id}",
        summary=json.dumps(summary, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportDetailResponse.model_validate(report)


@router.get("", response_model=PaginatedResponse, summary="查询测试报告列表")
def list_reports(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        project_id: Optional[int] = Query(None),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    query = db.query(TestReport)

    if not current_user.is_superuser:
        user_project_ids = [item.id for item in db.query(Project).filter(Project.owner_id == current_user.id).all()]
        query = query.filter(TestReport.project_id.in_(user_project_ids))

    if project_id is not None:
        query = query.filter(TestReport.project_id == project_id)

    total = query.count()
    items = query.order_by(TestReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ReportListItem.model_validate(item) for item in items],
    )


@router.get("/{report_id}", response_model=ReportDetailResponse, summary="查询测试报告详情")
def get_report_detail(
        report_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    report = db.query(TestReport).filter(TestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="测试报告不存在")

    project = db.query(Project).filter(Project.id == report.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该测试报告")

    return ReportDetailResponse.model_validate(report)
