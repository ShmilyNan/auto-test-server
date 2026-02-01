# 接口自动化测试平台 - 架构设计与代码模板

## 📋 项目概述

基于 Python + Pytest + Allure + Requests/httpx 的接口自动化测试平台，支持多环境配置、动态参数化、数据依赖、多元化断言等功能。

## 🎯 核心特性

✅ **双HTTP客户端支持**：Requests 和 httpx 可平滑切换  
✅ **测试数据管理**：YAML + JSON 格式，自动解析加载  
✅ **多环境配置**：动态环境切换，自动识别配置  
✅ **动态参数化**：全局变量、局部变量、缓存变量、关联变量  
✅ **数据依赖**：接口返回数据共享，轻松实现依赖  
✅ **钩子函数**：支持自定义钩子扩展功能  
✅ **日志记录**：基于 loguru 的完整日志系统  
✅ **多元化断言**：JSON、SQL、JSON-Schema、正则、Python assert  
✅ **测试报告**：Allure 详细美观报告  
✅ **结果通知**：飞书、钉钉、企业微信、邮箱

## 📁 项目目录结构

```
auto-test-platform/
├── README.md                          # 项目说明
├── requirements.txt                   # 依赖清单
├── pytest.ini                        # pytest配置
├── run.py                            # 运行入口
├── config/                           # 配置目录
│   ├── __init__.py
│   ├── config.yaml                   # 主配置文件
│   └── env/                          # 环境配置
│       ├── dev.yaml                  # 开发环境
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
│   │   └── notifier.py               # 通知发送器
│   └── api/                          # API测试用例
│       ├── __init__.py
│       └── test_cases/               # 测试用例目录
├── test_data/                        # 测试数据
│   ├── user_module.yaml
│   ├── order_module.yaml
│   └── product_module.json
├── hooks/                            # 自定义钩子
│   ├── __init__.py
│   └── custom_hooks.py
├── logs/                             # 日志目录
├── reports/                          # 报告目录
│   └── allure/                       # allure报告
└── docs/                             # 文档
    ├── architecture.md               # 架构设计文档
    ├── yaml_template.md              # YAML模板说明
    └── usage_guide.md                # 使用指南
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
default_env: dev  # 默认环境：dev/test/prod
log_level: INFO   # 日志级别
```

### 3. 运行测试

```bash
# 运行所有测试
python run.py

# 指定环境运行
python run.py --env test

# 生成报告
python run.py --report

# 查看报告
allure serve reports/allure
```

## 📖 核心功能说明

### 1. YAML测试用例格式

详见 `docs/yaml_template.md`

### 2. 多环境配置

支持 dev/test/prod 环境动态切换，配置文件位于 `config/env/`

### 3. 参数化支持

- `${global_var}` - 全局变量
- `${local_var}` - 局部变量
- `${cache.var}` - 缓存变量
- `${$extract.var}` - 关联变量（从响应中提取）

### 4. 断言类型

- `eq` - 等于
- `ne` - 不等于
- `gt` - 大于
- `lt` - 小于
- `in` - 包含
- `regex` - 正则匹配
- `json_schema` - JSON Schema 验证
- `sql` - SQL 断言

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
