# -*- coding: utf-8 -*-
"""
测试执行API路由
"""
import json
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from server.auth.auth import get_current_user
from server.infrastructure.persistence.database import get_db
from server.infrastructure.persistence.models import Project, TestCase, TestRun, User
from server.schemas.schemas import RunTestRequest, RunTestResponse
from src.core.client import RequestsClient
from src.core.validator import Validator

router = APIRouter(prefix="/api/executions", tags=["测试执行"])


def _parse_json_field(value: str | None, default: Any):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _build_full_url(base_url: str | None, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"测试用例URL不是完整地址且项目未配置base_url: {path}"
        )
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


@router.post("/run", response_model=RunTestResponse, summary="执行测试用例")
def run_testcases(
        request: RunTestRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """执行测试用例并保存执行结果。"""
    if not request.test_case_ids:
        raise HTTPException(status_code=400, detail="test_case_ids不能为空")

    test_cases: List[TestCase] = db.query(TestCase).filter(TestCase.id.in_(request.test_case_ids)).all()
    if len(test_cases) != len(set(request.test_case_ids)):
        raise HTTPException(status_code=404, detail="存在测试用例不存在")

    project_ids = {case.project_id for case in test_cases}
    if len(project_ids) != 1:
        raise HTTPException(status_code=400, detail="仅支持同一项目的测试用例批量执行")

    project_id = next(iter(project_ids))
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权执行该项目测试用例")

    batch_id = uuid.uuid4().hex
    run_name = request.run_name or f"执行计划-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    started = time.time()
    client = RequestsClient({"timeout": 30, "max_retries": 0, "retry_interval": 0})
    validator = Validator()

    results: List[Dict[str, Any]] = []
    passed = failed = error = 0

    for case in test_cases:
        case_started = time.time()
        case_status = "error"
        error_message = None
        resp = None
        # response_data: Dict[str, Any] | None = None

        headers = _parse_json_field(case.headers, {})
        params = _parse_json_field(case.params, {})
        body = _parse_json_field(case.body, None)
        assertions = _parse_json_field(case.assertions, [])

        try:
            url = _build_full_url(project.base_url, case.url)
            resp = client.request(
                method=case.method,
                url=url,
                headers=headers,
                params=params,
                json=body if isinstance(body, (dict, list)) else None,
                data=body if isinstance(body, str) else None,
                timeout=case.timeout or 30,
            )
            # response_data = {
            #     "status_code": resp.get("status_code"),
            #     "headers": resp.get("headers"),
            #     "body": resp.get("body"),
            # }
            assertion_results = validator.validate(resp, assertions) if assertions else []
            assertion_passed = all(item.passed for item in assertion_results) if assertions else (resp.get("status_code", 0) < 400)
            case_status = "passed" if assertion_passed else "failed"

            if case_status == "passed":
                passed += 1
            else:
                failed += 1

            results.append({
                "test_case_id": case.id,
                "test_case_name": case.name,
                "status": case_status,
                "duration": int((time.time() - case_started) * 1000),
                "assertions": [
                    {
                        "passed": item.passed,
                        "message": item.message,
                        "assertion_type": item.assertion_type,
                        "actual": item.actual,
                        "expected": item.expected,
                    }
                    for item in assertion_results
                ],
            })

        except Exception as exc:
            error += 1
            error_message = str(exc)
            results.append({
                "test_case_id": case.id,
                "test_case_name": case.name,
                "status": "error",
                "duration": int((time.time() - case_started) * 1000),
                "error_message": error_message,
            })

        duration = int((time.time() - case_started) * 1000)
        test_run = TestRun(
            test_case_id=case.id,
            project_id=case.project_id,
            executor_id=current_user.id,
            status=case_status,
            duration=duration,
            # request_data=json.dumps({
            #     "method": case.method,
            #     "url": case.url,
            #     "headers": headers,
            #     "params": params,
            #     "body": body,
            # }, ensure_ascii=False),
            request_url=case.url,
            request_method=case.method,
            request_headers=json.dumps(headers, ensure_ascii=False),
            request_body=json.dumps(body, ensure_ascii=False) if body else None,
            # response_data=json.dumps(response_data, ensure_ascii=False) if response_data else None,
            response_status=resp.get("status_code") if resp else None,
             response_headers=json.dumps(resp.get("headers"), ensure_ascii=False) if resp else None,
            response_body=json.dumps(resp.get("body"), ensure_ascii=False) if resp else None,
            error_message=error_message,
            environment=request.environment,
            run_name=run_name,
            batch_id=batch_id,
        )

        db.add(test_run)

        case.last_run_at = datetime.now()
        case.last_run_status = case_status

    db.commit()
    client.close()

    total = len(test_cases)
    return RunTestResponse(
        total=total,
        passed=passed,
        failed=failed,
        error=error,
        duration=int((time.time() - started) * 1000),
        results=results,
        batch_id=batch_id,
        run_name=run_name,
    )
