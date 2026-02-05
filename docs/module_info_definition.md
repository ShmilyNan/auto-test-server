# 模块信息定义示例

本文档展示如何在测试数据文件中定义模块信息，以及如何使用 pytest 的 `-k` 参数按模块筛选测试用例。

## 1. 定义模块信息

在 YAML 测试数据文件中，在文件顶部定义 `module_name` 和 `module_desc` 字段：

### 示例 1：用户模块

```yaml
# test_data/user_module.yaml

module_name: "user_module"
module_desc: "用户模块测试"

test_cases:
  - name: "用户登录"
    priority: p0
    tags:
      - smoke
      - positive
    method: POST
    url: /api/users/login
    body:
      username: test_user
      password: test_password
    extract:
      access_token: "$.data.token"
    validate:
      - eq: ["status_code", 200]
      - eq: ["$.code", 0]

  - name: "获取用户信息"
    priority: p1
    tags:
      - positive
    method: GET
    url: /api/users/info
    headers:
      Authorization: "Bearer ${extract.access_token}"
    validate:
      - eq: ["status_code", 200]
```

### 示例 2：商品模块

```yaml
# test_data/product_module.yaml

module_name: "product_module"
module_desc: "商品模块测试"

test_cases:
  - name: "获取商品列表"
    priority: p0
    tags:
      - smoke
      - positive
    method: GET
    url: /api/products
    params:
      page: 1
      page_size: 10
    validate:
      - eq: ["status_code", 200]
      - eq: ["$.code", 0]

  - name: "创建商品"
    priority: p1
    tags:
      - positive
    method: POST
    url: /api/products
    body:
      name: "测试商品"
      price: 99.99
      stock: 100
    validate:
      - eq: ["status_code", 201]
```

### 示例 3：数据清洗模块

```yaml
# test_data/cleanup_module.yaml

module_name: "cleanup_module"
module_desc: "数据清洗模块测试"

test_cases:
  - name: "创建数据-使用API清洗"
    priority: p1
    tags:
      - cleanup
      - positive
    method: POST
    url: /api/data
    body:
      name: "测试数据"
    extract:
      data_id: "$.data.id"
    cleanup:
      enabled: true
      type: "api"
      api:
        method: DELETE
        url: "/api/data/${extract.data_id}"
    validate:
      - eq: ["status_code", 201]
```

### 示例 4：订单模块

```yaml
# test_data/order_module.yaml

module_name: "order_module"
module_desc: "订单模块测试"

test_cases:
  - name: "创建订单"
    priority: p0
    tags:
      - smoke
      - positive
    method: POST
    url: /api/orders
    body:
      product_id: 123
      quantity: 2
    extract:
      order_id: "$.data.id"
    validate:
      - eq: ["status_code", 201]

  - name: "查询订单"
    priority: p1
    tags:
      - positive
    method: GET
    url: /api/orders/${extract.order_id}
    validate:
      - eq: ["status_code", 200]
```

## 2. 模块命名规范

建议使用以下命名规范：

| 模块名称 | 说明 |
|---------|------|
| `user_module` | 用户模块 |
| `product_module` | 商品模块 |
| `order_module` | 订单模块 |
| `payment_module` | 支付模块 |
| `cleanup_module` | 数据清洗模块 |
| `extract_module` | 数据提取模块 |
| `auth_module` | 认证模块 |
| `search_module` | 搜索模块 |
| `report_module` | 报表模块 |
| `config_module` | 配置模块 |

## 3. 使用 `-k` 参数按模块筛选

### 3.1 运行单个模块的所有测试用例

```bash
# 运行用户模块的所有测试
python -m pytest src/api/test_dynamic.py -k "user_module" -v

# 运行商品模块的所有测试
python -m pytest src/api/test_dynamic.py -k "product_module" -v

# 运行订单模块的所有测试
python -m pytest src/api/test_dynamic.py -k "order_module" -v
```

### 3.2 运行多个模块的测试用例

```bash
# 运行用户模块或商品模块的测试
python -m pytest src/api/test_dynamic.py -k "user_module or product_module" -v

# 运行用户模块、商品模块和订单模块的测试
python -m pytest src/api/test_dynamic.py -k "user_module or product_module or order_module" -v
```

### 3.3 组合筛选条件

```bash
# 运行用户模块的 P0 级用例
python -m pytest src/api/test_dynamic.py -k "user_module and p0" -v

# 运行商品模块的正向测试
python -m pytest src/api/test_dynamic.py -k "product_module and positive" -v

# 运行订单模块的冒烟测试
python -m pytest src/api/test_dynamic.py -k "order_module and smoke" -v

# 排除慢速测试
python -m pytest src/api/test_dynamic.py -k "user_module and not slow" -v
```

### 3.4 按模块名称模糊匹配

```bash
# 运行所有包含 "user" 的模块
python -m pytest src/api/test_dynamic.py -k "user" -v

# 运行所有包含 "module" 的模块
python -m pytest src/api/test_dynamic.py -k "module" -v
```

## 4. 使用 marker 运行特定类型的测试

### 4.1 按功能分类运行

```bash
# 运行所有冒烟测试
python -m pytest -m smoke -v

# 运行所有回归测试
python -m pytest -m regression -v

# 运行所有每日巡检测试
python -m pytest -m daily -v
```

### 4.2 按优先级运行

```bash
# 运行所有 P0 级用例
python -m pytest -m p0 -v

# 运行所有 P1 级用例
python -m pytest -m p1 -v

# 运行所有 P0 和 P1 级用例
python -m pytest -m "p0 or p1" -v
```

