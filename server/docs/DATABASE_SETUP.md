# 数据库初始化操作手册

## 一、创建数据库

```sql
-- 连接 PostgreSQL（使用管理员账号或 postgres 账号）
-- 执行以下命令创建数据库

CREATE DATABASE autotest_db;

-- 授权给 autotest_user（如果用户不存在，先创建）
-- CREATE USER autotest_user WITH PASSWORD '776462';
-- GRANT ALL PRIVILEGES ON DATABASE autotest_db TO autotest_user;
```

---

## 二、创建表结构

```sql
-- 连接到 autotest_db 数据库
\c autotest_db

-- 设置时区
SET TIME ZONE 'Asia/Shanghai';

-- ============================================================
-- 删除已存在的表（注意顺序，先删除有外键依赖的表）
-- ============================================================
DROP TABLE IF EXISTS test_runs CASCADE;
DROP TABLE IF EXISTS test_cases CASCADE;
DROP TABLE IF EXISTS environments CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS role_permission CASCADE;
DROP TABLE IF EXISTS user_role CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- 角色表
-- ============================================================
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roles_code ON roles(code);

-- ============================================================
-- 权限表
-- ============================================================
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_code ON permissions(code);

-- ============================================================
-- 用户-角色关联表
-- ============================================================
CREATE TABLE user_role (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================
-- 角色-权限关联表
-- ============================================================
CREATE TABLE role_permission (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================================
-- 项目表
-- ============================================================
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    base_url VARCHAR(255),
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_code ON projects(code);
CREATE INDEX idx_projects_owner ON projects(owner_id);

-- ============================================================
-- 环境配置表
-- ============================================================
CREATE TABLE environments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(30) NOT NULL,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    base_url VARCHAR(255),
    headers TEXT,
    variables TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_environments_project ON environments(project_id);

-- ============================================================
-- 测试用例表
-- ============================================================
CREATE TABLE test_cases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    method VARCHAR(10) NOT NULL,
    url VARCHAR(500) NOT NULL,
    headers TEXT,
    params TEXT,
    body TEXT,
    assertions TEXT,
    extract TEXT,
    setup TEXT,
    teardown TEXT,
    timeout INTEGER DEFAULT 30,
    retry INTEGER DEFAULT 0,
    tags VARCHAR(255),
    category VARCHAR(100),
    priority INTEGER DEFAULT 3,
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    last_run_status VARCHAR(20),
    description TEXT,
    source VARCHAR(20) DEFAULT 'manual',
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_cases_project ON test_cases(project_id);
CREATE INDEX idx_test_cases_creator ON test_cases(creator_id);

-- ============================================================
-- 测试执行记录表
-- ============================================================
CREATE TABLE test_runs (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    executor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration INTEGER,
    request_url TEXT,
    request_method VARCHAR(10),
    request_headers TEXT,
    request_body TEXT,
    response_status INTEGER,
    response_headers TEXT,
    response_body TEXT,
    assertions_result TEXT,
    error_message TEXT,
    environment VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_runs_test_case ON test_runs(test_case_id);
CREATE INDEX idx_test_runs_project ON test_runs(project_id);
CREATE INDEX idx_test_runs_status ON test_runs(status);

-- ============================================================
-- 创建更新时间触发器
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_environments_updated_at BEFORE UPDATE ON environments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_cases_updated_at BEFORE UPDATE ON test_cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 三、插入初始数据

```sql
-- ============================================================
-- 插入权限数据（26个）
-- ============================================================
INSERT INTO permissions (name, code, resource, action) VALUES
-- 用户管理
('查看用户列表', 'user:list', 'user', 'list'),
('查看用户详情', 'user:read', 'user', 'read'),
('创建用户', 'user:create', 'user', 'create'),
('编辑用户', 'user:update', 'user', 'update'),
('删除用户', 'user:delete', 'user', 'delete'),

-- 角色管理
('查看角色列表', 'role:list', 'role', 'list'),
('查看角色详情', 'role:read', 'role', 'read'),
('创建角色', 'role:create', 'role', 'create'),
('编辑角色', 'role:update', 'role', 'update'),
('删除角色', 'role:delete', 'role', 'delete'),

-- 权限管理
('查看权限列表', 'permission:list', 'permission', 'list'),
('查看权限详情', 'permission:read', 'permission', 'read'),
('分配权限', 'permission:assign', 'permission', 'assign'),

-- 项目管理
('查看项目列表', 'project:list', 'project', 'list'),
('查看项目详情', 'project:read', 'project', 'read'),
('创建项目', 'project:create', 'project', 'create'),
('编辑项目', 'project:update', 'project', 'update'),
('删除项目', 'project:delete', 'project', 'delete'),

