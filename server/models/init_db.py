# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建默认角色、权限和超级管理员
"""
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from server.models.models import (
    Base, User, Role, Permission
)
from server.models.database import engine, get_db_session

# 密码加密 - 使用Argon2 更安全且无长度限制
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=2 ** 16,
    argon2__parallelism=4
)


def init_permissions(db: Session):
    """初始化权限"""
    permissions = [
        # 用户管理
        {"name": "查看用户列表", "code": "user:list", "resource": "user", "action": "list"},
        {"name": "查看用户详情", "code": "user:read", "resource": "user", "action": "read"},
        {"name": "创建用户", "code": "user:create", "resource": "user", "action": "create"},
        {"name": "编辑用户", "code": "user:update", "resource": "user", "action": "update"},
        {"name": "删除用户", "code": "user:delete", "resource": "user", "action": "delete"},

        # 角色管理
        {"name": "查看角色列表", "code": "role:list", "resource": "role", "action": "list"},
        {"name": "查看角色详情", "code": "role:read", "resource": "role", "action": "read"},
        {"name": "创建角色", "code": "role:create", "resource": "role", "action": "create"},
        {"name": "编辑角色", "code": "role:update", "resource": "role", "action": "update"},
        {"name": "删除角色", "code": "role:delete", "resource": "role", "action": "delete"},

        # 权限管理
        {"name": "查看权限列表", "code": "permission:list", "resource": "permission", "action": "list"},
        {"name": "查看权限详情", "code": "permission:read", "resource": "permission", "action": "read"},
        {"name": "分配权限", "code": "permission:assign", "resource": "permission", "action": "assign"},

        # 项目管理
        {"name": "查看项目列表", "code": "project:list", "resource": "project", "action": "list"},
        {"name": "查看项目详情", "code": "project:read", "resource": "project", "action": "read"},
        {"name": "创建项目", "code": "project:create", "resource": "project", "action": "create"},
        {"name": "编辑项目", "code": "project:update", "resource": "project", "action": "update"},
        {"name": "删除项目", "code": "project:delete", "resource": "project", "action": "delete"},

        # 测试用例管理
        {"name": "查看测试用例", "code": "testcase:list", "resource": "testcase", "action": "list"},
        {"name": "查看用例详情", "code": "testcase:read", "resource": "testcase", "action": "read"},
        {"name": "创建测试用例", "code": "testcase:create", "resource": "testcase", "action": "create"},
        {"name": "编辑测试用例", "code": "testcase:update", "resource": "testcase", "action": "update"},
        {"name": "删除测试用例", "code": "testcase:delete", "resource": "testcase", "action": "delete"},
        {"name": "执行测试用例", "code": "testcase:run", "resource": "testcase", "action": "run"},
        {"name": "导入测试用例", "code": "testcase:import", "resource": "testcase", "action": "import"},
        {"name": "导出测试用例", "code": "testcase:export", "resource": "testcase", "action": "export"},
    ]

    created_count = 0
    for perm_data in permissions:
        existing = db.query(Permission).filter(Permission.code == perm_data['code']).first()
        if not existing:
            permission = Permission(**perm_data)
            db.add(permission)
            created_count += 1

    db.commit()
    print(f"✅ 创建了 {created_count} 个新权限")


def init_roles(db: Session):
    """初始化角色"""
    roles = [
        {
            "name": "超级管理员",
            "code": "admin",
            "description": "系统超级管理员，拥有所有权限"
        },
        {
            "name": "项目管理员",
            "code": "project_admin",
            "description": "项目管理员，可以管理项目和相关测试用例"
        },
        {
            "name": "测试工程师",
            "code": "tester",
            "description": "测试工程师，可以创建和执行测试用例"
        },
        {
            "name": "普通用户",
            "code": "user",
            "description": "普通用户，只能查看信息"
        },
    ]

    created_count = 0
    for role_data in roles:
        existing = db.query(Role).filter(Role.code == role_data['code']).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            created_count += 1

    db.commit()
    print(f"✅ 创建了 {created_count} 个新角色")


def assign_permissions_to_admin(db: Session):
    """为超级管理员分配所有权限"""
    admin_role = db.query(Role).filter(Role.code == 'admin').first()
    if not admin_role:
        print("⚠️ 超级管理员角色不存在")
        return

    # 获取所有权限
    all_permissions = db.query(Permission).all()

    # 检查是否已分配
    existing_perm_ids = {p.id for p in admin_role.permissions}
    new_permissions = [p for p in all_permissions if p.id not in existing_perm_ids]

    if new_permissions:
        admin_role.permissions.extend(new_permissions)
        db.commit()
        print(f"✅ 为超级管理员分配了 {len(new_permissions)} 个新权限")
    else:
        print("ℹ️ 超级管理员已拥有所有权限")


def assign_permissions_to_project_admin(db: Session):
    """为项目管理员分配权限"""
    role = db.query(Role).filter(Role.code == 'project_admin').first()
    if not role:
        return

    # 项目管理权限
    perm_codes = [
        'project:list', 'project:read', 'project:create', 'project:update', 'project:delete',
        'testcase:list', 'testcase:read', 'testcase:create', 'testcase:update', 'testcase:delete',
        'testcase:run', 'testcase:import', 'testcase:export',
        'user:list', 'user:read',
    ]

    permissions = db.query(Permission).filter(Permission.code.in_(perm_codes)).all()
    role.permissions = permissions
    db.commit()
    print(f"✅ 为项目管理员分配了 {len(permissions)} 个权限")


def assign_permissions_to_tester(db: Session):
    """为测试工程师分配权限"""
    role = db.query(Role).filter(Role.code == 'tester').first()
    if not role:
        return

    perm_codes = [
        'project:list', 'project:read',
        'testcase:list', 'testcase:read', 'testcase:create', 'testcase:update', 'testcase:delete',
        'testcase:run', 'testcase:import', 'testcase:export',
    ]

    permissions = db.query(Permission).filter(Permission.code.in_(perm_codes)).all()
    role.permissions = permissions
    db.commit()
    print(f"✅ 为测试工程师分配了 {len(permissions)} 个权限")


def assign_permissions_to_user(db: Session):
    """为普通用户分配权限"""
    role = db.query(Role).filter(Role.code == 'user').first()
    if not role:
        return

    perm_codes = [
        'project:list', 'project:read',
        'testcase:list', 'testcase:read',
    ]

    permissions = db.query(Permission).filter(Permission.code.in_(perm_codes)).all()
    role.permissions = permissions
    db.commit()
    print(f"✅ 为普通用户分配了 {len(permissions)} 个权限")


def create_super_admin(db: Session):
    """创建超级管理员账号"""
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "Admin123"  # 默认密码，建议首次登录后修改

    # 检查是否已存在
    existing = db.query(User).filter(User.username == admin_username).first()
    if existing:
        print("ℹ️ 超级管理员账号已存在")
        return

    # 创建超级管理员
    hashed_password = pwd_context.hash(admin_password)
    admin_user = User(
        username=admin_username,
        email=admin_email,
        hashed_password=hashed_password,
        full_name="系统管理员",
        is_active=True,
        is_superuser=True
    )

    # 分配超级管理员角色
    admin_role = db.query(Role).filter(Role.code == 'admin').first()
    if admin_role:
        admin_user.roles.append(admin_role)

    db.add(admin_user)
    db.commit()

    print(f"✅ 创建超级管理员账号成功")
    print(f"   用户名: {admin_username}")
    print(f"   密码: {admin_password}")
    print(f"   ⚠️ 请登录后立即修改密码！")


def init_database():
    """初始化数据库"""
    print("\n" + "=" * 60)
    print("🚀 开始初始化数据库")
    print("=" * 60)

    # 创建所有表
    print("\n📦 创建数据库表...")
    Base.metadata.create_all(bind=engine)

    # 获取数据库会话
    db = get_db_session()

    try:
        # 初始化权限
        print("\n📋 初始化权限...")
        init_permissions(db)

        # 初始化角色
        print("\n👥 初始化角色...")
        init_roles(db)

        # 分配权限
        print("\n🔐 分配权限...")
        assign_permissions_to_admin(db)
        assign_permissions_to_project_admin(db)
        assign_permissions_to_tester(db)
        assign_permissions_to_user(db)

        # 创建超级管理员
        print("\n👤 创建超级管理员...")
        create_super_admin(db)

        print("\n" + "=" * 60)
        print("✅ 数据库初始化完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