### 4.3 按测试类型运行

```bash
# 运行所有 API 测试
python -m pytest -m api -v

# 运行所有 SQL 测试
python -m pytest -m sql -v

# 运行所有数据清洗测试
python -m pytest -m cleanup -v

# 运行所有数据提取测试
python -m pytest -m extract -v
```

### 4.4 按正负向运行

```bash
# 运行所有正向测试
python -m pytest -m positive -v

# 运行所有负向测试
python -m pytest -m negative -v
```

## 5. 组合使用 marker 和 `-k` 参数

```bash
# 运行用户模块的冒烟测试
python -m pytest src/api/test_dynamic.py -k "user_module" -m smoke -v

# 运行商品模块的 P0 级用例
python -m pytest src/api/test_dynamic.py -k "product_module" -m p0 -v

# 运行订单模块的正向测试
python -m pytest src/api/test_dynamic.py -k "order_module" -m positive -v
```

## 6. 实际使用场景

### 场景 1：冒烟测试（发布前验证）

```bash
# 运行所有模块的冒烟测试
python -m pytest -m smoke -v

# 只运行核心模块的冒烟测试
python -m pytest src/api/test_dynamic.py -k "user_module or product_module or order_module" -m smoke -v
```

### 场景 2：回归测试（完整验证）

```bash
# 运行所有回归测试
python -m pytest -m regression -v

# 运行所有 P0 和 P1 级用例（核心功能验证）
python -m pytest -m "p0 or p1" -v
```

### 场景 3：模块开发测试

```bash
# 开发用户模块时，只运行用户模块的测试
python -m pytest src/api/test_dynamic.py -k "user_module" -v

# 开发商品模块时，只运行商品模块的测试
python -m pytest src/api/test_dynamic.py -k "product_module" -v
```

### 场景 4：Bug 修复验证

```bash
# 修复某个 Bug 后，只运行相关的测试用例
python -m pytest src/api/test_dynamic.py -k "user_login" -v
```

### 场景 5：性能测试

```bash
# 运行性能测试
python -m pytest -m performance -v

# 排除慢速测试
python -m pytest -m "not slow" -v
```

## 7. 在 Allure 报告中显示模块信息

### 7.1 在测试代码中设置模块信息

修改 `src/api/test_dynamic.py`，添加模块信息到 Allure 报告：

```python
import allure

# 在测试函数中
def test_dynamic_test(test_data, request):
    # 读取模块信息
    module_name = test_data.get("module_name", "unknown")
    module_desc = test_data.get("module_desc", "")

    # 添加到 Allure 报告
    allure.dynamic.parameter("module", module_name)
    if module_desc:
        allure.dynamic.description(f"{module_desc}\n\n{test_data.get('name', '')}")

    # ... 测试逻辑
```

### 7.2 在 Allure 报告中按模块筛选

```bash
# 生成 Allure 报告
python -m pytest src/api/test_dynamic.py -k "user_module" --alluredir=reports/allure

# 在 Allure 报告中按模块筛选
allure serve reports/allure

# 或生成 HTML 报告
allure generate reports/allure -o reports/allure-report --clean
```

## 8. 最佳实践

1. **始终定义模块名称**：在所有 YAML 文件中定义 `module_name` 字段
2. **使用有意义的模块名称**：遵循命名规范，便于理解和筛选
3. **合理使用 marker**：按照功能和优先级划分 marker，而不是按模块划分
4. **组合使用筛选条件**：灵活使用 `-k` 参数和 marker 组合筛选
5. **编写清晰的模块描述**：在 `module_desc` 中简要描述模块的功能
6. **定期清理无用模块**：删除不再使用的模块和测试用例

## 9. 常见问题

### Q1: 如何知道当前有哪些模块？

**A**: 查看所有测试数据文件，或者运行以下命令：

```bash
# 收集所有测试用例，查看模块信息
python -m pytest src/api/test_dynamic.py --collect-only -v
```

### Q2: 如何运行所有测试用例？

**A**:

```bash
# 运行所有测试用例
python -m pytest src/api/test_dynamic.py -v

# 或使用 marker 运行所有测试
python -m pytest -v
```

### Q3: 如何跳过某些模块的测试？

**A**:

```bash
# 跳过用户模块的测试
python -m pytest src/api/test_dynamic.py -k "not user_module" -v

# 跳过用户模块和商品模块的测试
python -m pytest src/api/test_dynamic.py -k "not (user_module or product_module)" -v
```

### Q4: 如何按测试用例名称筛选？

**A**:

```bash
# 运行名称包含 "login" 的测试用例
python -m pytest src/api/test_dynamic.py -k "login" -v

# 运行名称包含 "create" 的测试用例
python -m pytest src/api/test_dynamic.py -k "create" -v
```

## 总结

通过在 YAML 测试数据中定义模块信息，并使用 pytest 的 `-k` 参数筛选测试用例，可以实现：

1. ✅ **灵活的模块筛选**：按模块名称筛选测试用例
2. ✅ **简洁的 marker 配置**：不需要为每个模块单独注册 marker
3. ✅ **易于维护**：模块信息集中管理，易于维护和扩展
4. ✅ **更好的可读性**：模块信息清晰明了，易于理解
5. ✅ **高效的测试执行**：只运行相关的测试用例，提高测试效率

详见 `docs/marker_optimization_guide.md` 了解更多关于 marker 优化的信息。
