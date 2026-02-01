# YAML测试用例模板说明

## 📖 概述

本平台支持使用 YAML 和 JSON 格式编写测试用例。YAML 格式更易读，JSON 格式更紧凑。本文档详细说明 YAML 格式的使用方法。

---

## 📝 模板结构

### 完整模板

```yaml
# ========================================
# 模块信息
# ========================================
module:
  name: "模块名称"
  version: "1.0.0"
  description: "模块描述"
  author: "作者"

# ========================================
# 全局配置
# ========================================
config:
  # 默认请求头
  headers:
    Content-Type: "application/json"
    Accept: "application/json"
  
  # 默认超时时间
  timeout: 30
  
  # 默认参数
  params:
    debug: "true"

# ========================================
# 测试用例列表
# ========================================
test_cases:
  - name: "用例名称"
    description: "用例描述"
    priority: "p0"  # p0/p1/p2/p3
    tags: ["smoke", "regression"]
    
    # 请求配置
    method: "GET"  # GET/POST/PUT/DELETE/PATCH
    url: "/api/path"
    
    # 请求头
    headers:
      X-Token: "${token}"
    
    # URL参数
    params:
      page: 1
      size: 10
    
    # 请求体
    body:
      username: "test"
      password: "123456"
    
    # 断言验证
    validate:
      - type: "status_code"
        expected: 200
      - type: "eq"
        path: "body.code"
        expected: 0
    
    # 数据提取
    extract:
      user_id:
        type: "jsonpath"
        expression: "$.data.id"
    
    # 钩子函数
    hooks:
      - "after_login"
    
    # 其他配置
    timeout: 30
    skip: false
    retry: 0
```

---

## 🔧 字段说明

### 1. 基本信息字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 用例名称，必须唯一 |
| description | string | ❌ | 用例描述 |
| priority | string | ❌ | 优先级：p0/p1/p2/p3，默认p2 |
| tags | list | ❌ | 标签列表，用于分类 |

### 2. 请求配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| method | string | ✅ | HTTP方法：GET/POST/PUT/DELETE/PATCH |
| url | string | ✅ | 请求URL，相对路径 |
| headers | dict | ❌ | 请求头 |
| params | dict | ❌ | URL参数 |
| body | any | ❌ | 请求体（JSON/表单/文本） |
| files | dict | ❌ | 文件上传 |
| timeout | int | ❌ | 超时时间（秒），默认30 |

### 3. 断言验证字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| validate | list | ❌ | 断言规则列表 |
| type | string | ✅ | 断言类型 |
| path | string | ❌ | JSONPath路径 |
| expected | any | ❌ | 期望值 |
| expression | string | ❌ | 表达式（用于正则/JSON Schema） |

### 4. 数据提取字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| extract | dict | ❌ | 数据提取规则 |
| type | string | ✅ | 提取类型：jsonpath/regex/header/cookie |
| expression | string | ✅ | 提取表达式 |

### 5. 其他字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| depends_on | string | ❌ | 依赖的用例名称 |
| hooks | list | ❌ | 钩子函数列表 |
| skip | bool | ❌ | 是否跳过，默认false |
| skip_reason | string | ❌ | 跳过原因 |
| retry | int | ❌ | 重试次数，默认0 |
| metadata | dict | ❌ | 元数据（自定义字段） |

---

## 💡 断言类型详解

### 1. 状态码断言

```yaml
validate:
  - type: "status_code"
    expected: 200
```

### 2. 等于断言

```yaml
validate:
  - type: "eq"
    path: "body.code"
    expected: 0
```

### 3. 不等于断言

```yaml
validate:
  - type: "ne"
    path: "body.message"
    expected: "error"
```

### 4. 大于/小于断言

```yaml
validate:
  - type: "gt"
    path: "body.count"
    expected: 0
  
  - type: "lt"
    path: "elapsed"
    expected: 1.0
```

### 5. 包含断言

```yaml
validate:
  # 检查值是否在列表中
  - type: "in"
    path: "body.status"
    expected: ["success", "ok"]
  
  # 检查字符串是否包含子串
  - type: "in"
    path: "body.message"
    expected: "成功"
```

### 6. 正则断言

```yaml
validate:
  - type: "regex"
    path: "body.email"
    pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
```

### 7. JSON Schema断言

```yaml
validate:
  - type: "json_schema"
    path: "body.data"
    schema:
      type: "object"
      required: ["id", "name"]
      properties:
        id:
          type: "integer"
        name:
          type: "string"
```

### 8. SQL断言

```yaml
validate:
  - type: "sql"
    sql: "SELECT COUNT(*) FROM users WHERE id = ${body.data.id}"
    expected: 1
```

### 9. 类型断言

```yaml
validate:
  - type: "type"
    path: "body.data"
    expected: "dict"
```

### 10. 长度断言

```yaml
validate:
  - type: "length"
    path: "body.list"
    min: 1
    max: 100
```

### 11. None断言

```yaml
validate:
  - type: "is_none"
    path: "body.error"
  
  - type: "is_not_none"
    path: "body.data"
```

---

## 🔍 数据提取详解

