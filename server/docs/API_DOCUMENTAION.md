# 接口自动化测试平台API文档

## 📋 目录

- [快速开始](#快速开始)
- [认证说明](#认证说明)
- [API接口列表](#api接口列表)
  - [认证相关](#认证相关)
  - [用户管理](#用户管理)
  - [角色权限管理](#角色权限管理)
  - [项目管理](#项目管理)
  - [测试用例管理](#测试用例管理)
- [数据模型](#数据模型)
- [错误码说明](#错误码说明)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd auto-test-server
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1：使用启动脚本
python server/start_server.py

# 方式2：使用uvicorn
uvicorn server.main:app --host 0.0.0.0 --port 5000 --reload
```

### 3. 访问API文档

服务启动后，可以访问以下地址查看API文档：

- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

### 4. 默认账号

系统初始化后会创建超级管理员账号：

- 用户名: `admin`
- 密码: `admin123`
- **⚠️ 请登录后立即修改密码！**

---

## 🔐 认证说明

### JWT Token认证

API使用JWT Token进行身份认证。获取Token后，需要在请求头中添加：

```
Authorization: Bearer <your_token>
```

### 获取Token

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "roles": [...]
  }
}
```

---

## 📚 API接口列表

### 认证相关

#### 用户登录
```http
POST /api/auth/login
```

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

#### 获取当前用户信息
```http
GET /api/auth/me
Authorization: Bearer <token>
```

#### 修改密码
```http
PUT /api/auth/change-password
Authorization: Bearer <token>
```

**请求体**:
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

#### 用户登出
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

---

### 用户管理

#### 获取用户列表
```http
GET /api/users?page=1&page_size=20
Authorization: Bearer <token>
```

**权限要求**: `user:list`

**查询参数**:
- `page`: 页码（默认1）
- `page_size`: 每页大小（默认20，最大100）
- `username`: 用户名（模糊搜索）
- `email`: 邮箱（模糊搜索）
- `is_active`: 是否激活

#### 获取用户详情
```http
GET /api/users/{user_id}
Authorization: Bearer <token>
```

**权限要求**: `user:read`

#### 创建用户
```http
POST /api/users
Authorization: Bearer <token>
```

**权限要求**: `user:create`

**请求体**:
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123",
  "full_name": "测试用户",
  "role_ids": [2, 3]
}
```

#### 更新用户
```http
PUT /api/users/{user_id}
Authorization: Bearer <token>
```

**权限要求**: `user:update`

#### 删除用户
```http
DELETE /api/users/{user_id}
Authorization: Bearer <token>
```

**权限要求**: `user:delete`

---

### 角色权限管理

#### 获取角色列表
```http
GET /api/roles?page=1&page_size=20
Authorization: Bearer <token>
```

**权限要求**: `role:list`

#### 获取所有角色（不分页）
```http
GET /api/roles/all
Authorization: Bearer <token>
```

#### 创建角色
```http
POST /api/roles
Authorization: Bearer <token>
```

**权限要求**: `role:create`

**请求体**:
```json
{
  "name": "测试管理员",
  "code": "test_admin",
  "description": "负责测试的管理员",
  "permission_ids": [1, 2, 3]
}
```

#### 为角色分配权限
```http
POST /api/roles/{role_id}/permissions
Authorization: Bearer <token>
```

**权限要求**: `permission:assign`

**请求体**:
```json
[1, 2, 3, 4, 5]
```

#### 获取权限列表
```http
GET /api/permissions
Authorization: Bearer <token>
```

**权限要求**: `permission:list`

---

### 项目管理

#### 获取项目列表
```http
GET /api/projects?page=1&page_size=20
Authorization: Bearer <token>
```

**权限要求**: `project:list`

**数据隔离**: 非超级管理员只能看到自己创建的项目

#### 创建项目
```http
POST /api/projects
Authorization: Bearer <token>
```

**权限要求**: `project:create`

**请求体**:
```json
{
  "name": "测试项目",
  "code": "test_project",
  "description": "这是一个测试项目",
  "base_url": "https://api.example.com"
}
```

#### 创建环境配置
```http
POST /api/projects/{project_id}/environments
Authorization: Bearer <token>
```

**权限要求**: `project:update`

**请求体**:
```json
{
  "name": "测试环境",
  "code": "test",
  "base_url": "https://test.example.com",
  "headers": {
    "Content-Type": "application/json"
  },
  "variables": {
    "api_key": "test_key"
  }
}
```

---

### 测试用例管理

#### 获取测试用例列表
```http
GET /api/testcases?page=1&page_size=20
Authorization: Bearer <token>
```

**权限要求**: `testcase:list`

**查询参数**:
- `project_id`: 项目ID
- `name`: 用例名称（模糊搜索）
- `method`: 请求方法
- `category`: 分类
- `priority`: 优先级（1-5）

**数据隔离**: 非超级管理员只能看到自己项目的用例

#### 手工创建测试用例
```http
POST /api/testcases
Authorization: Bearer <token>
```

**权限要求**: `testcase:create`

**请求体**:
```json
{
  "name": "获取用户列表",
  "project_id": 1,
  "method": "GET",
  "url": "/api/users",
  "headers": {
    "Authorization": "Bearer ${token}"
  },
  "params": {
    "page": 1,
    "page_size": 20
  },
  "assertions": [
    {
      "type": "status_code",
      "expected": 200
    },
    {
      "type": "json_path",
      "path": "$.total",
      "expected": 100
    }
  ],
  "extract": {
    "token": "$.data.token"
  },
  "timeout": 30,
  "priority": 3,
  "description": "测试获取用户列表接口"
}
```

#### 从YAML文件导入
```http
POST /api/testcases/import/yaml?project_id=1
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <yaml_file>
```

**权限要求**: `testcase:import`

**YAML文件格式**:
```yaml
test_cases:
  - name: 获取用户列表
    method: GET
    url: /api/users
    params:
      page: 1
      page_size: 20
    assertions:
      - type: status_code
        expected: 200
  
  - name: 创建用户
    method: POST
    url: /api/users
    body:
      username: testuser
      email: test@example.com
    assertions:
      - type: status_code
        expected: 201
```

#### 从JSON文件导入
```http
POST /api/testcases/import/json?project_id=1
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <json_file>
```

**权限要求**: `testcase:import`

#### 从CURL命令导入
```http
POST /api/testcases/import/curl?project_id=1&curl_command=<curl_command>&name=测试用例
Authorization: Bearer <token>
```

**权限要求**: `testcase:import`

**示例CURL命令**:
```bash
curl -X GET "https://api.example.com/users?page=1" -H "Authorization: Bearer token"
```

#### 从Swagger导入
```http
POST /api/testcases/import/swagger
Authorization: Bearer <token>
```

**权限要求**: `testcase:import`

**请求体**:
```json
{
  "project_id": 1,
  "source": "swagger",
  "file_url": "https://petstore.swagger.io/v2/swagger.json"
}
```

#### 导出测试用例为YAML
```http
GET /api/testcases/{testcase_id}/export/yaml
Authorization: Bearer <token>
```

**权限要求**: `testcase:export`

---

## 📊 数据模型

### 用户 (User)
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "系统管理员",
  "is_active": true,
  "is_superuser": true,
  "roles": [...],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### 角色 (Role)
```json
{
  "id": 1,
  "name": "超级管理员",
  "code": "admin",
  "description": "系统超级管理员",
  "is_active": true,
  "permissions": [...],
  "created_at": "2024-01-01T00:00:00"
}
```

### 项目 (Project)
```json
{
  "id": 1,
  "name": "测试项目",
  "code": "test_project",
  "description": "项目描述",
  "base_url": "https://api.example.com",
  "owner_id": 1,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

### 测试用例 (TestCase)
```json
{
  "id": 1,
  "name": "获取用户列表",
  "project_id": 1,
  "creator_id": 1,
  "method": "GET",
  "url": "/api/users",
  "headers": {...},
  "params": {...},
  "body": {...},
  "assertions": [...],
  "extract": {...},
  "timeout": 30,
  "priority": 3,
  "source": "manual",
  "created_at": "2024-01-01T00:00:00"
}
```

---

## ⚠️ 错误码说明

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

**错误响应格式**:
```json
{
  "detail": "错误详细信息"
}
```

---

## ❓ 常见问题

### 1. 如何获取访问Token？

通过登录接口获取：
```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2. 如何测试有权限要求的接口？

在请求头中添加Token：
```bash
curl -X GET "http://localhost:5000/api/users" \
  -H "Authorization: Bearer your_token_here"
```

### 3. 数据隔离是如何实现的？

- 项目级别：非超级管理员只能看到自己创建的项目
- 测试用例级别：非超级管理员只能看到自己项目的测试用例
- 用户只能访问和操作自己有权限的资源

### 4. 如何添加新权限？

目前权限创建仅限超级管理员，可以通过以下方式添加：
1. 在`server/models/init_db.py`中添加新权限定义
2. 重新初始化数据库
3. 为角色分配新权限

### 5. 支持哪些数据库？

默认使用SQLite（适合开发和小规模使用），也可以配置MySQL、PostgreSQL等数据库。修改环境变量`DATABASE_URL`即可：
```
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
```

---

## 📞 技术支持

如有问题，请查看：
- API文档: http://localhost:5000/docs
- 项目日志: logs/app_*.log
- 错误日志: logs/error_*.log
