# Marker 优化方案与使用指南

## 问题背景

### 原有方案的问题

在原有的 pytest.ini 配置中，每个测试模块都需要注册对应的 marker：

```ini
markers =
    module_user_module: 用户模块测试
    module_product_module: 商品模块测试
    module_country_module: 国家模块测试
    module_cleanup_module: 数据清洗模块测试
    module_extract_module: 数据提取模块测试
    # ... 每新增一个模块就要添加一个 marker
```

**存在的问题**：
- ❌ 随着测试用例增加，配置文件会变得非常臃肿
- ❌ 维护成本高，每次新增模块都要修改配置
- ❌ markers 数量不可控，容易混乱

## 优化方案

### 核心思想

1. **只保留核心的 marker 类型**：按功能、优先级、测试类型分类，而不是按每个模块单独注册
2. **使用 `-k` 参数按模块筛选**：通过 pytest 的 `-k` 参数筛选特定模块的测试用例
3. **在 YAML 配置中定义模块信息**：使用自定义字段管理模块、标签等信息

### 优化后的 Markers

```toml
markers = [
    # 功能分类
    "smoke: 冒烟测试（核心功能测试）",
    "regression: 回归测试（完整回归）",
    "daily: 每日巡检测试",

    # 优先级分类
    "p0: P0级用例（核心业务，必须通过）",
    "p1: P1级用例（重要功能）",
    "p2: P2级用例（一般功能）",
    "p3: P3级用例（边缘功能）",

    # 测试类型分类
    "api: API接口测试",
    "sql: SQL数据库测试",
    "extract: 数据提取测试",
    "cleanup: 数据清洗测试",
    "performance: 性能测试",

    # 测试结果分类
    "slow: 慢速测试",
    "skip: 跳过此测试",
    "xfail: 预期失败",

    # 正负向分类
    "positive: 正向测试（验证功能正常）",
    "negative: 负向测试（验证异常处理）",

    # 自定义标记
    "tag: 通用标记，可用于自定义分类",
]
```

**优势**：
- ✅ markers 数量可控（从 28 个减少到 ~15 个）
- ✅ 不会随着测试用例增加而臃肿
- ✅ 易于维护和理解
- ✅ 灵活性更高

## 使用方式

### 1. 在 YAML 配置中定义模块信息

在测试数据文件中定义模块名称和标签：

```yaml
# test_data/user_module.yaml
module_name: "user_module"
module_desc: "用户模块测试"

test_cases:
  - name: "用户登录"
    method: POST
    url: /api/users/login
    # ...

# test_data/product_module.yaml
module_name: "product_module"
module_desc: "商品模块测试"

test_cases:
  - name: "获取商品列表"
    method: GET
    url: /api/products
    # ...
```

### 2. 在测试代码中读取模块信息

在 `src/api/test_dynamic.py` 中读取模块名称：

```python
# 从 YAML 配置中读取模块名称
module_name = test_data.get("module_name", "unknown")
module_desc = test_data.get("module_desc", "")

# 设置自定义属性
request.node.add_marker(pytest.mark.module(module_name))
```

### 3. 使用 `-k` 参数按模块筛选

**运行特定模块的所有测试用例**：

```bash
# 运行用户模块的所有测试
python -m pytest src/api/test_generator.py -k "user_module" -v

# 运行商品模块的所有测试
python -m pytest src/api/test_generator.py -k "product_module" -v

# 运行数据清洗模块的所有测试
python -m pytest src/api/test_generator.py -k "cleanup_module" -v
```

### 4. 组合筛选条件

```bash
# 运行用户模块的 P0 级用例
python -m pytest src/api/test_generator.py -k "user_module and p0" -v

# 运行冒烟测试中的 API 测试
python -m pytest src/api/test_generator.py -k "smoke and api" -v

# 排除慢速测试
python -m pytest src/api/test_generator.py -k "not slow" -v

# 运行正向测试
python -m pytest src/api/test_generator.py -k "positive" -v
```

### 5. 使用 marker 运行特定类型的测试

```bash
# 运行所有冒烟测试
python -m pytest -m smoke -v

# 运行所有 P0 级用例
python -m pytest -m p0 -v

# 运行所有 API 测试
python -m pytest -m api -v

# 运行所有正向测试
python -m pytest -m positive -v

# 组合标记：运行冒烟测试中的 P0 级用例
python -m pytest -m "smoke and p0" -v

# 排除慢速测试
python -m pytest -m "not slow" -v
```

## 自定义标记使用

### 1. 使用 tag 标记

```yaml
test_cases:
  - name: "用户登录"
    method: POST
    url: /api/users/login
    markers:
      - "tag:auth"
      - "tag:critical"
    # ...
```

运行：

```bash
# 运行所有带有 auth 标签的测试
python -m pytest -m "tag(auth)" -v

# 运行所有带有 critical 标签的测试
python -m pytest -m "tag(critical)" -v
```

