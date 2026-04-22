# 接口自动化测试框架

基于 Python + Pytest + Allure 的接口自动化测试框架，支持 YAML/JSON 测试用例动态生成、多环境配置、数据依赖、懒加载登录等功能。

## ✨ 核心特性

- 🚀 **懒加载登录**：按需登录，支持多服务独立登录和重试机制
- 📝 **动态测试用例**：从 YAML/JSON 文件自动生成测试用例
- 🔄 **多环境支持**：动态环境切换，支持多服务配置
- 🎯 **智能重试**：登录失败自动重试，失败后自动跳过相关用例
- 🔍 **数据提取**：支持从响应中提取数据，用于后续用例
- ✅ **多元化断言**：支持状态码、JSONPath、正则、SQL 等多种断言
- 📊 **Allure 报告**：生成详细的测试报告
- 🧹 **数据清洗**：支持 API 和 SQL 删除测试数据

## 📁 项目结构

```
├── config/                    # 配置文件
│   └── env/                   # 环境配置
│       └── test.yaml         # 测试环境配置
├── src/                       # 源代码
│   ├── api/                  # 测试用例生成器
│   │   └── test_generator.py # 动态生成测试用例
│   ├── core/                 # 核心模块
│   │   ├── client.py        # HTTP 客户端
│   │   ├── parser.py        # 测试用例解析器
│   │   ├── validator.py     # 断言验证器
│   │   └── extractor.py     # 数据提取器
│   ├── fixtures/             # Fixtures
│   │   └── login_fixture.py # 懒加载登录 fixtures
│   ├── hooks/                # 钩子函数
│   └── utils/                # 工具类
├── test_data/                 # 测试数据
│   ├── login/                # 登录用例
│   ├── user_module.yaml      # 用户模块测试用例
│   └── dsp_app_manage.yaml   # DSP 应用管理测试用例
├── conftest.py                # pytest 配置
├── AGENTS.md                  # 项目结构索引
└── README.md                  # 项目说明
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/env/test.yaml`：

```yaml
base_urls:
  operation: http://localhost:8899
  dsp: http://localhost:8900

auth:
  retry:
    max_retries: 3
    retry_delay: 2
    timeout: 30
```

### 3. 添加登录用例

在 `test_data/login/` 目录下添加登录用例：

```yaml
# test_data/login/test_operation.yaml
test_cases:
  - name: operation 登录
    base_url: operation
    method: POST
    url: /prod-api/login
    body:
      username: admin
      password: "123456"
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        path: body.code
        expected: 200
    extractions:
      - name: auth_token
        type: jsonpath
        expression: "$.token"
```

### 4. 添加测试用例

在 `test_data/` 目录下添加测试用例：

```yaml
test_cases:
  - name: 获取用户信息
    priority: p0
    base_url: operation
    require_login: true
    method: GET
    url: /api/user/info
    assertions:
      - type: status_code
        expected: 200
```

### 5. 运行测试

```bash
# 运行所有测试
pytest

# 运行指定模块
pytest -k "user_module"

# 生成 Allure 报告
pytest --alluredir=allure-results
allure serve allure-results
```

## 📖 核心功能

### 1. 懒加载登录

- **按需登录**：只在测试用例实际需要时才执行登录
- **多服务支持**：每个服务有独立的 token 和 headers
- **登录重试**：网络异常、断言失败时自动重试
- **失败跳过**：登录失败后自动跳过对应服务的后续用例

### 2. 测试用例自动生成

从 YAML/JSON 文件自动生成 pytest 测试用例：

- **数据与代码分离**：测试数据存储在 YAML/JSON 文件中
- **自动收集**：pytest 自动收集 `test_data/` 目录下的所有测试数据
- **动态生成**：无需编写 Python 测试代码，自动生成对应的测试函数

### 3. 数据提取和依赖

支持从响应中提取数据，用于后续用例：

```yaml
test_cases:
  - name: 创建用户
    extract:
      user_id:
        type: jsonpath
        expression: "$.data.id"

  - name: 获取用户详情
    url: /api/users/${$extract.user_id}
```

### 4. 断言验证

支持多种断言类型：

- `status_code` - 状态码断言
- `eq` - 等于断言
- `ne` - 不等于断言
- `in` - 包含断言
- `regex` - 正则匹配
- `is_not_none` - 非空断言

### 5. 数据清洗

支持 API 和 SQL 删除测试数据：

```yaml
test_cases:
  - name: 删除测试数据
    cleanup:
      action: delete
      collection: users
      filter:
        username: test_user
```

## 🎯 最佳实践

1. **用例命名**：使用中文，清晰描述测试场景
2. **优先级**：重要用例标记为 p0，次要用例标记为 p1
3. **断言完整**：至少包含状态码和业务状态码断言
4. **数据清洗**：测试后清理测试数据，保持环境干净

## 🔧 配置说明

### 环境配置（config/env/test.yaml）

```yaml
# 多服务配置
base_urls:
  operation: http://localhost:8899
  dsp: http://localhost:8900

# 登录重试配置
auth:
  retry:
    max_retries: 3      # 最大重试次数
    retry_delay: 2      # 重试间隔（秒）
    timeout: 30         # 登录超时时间（秒）

# 默认请求头
headers:
  Content-Type: application/json
  Accept: application/json
```

## 📄 License

MIT License
