# 默认请求头功能说明

## 功能概述

本平台支持在测试数据文件中定义默认请求头，所有测试用例都会自动使用这些默认请求头。用例级别的自定义请求头可以覆盖默认请求头。

## 配置方式

### YAML 文件格式

```yaml
# 模块信息
module:
  name: "用户模块"
  version: "1.0.0"
  description: "用户相关接口测试"

# 全局配置
config:
  # 默认请求头
  headers:
    Content-Type: "application/json"
    Accept: "application/json"
    X-Auth-Token: "${env.AUTH_TOKEN}"

  # 默认超时时间
  timeout: 30

# 测试用例列表
test_cases:
  - name: "用户注册"
    method: POST
    url: /api/users/register
    # 不设置 headers，使用默认请求头
    body:
      username: test_user
      password: test_password

  - name: "用户登录"
    method: POST
    url: /api/users/login
    # 自定义请求头，会覆盖默认请求头
    headers:
      Content-Type: "application/json"
      Accept: "application/json"
      X-Request-Id: "${uuid()}"
    body:
      username: test_user
      password: test_password
```

### JSON 文件格式

```json
{
  "module": {
    "name": "商品模块",
    "version": "1.0.0"
  },
  "config": {
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "timeout": 30
  },
  "test_cases": [
    {
      "name": "获取商品列表",
      "method": "GET",
      "url": "/products"
    }
  ]
}
```

## 请求头合并规则

### 规则说明

1. **默认请求头优先级较低**：config.headers 中定义的默认请求头会自动应用到所有测试用例
2. **用例自定义请求头优先级较高**：测试用例中定义的 headers 会覆盖默认请求头
3. **合并策略**：默认请求头和用例自定义请求头合并时，用例自定义请求头会覆盖同名键

### 合并示例

**默认请求头（config.headers）**：
```yaml
headers:
  Content-Type: "application/json"
  Accept: "application/json"
  X-Auth-Token: "token123"
```

**用例自定义请求头（test_case.headers）**：
```yaml
headers:
  X-Request-Id: "${uuid()}"
  X-Auth-Token: "token456"  # 覆盖默认值
```

**最终使用的请求头**：
```json
{
  "Content-Type": "application/json",    // 来自默认请求头
  "Accept": "application/json",         // 来自默认请求头
  "X-Auth-Token": "token456",          // 被用例自定义请求头覆盖
  "X-Request-Id": "${uuid()}"          // 来自用例自定义请求头
}
```

## 使用场景

### 场景1：所有用例使用相同的请求头

适用于大部分接口需要相同请求头的场景，如：
- 所有接口都需要 Content-Type: application/json
- 所有接口都需要 Accept: application/json
- 所有接口都需要认证令牌

```yaml
config:
  headers:
    Content-Type: "application/json"
    Accept: "application/json"
    Authorization: "Bearer ${env.API_TOKEN}"

test_cases:
  - name: 获取用户信息
    method: GET
    url: /api/users/me

  - name: 更新用户信息
    method: PUT
    url: /api/users/me
    body:
      name: "新名字"
```

### 场景2：部分用例需要特殊请求头

适用于大部分用例使用默认请求头，少数用例需要特殊请求头的场景。

```yaml
config:
  headers:
    Content-Type: "application/json"
    Accept: "application/json"

test_cases:
  - name: 普通接口调用
    method: POST
    url: /api/normal
    # 使用默认请求头

  - name: 上传文件接口
    method: POST
    url: /api/upload
    headers:
      Content-Type: "multipart/form-data"  # 覆盖默认值
    files:
      file: "@/path/to/file.jpg"
```

### 场景3：在默认请求头基础上添加额外请求头

适用于在默认请求头基础上，某些用例需要额外添加请求头。

```yaml
config:
  headers:
    Content-Type: "application/json"
    Accept: "application/json"

test_cases:
  - name: 带追踪ID的请求
    method: POST
    url: /api/trace
    headers:
      X-Trace-ID: "${uuid()}"  # 添加额外请求头
    body:
      data: "test"
```

## 验证方法

### 方法1：查看解析结果

```python
from src.core.parser import CaseDataParser

parser = CaseDataParser('test_data')
cases_dict = parser.parse_dir()

for module_name, cases in cases_dict.items():
    if cases:
        case = cases[0]
        print(f'{module_name}:')
        print(f'  默认请求头: {case.default_headers}')
        print(f'  合并后的请求头: {case.headers}')
```

### 方法2：运行测试脚本

```bash
cd auto-test-platform
python test_default_headers.py
```

输出示例：
```
模块: user_module
用例名称: 用户注册-正常流程
默认请求头: {'Content-Type': 'application/json', 'Accept': 'application/json'}
合并后的请求头: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Request-Id': '${uuid()}'}
实际使用的请求头: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Request-Id': '${uuid()}'}
✓ 默认请求头 [Content-Type]: application/json 已正确应用
✓ 默认请求头 [Accept]: application/json 已正确应用
```

### 方法3：查看日志

运行测试时，日志会显示实际使用的请求头：

```bash
python -m pytest src/api/test_dynamic.py -v
```

日志输出：
```
发送请求: POST http://example.com/api/users/register
请求头: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Auth-Token': 'token123'}
```

## 注意事项

### 1. Content-Type 特殊处理

- 如果 Content-Type 为 application/json，请求体会被作为 JSON 发送（使用 `json` 参数）
- 如果 Content-Type 为其他值，请求体会被作为表单数据发送（使用 `data` 参数）

### 2. 变量替换

请求头中的变量会在运行时被替换：

```yaml
config:
  headers:
    X-Auth-Token: "${env.API_TOKEN}"
    X-Request-Id: "${uuid()}"
```

### 3. 跨模块默认请求头

每个模块的 config.headers 是独立的，不同模块可以有不同的默认请求头：

```yaml
# user_module.yaml
config:
  headers:
    Authorization: "Bearer user_token"

# admin_module.yaml
config:
  headers:
    Authorization: "Bearer admin_token"
```

### 4. 空请求头

如果测试数据文件中没有定义 config.headers，或者 config.headers 为空，则不会添加任何默认请求头。

## 最佳实践

1. **通用请求头放在 config.headers**：如 Content-Type、Accept、认证令牌等
2. **特殊请求头放在用例级别**：如 X-Request-Id、X-Trace-ID 等
3. **使用变量避免硬编码**：如 `${env.API_TOKEN}`、`${uuid()}`
4. **注释说明用途**：在 YAML 文件中添加注释说明每个请求头的用途

## 完整示例

参见 `test_data/user_module.yaml` 和 `test_data/order_module.yaml` 获取完整的使用示例。
