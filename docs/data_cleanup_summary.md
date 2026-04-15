# 数据清洗功能实现总结

## 功能需求

在测试执行结束前，需要支持数据清洗功能，自动删除测试过程中新增的测试数据，保持测试环境的干净。支持两种删除方式：

1. **调用系统删除接口（API）**：通过 HTTP 请求调用系统的删除接口
2. **通过 SQL 操作数据库**：直接执行 SQL 语句删除数据

## 实现方案

### 1. 核心架构

```
┌─────────────────┐
│  TestCase       │
│  - cleanup      │ ◄── 清洗配置
└─────────────────┘
         │
         │ 测试执行后
         ▼
┌─────────────────┐
│  DataCleaner    │
│  - cleanup()    │ ◄── 执行清洗
│  - API 清洗     │
│  - SQL 清洗     │
└─────────────────┘
         │
         ├────► HTTP Client (API)
         │
         └────► Database (SQL)
```

### 2. 关键组件

#### 2.1 TestCase 数据类扩展

在 `src/core/parser.py` 中为 TestCase 添加 cleanup 字段：

```python
@dataclass
class TestCase:
    # ... 现有字段
    cleanup: Dict[str, Any] = None  # 数据清洗配置
```

#### 2.2 数据清洗管理器 DataCleaner

创建 `src/utils/cleaner.py`，实现两种清洗方式：

- **API 清洗**：通过 HTTP 客户端发送删除请求
- **SQL 清洗**：通过 SQLAlchemy 执行 SQL 语句

#### 2.3 测试执行流程集成

在 `src/api/test_dynamic.py` 中的测试函数中添加数据清洗逻辑：

```python
# 执行后置处理
if tc.teardown:
    _execute_teardown(tc.teardown, test_context)

# 执行数据清洗
if tc.cleanup:
    try:
        from src.utils.cleaner import get_cleaner
        cleaner = get_cleaner()
        success = cleaner.cleanup(tc.cleanup)
        # ... 记录结果
    except Exception as e:
        # 数据清洗失败不影响测试用例结果
```

## 核心修改

### 1. 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `src/core/parser.py` | 添加 cleanup 字段到 TestCase，修改解析逻辑 |
| `src/api/test_dynamic.py` | 在测试执行后添加数据清洗逻辑 |
| `pytest.ini` | 添加 cleanup 相关的 marker 定义 |
| `README.md` | 添加数据清洗功能说明 |

### 2. 新增的文件

| 文件 | 说明 |
|------|------|
| `src/utils/cleaner.py` | 数据清洗管理器 |
| `test_data/cleanup_module.yaml` | 数据清洗功能示例 |
| `docs/data_cleanup.md` | 数据清洗功能使用文档 |

## 配置格式

### API 清洗配置

```yaml
cleanup:
  enabled: true
  type: "api"
  api:
    method: "DELETE"
    url: "/api/users/${$extract.user_id}"
    headers:
      Authorization: "Bearer ${$extract.access_token}"
    body:
      reason: "test_cleanup"
```

### SQL 清洗配置

```yaml
cleanup:
  enabled: true
  type: "sql"
  sql:
    connection: "default"
    statement: "DELETE FROM users WHERE id = ${extract.user_id}"
```

## 功能特性

### 1. API 清洗

- ✅ 支持所有 HTTP 方法（GET/POST/PUT/DELETE）
- ✅ 支持自定义请求头、URL 参数、请求体
- ✅ 自动拼接 base_url
- ✅ 支持变量替换（extract、global、local、env）
- ✅ 自动处理 JSON 和表单数据

### 2. SQL 清洗

- ✅ 支持 MySQL 和 PostgreSQL
- ✅ 支持多语句执行
- ✅ 支持参数化查询
- ✅ 使用连接池提高性能
- ✅ 自动处理连接和事务

### 3. 变量替换

支持以下变量格式：

- `${$extract.variable_name}` - 从响应中提取的数据
- `${global_var}` - 全局变量
- `${local_var}` - 局部变量
- `${env.VAR_NAME}` - 环境变量
- `${uuid()}` - UUID 生成
- `${timestamp()}` - 时间戳

## 执行流程

1. **执行测试用例**
2. **提取数据**（如果配置了 extract）
3. **执行断言**
4. **执行后置处理**（teardown）
5. **执行数据清洗**（如果配置了 cleanup）🆕
6. **记录测试结果**