### 2. 在代码中添加自定义标记

```python
# test_generator.py

@pytest.mark.tag("custom-tag")
def test_example():
    pass
```

## pyproject.toml 配置

### 配置结构

```toml
[tool.pytest.ini_options]
# 测试用例目录
testpaths = ["src/api"]

# 测试文件模式
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 命令行选项
addopts = [
    "-v",
    "-s",
    "--strict-markers",
    "--tb=short",
    "--alluredir=reports/allure",
    "--clean-alluredir",
]

# 标记定义
markers = [
    "smoke: 冒烟测试",
    "regression: 回归测试",
    # ...
]
```

### 迁移步骤

1. **创建 pyproject.toml 文件**
2. **将 pytest.ini 的配置迁移到 pyproject.toml**
3. **删除或备份 pytest.ini 文件**
4. **验证配置是否正常工作**

### 验证配置

```bash
# 查看配置
python -m pytest --help

# 查看所有标记
python -m pytest --markers

# 运行测试
python -m pytest -v
```

## 最佳实践

### 1. 模块命名规范

使用有意义的模块名称，便于筛选：

```
user_module          - 用户模块
product_module       - 商品模块
order_module         - 订单模块
payment_module       - 支付模块
cleanup_module       - 数据清洗模块
extract_module       - 数据提取模块
```

### 2. 标记使用规范

- **smoke**：核心功能，每次发布前必须测试
- **regression**：完整回归测试，包含所有功能点
- **daily**：每日巡检，验证系统基本功能
- **p0/p1/p2/p3**：按优先级划分，p0 最高
- **api/sql/extract/cleanup**：按测试类型划分
- **positive/negative**：按正负向测试划分

### 3. 组合使用

```bash
# 冒烟测试 + P0 级用例
python -m pytest -m "smoke and p0" -v

# 用户模块 + 正向测试
python -m pytest -k "user_module and positive" -v

# 排除慢速测试 + API 测试
python -m pytest -m "api and not slow" -v
```

## 对比：pytest.ini vs pyproject.toml

| 特性 | pytest.ini | pyproject.toml |
|------|-----------|----------------|
| 配置位置 | 单独文件 | 项目根目录，与其他配置统一 |
| 格式 | INI 格式 | TOML 格式 |
| 可读性 | 一般 | 更好（支持层级结构） |
| 生态兼容 | 仅 pytest | 可集成 Black、Flake8、MyPy 等 |
| 推荐程度 | 传统方式 | 现代推荐方式 |

## 常见问题

### Q1: 为什么不继续使用 module_* markers？

**A**: module_* markers 会导致 markers 数量不可控，随着测试用例增加，配置文件会变得臃肿，维护成本高。使用 `-k` 参数筛选模块更加灵活和高效。

### Q2: 如何运行多个模块的测试？

**A**: 使用 `-k` 参数的 or 逻辑：

```bash
# 运行用户模块或商品模块的测试
python -m pytest -k "user_module or product_module" -v
```

### Q3: 如何在 Allure 报告中显示模块信息？

**A**: 在测试代码中设置自定义属性：

```python
# 在测试函数中
request.node.add_marker(pytest.mark.module(module_name))

# 在 teardown 中
allure.attach(module_name, name="Module", attachment_type=allure.attachment_type.TEXT)
```

### Q4: 旧的 pytest.ini 可以继续使用吗？

**A**: 可以。pytest 会同时读取 pytest.ini 和 pyproject.toml 中的配置，如果两者有冲突，pytest.ini 的优先级更高。建议迁移后删除或重命名 pytest.ini。

### Q5: 如何添加新的 marker 类型？

**A**: 在 pyproject.toml 中添加新的 marker 定义：

```toml
[tool.pytest.ini_options]
markers = [
    # ... 现有 markers
    "security: 安全测试",
    "ui: UI测试",
]
```

## 总结

通过优化 marker 注册方式和迁移到 pyproject.toml，我们实现了：

1. ✅ **配置文件更简洁**：markers 数量从 28 个减少到 ~15 个
2. ✅ **维护成本更低**：不需要为每个新增模块注册 marker
3. ✅ **灵活性更高**：可以使用 `-k` 参数灵活筛选测试用例
4. ✅ **配置更现代化**：使用 pyproject.toml 统一管理项目配置
5. ✅ **生态兼容性更好**：可以集成更多工具的配置

## 迁移检查清单

- [ ] 创建 pyproject.toml 文件
- [ ] 迁移 pytest 配置到 pyproject.toml
- [ ] 优化 markers 定义（移除 module_* markers）
- [ ] 更新测试代码，从 YAML 读取模块信息
- [ ] 删除或备份 pytest.ini
- [ ] 运行测试验证配置是否正常
- [ ] 更新项目文档
- [ ] 通知团队成员配置变更
