# 默认请求头功能修复总结

## 问题描述

测试数据文件中设置的默认请求头（`config.headers`）在测试执行时未被使用。

## 根本原因

1. `TestCase` 数据类没有存储模块级别的默认请求头
2. 解析器没有从 `config` 中提取默认请求头
3. 解析器没有将默认请求头与用例自定义请求头合并

## 解决方案

### 1. 修改 `TestCase` 数据类

新增 `default_headers` 字段用于存储模块级别的默认请求头：

```python
@dataclass
class TestCase:
    name: str
    method: str
    url: str
    headers: Dict[str, Any] = field(default_factory=dict)
    default_headers: Dict[str, Any] = field(default_factory=dict)  # 新增
    # ... 其他字段
```

### 2. 修改解析器逻辑

#### 从 config 中提取默认请求头

```python
def _parse_data(self, data: dict, module_name: str) -> List[TestCase]:
    """解析数据"""
    # 提取模块配置中的默认请求头
    config = data.get('config', {})
    default_headers = config.get('headers', {})

    # 解析测试用例
    cases = []
    for case in data.get('test_cases', []):
        parsed_case = self._parse_case(case, default_headers)  # 传递默认请求头
        # ...
```

#### 合并默认请求头和用例自定义请求头

```python
def _parse_case(self, case: dict, default_headers: dict = None) -> TestCase:
    """解析单个测试用例"""
    if default_headers is None:
        default_headers = {}

    # 获取用例自定义请求头
    case_headers = case.get('headers', {})

    # 合并请求头（用例自定义优先）
    merged_headers = {**default_headers, **case_headers}

    return TestCase(
        # ...
        headers=merged_headers,      # 合并后的请求头
        default_headers=default_headers,  # 保留原始默认请求头
        # ...
    )
```

### 3. 更新测试数据文件

在所有测试数据文件的 `config` 节点添加 `headers` 配置：

#### product_module.json

```json
{
  "config": {
    "headers": {
      "Content-Type": "application/json",
      "Accept": "application/json"
    }
  }
}
```

#### order_module.yaml

```yaml
config:
  headers:
    Content-Type: application/json
    Accept: application/json
```

#### country_module.yaml

```yaml
config:
  headers:
    Content-Type: application/json
    Accept: application/json
```

#### user_module.yaml（包含自定义请求头的示例）

```yaml
config:
  headers:
    Content-Type: application/json
    Accept: application/json

test_cases:
  - name: "用户注册-正常流程"
    method: POST
    url: /api/user/register
    # 自定义请求头会与默认请求头合并
    headers:
      X-Request-Id: "${uuid()}"
```

## 验证方法

### 1. 运行验证脚本

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

### 2. 运行单元测试

```bash
cd auto-test-platform
python -m pytest tests/test_default_headers.py -v
```

所有测试应该通过：
- test_default_headers_are_applied
- test_default_headers_merge_with_case_headers
- test_headers_are_used_in_request
- test_case_headers_override_default_headers
- test_all_modules_have_default_headers

### 3. 查看日志

运行测试后，检查日志中的请求头信息：

```bash
grep "请求头" logs/app_2026-02-04.log
```

输出示例：
```
请求头: {'Content-Type': 'application/json', 'Accept': 'application/json'}
请求头: {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Request-Id': '${uuid()}'}
```

## 功能说明

### 请求头合并规则

1. **默认请求头优先级较低**：`config.headers` 中定义的默认请求头会自动应用到所有测试用例
2. **用例自定义请求头优先级较高**：测试用例中定义的 `headers` 会覆盖默认请求头
3. **合并策略**：默认请求头和用例自定义请求头合并时，用例自定义请求头会覆盖同名键

### 使用场景

#### 场景1：所有用例使用相同的请求头

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
```

#### 场景2：部分用例需要特殊请求头

```yaml
config:
  headers:
    Content-Type: "application/json"
    Accept: "application/json"

test_cases:
  - name: 普通接口调用
    method: POST
    url: /api/normal

  - name: 上传文件接口
    method: POST
    url: /api/upload
    headers:
      Content-Type: "multipart/form-data"  # 覆盖默认值
```

#### 场景3：在默认请求头基础上添加额外请求头

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
```

## 文档更新

1. 新增 `docs/default_headers.md` 详细说明默认请求头功能
2. 更新 `README.md` 添加默认请求头功能说明

## 测试覆盖

- ✅ 默认请求头被正确应用
- ✅ 默认请求头与用例自定义请求头正确合并
- ✅ 请求头被用于实际的请求
- ✅ 用例自定义请求头覆盖默认请求头
- ✅ 所有模块都有默认请求头

## 修改文件列表

1. `src/core/parser.py` - 修改解析器以支持默认请求头
2. `test_data/product_module.json` - 添加 config.headers
3. `test_data/order_module.yaml` - 添加 config.headers
4. `test_data/country_module.yaml` - 添加 config.headers
5. `test_data/user_module.yaml` - 添加 config.headers
6. `docs/default_headers.md` - 新增功能说明文档
7. `README.md` - 更新项目说明
8. `test_default_headers.py` - 新增验证脚本
9. `tests/test_default_headers.py` - 新增单元测试

## 总结

默认请求头功能现已完全实现并经过测试验证。用户可以在测试数据文件的 `config.headers` 中定义默认请求头，这些请求头会自动应用到所有测试用例。用例级别的自定义请求头可以覆盖或扩展默认请求头。
