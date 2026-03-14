# 接口自动化测试平台 - 后端API服务

## 📖 简介

这是一个基于FastAPI构建的接口自动化测试平台后端服务，提供完整的RESTful API接口，支持前端项目对接。

### 核心功能

- ✅ **用户管理**: 用户注册、登录、权限控制
- ✅ **角色权限管理**: 角色、权限的增删改查，RBAC权限模型
- ✅ **项目管理**: 项目和环境配置管理，数据隔离
- ✅ **测试用例管理**: 
  - 手工创建测试用例
  - 从YAML文件导入
  - 从JSON文件导入
  - 从CURL命令导入
  - 从Swagger文档导入
  - 导出测试用例

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 方式1：使用启动脚本（推荐）
python server/start_server.py

# 方式2：使用uvicorn
uvicorn server.main:app --host 0.0.0.0 --port 8899 --reload
```

### 3. 访问API文档

服务启动后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8899/docs
- **ReDoc**: http://localhost:8899/redoc

### 4. 默认账号

系统会自动创建超级管理员账号：

- 用户名: `admin`
- 密码: `admin123`
- ⚠️ **请登录后立即修改密码**

## 📁 项目结构

```
server/
├── api/              # API路由模块
│   ├── auth.py       # 认证相关API
│   ├── users.py      # 用户管理API
│   ├── roles.py      # 角色权限管理API
│   ├── projects.py   # 项目管理API
│   └── testcases.py  # 测试用例管理API
├── auth/             # 认证模块
│   └── auth.py       # JWT Token认证
├── models/           # 数据库模型
│   ├── models.py     # ORM模型定义
│   ├── database.py   # 数据库配置
│   └── init_db.py    # 数据库数据库初始化
├── schemas/          # Pydantic模型
│   └── schemas.py    # 数据验证模型
├── tests/            # 测试文件
│   └── test_api.py   # API测试脚本
├── docs/             # 文档
│   └── API_DOCUMENTATION.md
├── main.py           # FastAPI主应用
└── start_server.py   # 启动脚本
```

## 🔧 配置说明

### 数据库配置

默认使用SQLite数据库，数据文件保存在项目根目录的`test_platform.db`。

可以通过环境变量配置其他数据库：

```bash
# MySQL
export DATABASE_URL="mysql+pymysql://user:password@localhost/dbname"

# postgresql
export DATABASE_URL="postgresql://user:password@localhost/dbname"
```

### JWT配置

JWT Token的密钥配置在`server/auth/auth.py`中：

```python
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
```

**⚠️ 生产环境请务必修改SECRET_KEY！**

## 📚 API使用示例

### 1. 登录获取Token

```bash
curl -X POST "http://localhost:8899/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2. 创建项目

```bash
curl -X POST "http://localhost:8899/api/projects" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试项目",
    "code": "test_project",
    "description": "这是一个测试项目",
    "base_url": "https://api.example.com"
  }'
```

### 3. 创建测试用例

```bash
curl -X POST "http://localhost:8899/api/testcases" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "获取用户列表",
    "project_id": 1,
    "method": "GET",
    "url": "/api/users",
    "assertions": [
      {"type": "status_code", "expected": 200}
    ]
  }'
```

### 4. 从CURL导入

```bash
curl -X POST "http://localhost:8899/api/testcases/import/curl?project_id=1&curl_command=curl%20-X%20GET%20https://api.example.com/test" \
  -H "Authorization: Bearer <your_token>"
```

更多API使用示例请查看 [API文档](./docs/API_DOCUMENTATION.md)

## 🧪 测试

### 运行API测试

```bash
# 确保服务已启动
python server/tests/test_api.py
```

### 运行单元测试

```bash
pytest server/tests/
```

## 🔐 权限系统

### 默认角色

系统预置了4个角色：

1. **超级管理员 (admin)**: 拥有所有权限
2. **项目管理员 (project_admin)**: 可以管理项目和测试用例
3. **测试工程师 (tester)**: 可以创建和执行测试用例
4. **普通用户 (user)**: 只能查看信息

### 权限列表

完整的权限列表请查看`server/models/init_db.py`中的`init_permissions`函数。

### 数据隔离

- 非超级管理员只能看到自己创建的项目
- 非超级管理员只能看到自己项目的测试用例
- 用户只能访问和操作自己有权限的资源

## 📝 开发指南

### 添加新的API接口

1. 在`server/api/`目录下创建新的路由文件
2. 在`server/schemas/schemas.py`中定义请求和响应模型
3. 在`server/main.py`中注册路由

### 添加新的权限

1. 在`server/models/init_db.py`的`init_permissions`函数中添加权限定义
2. 为需要的角色分配权限
3. 在API接口中使用`require_permission`装饰器

### 数据库迁移

如果修改了数据库模型，需要创建迁移：

```bash
# 创建迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 🐛 常见问题

### 1. 端口被占用

如果8899端口被占用，可以修改启动命令：

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 2. 数据库初始化失败

确保数据库连接配置正确，或者删除现有数据库文件重新初始化：

```bash
rm test_platform.db
python server/start_server.py
```

### 3. Token过期

Token默认24小时过期，需要重新登录获取新Token。

## 📞 技术栈

- **FastAPI**: 现代化的Python Web框架
- **SQLAlchemy**: Python ORM框架
- **Pydantic**: 数据验证
- **JWT**: Token认证
- **SQLite/MySQL/PostgreSQL**: 数据库支持

## 📄 License

MIT License
