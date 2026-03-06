# -*- coding: utf-8 -*-
"""
后端API服务 - 数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 用户-角色关联表
user_role = Table(
    'user_role',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.now)
)

# 角色-权限关联表
role_permission = Table(
    'role_permission',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.now)
)


class User(Base):
    """用户模型"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment='用户名')
    email = Column(String(100), unique=True, index=True, nullable=False, comment='邮箱')
    hashed_password = Column(String(255), nullable=False, comment='密码哈希')
    full_name = Column(String(100), comment='全名')
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_superuser = Column(Boolean, default=False, comment='是否超级管理员')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    roles = relationship('Role', secondary=user_role, back_populates='users')
    projects = relationship('Project', back_populates='owner')
    test_cases = relationship('TestCase', back_populates='creator')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Role(Base):
    """角色模型"""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False, comment='角色名称')
    code = Column(String(50), unique=True, index=True, nullable=False, comment='角色代码')
    description = Column(String(255), comment='角色描述')
    is_active = Column(Boolean, default=True, comment='是否激活')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    users = relationship('User', secondary=user_role, back_populates='roles')
    permissions = relationship('Permission', secondary=role_permission, back_populates='roles')

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """权限模型"""
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False, comment='权限名称')
    code = Column(String(100), unique=True, index=True, nullable=False, comment='权限代码')
    resource = Column(String(50), nullable=False, comment='资源类型')
    action = Column(String(20), nullable=False, comment='操作类型')
    description = Column(String(255), comment='权限描述')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关系
    roles = relationship('Role', secondary=role_permission, back_populates='permissions')

    def __repr__(self):
        return f"<Permission(id={self.id}, code={self.code})>"


class Project(Base):
    """项目模型"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment='项目名称')
    code = Column(String(50), unique=True, index=True, nullable=False, comment='项目代码')
    description = Column(Text, comment='项目描述')
    base_url = Column(String(255), comment='基础URL')
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='项目所有者')
    is_active = Column(Boolean, default=True, comment='是否激活')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    owner = relationship('User', back_populates='projects')
    test_cases = relationship('TestCase', back_populates='project', cascade='all, delete-orphan')
    environments = relationship('Environment', back_populates='project', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"


class Environment(Base):
    """环境配置模型"""
    __tablename__ = 'environments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment='环境名称')
    code = Column(String(30), nullable=False, comment='环境代码')
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, comment='项目ID')
    base_url = Column(String(255), comment='基础URL')
    headers = Column(Text, comment='默认请求头(JSON)')
    variables = Column(Text, comment='环境变量(JSON)')
    is_active = Column(Boolean, default=True, comment='是否激活')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    project = relationship('Project', back_populates='environments')

    def __repr__(self):
        return f"<Environment(id={self.id}, name={self.name})>"


class TestCase(Base):
    """测试用例模型"""
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment='用例名称')
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, comment='项目ID')
    creator_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='创建者ID')

    # 测试用例基本信息
    method = Column(String(10), nullable=False, comment='请求方法')
    url = Column(String(500), nullable=False, comment='请求URL')
    headers = Column(Text, comment='请求头(JSON)')
    params = Column(Text, comment='URL参数(JSON)')
    body = Column(Text, comment='请求体(JSON)')

    # 断言和提取
    assertions = Column(Text, comment='断言配置(JSON)')
    extract = Column(Text, comment='数据提取配置(JSON)')

    # 其他配置
    setup = Column(Text, comment='前置步骤(JSON)')
    teardown = Column(Text, comment='后置步骤(JSON)')
    timeout = Column(Integer, default=30, comment='超时时间(秒)')
    retry = Column(Integer, default=0, comment='重试次数')

    # 标签和分类
    tags = Column(String(255), comment='标签(逗号分隔)')
    category = Column(String(100), comment='分类')
    priority = Column(Integer, default=3, comment='优先级(1-5)')

    # 状态
    is_active = Column(Boolean, default=True, comment='是否激活')
    last_run_at = Column(DateTime, comment='最后执行时间')
    last_run_status = Column(String(20), comment='最后执行状态')

    # 元数据
    description = Column(Text, comment='用例描述')
    source = Column(String(20), default='manual', comment='来源(manual/yaml/json/swagger/curl)')
    source_file = Column(String(255), comment='源文件路径')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    project = relationship('Project', back_populates='test_cases')
    creator = relationship('User', back_populates='test_cases')

    def __repr__(self):
        return f"<TestCase(id={self.id}, name={self.name})>"


class TestRun(Base):
    """测试执行记录模型"""
    __tablename__ = 'test_runs'

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False,
                          comment='测试用例ID')
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, comment='项目ID')
    executor_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), comment='执行者ID')

    # 执行结果
    status = Column(String(20), nullable=False, comment='执行状态(passed/failed/error)')
    duration = Column(Integer, comment='执行时长(毫秒)')

    # 请求和响应
    request_data = Column(Text, comment='请求数据(JSON)')
    response_data = Column(Text, comment='响应数据(JSON)')

    # 错误信息
    error_message = Column(Text, comment='错误信息')
    stack_trace = Column(Text, comment='堆栈跟踪')

    # 环境
    environment = Column(String(30), comment='执行环境')

    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    def __repr__(self):
        return f"<TestRun(id={self.id}, status={self.status})>"
