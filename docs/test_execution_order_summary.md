# 测试用例执行顺序控制功能 - 实现总结

## 功能需求

支持测试用例执行顺序的灵活控制：
1. **默认执行顺序**：测试用例按文件中的定义顺序（从上往下）执行
2. **自定义执行顺序**：可以通过 `order` 字段设置特定用例的执行顺序
3. **混合模式**：已设置 `order` 的用例按设置的顺序执行，未设置 `order` 的用例按文件顺序执行

## 实现方案

### 1. 数据结构扩展

在 `TestCase` 数据类中添加 `order` 字段：

```python
@dataclass
class TestCase:
    # ... 其他字段
    order: Optional[int] = None  # 执行顺序（未设置时自动按文件顺序）
```

### 2. 自动分配逻辑

实现 `_assign_order` 方法，为未设置 `order` 的用例自动分配顺序：

```python
def _assign_order(self, test_cases: List[TestCase], module: str) -> List[TestCase]:
    """为未设置 order 的用例自动分配顺序"""
    # 收集已设置的 order 值
    existing_orders = set()
    for case in test_cases:
        if case.order is not None:
            existing_orders.add(case.order)

    # 为未设置 order 的用例分配 order（按文件顺序）
    current_order = 0
    for case in test_cases:
        if case.order is None:
            # 跳过已存在的 order 值
            while current_order in existing_orders:
                current_order += 1

            case.order = current_order
            logger.debug(f"用例 '{case.name}' 自动分配 order: {current_order}")
            existing_orders.add(current_order)
            current_order += 1

    return test_cases
```

### 3. 排序逻辑

在 `_parse_data` 方法中，为所有用例分配 `order` 后，按 `order` 排序：

```python
# 自动为未设置 order 的用例分配顺序
test_cases = self._assign_order(test_cases, module)

# 按 order 排序
test_cases.sort(key=lambda x: x.order)
```

### 4. 标记应用

在 `test_dynamic.py` 中，为生成的测试函数添加 pytest-order 标记：

```python
# 添加执行顺序标记（优先级最高）
if test_case.order is not None:
    try:
        # 使用 pytest-order 插件的标记
        test_func = pytest.mark.order(test_case.order)(test_func)
    except:
        pass
```

## 使用示例

### 示例1：默认执行顺序

```yaml
test_cases:
  - name: 测试用例_创建订单
    method: POST
    url: /api/orders

  - name: 测试用例_查询订单
    method: GET
    url: /api/orders/1

  - name: 测试用例_更新订单
    method: PUT
    url: /api/orders/1
```

**执行顺序**：
1. 测试用例_创建订单 (order=0, 自动分配)
2. 测试用例_查询订单 (order=1, 自动分配)
3. 测试用例_更新订单 (order=2, 自动分配)

### 示例2：自定义执行顺序

```yaml
test_cases:
  - name: 测试用例_创建订单
    order: 1
    method: POST
    url: /api/orders

  - name: 测试用例_删除订单
    order: 100
    method: DELETE
    url: /api/orders/1

  - name: 测试用例_查询订单
    order: 2
    method: GET
    url: /api/orders/1
```

**执行顺序**：
1. 测试用例_创建订单 (order=1)
2. 测试用例_查询订单 (order=2)
...
100. 测试用例_删除订单 (order=100)

### 示例3：混合模式

```yaml
test_cases:
  - name: 测试用例_创建订单
    method: POST
    url: /api/orders

  - name: 测试用例_查询订单
    method: GET
    url: /api/orders/1

  - name: 测试用例_更新订单
    method: PUT
    url: /api/orders/1

  - name: 测试用例_查询订单详情
    method: GET
    url: /api/orders/1/details

  - name: 测试用例_评价订单
    method: POST
    url: /api/orders/1/review

  - name: 测试用例_取消订单
    order: 50
    method: POST
    url: /api/orders/1/cancel

  - name: 测试用例_支付订单
    order: 100
    method: POST
    url: /api/orders/1/pay

  - name: 测试用例_申请退款
    order: 150
    method: POST
    url: /api/orders/1/refund

  - name: 测试用例_删除订单
    order: 200
    method: DELETE
    url: /api/orders/1
```

**执行顺序**：
1. 测试用例_创建订单 (order=0, 自动分配)
2. 测试用例_查询订单 (order=1, 自动分配)
3. 测试用例_更新订单 (order=2, 自动分配)
4. 测试用例_查询订单详情 (order=3, 自动分配)
5. 测试用例_评价订单 (order=4, 自动分配)
...
50. 测试用例_取消订单 (order=50, 用户设置)
...
100. 测试用例_支付订单 (order=100, 用户设置)
...
150. 测试用例_申请退款 (order=150, 用户设置)
...
200. 测试用例_删除订单 (order=200, 用户设置)

## 验证结果

### 测试用例收集

```bash
$ python -m pytest src/api/test_generator.py --collect-only
collected 28 items
        <Function test_测试用例_创建订单_0>
        <Function test_测试用例_查询订单_1>
        <Function test_测试用例_更新订单_2>
        <Function test_测试用例_查询订单详情_3>
        <Function test_测试用例_评价订单_4>
        <Function test_测试用例_取消订单_5>
        <Function test_测试用例_支付订单_6>
        <Function test_测试用例_申请退款_7>
        <Function test_测试用例_删除订单_8>
```

### order 值分配

```bash
$ python -c "from src.core.parser import TestParser; ..."
order_module 测试用例:
1. 测试用例_创建订单: order=0
2. 测试用例_查询订单: order=1
3. 测试用例_更新订单: order=2
4. 测试用例_查询订单详情: order=3
5. 测试用例_评价订单: order=4
6. 测试用例_取消订单: order=50
7. 测试用例_支付订单: order=100
8. 测试用例_申请退款: order=150
9. 测试用例_删除订单: order=200
```

## 关键特性

1. **自动分配**：未设置 `order` 的用例自动从 0 开始分配连续的 order 值
2. **冲突避免**：自动跳过已设置的 order 值，避免冲突
3. **保持文件顺序**：未设置 order 的用例按文件中的顺序执行
4. **灵活控制**：可以通过设置特定 order 值来控制执行顺序
5. **跨模块支持**：不同模块的测试用例统一按 order 排序

## 文档更新

1. **README.md**：
   - 在核心特性中添加执行顺序控制说明
   - 在核心功能说明中添加详细使用示例
   - 更新文档链接

2. **test_execution_order.md**：
   - 创建完整的执行顺序控制功能说明文档
   - 包含配置方式、使用建议、注意事项等

3. **test_data/order_module.yaml**：
   - 创建完整的测试示例文件
   - 演示默认顺序、自定义顺序、混合模式三种使用场景

## 总结

成功实现了测试用例执行顺序控制功能，支持：
- ✅ 默认按文件顺序执行
- ✅ 自定义执行顺序（通过 order 字段）
- ✅ 混合模式（部分设置 order，部分不设置）
- ✅ 自动分配 order 值，避免冲突
- ✅ 跨模块统一排序

测试人员现在可以灵活地控制测试用例的执行顺序，满足各种测试场景的需求！
