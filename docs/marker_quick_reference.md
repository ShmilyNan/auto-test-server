# Marker 优化快速参考指南

## 快速开始

### 查看所有 markers

```bash
python -m pytest --markers
```

### 查看配置

```bash
python -m pytest --help
```

## 常用命令

### 1. 按模块筛选

```bash
# 运行用户模块的所有测试
python -m pytest src/api/test_dynamic.py -k "user_module" -v

# 运行商品模块的所有测试
python -m pytest src/api/test_dynamic.py -k "product_module" -v

# 运行多个模块
python -m pytest src/api/test_dynamic.py -k "user_module or product_module" -v
```

### 2. 按 marker 筛选

```bash
# 运行冒烟测试
python -m pytest -m smoke -v

# 运行 P0 级用例
python -m pytest -m p0 -v

# 运行 API 测试
python -m pytest -m api -v

# 运行正向测试
python -m pytest -m positive -v
```

### 3. 组合筛选

```bash
# 用户模块 + P0 级用例
python -m pytest src/api/test_dynamic.py -k "user_module and p0" -v

# 用户模块 + 冒烟测试
python -m pytest src/api/test_dynamic.py -k "user_module" -m smoke -v

# 商品模块 + 正向测试
python -m pytest src/api/test_dynamic.py -k "product_module and positive" -v

# 排除慢速测试
python -m pytest -m "not slow" -v
```

### 4. 运行所有测试

```bash
# 运行所有测试
python -m pytest src/api/test_dynamic.py -v

# 或
python -m pytest -v
```

## Markers 列表

### 功能分类

- `@pytest.mark.smoke` - 冒烟测试（核心功能测试）
- `@pytest.mark.regression` - 回归测试（完整回归）
- `@pytest.mark.daily` - 每日巡检测试

### 优先级分类

- `@pytest.mark.p0` - P0级用例（核心业务，必须通过）
- `@pytest.mark.p1` - P1级用例（重要功能）
- `@pytest.mark.p2` - P2级用例（一般功能）
- `@pytest.mark.p3` - P3级用例（边缘功能）

### 测试类型分类

- `@pytest.mark.api` - API接口测试
- `@pytest.mark.sql` - SQL数据库测试
- `@pytest.mark.extract` - 数据提取测试
- `@pytest.mark.cleanup` - 数据清洗测试
- `@pytest.mark.performance` - 性能测试
- `@pytest.mark.database` - 数据库相关测试
- `@pytest.mark.file` - 文件上传下载测试

### 测试结果分类

- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.skip` - 跳过此测试
- `@pytest.mark.xfail` - 预期失败

### 正负向分类

- `@pytest.mark.positive` - 正向测试（验证功能正常）
- `@pytest.mark.negative` - 负向测试（验证异常处理）

### 自定义标记

- `@pytest.mark.tag` - 通用标记（使用方式：`@pytest.mark.tag('custom-tag')`）

## YAML 配置示例

### 定义模块信息

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
    # ...
```

### 使用 marker

```yaml
test_cases:
  - name: "用户登录"
    markers:
      - smoke
      - positive
    # ...
```

## pyproject.toml 配置

### Pytest 配置

```toml
[tool.pytest.ini_options]
testpaths = ["src/api"]
addopts = ["-v", "-s", "--strict-markers"]
markers = [
    "smoke: 冒烟测试",
    # ...
]
```

### 运行测试

```bash
# 使用 pyproject.toml 配置运行
python -m pytest -v

# 查看配置
python -m pytest --help
```

## 常见场景

### 发布前验证

```bash
# 运行所有冒烟测试
python -m pytest -m smoke -v

# 运行所有 P0 级用例
python -m pytest -m p0 -v
```

### 模块开发测试

```bash
# 开发用户模块时，只运行用户模块的测试
python -m pytest src/api/test_dynamic.py -k "user_module" -v
```

### Bug 修复验证

```bash
# 修复某个 Bug 后，只运行相关的测试用例
python -m pytest src/api/test_dynamic.py -k "user_login" -v
```

### 回归测试

```bash
# 运行所有回归测试
python -m pytest -m regression -v

# 运行所有 P0 和 P1 级用例
python -m pytest -m "p0 or p1" -v
```

## 性能测试

```bash
# 运行性能测试
python -m pytest -m performance -v

# 排除慢速测试
python -m pytest -m "not slow" -v
```

## 注意事项

1. **模块命名规范**：使用有意义的模块名称，如 `user_module`、`product_module`
2. **Marker 选择**：按照功能和优先级选择合适的 marker
3. **组合使用**：灵活使用 `-k` 参数和 marker 组合筛选
4. **配置验证**：定期验证 pyproject.toml 配置是否正确

## 帮助命令

```bash
# 查看所有 markers
python -m pytest --markers

# 查看 pytest 帮助
python -m pytest --help

# 收集但不执行测试
python -m pytest --collect-only

# 查看测试版本
python -m pytest --version
```

## 相关文档

- [Marker 优化方案与使用指南](./marker_optimization_guide.md)
- [模块信息定义示例](./module_info_definition.md)
- [Marker 优化总结](./marker_optimization_summary.md)
