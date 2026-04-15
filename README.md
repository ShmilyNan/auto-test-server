# 接口自动化测试平台 - 架构设计与代码模板

## 📋 项目概述

基于 Python + Pytest + Allure + Requests/httpx 的接口自动化测试平台，支持多环境配置、动态参数化、数据依赖、多元化断言等功能。

## 🎯 核心特性

✅ **双HTTP客户端支持**：Requests 和 httpx 可平滑切换
✅ **测试数据管理**：YAML + JSON 格式，自动解析加载
✅ **多环境配置**：动态环境切换，自动识别配置
✅ **动态参数化**：全局变量、局部变量、缓存变量、关联变量
✅ **数据依赖**：接口返回数据共享，轻松实现依赖
✅ **数据清洗**：支持 API 和 SQL 删除测试数据，保持测试环境干净 🆕
✅ **全局前置登录**：测试会话开始时自动登录，Token 自动添加到所有测试用例，无需手动配置 Authorization header 🆕
✅ **优化标记系统**：精简的 marker 配置，支持按模块名称灵活筛选，配置文件更简洁 🆕
✅ **配置管理现代化**：使用 pyproject.toml 统一管理项目配置，支持多工具集成 🆕
✅ **钩子函数**：支持自定义钩子扩展功能
✅ **日志记录**：基于 loguru 的完整日志系统
✅ **多元化断言**：JSON、SQL、JSON-Schema、正则、Python assert
✅ **执行顺序控制**：支持自定义用例执行顺序，默认按文件顺序
✅ **测试报告**：Allure 详细美观报告
✅ **结果通知**：飞书、钉钉、企业微信、邮箱

## 📁 项目目录结构

```
auto-test-platform/
├── README.md                          # 项目说明
├── requirements.txt                   # 依赖清单
├── pyproject.toml                    # 项目配置（pytest、black、flake8等）🆕
├── run.py                            # 运行入口
├── config/                           # 配置目录
│   ├── __init__.py
│   ├── config.yaml                   # 主配置文件
│   └── env/                          # 环境配置
│       ├── test.yaml                 # 测试环境
│       └── prod.yaml                 # 生产环境
├── src/                              # 核心代码
│   ├── __init__.py
│   ├── core/                         # 核心模块
│   │   ├── __init__.py
│   │   ├── client.py                 # HTTP客户端封装（requests/httpx）
│   │   ├── context.py                # 上下文管理（变量、数据）
│   │   ├── parser.py                 # YAML/JSON解析器
│   │   └── validator.py              # 断言验证器
│   ├── plugins/                      # pytest插件
│   │   ├── __init__.py
│   │   ├── data_generator.py         # 测试数据生成器
│   │   └── hooks.py                  # 钩子函数管理
│   ├── utils/                        # 工具类
│   │   ├── __init__.py
│   │   ├── logger.py                 # loguru日志
│   │   ├── extractor.py              # 数据提取器
│   │   ├── notifier.py               # 通知发送器
│   │   ├── cleaner.py                # 🆕 数据清洗工具
│   │   ├── global_login.py           # 🆕 全局登录管理器
│   │   └── yaml_loader.py            # YAML加载器
│   └── api/                          # API测试用例
│       ├── __init__.py
│       ├── test_dynamic.py           # 🆕 动态测试用例生成器
│       └── test_cases/               # 测试用例目录
├── test_data/                        # 测试数据
│   ├── user_module.yaml
│   ├── offer_manage.json
├── hooks/                            # 自定义钩子
│   ├── __init__.py
│   └── custom_hooks.py
├── logs/                             # 日志目录
├── reports/                          # 报告目录
│   └── allure/                       # allure报告
└── docs/                             # 文档
    ├── architecture.md               # 架构设计文档
    ├── yaml_template.md              # YAML模板说明
    ├── usage_guide.md                # 使用指南
    ├── test_case_generation.md       # 🆕 测试用例自动生成说明
    ├── data_extraction_processing.md  # 🆕 数据提取后处理说明
    ├── test_execution_order.md       # 🆕 测试用例执行顺序控制说明
    ├── data_cleanup.md               # 🆕 数据清洗功能说明
    ├── data_cleanup_summary.md       # 🆕 数据清洗功能实现总结
    ├── marker_optimization_guide.md  # 🆕 Marker优化方案与使用指南
    ├── marker_optimization_summary.md# 🆕 Marker优化总结
    ├── module_info_definition.md     # 🆕 模块信息定义示例
    ├── marker_quick_reference.md     # 🆕 Marker快速参考指南
    ├── code_adaptation_guide.md      # 🆕 代码适配与YAML配置迁移指南
    ├── code_adaptation_summary.md    # 🆕 代码适配与YAML配置修改完成总结
    ├── global_login_guide.md         # 🆕 全局登录功能使用指南
    └── global_login_summary.md       # 🆕 全局登录功能实现总结
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config/config.yaml` 设置默认环境：

```yaml
default_env: test  # 默认环境：test/prod
log_level: INFO   # 日志级别
```

### 3. 添加测试数据

在 `test_data/` 目录下添加 YAML 或 JSON 格式的测试数据文件：

```yaml
module_name: user_module
cases:
  - name: 用户登录_正常流程
    priority: p0
    tags:
      - smoke
      - positive
    description: 测试用户正常登录
    method: POST
    url: /api/users/login
    headers:
      Content-Type: application/json
    body:
      username: test_user
      password: test_password
    validate:
      - eq: ["status_code", 200]
      - contains: ["message", "登录成功"]
```

### 4. 运行测试

