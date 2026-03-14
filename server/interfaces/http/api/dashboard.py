# -*- coding: utf-8 -*-
"""仪表盘统计API"""
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.auth.auth import get_current_user
from server.infrastructure.persistence.database import get_db
from server.infrastructure.persistence.models import Project, TestCase, TestRun, User
from server.schemas.schemas import DashboardStatsResponse

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/stats", response_model=DashboardStatsResponse, summary="获取仪表盘统计数据")
def dashboard_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    project_query = db.query(Project)
    if not current_user.is_superuser:
        project_query = project_query.filter(Project.owner_id == current_user.id)
    project_ids = [p.id for p in project_query.all()]

    if not project_ids:
        return DashboardStatsResponse(
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
            running_cases=0,
            execution_trend=[],
            project_pass_rate=[],
            recent_runs=[],
        )

    total_cases = db.query(TestCase).filter(TestCase.project_id.in_(project_ids)).count()
    passed_cases = db.query(TestRun).filter(TestRun.project_id.in_(project_ids), TestRun.status == "passed").count()
    failed_cases = db.query(TestRun).filter(TestRun.project_id.in_(project_ids), TestRun.status.in_(["failed", "error"])).count()
    running_cases = db.query(TestRun).filter(TestRun.project_id.in_(project_ids), TestRun.status == "running").count()

    today = datetime.now().date()
    daily = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    for idx in range(7):
        day = today - timedelta(days=6 - idx)
        daily[day.isoformat()] = {"total": 0, "passed": 0, "failed": 0}

    runs = db.query(TestRun).filter(TestRun.project_id.in_(project_ids), TestRun.created_at >= datetime.now() - timedelta(days=7)).all()
    for run in runs:
        key = run.created_at.date().isoformat()
        if key not in daily:
            continue
        daily[key]["total"] += 1
        if run.status == "passed":
            daily[key]["passed"] += 1
        elif run.status in ["failed", "error"]:
            daily[key]["failed"] += 1

    execution_trend = [
        {
            "date": key,
            "total": value["total"],
            "passed": value["passed"],
            "failed": value["failed"],
        }
        for key, value in sorted(daily.items())
    ]

    project_pass_rate = []
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    for project in projects:
        project_runs = db.query(TestRun).filter(TestRun.project_id == project.id).all()
        total = len(project_runs)
        passed = sum(1 for item in project_runs if item.status == "passed")
        rate = (passed / total) if total else 0
        project_pass_rate.append({
            "project_id": project.id,
            "project_name": project.name,
            "total": total,
            "passed": passed,
            "pass_rate": round(rate, 4),
        })

    recent_run_query = db.query(TestRun, Project, TestCase).join(
        Project, Project.id == TestRun.project_id
    ).join(
        TestCase, TestCase.id == TestRun.test_case_id
    ).filter(
        TestRun.project_id.in_(project_ids)
    ).order_by(TestRun.created_at.desc()).limit(10).all()

    recent_runs = [
        {
            "run_name": run.run_name or f"执行-{run.batch_id or run.id}",
            "project_name": project.name,
            "case_count": 1,
            "status": run.status,
            "created_at": run.created_at,
            "test_case_name": testcase.name,
        }
        for run, project, testcase in recent_run_query
    ]

    return DashboardStatsResponse(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        running_cases=running_cases,
        execution_trend=execution_trend,
        project_pass_rate=project_pass_rate,
        recent_runs=recent_runs,
    )