-- 测试用例管理
('查看测试用例', 'testcase:list', 'testcase', 'list'),
('查看用例详情', 'testcase:read', 'testcase', 'read'),
('创建测试用例', 'testcase:create', 'testcase', 'create'),
('编辑测试用例', 'testcase:update', 'testcase', 'update'),
('删除测试用例', 'testcase:delete', 'testcase', 'delete'),
('执行测试用例', 'testcase:run', 'testcase', 'run'),
('导入测试用例', 'testcase:import', 'testcase', 'import'),
('导出测试用例', 'testcase:export', 'testcase', 'export')
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- 插入角色数据（4个）
-- ============================================================
INSERT INTO roles (name, code, description, is_active) VALUES
('超级管理员', 'admin', '系统超级管理员，拥有所有权限', TRUE),
('项目管理员', 'project_admin', '项目管理员，可以管理项目和相关测试用例', TRUE),
('测试工程师', 'tester', '测试工程师，可以创建和执行测试用例', TRUE),
('普通用户', 'user', '普通用户，只能查看信息', TRUE)
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- 为超级管理员分配所有权限
-- ============================================================
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'admin'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 为项目管理员分配权限
-- ============================================================
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'project_admin'
  AND p.code IN (
    'project:list', 'project:read', 'project:create', 'project:update', 'project:delete',
    'testcase:list', 'testcase:read', 'testcase:create', 'testcase:update', 'testcase:delete',
    'testcase:run', 'testcase:import', 'testcase:export',
    'user:list', 'user:read'
  )
ON CONFLICT DO NOTHING;

-- ============================================================
-- 为测试工程师分配权限
-- ============================================================
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'tester'
  AND p.code IN (
    'project:list', 'project:read',
    'testcase:list', 'testcase:read', 'testcase:create', 'testcase:update', 'testcase:delete',
    'testcase:run', 'testcase:import', 'testcase:export'
  )
ON CONFLICT DO NOTHING;

-- ============================================================
-- 为普通用户分配权限
-- ============================================================
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'user'
  AND p.code IN (
    'project:list', 'project:read',
    'testcase:list', 'testcase:read'
  )
ON CONFLICT DO NOTHING;
```

---

## 四、创建超级管理员账号

### 步骤 1：生成密码哈希

在 Python 环境中执行以下命令生成密码哈希：

```cmd
python -c "from passlib.context import CryptContext; pwd = CryptContext(schemes=['argon2'], argon2__time_cost=3, argon2__memory_cost=65536, argon2__parallelism=4); print(pwd.hash('admin123'))"
```

**输出示例**（每次生成的哈希值不同）：
```
$argon2id$v=19$m=65536,t=3,p=4$AbCdEfGhIjKlMnOpQrStUv$WxYz1234567890AbCdEfGhIjKlMnOpQrStUvWxYz
```

### 步骤 2：插入管理员数据

将上面生成的哈希值替换到下面的 SQL 中执行：

```sql
-- 插入超级管理员（将 HASH_VALUE 替换为步骤1生成的哈希值）
INSERT INTO users (username, email, hashed_password, full_name, is_active, is_superuser)
VALUES (
    'admin',
    'admin@example.com',
    'HASH_VALUE',  -- 替换为步骤1生成的哈希值
    '系统管理员',
    TRUE,
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- 为管理员分配超级管理员角色
INSERT INTO user_role (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.username = 'admin' AND r.code = 'admin'
ON CONFLICT DO NOTHING;
```

---

## 五、验证数据

```sql
-- 查看表是否创建成功
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- 查看权限数量（应为 26）
SELECT COUNT(*) as permission_count FROM permissions;

-- 查看角色数量（应为 4）
SELECT COUNT(*) as role_count FROM roles;

-- 查看超级管理员角色权限数量（应为 26）
SELECT COUNT(*) as admin_permissions FROM role_permission rp
JOIN roles r ON rp.role_id = r.id WHERE r.code = 'admin';

-- 查看管理员账号
SELECT id, username, email, full_name, is_superuser FROM users WHERE username = 'admin';
```

---

## 六、完整执行流程

在 PostgreSQL 命令行或 pgAdmin 中依次执行：

```sql
-- 1. 创建数据库
CREATE DATABASE autotest_db;

-- 2. 连接数据库
\c autotest_db

-- 3. 执行"二、创建表结构"中的所有 SQL

-- 4. 执行"三、插入初始数据"中的所有 SQL

-- 5. 生成密码哈希并执行"四、创建超级管理员账号"中的 SQL

-- 6. 执行"五、验证数据"中的 SQL 确认结果
```

---

## 七、默认账号信息

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| admin | admin123 | 超级管理员 | 请登录后立即修改密码 |

---

## 八、数据库连接配置

项目代码中的连接配置：

```
postgresql://autotest_user:776462@localhost:5432/autotest_db
```

如需修改，在 `server/models/database.py` 中更改 `DATABASE_URL` 变量。