```bash
# 运行所有测试（自动从 test_data 生成测试用例）
python -m pytest src/api/test_generator.py

# 使用运行入口
python run.py

# 指定环境运行
python run.py --env test

# 生成报告
python run.py --report

# 查看报告
allure serve reports/allure
```

### 5. 查看生成的测试用例

```bash
# 收集但不执行测试，查看生成的测试用例
python -m pytest src/api/test_generator.py --collect-only
```

## 📖 核心功能说明

### 1. 测试用例自动生成 🆕

项目实现了从 `test_data` 目录中的 YAML/JSON 文件自动生成 pytest 测试用例的功能：

- **数据与代码分离**：测试数据存储在 YAML/JSON 文件中
- **自动收集**：pytest 自动收集 `test_data/` 目录下的所有测试数据
- **动态生成**：无需编写 Python 测试代码，自动生成对应的测试函数
- **实时更新**：修改测试数据后无需重启，下次运行自动生效



详见 `docs/yaml_template.md`

### 2. 默认请求头功能 🆕

支持在测试数据文件中定义模块级别的默认请求头，所有测试用例自动使用：

- **统一配置**：在 `config.headers` 中定义默认请求头
- **自动合并**：默认请求头与用例自定义请求头自动合并
- **优先级控制**：用例自定义请求头优先级高于默认请求头
- **变量支持**：支持在请求头中使用变量替换

详见 `docs/default_headers.md`

### 3. 全局前置登录功能 🆕

支持在测试会话开始时自动执行登录操作，获取 Token 并自动添加到所有测试用例的请求头中：

- **自动登录**：测试会话开始时自动执行登录
- **自动添加 Authorization header**：所有测试用例自动携带 Token
- **Token 管理**：支持 Token 过期管理和自动刷新
- **灵活配置**：支持自定义登录接口、请求头、请求体等
- **用户可覆盖**：测试用例可以自定义 Authorization header 覆盖全局配置

**使用方式**：

1. 在 `config/config.yaml` 中配置全局登录：

```yaml
global_login:
  enable: true
  login_url: "/api/auth/login"
  username: "admin"
  password: "admin123"
  request_method: "POST"
  request_body_type: "json"
  body_template: |
    {
      "username": "${username}",
      "password": "${password}"
    }
  token_path: "$.data.token"
  token_type: "Bearer"
  token_ttl: 7200
```

2. 测试用例无需配置 Authorization header：

```yaml
test_cases:
  - name: "获取用户信息"
    method: GET
    url: /api/user/info
    # 不需要配置 Authorization header
    validate:
      - eq: ["status_code", 200]
```

详见 `docs/global_login_guide.md`

### 4. 多环境配置

支持 test/prod 环境动态切换，配置文件位于 `config/env/`

### 5. 参数化支持

- `${global_var}` - 全局变量
- `${local_var}` - 局部变量
- `${cache.var}` - 缓存变量
- `${$extract.var}` - 关联变量（从响应中提取）

### 6. 断言类型

- `eq` - 等于
- `ne` - 不等于
- `gt` - 大于
- `lt` - 小于
- `in` - 包含
- `regex` - 正则匹配
- `json_schema` - JSON Schema 验证
- `sql` - SQL 断言

### 7. 配置管理优化 🆕

#### 7.1 pyproject.toml 统一配置管理

项目已迁移到使用 `pyproject.toml` 统一管理项目配置，替代传统的 `pytest.ini`：

**优势**：
- 统一配置文件：pytest、black、flake8、mypy 等工具配置集中管理
- 更好的可读性：使用 TOML 格式，支持层级结构
- 更好的生态兼容：现代 Python 项目标准配置方式

**配置结构**：
```toml
[tool.pytest.ini_options]
testpaths = ["src/api"]
addopts = ["-v", "-s", "--strict-markers"]
markers = [
    "smoke: 冒烟测试",
    "regression: 回归测试",
    # ...
]
```

详见 `docs/marker_optimization_guide.md`

#### 7.2 Marker 优化方案 🆕

优化了 pytest marker 的注册方式，解决了 markers 数量臃肿的问题：

**优化前**：每个模块都需要注册对应的 marker（如 `module_user_module`）
```ini
markers =
    module_user_module: 用户模块测试
    module_product_module: 商品模块测试
    # ... 每新增一个模块就要添加一个 marker
```

**优化后**：只保留核心的 marker 类型，使用 `-k` 参数按模块筛选
```toml
markers = [
    # 功能分类
    "smoke: 冒烟测试",
    "regression: 回归测试",
    # 优先级分类
    "p0: P0级用例",
    "p1: P1级用例",
    # 测试类型分类
    "api: API接口测试",
    "sql: SQL数据库测试",
    # ...
]
```

**使用方式**：
```bash
# 运行特定模块的测试用例
python -m pytest src/api/test_generator.py -k "user_module" -v

# 运行特定类型的测试
python -m pytest -m "smoke and p0" -v

# 组合筛选
python -m pytest -k "user_module and positive" -v
```

**优势**：
- ✅ Markers 数量可控（从 28 个减少到 ~15 个）
- ✅ 不会随着测试用例增加而臃肿
- ✅ 更灵活的筛选方式
- ✅ 更易于维护

详见 `docs/marker_optimization_guide.md`

### 8. 数据清洗功能 🆕

## 📊 测试报告

运行测试后自动生成 Allure 报告：

```bash
allure serve reports/allure
```

## 🔔 结果通知

支持配置飞书、钉钉、企业微信、邮箱通知，在 `config/config.yaml` 中配置。

## 📝 开发指南

详见 `docs/` 目录下的详细文档。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License
