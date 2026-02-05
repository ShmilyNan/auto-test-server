# 测试用例执行顺序控制功能说明

## 功能概述

本平台支持测试用例执行顺序的灵活控制：
- **默认行为**：测试用例按文件中的定义顺序（从上往下）执行
- **自定义顺序**：可以通过 `order` 字段设置特定用例的执行顺序
- **混合模式**：已设置 `order` 的用例按设置的顺序执行，未设置 `order` 的用例按文件顺序执行

## 配置方式

### 1. 默认执行顺序（推荐）

不设置 `order` 字段，用例将按文件中出现的顺序依次执行。

```yaml
test_cases:
  - name: 测试用例_创建订单
    method: POST
    url: /api/orders
    # ... 其他配置

  - name: 测试用例_查询订单
    method: GET
    url: /api/orders/1
    # ... 其他配置

  - name: 测试用例_更新订单
    method: PUT
    url: /api/orders/1
    # ... 其他配置
```

**执行顺序**：
1. 测试用例_创建订单
2. 测试用例_查询订单
3. 测试用例_更新订单

### 2. 自定义执行顺序

通过 `order` 字段设置特定用例的执行顺序。

```yaml
test_cases:
  - name: 测试用例_创建订单
    order: 1  # 第1个执行
    method: POST
    url: /api/orders

  - name: 测试用例_删除订单
    order: 100  # 第100个执行
    method: DELETE
    url: /api/orders/1

  - name: 测试用例_查询订单
    order: 2  # 第2个执行
    method: GET
    url: /api/orders/1
```

**执行顺序**：
1. 测试用例_创建订单 (order=1)
2. 测试用例_查询订单 (order=2)
...
100. 测试用例_删除订单 (order=100)

### 3. 混合模式（推荐用于复杂场景）

部分用例设置 `order`，部分用例不设置。

```yaml
test_cases:
  # 未设置 order，按文件顺序执行
  - name: 测试用例_创建订单
    method: POST
    url: /api/orders

  - name: 测试用例_查询订单
    method: GET
    url: /api/orders/1

  - name: 测试用例_更新订单
    method: PUT
    url: /api/orders/1

  # 未设置 order，按文件顺序执行
  - name: 测试用例_查询订单详情
    method: GET
    url: /api/orders/1/details

  - name: 测试用例_评价订单
    method: POST
    url: /api/orders/1/review

  # 设置 order，强制在指定位置执行
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

## 自动分配规则

当测试用例未设置 `order` 时，系统会自动分配：

1. 从 0 开始，按文件顺序依次分配 0, 1, 2, 3, ...
2. 遇到已设置的 `order` 值时跳过
3. 确保不会与已设置的 `order` 冲突

### 示例

```yaml
test_cases:
  - name: 用例1  # 自动分配 order=0
  - name: 用例2  # 自动分配 order=1
  - name: 用例3  # 自动分配 order=2
  - name: 用例4  # order=10（用户设置）
  - name: 用例5  # 自动分配 order=3（跳过10，继续分配）
  - name: 用例6  # 自动分配 order=4
```

## 使用建议

### 1. 简单场景：使用默认顺序

对于简单的测试流程，直接按文件顺序定义用例即可：

```yaml
test_cases:
  - name: 登录
  - name: 创建订单
  - name: 支付订单
  - name: 查询订单
  - name: 取消订单
```

### 2. 复杂场景：使用自定义顺序

对于复杂的测试流程，特别是有分支或特殊顺序要求的场景：

```yaml
test_cases:
  # 主流程
  - name: 登录
    order: 1

  - name: 创建订单
    order: 2

  - name: 支付订单
    order: 3

  # 后续流程（使用大数值，确保在主流程之后）
  - name: 申请退款
    order: 100

  - name: 查询退款状态
    order: 101
```

### 3. 混合场景：结合使用

对于既有主流程又有分支的场景：

```yaml
test_cases:
  # 主流程（不设置 order，按文件顺序）
  - name: 登录
  - name: 查看商品
  - name: 加入购物车
  - name: 创建订单

  # 特殊操作（设置 order，确保在特定位置执行）
  - name: 支付订单
    order: 50

  - name: 确认支付
    order: 51

  # 后续操作（不设置 order，继续按文件顺序）
  - name: 查询订单
  - name: 申请退款

  # 清理操作（设置大数值，确保最后执行）
  - name: 删除订单
    order: 999
```

## 验证执行顺序

### 方法1：收集测试用例

```bash
# 查看所有测试用例及其顺序
python -m pytest src/api/test_dynamic.py --collect-only -v
```

### 方法2：使用日志

系统会自动记录每个用例分配的 order 值：

```bash
# 运行测试并查看日志
python -m pytest src/api/test_dynamic.py -v
```

日志输出示例：
```
2026-02-04 15:10:07 | DEBUG | 用例 '测试用例_创建订单' 自动分配 order: 0
2026-02-04 15:10:07 | DEBUG | 用例 '测试用例_查询订单' 自动分配 order: 1
2026-02-04 15:10:07 | DEBUG | 用例 '测试用例_更新订单' 自动分配 order: 2
```

## 注意事项

### 1. order 值冲突

如果多个用例设置了相同的 `order` 值，系统会保留第一个遇到的用例，后续用例会被重新分配。

```yaml
test_cases:
  - name: 用例1
    order: 10

  - name: 用例2
    order: 10  # 冲突，会被重新分配
```

### 2. order 值范围

- 建议使用正整数（0, 1, 2, ...）
- 避免使用负数或非常大的数值
- 使用 10 的倍数（10, 20, 30）方便后续插入新用例

### 3. 跨模块顺序

不同模块的测试用例会合并到同一个测试会话中，统一按 `order` 排序。如果需要跨模块控制顺序，建议使用更大的 `order` 值范围。

```yaml
# module1.yaml
test_cases:
  - name: 模块1用例1
    order: 1000  # 使用 1000 开始

# module2.yaml
test_cases:
  - name: 模块2用例1
    order: 2000  # 使用 2000 开始，确保在模块1之后
```

## 完整示例

参见 `test_data/order_module.yaml` 获取完整的使用示例。