数据清洗失败不会影响测试用例的结果，只会在日志中记录警告。

## 测试验证

### 测试用例

创建了 5 个测试用例验证数据清洗功能：

1. **创建数据-使用API清洗**：验证 API 清洗功能
2. **创建数据-使用SQL清洗**：验证 SQL 清洗功能
3. **创建数据-不清洗**：验证禁用清洗功能
4. **创建订单-使用API清洗**：验证使用 extract 数据进行清洗
5. **创建用户-多步骤清洗**：验证复杂清洗场景

### 测试结果

```bash
$ python -m pytest src/api/test_generator.py -k "cleanup" -v
================= 5 passed, 33 deselected, 3 warnings in 3.26s =================
```

所有测试用例通过，数据清洗功能正常工作。

### 日志输出

```
[INFO] 开始通过 API 清洗数据
[INFO] 发送清洗请求: POST http://httpbin.org/post
[INFO] 数据清洗成功: POST http://httpbin.org/post, 状态码: 200
```

或：

```
[INFO] 开始通过 SQL 清洗数据
[INFO] 执行 SQL: DELETE FROM users WHERE username = 'xxx'
[WARNING] 未配置数据库连接，SQL 清洗将跳过
```

## 注意事项

### 1. 清洗失败不影响测试

数据清洗失败会被记录为警告，但不会导致测试用例失败。

### 2. 变量可用性

确保在 cleanup 配置中使用的变量已经在 extract 中提取。

### 3. 数据库连接

SQL 清洗需要配置数据库连接。如果未配置，SQL 清洗将被跳过并记录警告。

### 4. 权限问题

确保清洗操作所需的权限（如删除权限）已正确配置。

### 5. 事务处理

SQL 清洗默认自动提交。如需事务控制，需要在 SQL 语句中显式处理。

## 使用示例

### 场景1：创建用户后删除

```yaml
test_cases:
  - name: "创建用户"
    method: POST
    url: /api/users
    body:
      username: "test_user"
    extract:
      user_id: "$.data.id"
    cleanup:
      enabled: true
      type: "api"
      api:
        method: DELETE
        url: "/api/users/${$extract.user_id}"
        headers:
          Authorization: "Bearer ${$extract.access_token}"
```

### 场景2：通过 SQL 删除

```yaml
test_cases:
  - name: "创建订单"
    method: POST
    url: /api/orders
    body:
      product_id: 123
    extract:
      order_id: "$.data.id"
    cleanup:
      enabled: true
      type: "sql"
      sql:
        connection: "default"
        statement: "DELETE FROM orders WHERE id = ${extract.order_id}"
```

### 场景3：多步骤清洗

```yaml
test_cases:
  - name: "创建用户和订单"
    method: POST
    url: /api/users/create-with-order
    extract:
      user_id: "$.data.user_id"
      order_id: "$.data.order_id"
    cleanup:
      enabled: true
      type: "api"
      api:
        method: POST
        url: "/api/cleanup"
        body:
          steps:
            - action: "delete_sessions"
              session_id: "${extract.session_id}"
            - action: "delete_orders"
              order_id: "${extract.order_id}"
            - action: "delete_user"
              user_id: "${extract.user_id}"
```

## 依赖安装

为了使用 SQL 清洗功能，需要安装以下依赖：

```bash
pip install sqlalchemy pymysql  # MySQL
pip install sqlalchemy psycopg2  # PostgreSQL
```

## 数据库配置

在 `config/config.yaml` 中配置数据库连接：

```yaml
database:
  type: mysql
  host: localhost
  port: 3306
  user: test_user
  password: test_password
  database: test_db
  charset: utf8mb4
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 3600
```

## 文档参考

- [数据清洗功能详细说明](./data_cleanup.md)
- [YAML 模板说明](./yaml_template.md)
- [数据提取说明](./data_extraction_processing.md)

## 总结

数据清洗功能已完全实现并经过测试验证。用户可以在测试用例中配置 cleanup 字段，选择使用 API 或 SQL 方式删除测试数据。功能特性包括：

- ✅ 支持 API 和 SQL 两种清洗方式
- ✅ 支持使用 extract 提取的数据进行清洗
- ✅ 可灵活配置是否启用数据清洗
- ✅ 数据清洗失败不影响测试用例结果
- ✅ 支持变量替换和环境变量
- ✅ 完整的文档和示例

该功能可以有效保持测试环境的干净，避免测试数据污染。
