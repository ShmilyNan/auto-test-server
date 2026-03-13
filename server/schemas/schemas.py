# -*- coding: utf-8 -*-
"""
Pydantic模型 - 用于API数据验证和序列化
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== 基础模型 ====================

class ResponseModel(BaseModel):
    """统一响应模型"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[Any] = Field(default=None, description="数据")


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    total: int = Field(description="总数")
    page: int = Field(description="当前页")
    page_size: int = Field(description="每页大小")
    items: List[Any] = Field(description="数据列表")


# ==================== 用户相关 ====================

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    role_ids: Optional[List[int]] = Field(default=[], description="角色ID列表")


class UserUpdate(BaseModel):
    """更新用户"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=50)
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    is_active: bool
    is_superuser: bool
    roles: List['RoleResponse'] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(UserBase):
    """用户列表响应（简化版）"""
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 角色相关 ====================

class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    code: str = Field(..., min_length=2, max_length=50, description="角色代码")
    description: Optional[str] = Field(None, max_length=255, description="角色描述")


class RoleCreate(RoleBase):
    """创建角色"""
    permission_ids: Optional[List[int]] = Field(default=[], description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int
    is_active: bool
    permissions: List['PermissionResponse'] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(RoleBase):
    """角色列表响应（简化版）"""
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 权限相关 ====================

class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str = Field(..., max_length=100, description="权限名称")
    code: str = Field(..., max_length=100, description="权限代码")
    resource: str = Field(..., max_length=50, description="资源类型")
    action: str = Field(..., max_length=20, description="操作类型")
    description: Optional[str] = Field(None, max_length=255, description="权限描述")


class PermissionCreate(PermissionBase):
    """创建权限"""
    pass


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 项目相关 ====================

class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=2, max_length=100, description="项目名称")
    code: str = Field(..., min_length=2, max_length=50, description="项目代码")
    description: Optional[str] = Field(None, description="项目描述")
    base_url: Optional[str] = Field(None, max_length=255, description="基础URL")


class ProjectCreate(ProjectBase):
    """创建项目"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    owner_id: int
    owner: Optional[UserListResponse] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnvironmentBase(BaseModel):
    """环境基础模型"""
    name: str = Field(..., max_length=50, description="环境名称")
    code: str = Field(..., max_length=30, description="环境代码")
    base_url: Optional[str] = Field(None, max_length=255, description="基础URL")
    headers: Optional[Dict[str, Any]] = Field(None, description="默认请求头")
    variables: Optional[Dict[str, Any]] = Field(None, description="环境变量")


class EnvironmentCreate(EnvironmentBase):
    """创建环境"""
    pass


class EnvironmentResponse(EnvironmentBase):
    """环境响应模型"""
    id: int
    project_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 测试用例相关 ====================

class TestCaseBase(BaseModel):
    """测试用例基础模型"""
    name: str = Field(..., min_length=2, max_length=200, description="用例名称")
    method: str = Field(..., description="请求方法")
    url: str = Field(..., max_length=500, description="请求URL")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(None, description="URL参数")
    body: Optional[Dict[str, Any]] = Field(None, description="请求体")
    assertions: Optional[List[Dict[str, Any]]] = Field(None, description="断言配置")
    extract: Optional[Dict[str, Any]] = Field(None, description="数据提取配置")
    setup: Optional[List[Dict[str, Any]]] = Field(None, description="前置步骤")
    teardown: Optional[List[Dict[str, Any]]] = Field(None, description="后置步骤")
    timeout: Optional[int] = Field(default=30, ge=1, le=600, description="超时时间(秒)")
    retry: Optional[int] = Field(default=0, ge=0, le=5, description="重试次数")
    tags: Optional[str] = Field(None, max_length=255, description="标签")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    priority: Optional[int] = Field(default=3, ge=1, le=5, description="优先级")
    description: Optional[str] = Field(None, description="用例描述")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v):
        allowed = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if v.upper() not in allowed:
            raise ValueError(f'请求方法必须是: {", ".join(allowed)}')
        return v.upper()


