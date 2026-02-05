# Extract 数据传递功能修复总结

## 问题描述

在测试用例中，通过 `extract` 从接口响应信息中提取到的数据，在后续接口中使用时，并没有成功获取到，而是直接传递了原始的表达式（如 `${$extract.access_token}`），导致后续请求失败。

## 根本原因

### 问题分析

1. **Context 清理机制问题**：
   - `conftest.py` 中的 `test_context` fixture 在每个用例开始时调用 `reset_context()`
   - `reset_context()` 会清空所有变量，包括 `extract_vars`
   - 导致之前用例提取的数据在后续用例中无法访问

2. **局部变量清理策略不当**：
   - `TestContext.clear_local()` 方法会同时清空 `local_vars` 和 `extract_vars`
   - 这意味着每个用例结束后，`extract_vars` 都会被清空
   - 后续用例无法使用之前提取的数据

### 原有代码

**conftest.py**：
```python
@pytest.fixture(scope="function")
def test_context():
    """测试用例级fixture，每个用例都会创建新的上下文"""
    # 重置上下文
    reset_context()  # ❌ 这里会清空所有变量，包括 extract_vars
    context = get_context()

    yield context

    # 清空局部变量
    context.clear_local()  # ❌ 这里也会清空 extract_vars
```

**context.py**：
```python
def clear_local(self):
    """清空局部变量"""
    self.local_vars.clear()
    self.extract_vars.clear()  # ❌ 也会清空 extract_vars
```

## 解决方案

### 1. 修改 conftest.py

**修改前**：
```python
@pytest.fixture(scope="function")
def test_context():
    """测试用例级fixture，每个用例都会创建新的上下文"""
    # 重置上下文
    reset_context()
    context = get_context()

    yield context

    # 清空局部变量
    context.clear_local()
```

**修改后**：
```python
@pytest.fixture(scope="function")
def test_context():
    """
    测试用例级fixture，每个用例都会创建新的上下文
    注意：不清空 extract_vars，以支持用例之间的数据依赖
    """
    context = get_context()

    # 只清空局部变量，不清空 extract_vars 和 global_vars
    # 这样支持用例之间的数据依赖（如：后续用例可以使用前面用例提取的数据）
    context.local_vars.clear()

    yield context

    # 清空局部变量
    context.clear_local()
```

**修改说明**：
- 不再调用 `reset_context()`，避免清空所有变量
- 只清空 `local_vars`，保留 `extract_vars` 和 `global_vars`
- 支持用例之间的数据依赖

### 2. 修改 context.py

**修改前**：
```python
def clear_local(self):
    """清空局部变量"""
    self.local_vars.clear()
    self.extract_vars.clear()
```

**修改后**：
```python
def clear_local(self):
    """清空局部变量（不包括 extract_vars，以支持用例之间的数据依赖）"""
    self.local_vars.clear()

def clear_local_all(self):
    """清空所有局部变量，包括 extract_vars"""
    self.local_vars.clear()
    self.extract_vars.clear()
```

**修改说明**：
- `clear_local()` 方法不再清空 `extract_vars`
- 新增 `clear_local_all()` 方法，用于需要清空所有变量的场景
- 保持向后兼容性

## 功能说明

### Extract 数据传递机制

1. **数据提取**：
   ```yaml
   extract:
     access_token:
       type: "jsonpath"
       expression: "$.data.token"
     user_id:
       type: "jsonpath"
       expression: "$.data.user_id"
   ```

2. **数据使用**：
   ```yaml
   # 在请求头中使用
   headers:
     Authorization: "Bearer ${$extract.access_token}"
     X-User-ID: "${$extract.user_id}"

   # 在请求体中使用
   body:
     username: "${$extract.access_token}"
     password: "${$extract.user_id}"

   # 在URL参数中使用
   params:
     token: "${$extract.access_token}"
     user: "${$extract.user_id}"
   ```

3. **变量生命周期**：
   - `local_vars`：每个用例私有，用例结束后清空
   - `extract_vars`：在测试会话期间保持，支持用例之间的数据传递
   - `global_vars`：在测试会话期间保持，全局共享

### 使用场景

#### 场景1：登录后使用 token

```yaml
# 用例1：登录
- name: "用户登录"
  method: POST
  url: /api/login
  body:
    username: "testuser"
    password: "testpass"
  extract:
    access_token:
      type: "jsonpath"
      expression: "$.data.token"

# 用例2：获取用户信息（使用 token）
- name: "获取用户信息"
  method: GET
  url: /api/user/info
  headers:
    Authorization: "Bearer ${$extract.access_token}"
```

