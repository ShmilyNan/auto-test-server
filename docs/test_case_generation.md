# 测试用例自动生成功能说明

## 概述

本项目实现了从 `test_data` 目录中的 YAML/JSON 文件自动生成 pytest 测试用例的功能。测试数据与测试代码分离，通过动态生成机制实现了数据驱动的接口自动化测试。

## 工作原理

### 1. 测试数据加载

- 测试数据存储在 `test_data/` 目录
- 支持 `.yaml` 和 `.json` 两种格式
- 每个文件代表一个测试模块，包含多个测试用例

### 2. 动态测试用例生成

当 pytest 收集测试时，`src/api/test_dynamic.py` 模块会：

1. 加载 `test_data/` 目录下的所有 YAML/JSON 文件
2. 使用 `TestParser` 解析每个文件，提取测试用例
3. 为每个测试用例动态生成对应的 pytest 测试函数
4. 将生成的函数注册到模块命名空间

### 3. 测试用例执行

动态生成的测试函数会：

1. 检查测试用例是否被标记为跳过
2. 执行前置处理（setup）
3. 准备请求数据（变量替换）
4. 构建完整的请求 URL
5. 发送 HTTP 请求
6. 保存响应到测试上下文
7. 提取数据（extract）
8. 执行断言验证（validate）
9. 执行后置处理（teardown）
10. 记录执行时间

## 使用方法

### 运行所有测试

```bash
cd auto-test-platform
python -m pytest src/api/test_dynamic.py
```

### 运行特定测试

```bash
# 运行特定测试用例
python -m pytest src/api/test_dynamic.py::test_用户登录_正常流程_1

# 运行特定模块的所有测试
python -m pytest src/api/test_dynamic.py -k "user_module"

# 运行特定优先级的测试
python -m pytest src/api/test_dynamic.py -m p0
```

### 查看测试用例

```bash
# 只收集测试用例，不执行
python -m pytest src/api/test_dynamic.py --collect-only
```

## 测试数据格式

### YAML 格式示例

```yaml
module_name: user_module
cases:
  - name: 用户注册_正常流程
    priority: p0
    tags:
      - smoke
      - positive
    description: 测试用户正常注册流程
    skip: false
    method: POST
    url: /api/users/register
    headers:
      Content-Type: application/json
    body:
      username: ${random_username}
      password: ${random_password}
      email: ${random_email}
    validate:
      - eq: ["status_code", 201]
      - contains: ["message", "注册成功"]
```

### JSON 格式示例

```json
{
  "module_name": "product_module",
  "cases": [
    {
      "name": "获取商品列表",
      "priority": "p0",
      "tags": ["smoke", "positive"],
      "description": "获取商品列表数据",
      "method": "GET",
      "url": "/api/products",
      "params": {
        "page": 1,
        "page_size": 20,
        "category": "electronics"
      },
      "validate": [
        {"eq": ["status_code", 200]},
        {"contains": ["message", "成功"]}
      ]
    }
  ]
}
```

## 生成的测试用例

测试用例的函数名会自动生成，格式为：

```
test_<测试用例名称>_<索引>
```

例如：
- `test_获取商品列表_0`
- `test_用户登录_正常流程_1`
- `test_用户注册_缺少必填字段_6`

## 高级特性

### 1. 变量替换

测试用例中支持变量替换：

- `${random_username}` - 生成随机用户名
- `${random_password}` - 生成随机密码
- `${random_email}` - 生成随机邮箱
- `${extract.token}` - 使用提取的变量
- `${env.BASE_URL}` - 使用环境变量

### 2. 数据提取

支持从响应中提取数据：

```yaml
extract:
  token: "$.data.token"
  user_id: "$.data.user.id"
```

### 3. 多元化断言

支持多种断言类型：

```yaml
validate:
  - eq: ["status_code", 200]           # 等于
  - ne: ["error_code", 0]              # 不等于
  - gt: ["data.count", 0]              # 大于
  - lt: ["data.page_size", 100]        # 小于
  - contains: ["message", "成功"]       # 包含
  - regex: ["data.email", "^[a-z]+@"]  # 正则匹配
```

### 4. 前置/后置处理

支持 setup 和 teardown：

```yaml
setup:
  - action: set_var
    name: test_user
    value: "test_user_001"

teardown:
  - action: clear_local
```

### 5. 数据依赖

支持测试用例之间的数据依赖：

```yaml
# 第一个用例提取数据
extract:
  user_id: "$.data.user.id"

# 第二个用例使用提取的数据
url: /api/users/${extract.user_id}
```

## 报告生成

### Allure 报告

```bash
# 运行测试并生成 Allure 报告
python -m pytest src/api/test_dynamic.py --alluredir=reports/allure

# 查看报告
allure serve reports/allure
```

### HTML 报告

```bash
# 生成 HTML 报告
python -m pytest src/api/test_dynamic.py --html=reports/report.html
```

## 配置文件

### pytest.ini

```ini
[pytest]
testpaths = src/api
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    -s
    --strict-markers
    --tb=short
    --alluredir=reports/allure
    --clean-alluredir
```

### config/config.yaml

```yaml
default_env: dev

http_client:
  type: requests  # 或 httpx
  timeout: 30
  retry: 3
```

## 常见问题

### Q1: 为什么测试用例收集数为 0？

A: 确保以下配置正确：
1. `test_data/` 目录下有 YAML/JSON 文件
2. 文件格式符合规范
3. `pytest.ini` 中 `testpaths` 配置正确
4. `src/api/test_dynamic.py` 文件存在

### Q2: 如何添加新的测试用例？

A: 在 `test_data/` 目录下创建新的 YAML/JSON 文件，按照格式添加测试用例即可。无需修改代码，pytest 会自动收集。

### Q3: 如何跳过某个测试用例？

A: 在测试用例中设置 `skip: true`，并可选提供 `skip_reason`：

```yaml
skip: true
skip_reason: "接口暂未实现"
```

### Q4: 如何执行冒烟测试？

A: 使用 `-m smoke` 标记：

```bash
python -m pytest src/api/test_dynamic.py -m smoke
```

## 最佳实践

1. **测试数据组织**：按功能模块划分文件，如 `user_module.yaml`, `product_module.json`
2. **命名规范**：测试用例名称清晰描述测试场景
3. **优先级管理**：合理设置 p0-p3 优先级
4. **标签使用**：使用标签分类测试用例（smoke, regression, daily）
5. **数据提取**：避免硬编码，使用数据提取和变量替换
6. **断言完整**：验证状态码、业务逻辑、数据完整性

## 总结

通过动态测试用例生成机制，项目实现了测试数据与测试代码的完全分离。测试人员只需维护 YAML/JSON 格式的测试数据，无需编写 Python 测试代码，大大提高了测试用例维护效率和团队协作效率。