class TestCaseCreate(TestCaseBase):
    """创建测试用例"""
    project_id: int = Field(..., description="项目ID")


class TestCaseUpdate(BaseModel):
    """更新测试用例"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    method: Optional[str] = None
    url: Optional[str] = Field(None, max_length=500)
    headers: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    assertions: Optional[List[Dict[str, Any]]] = None
    extract: Optional[Dict[str, Any]] = None
    setup: Optional[List[Dict[str, Any]]] = None
    teardown: Optional[List[Dict[str, Any]]] = None
    timeout: Optional[int] = Field(None, ge=1, le=600)
    retry: Optional[int] = Field(None, ge=0, le=5)
    tags: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TestCaseResponse(TestCaseBase):
    """测试用例响应模型"""
    id: int
    project_id: int
    creator_id: int
    source: str
    is_active: bool
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestCaseListResponse(BaseModel):
    """测试用例列表响应（简化版）"""
    id: int
    name: str
    method: str
    url: str
    project_id: int
    tags: Optional[str] = None
    category: Optional[str] = None
    priority: int
    is_active: bool
    last_run_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 认证相关 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(default=3600, description="过期时间(秒)")
    user: UserResponse = Field(..., description="用户信息")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


# ==================== 导入导出相关 ====================

class ImportRequest(BaseModel):
    """导入请求"""
    project_id: int = Field(..., description="项目ID")
    source: str = Field(..., description="来源(manual/yaml/json/swagger/curl)")
    content: Optional[str] = Field(None, description="内容(yaml/json/curl)")
    file_url: Optional[str] = Field(None, description="文件URL(swagger)")


class ImportResponse(BaseModel):
    """导入响应"""
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    test_cases: List[TestCaseListResponse] = Field(default=[], description="导入的测试用例")
    errors: List[str] = Field(default=[], description="错误信息")


# ==================== 执行相关 ====================

class RunTestRequest(BaseModel):
    """执行测试请求"""
    test_case_ids: List[int] = Field(..., description="测试用例ID列表")
    environment: Optional[str] = Field(None, description="执行环境")
    run_name: Optional[str] = Field(None, description="执行名称")

class RunTestResponse(BaseModel):
    """执行测试响应"""
    total: int = Field(description="总数")
    passed: int = Field(description="通过数")
    failed: int = Field(description="失败数")
    error: int = Field(description="错误数")
    duration: int = Field(description="执行时长(毫秒)")
    results: List[Dict[str, Any]] = Field(description="执行结果")
    batch_id: Optional[str] = Field(description="执行批次ID")
    run_name: Optional[str] = Field(description="执行名称")


class TrendItem(BaseModel):
    """执行趋势项"""
    date: str
    total: int
    passed: int
    failed: int


class ProjectPassRateItem(BaseModel):
    """项目通过率"""
    project_id: int
    project_name: str
    total: int
    passed: int
    pass_rate: float


class RecentRunItem(BaseModel):
    run_name: str
    project_name: str
    case_count: int
    status: str
    created_at: datetime
    test_case_name: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    running_cases: int
    execution_trend: List[TrendItem]
    project_pass_rate: List[ProjectPassRateItem]
    recent_runs: List[RecentRunItem]


class ReportCreateRequest(BaseModel):
    batch_id: str = Field(..., description="执行批次ID")
    name: Optional[str] = Field(None, description="测试报告名称")


class ReportListItem(BaseModel):
    id: int
    name: str
    batch_id: str
    project_id: int
    total: int
    passed: int
    failed: int
    error: int
    pass_rate: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReportDetailResponse(ReportListItem):
    creator_id: Optional[int] = None
    allure_report_path: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


# 更新forward references
UserResponse.model_rebuild()
RoleResponse.model_rebuild()