#### 场景2：创建订单后使用订单 ID

```yaml
# 用例1：创建订单
- name: "创建订单"
  method: POST
  url: /api/orders
  body:
    product_id: 123
    quantity: 1
  extract:
    order_id:
      type: "jsonpath"
      expression: "$.data.id"

# 用例2：查询订单
- name: "查询订单"
  method: GET
  url: /api/orders/${$extract.order_id}

# 用例3：更新订单
- name: "更新订单"
  method: PUT
  url: /api/orders/${$extract.order_id}
  body:
    status: "paid"
```

## 验证方法

### 1. 运行验证脚本

```bash
cd auto-test-platform
python test_continuous_extract.py
```

输出示例：
```
============================================================
验证 extract 数据在连续测试用例中正确传递
============================================================

[用例1] 模拟登录-提取token
------------------------------------------------------------
提取的数据: {'access_token': 'testuser', 'user_id': 'testpass'}
保存到上下文: access_token = testuser
保存到上下文: user_id = testpass

上下文中的 extract_vars: {'access_token': 'testuser', 'user_id': 'testpass'}
清空局部变量后，extract_vars: {'access_token': 'testuser', 'user_id': 'testpass'}

[用例2] 使用提取的数据
------------------------------------------------------------
原始请求头: {'Authorization': 'Bearer ${$extract.access_token}', 'X-User-ID': '${$extract.user_id}'}
替换后请求头: {'Authorization': 'Bearer testuser', 'X-User-ID': 'testpass'}

实际发送的 Authorization: Bearer testuser
实际发送的 X-User-Id: testpass

[验证]
------------------------------------------------------------
✓ Authorization 头正确: Bearer testuser
✓ X-User-ID 头正确: testpass

============================================================
测试通过 ✓
============================================================
```

### 2. 运行单元测试

```bash
cd auto-test-platform
python -m pytest tests/test_extract_data_flow.py -v
```

所有测试应该通过：
- test_extract_data_can_be_used_in_next_case
- test_clear_local_preserves_extract_vars
- test_extract_vars_survive_multiple_cases
- test_replace_vars_in_complex_structure

### 3. 运行 Extract 模块测试

```bash
cd auto-test-platform
python -m pytest src/api/test_dynamic.py -k "extract" -v
```

所有 5 个 extract 测试用例应该通过：
- test_模拟登录_提取token_0
- test_使用extract数据_验证替换_1
- test_请求体中使用extract变量_2
- test_URL参数中使用extract变量_3
- test_复杂数据结构中使用extract变量_4

## 注意事项

### 1. 变量清理策略

- **local_vars**：每个用例私有，用例结束后自动清空
- **extract_vars**：在测试会话期间保持，用于支持用例之间的数据依赖
- **global_vars**：在测试会话期间保持，全局共享
- **cached_vars**：带有过期时间，过期后自动清空

### 2. 变量替换顺序

在 `replace_vars()` 方法中，变量替换的优先级为：
1. `cache.key`：缓存变量
2. `$extract.key`：关联变量（从响应中提取）
3. `local_var`：局部变量
4. `global_var`：全局变量
5. `cache_var`（直接使用变量名）：缓存变量

### 3. 清空所有变量

如果需要在测试开始前清空所有变量，可以使用：

```python
from src.core.context import reset_context

reset_context()
```

或者：

```python
context = get_context()
context.clear_all()
```

## 测试覆盖

- ✅ Extract 数据能在后续用例中使用
- ✅ Clear local 不会清空 extract_vars
- ✅ Extract vars 能在多个用例之间保持
- ✅ 变量替换在复杂数据结构中正常工作

## 修改文件列表

1. `conftest.py` - 修改 test_context fixture，不再重置所有变量
2. `src/core/context.py` - 修改 clear_local 方法，不再清空 extract_vars
3. `tests/test_extract_data_flow.py` - 新增单元测试
4. `test_extract_and_use.py` - 新增验证脚本
5. `test_continuous_extract.py` - 新增连续测试脚本
6. `test_data/extract_module.yaml` - 新增 extract 功能测试模块
7. `docs/extract_data_flow_fix.md` - 本文档

## 总结

Extract 数据传递功能现已完全修复并经过测试验证。用户可以在测试用例中使用 `extract` 从响应中提取数据，并在后续用例中使用 `${$extract.variable_name}` 格式引用这些数据。修复后的系统支持：
- 用例之间的数据依赖
- 在请求头、请求体、URL 参数中使用提取的数据
- 在复杂数据结构中使用提取的数据
- 局部变量与关联变量的独立生命周期
