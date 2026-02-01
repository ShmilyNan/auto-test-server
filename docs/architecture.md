# 接口自动化测试平台 - 架构设计文档

## 📐 目录

1. [总体架构](#总体架构)
2. [核心模块设计](#核心模块设计)
3. [数据流设计](#数据流设计)
4. [扩展机制](#扩展机制)
5. [性能优化](#性能优化)
6. [安全设计](#安全设计)

---

## 总体架构

### 架构分层

```
┌─────────────────────────────────────────────────────┐
│                   测试用例层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ YAML/JSON│  │Pytest用例│  │动态生成  │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│                   框架核心层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ 测试引擎 │  │ 断言引擎 │  │ 上下文   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ 解析引擎 │  │ 提取引擎 │  │ 钩子系统 │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│                   适配器层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │HTTP客户端│  │数据库客户端│ │通知客户端│         │
│  │(Requests)│  │ (MySQL)  │  │(多渠道)  │         │
│  │  (HTTPX) │  │(PostgreSQL)│          │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│                   基础设施层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ 日志系统 │  │ 配置管理 │  │ 异常处理 │         │
│  │(loguru)  │  │ (YAML)   │  │          │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ 测试报告 │  │ 通知系统 │  │ 工具库   │         │
│  │ (Allure) │  │(多渠道)  │  │          │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
```

### 架构特点

1. **分层清晰**：测试用例、框架核心、适配器、基础设施四层分离
2. **高内聚低耦合**：各模块职责单一，依赖关系明确
3. **可扩展性强**：支持插件式扩展，易于添加新功能
4. **易于维护**：代码结构清晰，便于理解和修改

---

## 核心模块设计

### 1. HTTP客户端模块 (client.py)

#### 设计目标

- 双HTTP客户端支持（Requests/HTTPX）
- 连接池管理
- 自动重试机制
- 统一接口封装

#### 类结构

```
BaseHTTPClient (抽象基类)
    ├── RequestsClient
    └── HTTPXClient

工厂方法: create_client(type, config) -> BaseHTTPClient
```

#### 核心方法

```python
class BaseHTTPClient:
    def request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        统一请求接口
        
        Returns:
            {
                'status_code': 200,
                'headers': {...},
                'body': {...},
                'text': '...',
                'elapsed': 1.234,
                'cookies': {...},
                'request': {...}
            }
        """
        pass
```

#### 设计亮点

- **抽象基类**：定义统一接口，便于切换实现
- **连接池**：自动管理HTTP连接，提高性能
- **重试策略**：自动重试失败请求，提高稳定性
- **统一响应格式**：标准化响应数据结构

---

### 2. 上下文管理模块 (context.py)

#### 设计目标

- 全局变量管理
- 局部变量管理
- 缓存变量管理
- 关联变量管理

#### 核心类

```python
class TestContext:
    # 全局变量（会话级）
    global_vars: Dict[str, Any]
    
    # 缓存变量（带TTL）
    cached_vars: Dict[str, tuple]  # {key: (value, expire_time)}
    
    # 局部变量（用例级）
    local_vars: Dict[str, Any]
    
    # 关联变量（从响应提取）
    extract_vars: Dict[str, Any]
    
    # 上一个响应
    last_response: Dict[str, Any]
```

#### 变量替换规则

```
${global_var}      # 全局变量
${local_var}       # 局部变量
${cache.key}       # 缓存变量
${$extract.key}    # 关联变量
```

#### 设计亮点

- **线程安全**：使用锁保护共享变量
- **递归替换**：支持嵌套数据结构的变量替换
- **过期机制**：缓存变量自动过期
- **隔离性**：局部变量用例间隔离

---

### 3. 解析器模块 (parser.py)

#### 设计目标

- YAML/JSON格式支持
- 自动数据校验
- 精准错误定位
- 测试用例生成

#### 数据结构

```python
@dataclass
class TestCase:
    # 基本信息
    name: str
    module: str
    description: Optional[str]
    priority: str  # p0/p1/p2/p3
    tags: List[str]
    
    # 请求信息
    method: str
    url: str
    headers: Dict[str, str]
    params: Dict[str, Any]
    body: Any
    files: Dict[str, str]
    
    # 验证
    validate: List[Dict]
    extract: Dict[str, Any]
    
    # 配置
    timeout: int
    skip: bool
    retry: int
```

#### 解析流程

```
文件读取 → 格式识别 → 数据校验 → 用例解析 → 对象构建
```

#### 设计亮点

- **多格式支持**：YAML/JSON统一接口
- **数据校验**：必填字段、类型检查
- **错误定位**：精确到字段和行号
- **灵活扩展**：支持自定义字段

---

### 4. 断言验证器模块 (validator.py)

#### 设计目标

- 多种断言类型
- 统一断言接口
- 详细失败信息
- 批量断言支持

#### 支持的断言类型

| 类型 | 说明 | 示例 |
|------|------|------|
| eq | 等于 | `{'type': 'eq', 'path': 'body.code', 'expected': 0}` |
| ne | 不等于 | `{'type': 'ne', 'path': 'body.data', 'expected': null}` |
| gt/gte | 大于/大于等于 | `{'type': 'gt', 'path': 'body.count', 'expected': 0}` |
| lt/lte | 小于/小于等于 | `{'type': 'lt', 'path': 'elapsed', 'expected': 1.0}` |
| in | 包含 | `{'type': 'in', 'path': 'body.status', 'expected': ['success', 'ok']}` |
| regex | 正则匹配 | `{'type': 'regex', 'path': 'body.email', 'pattern': '^[^@]+@[^@]+$'}` |
| json_schema | JSON Schema | `{'type': 'json_schema', 'schema': {...}}` |
| sql | SQL断言 | `{'type': 'sql', 'sql': 'SELECT COUNT(*) FROM users', 'expected': 10}` |
| type | 类型检查 | `{'type': 'type', 'path': 'body.data', 'expected': 'list'}` |
| length | 长度检查 | `{'type': 'length', 'path': 'body.list', 'min': 1, 'max': 100}` |
| status_code | 状态码 | `{'type': 'status_code', 'expected': 200}` |

#### 设计亮点

- **统一接口**：所有断言类型使用相同格式
- **路径提取**：支持JSONPath提取字段
- **详细结果**：包含实际值、期望值、错误详情
- **批量验证**：一次调用执行多个断言

---

### 5. 工具模块

#### 5.1 日志模块 (logger.py)

基于loguru的日志系统

```python
# 日志级别
TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL

# 日志输出
- 控制台输出（彩色）
- 文件输出（按日期）
- 错误日志单独记录
- 支持日志轮转
```

#### 5.2 数据提取器 (extractor.py)

支持多种提取方式

```python
# JSONPath提取
{'type': 'jsonpath', 'expression': '$.data.user_id'}

# 正则提取
{'type': 'regex', 'pattern': '"token":"([^"]+)"', 'group': 1}

# 响应头提取
{'type': 'header', 'header_name': 'X-Token'}

# Cookie提取
{'type': 'cookie', 'cookie_name': 'session_id'}

# XPath提取
{'type': 'xpath', 'xpath': '//div[@class="user-id"]/text()'}
```

#### 5.3 通知模块 (notifier.py)

支持多渠道通知

```
┌─────────────┐
│ Notification│
│  Manager    │
└──────┬──────┘
       │
   ┌───┴───┬──────┬──────┬──────┐
   │       │      │      │      │
   ▼       ▼      ▼      ▼      ▼
 DingTalk Feishu WeChat Email Other
```

---

## 数据流设计

### 1. 测试执行流程

```
┌──────────────┐
│ 读取配置文件  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 加载环境配置  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 解析测试数据  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 生成测试用例  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 执行前置钩子  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 变量替换     │
└──────┬───────┘
       ↓
┌──────────────┐
│ 发送HTTP请求  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 提取响应数据  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 执行断言验证  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 执行后置钩子  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 生成测试报告  │
└──────┬───────┘
       ↓
┌──────────────┐
│ 发送通知     │
└──────────────┘
```

### 2. 数据依赖流程

```
用例A: 用户登录
    ↓
    发送请求 → 获取响应
    ↓
    提取token: ${$extract.access_token}
    ↓
    存储到上下文

用例B: 获取用户信息（依赖用例A）
    ↓
    读取token: ${$extract.access_token}
    ↓
    设置请求头: Authorization: Bearer ${token}
    ↓
    发送请求 → 验证响应
```

---

## 扩展机制

### 1. 钩子系统

#### 钩子类型

```python
# 用例级钩子
before_testcase()    # 用例执行前
after_testcase()     # 用例执行后

# 步骤级钩子
before_request()     # 请求前
after_request()      # 请求后
before_assertion()   # 断言前
after_assertion()    # 断言后

# 会话级钩子
before_suite()       # 套件前
after_suite()        # 套件后
before_session()     # 会话前
after_session()      # 会话后
```

#### 自定义钩子示例

```python
# hooks/custom_hooks.py
def before_login():
    """登录前钩子"""
    # 清除旧token
    context().set_local('access_token', None)

def after_register(response):
    """注册后钩子"""
    # 自动登录
    username = response['body']['data']['username']
    # 执行登录逻辑...
```

### 2. 插件机制

```python
# pytest插件
@pytest.hookimpl
def pytest_collection_modifyitems(config, items):
    """修改测试用例集合"""
    # 自定义排序、过滤等
    pass

@pytest.hookimpl
def pytest_runtest_makereport(item, call):
    """生成测试报告"""
    # 自定义报告内容
    pass
```

### 3. 自定义断言

```python
from src.core.validator import Validator

class CustomValidator(Validator):
    def assert_custom_field(self, actual, expected):
        """自定义断言"""
        # 实现自定义断言逻辑
        return AssertionResult(...)
```

---

## 性能优化

### 1. 连接池管理

```python
# HTTP连接池
max_connections: 100
max_keepalive_connections: 20
```

### 2. 并发执行

```bash
# 使用pytest-xdist进行并发测试
pytest -n 4  # 4个worker并发执行
```

### 3. 数据缓存

```python
# 变量缓存（带TTL）
context.set_cache(key, value, ttl=3600)
```

### 4. 延迟加载

```python
# 测试数据按需加载
test_cases = parser.parse_file(file_path)
```

---

## 安全设计

### 1. 敏感信息保护

```yaml
# 环境变量
auth:
  token: ${AUTH_TOKEN}  # 从环境变量读取
```

### 2. SQL注入防护

```python
# 参数化查询
sql = "SELECT * FROM users WHERE id = %s"
params = [user_id]
```

### 3. HTTPS支持

```python
# SSL证书验证
response = http_client.request(
    url="https://api.example.com",
    verify=True  # 启用SSL验证
)
```

### 4. 请求头过滤

```python
# 日志中过滤敏感头
filtered_headers = ['Authorization', 'Cookie']
```

---

## 总结

本框架采用分层架构设计，核心模块职责明确，扩展机制完善，能够满足复杂的接口自动化测试需求。通过灵活的配置和丰富的功能，可以快速搭建一套稳定、高效的测试体系。
