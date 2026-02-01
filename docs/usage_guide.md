# 接口自动化测试平台 - 使用指南

## 📋 目录

1. [快速开始](#快速开始)
2. [配置管理](#配置管理)
3. [编写测试用例](#编写测试用例)
4. [运行测试](#运行测试)
5. [查看报告](#查看报告)
6. [高级用法](#高级用法)
7. [常见问题](#常见问题)

---

## 快速开始

### 1. 环境准备

```bash
# 克隆或下载项目
cd auto-test-platform

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/config.yaml`：

```yaml
default_env: dev  # 设置默认环境
```

配置环境文件 `config/env/dev.yaml`：

```yaml
base_url: "http://dev.example.com/api"

auth:
  type: bearer
  token: "your_token_here"
```

### 3. 编写第一个测试用例

创建 `test_data/hello_world.yaml`：

```yaml
test_cases:
  - name: "健康检查"
    priority: "p0"
    tags: ["smoke"]
    
    method: "GET"
    url: "/health"
    
    validate:
      - type: "status_code"
        expected: 200
```

### 4. 运行测试

```bash
# 运行所有测试
python run.py

# 指定环境运行
python run.py --env test

# 运行指定标签的测试
python run.py -m smoke

# 查看帮助
python run.py --help
```

---

## 配置管理

### 主配置文件 (config/config.yaml)

```yaml
# 默认环境
default_env: dev

# HTTP客户端配置
http_client:
  type: requests  # 或 httpx
  timeout: 30
  max_retries: 3

# 日志配置
logging:
  level: INFO
  dir: logs

# 通知配置
notification:
  enable: true
  level: failed  # all/failed/error
```

### 环境配置文件

#### 开发环境 (config/env/dev.yaml)

```yaml
base_url: "http://dev.example.com/api"

auth:
  type: bearer
  token: "dev_token"

database:
  host: "dev-mysql.example.com"
  user: "test_user"
  password: "test_password"
  database: "test_db"
```

#### 测试环境 (config/env/test.yaml)

```yaml
base_url: "http://test.example.com/api"

auth:
  type: bearer
  token: "test_token"
```

#### 生产环境 (config/env/prod.yaml)

```yaml
base_url: "https://api.example.com"

auth:
  type: bearer
  token: "prod_token"
```

### 全局变量 (config/global_vars.yaml)

```yaml
auth:
  dev_token: "Bearer xxx"
  test_token: "Bearer yyy"

test_data:
  default_username: "testuser"
  default_password: "Test@123456"
```

---

## 编写测试用例

### 基本用例

```yaml
test_cases:
  - name: "获取用户信息"
    priority: "p0"
    
    method: "GET"
    url: "/user/info"
    
    headers:
      Authorization: "Bearer ${$extract.token}"
    
    validate:
      - type: "status_code"
        expected: 200
```

### 使用变量

```yaml
test_cases:
  - name: "用户注册"
    method: "POST"
    url: "/user/register"
    
    body:
      username: "user_${timestamp()}"
      password: "${test_data.default_password}"
```

### 数据提取

```yaml
test_cases:
  - name: "登录"
    method: "POST"
    url: "/user/login"
    
    body:
      username: "testuser"
      password: "123456"
    
    extract:
      token:
        type: "jsonpath"
        expression: "$.data.token"
```

### 数据依赖

```yaml
test_cases:
  - name: "创建订单"
    depends_on: "获取商品信息"
    method: "POST"
    url: "/order/create"
    
    body:
      product_id: "${$extract.product_id}"
      quantity: 1
```

### 多断言

```yaml
validate:
  # 状态码
  - type: "status_code"
    expected: 200
  
  # 业务码
  - type: "eq"
    path: "body.code"
    expected: 0
  
  # 字段存在
  - type: "not_none"
    path: "body.data"
  
  # 正则验证
  - type: "regex"
    path: "body.data.email"
    pattern: "^[^@]+@[^@]+$"
```

---

## 运行测试

### 基本命令

```bash
# 运行所有测试
python run.py

# 指定环境
python run.py --env test

# 运行指定标签
python run.py -m smoke
python run.py -m regression
python run.py -m "smoke or regression"

# 详细输出
python run.py -v -s

# 并发执行
python run.py -n 4
```

### Pytest命令

```bash
# 运行所有测试
pytest

# 运行指定模块
pytest src/api/test_user.py

# 运行指定用例
pytest -k "test_login"

# 运行指定标签
pytest -m smoke

# 生成报告
pytest --alluredir=reports/allure

# 并发执行
pytest -n auto
```

### 高级选项

```bash
# 只运行失败的用例
pytest --lf

# 先运行失败的用例，再运行其他
pytest --ff

# 遇到第一个失败就停止
pytest -x

# 每个用例失败后停止
pytest --maxfail=3

# 显示详细的错误堆栈
pytest --tb=long

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

---

## 查看报告

### Allure报告

```bash
# 生成HTML报告
allure generate reports/allure -o reports/html --clean

# 启动实时预览
allure serve reports/allure

# 打开已生成的报告
allure open reports/html
```

### 报告内容

- **概览**：测试执行统计
- **用例列表**：所有测试用例及执行结果
- **执行历史**：历史执行趋势
- **详情页**：每个用例的详细信息
  - 请求信息
  - 响应信息
  - 断言结果
  - 失败原因

---

## 高级用法

### 1. 自定义钩子

创建 `hooks/custom_hooks.py`：

```python
from src.core.context import get_context

def before_login():
    """登录前钩子"""
    context = get_context()
    context.set_local('login_start_time', time.time())

def after_request(response):
    """请求后钩子"""
    print(f"响应时间: {response['elapsed']}s")
```

在用例中使用：

```yaml
test_cases:
  - name: "用户登录"
    hooks:
      - "before_login"
      - "after_request"
    
    method: "POST"
    url: "/user/login"
```

### 2. 数据驱动测试

使用 pytest 参数化：

```python
# src/api/test_user.py
import pytest

test_data = [
    {"username": "user1", "password": "pass1"},
    {"username": "user2", "password": "pass2"},
]

@pytest.mark.parametrize("data", test_data)
def test_login(data, http_client):
    response = http_client.request(
        method="POST",
        url="/user/login",
        body=data
    )
    assert response['status_code'] == 200
```

### 3. 数据库断言

配置数据库：

```yaml
database:
  type: mysql
  host: "localhost"
  port: 3306
  user: "root"
  password: "password"
  database: "test_db"
```

使用SQL断言：

```yaml
validate:
  - type: "sql"
    sql: "SELECT COUNT(*) FROM users WHERE id = ${body.data.id}"
    expected: 1
```

### 4. 文件上传

```yaml
test_cases:
  - name: "上传头像"
    method: "POST"
    url: "/user/avatar"
    
    headers:
      Authorization: "Bearer ${$extract.token}"
    
    files:
      avatar: "test_data/avatar.jpg"
    
    params:
      type: "avatar"
```

### 5. 并发测试

```bash
# 4个worker并发执行
pytest -n 4

# 自动检测CPU核心数
pytest -n auto
```

### 6. 重试机制

在用例中配置：

```yaml
test_cases:
  - name: "可能失败的用例"
    retry: 3  # 失败后重试3次
    
    method: "GET"
    url: "/api/unstable"
```

或在pytest配置中：

```ini
[pytest]
# 安装pytest-rerunfailures
addopts = --reruns 2
```

### 7. 跳过用例

```yaml
test_cases:
  - name: "暂不执行的用例"
    skip: true
    skip_reason: "功能未上线"
    
    method: "GET"
    url: "/api/future"
```

或使用pytest标记：

```yaml
test_cases:
  - name: "条件跳过的用例"
    priority: "p3"
    
    method: "GET"
    url: "/api/test"
```

```python
# conftest.py
def pytest_collection_modifyitems(config, items):
    if os.environ.get('TEST_ENV') == 'prod':
        skip_p3 = pytest.mark.skip(reason="生产环境不执行P3用例")
        for item in items:
            if "p3" in item.keywords:
                item.add_marker(skip_p3)
```

---

## 常见问题

### 1. 模块导入错误

**问题**：ModuleNotFoundError

**解决**：
```bash
# 确保在项目根目录
cd /path/to/auto-test-platform

# 确保虚拟环境激活
source venv/bin/activate  # Windows: venv\Scripts\activate

# 重新安装依赖
pip install -r requirements.txt
```

### 2. YAML语法错误

**问题**：YAML解析失败

**解决**：
- 检查缩进（必须使用2个空格）
- 检查字符串是否加引号
- 使用在线YAML验证器检查语法

### 3. 变量未替换

**问题**：`${variable}` 没有被替换

**解决**：
- 确保变量在双引号中：`"${variable}"`
- 检查变量是否已定义
- 查看日志确认变量值

### 4. 断言失败

**问题**：测试用例执行失败

**解决**：
- 查看Allure报告获取详细信息
- 检查期望值是否正确
- 使用`-v -s`参数运行，查看详细输出

### 5. 连接超时

**问题**：请求超时

**解决**：
- 增加超时时间：`timeout: 60`
- 检查网络连接
- 检查服务器状态

### 6. 环境变量未生效

**问题**：环境配置没有生效

**解决**：
- 确认环境文件存在：`config/env/dev.yaml`
- 检查default_env配置
- 使用`--env`参数指定环境

### 7. 报告无法打开

**问题**：Allure报告打不开

**解决**：
```bash
# 确保已生成报告数据
ls reports/allure

# 重新生成报告
allure generate reports/allure -o reports/html --clean

# 使用serve命令
allure serve reports/allure
```

---

## 📚 更多资源

- [pytest官方文档](https://docs.pytest.org/)
- [Allure官方文档](https://docs.qameta.io/allure/)
- [Requests文档](https://requests.readthedocs.io/)
- [HTTPX文档](https://www.python-httpx.org/)
- [YAML语法](https://yaml.org/spec/)

---

## 🤝 获取帮助

遇到问题时：

1. 查看日志文件：`logs/app_*.log`
2. 查看Allure报告获取详细信息
3. 运行测试时添加`-v -s`参数查看详细输出
4. 查看本文档的常见问题部分

---

**祝测试顺利！** 🚀
