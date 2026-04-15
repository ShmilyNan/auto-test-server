# 数据清洗功能说明

## 功能概述

数据清洗功能允许在测试用例执行完成后，自动删除测试过程中新增的测试数据，保持测试环境的干净。支持两种清洗方式：

1. **API 清洗**：调用系统的删除接口进行数据删除
2. **SQL 清洗**：通过执行 SQL 语句直接操作数据库删除数据

## 功能特性

- ✅ 支持通过 API 删除测试数据
- ✅ 支持通过 SQL 删除测试数据
- ✅ 支持使用 extract 提取的数据进行清洗
- ✅ 可灵活配置是否启用数据清洗
- ✅ 数据清洗失败不影响测试用例结果
- ✅ 支持批量数据清洗

## 配置方式

### 1. API 清洗配置

```yaml
test_cases:
  - name: "创建用户"
    method: POST
    url: /api/users
    body:
      username: "test_user"
      password: "Test@123456"
    
    # 提取创建的用户ID
    extract:
      user_id:
        type: "jsonpath"
        expression: "$.data.id"
    
    # 数据清洗配置
    cleanup:
      enabled: true              # 是否启用数据清洗
      type: "api"                # 清洗类型：api 或 sql
      api:
        method: "DELETE"         # 请求方法
        url: "/api/users/${$extract.user_id}"  # 使用 extract 数据
        headers:
          Authorization: "Bearer ${$extract.access_token}"
        params:
          force: true
        body:
          reason: "test_cleanup"
    
    validate:
      - type: "status_code"
        expected: 200
```

### 2. SQL 清洗配置

```yaml
test_cases:
  - name: "创建订单"
    method: POST
    url: /api/orders
    body:
      product_id: 123
      quantity: 2
    
    # 提取订单信息
    extract:
      order_id:
        type: "jsonpath"
        expression: "$.data.id"
      order_number:
        type: "jsonpath"
        expression: "$.data.number"
    
    # 数据清洗配置
    cleanup:
      enabled: true
      type: "sql"
      sql:
        connection: "default"      # 数据库连接名称
        statement: "DELETE FROM orders WHERE id = ${extract.order_id} AND number = '${extract.order_number}'"
        params:
          cascade: true
    
    validate:
      - type: "status_code"
        expected: 200
```

### 3. 不启用数据清洗

```yaml
test_cases:
  - name: "创建数据-不清洗"
    method: POST
    url: /api/data
    body:
      name: "permanent_data"
    
    # 不启用数据清洗
    cleanup:
      enabled: false
    
    validate:
      - type: "status_code"
        expected: 200
```

## 配置说明

### cleanup 配置字段

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| enabled | boolean | 是 | 是否启用数据清洗（默认 false） |
| type | string | 是 | 清洗类型：api 或 sql |
| api | object | 否 | API 清洗配置（type=api 时必填） |
| sql | object | 否 | SQL 清洗配置（type=sql 时必填） |

### API 清洗配置 (api)

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| method | string | 否 | 请求方法（默认 DELETE） |
| url | string | 是 | 请求 URL |
| headers | object | 否 | 请求头 |
| params | object | 否 | URL 参数 |
| body | object | 否 | 请求体 |

### SQL 清洗配置 (sql)

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| connection | string | 否 | 数据库连接名称（默认 default） |
| statement | string | 是 | SQL 语句 |
| params | object | 否 | SQL 参数 |

## 变量替换

在数据清洗配置中，可以使用以下变量：

- `${$extract.variable_name}` - 从响应中提取的数据
- `${global_var}` - 全局变量
- `${local_var}` - 局部变量
- `${env.VAR_NAME}` - 环境变量

### 变量替换示例

```yaml
cleanup:
  enabled: true
  type: "api"
  api:
    url: "/api/users/${$extract.user_id}"
    headers:
      Authorization: "Bearer ${$extract.access_token}"
      X-Request-ID: "${uuid()}"
      X-Test-User: "${env.TEST_USER}"
```

## 数据库配置

### 方式1：使用 SQLAlchemy

在 `config/config.yaml` 中配置数据库连接：

```yaml
database:
  # 数据库类型: mysql, postgresql
  type: mysql
  host: localhost
  port: 3306
  user: test_user
  password: test_password
  database: test_db
  charset: utf8mb4
  # 连接池配置
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 3600
```

### 方式2：使用集成服务

使用项目中的数据库集成服务（`integration-postgre-database`）：

```python
from src.utils.cleaner import DataCleaner

cleaner = DataCleaner()
cleaner._execute_sql = lambda stmt, params: integration_execute_sql(stmt)
```

## 使用场景

### 场景1：创建用户后删除

```yaml
test_cases:
  # 创建用户
  - name: "创建用户"
    method: POST
    url: /api/users
    body:
      username: "test_user_${timestamp()}"
      password: "Test@123456"
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
    validate:
      - type: "status_code"
        expected: 200
```

### 场景2：创建订单后通过 SQL 删除

```yaml
test_cases:
  # 创建订单
  - name: "创建订单"
    method: POST
    url: /api/orders
    body:
      product_id: 123
      quantity: 2
    extract:
      order_id: "$.data.id"
    cleanup:
      enabled: true
      type: "sql"
      sql:
        connection: "default"
        statement: "DELETE FROM orders WHERE id = ${extract.order_id}"
    validate:
      - type: "status_code"
        expected: 200
```

### 场景3：多步骤数据清洗