### 1. JSONPath提取

```yaml
extract:
  user_id:
    type: "jsonpath"
    expression: "$.data.user_id"
  
  username:
    type: "jsonpath"
    expression: "$.data.user.name"
  
  first_item:
    type: "jsonpath"
    expression: "$.data.list[0]"
```

### 2. 正则提取

```yaml
extract:
  token:
    type: "regex"
    pattern: '"token":"([^"]+)"'
    group: 1
```

### 3. 响应头提取

```yaml
extract:
  auth_token:
    type: "header"
    header_name: "X-Auth-Token"
```

### 4. Cookie提取

```yaml
extract:
  session_id:
    type: "cookie"
    cookie_name: "JSESSIONID"
```

---

## 🌍 变量系统

### 1. 全局变量

定义位置：`config/global_vars.yaml`

```yaml
auth:
  dev_token: "Bearer xxx"
```

使用方式：

```yaml
headers:
  Authorization: "${auth.dev_token}"
```

### 2. 局部变量

在当前用例中设置：

```yaml
setup:
  - action: "set_var"
    name: "timestamp"
    value: "${timestamp()}"
```

使用方式：

```yaml
body:
  username: "test_${timestamp}"
```

### 3. 缓存变量

在用例间共享（带过期时间）：

```yaml
extract:
  user_id:
    type: "jsonpath"
    expression: "$.data.user_id"
    cache: true
    ttl: 3600  # 缓存1小时
```

使用方式：

```yaml
params:
  user_id: "${cache.user_id}"
```

### 4. 关联变量

从上一个用例响应中提取：

```yaml
extract:
  access_token:
    type: "jsonpath"
    expression: "$.data.token"
```

在后续用例中使用：

```yaml
headers:
  Authorization: "Bearer ${$extract.access_token}"
```

### 5. 内置函数

```yaml
# 生成UUID
headers:
  X-Request-Id: "${uuid()}"

# 生成时间戳
body:
  username: "user_${timestamp()}"

# 生成随机数
body:
  phone: "138${random(10000000, 99999999)}"

# 当前日期
body:
  date: "${date('%Y-%m-%d')}"

# 当前时间
body:
  datetime: "${datetime('%Y-%m-%d %H:%M:%S')}"
```

---

## 📚 完整示例

### 示例1：用户注册登录流程

```yaml
test_cases:
  - name: "用户注册"
    priority: "p0"
    tags: ["smoke"]
    
    method: "POST"
    url: "/user/register"
    
    body:
      username: "test_${timestamp()}"
      password: "Test@123456"
      email: "test_${timestamp()}@example.com"
    
    validate:
      - type: "status_code"
        expected: 200
      - type: "eq"
        path: "body.code"
        expected: 0
    
    extract:
      user_id:
        type: "jsonpath"
        expression: "$.data.user_id"
      token:
        type: "jsonpath"
        expression: "$.data.token"
  
  - name: "用户登录"
    priority: "p0"
    depends_on: "用户注册"
    
    method: "POST"
    url: "/user/login"
    
    body:
      username: "${$extract.username}"
      password: "Test@123456"
    
    validate:
      - type: "status_code"
        expected: 200
      - type: "not_none"
        path: "body.data.token"
```

### 示例2：商品搜索和详情

```yaml
test_cases:
  - name: "搜索商品"
    priority: "p1"
    
    method: "GET"
    url: "/products/search"
    
    params:
      keyword: "手机"
      page: 1
      size: 10
    
    validate:
      - type: "status_code"
        expected: 200
      - type: "type"
        path: "body.data.list"
        expected: "list"
      - type: "length"
        path: "body.data.list"
        min: 1
        max: 10
    
    extract:
      product_id:
        type: "jsonpath"
        expression: "$.data.list[0].product_id"
  
  - name: "获取商品详情"
    priority: "p1"
    depends_on: "搜索商品"
    
    method: "GET"
    url: "/products/${$extract.product_id}"
    
    validate:
      - type: "status_code"
        expected: 200
      - type: "eq"
        path: "body.data.product_id"
        expected: "${$extract.product_id}"
```

---

## ⚠️ 注意事项

1. **YAML缩进**：必须使用2个空格缩进，不能使用Tab
2. **变量替换**：变量必须在双引号中才能正确替换
3. **路径格式**：JSONPath路径以`$.`开头
4. **必填字段**：`name`、`method`、`url`是必填字段
5. **字段类型**：注意字段类型（字符串需要加引号）

---

## 🎯 最佳实践

1. **命名规范**：用例名称使用中文，清晰描述测试场景
2. **优先级**：重要用例标记为p0，次要用例标记为p1/p2
3. **标签使用**：使用标签分类（smoke、regression、daily等）
4. **断言完整**：至少包含状态码和业务状态码断言
5. **数据提取**：为后续用例提取必要的数据
6. **错误处理**：预期失败的用例设置skip或xfail

---

## 📚 更多资源

- [YAML官方文档](https://yaml.org/spec/)
- [JSONPath语法](https://goessner.net/articles/JsonPath/)
- [JSON Schema规范](https://json-schema.org/)