```yaml
test_cases:
  # 创建用户和相关数据
  - name: "创建用户和订单"
    method: POST
    url: /api/users/create-with-order
    body:
      username: "multi_test"
    extract:
      user_id: "$.data.user_id"
      order_id: "$.data.order_id"
      session_id: "$.data.session_id"
    cleanup:
      enabled: true
      type: "api"
      api:
        method: POST
        url: "/api/cleanup"
        headers:
          Authorization: "Bearer ${$extract.access_token}"
        body:
          steps:
            - action: "delete_sessions"
              params:
                session_id: "${extract.session_id}"
            - action: "delete_orders"
              params:
                order_id: "${extract.order_id}"
            - action: "delete_user"
              params:
                user_id: "${extract.user_id}"
    validate:
      - type: "status_code"
        expected: 200
```

## 执行流程

1. **执行测试用例**
2. **提取数据**（如果配置了 extract）
3. **执行断言**
4. **执行后置处理**（teardown）
5. **执行数据清洗**（如果配置了 cleanup）
6. **记录测试结果**

数据清洗失败不会影响测试用例的结果，只会在日志中记录警告。

## 注意事项

### 1. 清洗失败不影响测试

数据清洗失败会被记录为警告，但不会导致测试用例失败。

### 2. 变量可用性

确保在 cleanup 配置中使用的变量已经在 extract 中提取。如果变量未找到，会记录警告并使用原始表达式。

### 3. 数据库连接

SQL 清洗需要配置数据库连接。如果未配置，SQL 清洗将被跳过并记录警告。

### 4. 权限问题

确保清洗操作所需的权限（如删除权限）已正确配置。

### 5. 事务处理

SQL 清洗默认自动提交。如需事务控制，需要在 SQL 语句中显式处理。

## 完整示例

```yaml
# test_data/user_cleanup.yaml
module:
  name: "用户数据清洗测试"
  version: "1.0.0"

config:
  headers:
    Content-Type: "application/json"

test_cases:
  # 注册用户
  - name: "用户注册-自动清洗"
    description: "注册用户后自动删除"
    priority: "p0"
    tags: ["cleanup", "api"]
    
    method: "POST"
    url: "/api/users/register"
    
    headers:
      X-Request-ID: "${uuid()}"
    
    body:
      username: "cleanup_user_${timestamp()}"
      password: "Test@123456"
      email: "cleanup_${timestamp()}@test.com"
    
    extract:
      user_id:
        type: "jsonpath"
        expression: "$.data.user_id"
      access_token:
        type: "jsonpath"
        expression: "$.data.token"
    
    cleanup:
      enabled: true
      type: "api"
      api:
        method: DELETE
        url: "/api/users/${$extract.user_id}"
        headers:
          Authorization: "Bearer ${$extract.access_token}"
        body:
          reason: "auto_cleanup"
          cascade: true
    
    validate:
      - type: "status_code"
        expected: 200
      - type: "eq"
        path: "body.code"
        expected: 0
      - type: "not_none"
        path: "body.data.user_id"

  # 创建用户并关联订单
  - name: "创建用户-多数据清洗"
    description: "创建用户和订单后同时删除"
    priority: "p0"
    tags: ["cleanup", "sql"]
    
    method: "POST"
    url: "/api/users/with-order"
    
    body:
      username: "multi_cleanup_user"
      password: "Test@123456"
      product_id: 123
      quantity: 2
    
    extract:
      user_id: "$.data.user_id"
      order_id: "$.data.order_id"
    
    cleanup:
      enabled: true
      type: "sql"
      sql:
        connection: "default"
        statement: |
          DELETE FROM order_items WHERE order_id = ${extract.order_id};
          DELETE FROM orders WHERE id = ${extract.order_id};
          DELETE FROM user_sessions WHERE user_id = ${extract.user_id};
          DELETE FROM users WHERE id = ${extract.user_id};
    
    validate:
      - type: "status_code"
        expected: 200
```

## 验证方法

### 1. 运行 cleanup 测试

```bash
cd auto-test-server
python -m pytest src/api/test_generator.py -k "cleanup" -v
```

### 2. 查看日志

数据清洗操作会在日志中记录：

```
[INFO] 开始通过 API 清洗数据
[INFO] 发送清洗请求: DELETE /api/users/12345
[INFO] 数据清洗成功: DELETE /api/users/12345, 状态码: 200
```

或：

```
[INFO] 开始通过 SQL 清洗数据
[INFO] 执行 SQL: DELETE FROM users WHERE id = 12345
[INFO] SQL 执行成功，影响行数: 1
```

### 3. 检查数据库

测试执行后，检查数据库确认数据已被删除：

```sql
SELECT * FROM users WHERE id = 12345;
-- 应该返回空结果
```

## 最佳实践

1. **为创建类用例配置 cleanup**：所有创建数据的测试用例都应该配置数据清洗
2. **使用 extract 变量**：优先使用 extract 提取的数据进行清洗，确保准确性
3. **设置合理的超时时间**：删除操作可能需要较长时间，合理设置超时
4. **测试数据隔离**：使用唯一的测试数据标识，避免冲突
5. **环境区分**：在测试环境启用清洗，在生产环境禁用
6. **权限最小化**：只授予必要的删除权限

## 故障排查

### 问题1：清洗失败但测试通过

**原因**：数据清洗失败不会影响测试结果。

**解决**：查看日志中的清洗失败信息，检查配置是否正确。

### 问题2：SQL 清洗被跳过

**原因**：未配置数据库连接。

**解决**：在 `config/config.yaml` 中配置数据库连接信息。

### 问题3：变量未替换

**原因**：变量未在 extract 中提取或提取失败。

**解决**：检查 extract 配置，确保变量正确提取。

### 问题4：权限不足

**原因**：数据库用户或 API Token 缺少删除权限。

**解决**：授予必要的删除权限。

## 参考文档

- [YAML 模板说明](./yaml_template.md)
- [数据提取说明](./data_extraction_processing.md)
- [数据库配置](../config/config.yaml)
