# 数据提取后处理功能说明

## 功能概述

在接口自动化测试中，经常需要对从响应中提取的数据进行进一步处理，例如：
- 从 `[AC]Ascension Island` 中提取 `AC`
- 从 `SKU-00123` 中提取 `00123`
- 从 `user_001@example.com` 中提取 `user_001`
- 转换大小写、去除空格等

本平台支持在 `extract` 配置中添加 `process` 字段，对提取的数据进行后处理。

## 支持的处理类型

### 1. regex_extract - 正则提取

从字符串中使用正则表达式提取特定内容。

#### 使用场景
从 `[AC]Ascension Island` 中提取 `AC`

#### 配置示例

**方式1：字典格式（推荐）**
```yaml
extract:
  country_code:
    type: jsonpath
    expression: $.data[0].countryInfo
    process:
      type: regex_extract
      pattern: \[(.*?)\]  # 匹配中括号内的内容
      group: 1            # 1 表示第一个捕获组，即中括号内的内容
```

**方式2：字符串格式**
```yaml
extract:
  country_code:
    type: jsonpath
    expression: $.data[0].countryInfo
    process: "regex_extract:\\[(.*?)\\]|1"  # 格式: 类型:正则表达式|组索引
```

#### 参数说明
- `pattern`: 正则表达式
- `group`: 捕获组索引
  - `0`: 整个匹配的字符串（包含中括号，如 `[AC]`）
  - `1`: 第一个捕获组（不包含中括号，如 `AC`）
  - `2, 3, ...`: 第 N 个捕获组

#### 常见正则表达式示例
```yaml
# 提取中括号内的内容
pattern: \[(.*?)\]
# 输入: [AC]Ascension Island
# 输出: AC

# 提取括号内的数字
pattern: \((\d+)\)
# 输入: Order(12345)
# 输出: 12345

# 提取手机号
pattern: 1[3-9]\d{9}
# 输入: 联系电话:13800138000
# 输出: 13800138000

# 提取邮箱
pattern: [\w.-]+@[\w.-]+\.\w+
# 输入: 用户邮箱:test@example.com
# 输出: test@example.com
```

---

### 2. regex_replace - 正则替换

使用正则表达式替换字符串中的内容。

#### 配置示例
```yaml
extract:
  clean_text:
    type: jsonpath
    expression: $.data[0].description
    process:
      type: regex_replace
      pattern: \s+      # 匹配一个或多个空格
      replacement: ' '  # 替换为单个空格
```

**字符串格式：**
```yaml
process: "regex_replace:\\s+| "
```

#### 参数说明
- `pattern`: 正则表达式（要匹配的内容）
- `replacement`: 替换后的内容

---

### 3. substring - 字符串截取

截取字符串的指定部分。

#### 配置示例
```yaml
extract:
  short_id:
    type: jsonpath
    expression: $.data[0].order_id
    process:
      type: substring
      start: 0
      end: 10  # 从索引0开始，截取到索引10（不包含10）
```

**字符串格式：**
```yaml
process: "substring:0,10"  # 格式: substring:起始位置,结束位置
```

#### 参数说明
- `start`: 起始索引（从 0 开始）
- `end`: 结束索引（不包含此位置）

#### 示例
```yaml
# 输入: "ORDER-20231201-00123"
# start: 0, end: 10
# 输出: "ORDER-2023"

# start: 6
# 输出: "20231201-00123"

# start: -5  # Python 支持负索引
# 输出: "00123"
```

---

### 4. split - 分割后取某部分

使用分隔符分割字符串，并取指定部分。

#### 配置示例
```yaml
extract:
  sku_number:
    type: jsonpath
    expression: $.data[0].sku
    process:
      type: split
      separator: '-'
      index: 1  # 取分割后的第 1 部分（从 0 开始）
```

**字符串格式：**
```yaml
process: "split:-|1"  # 格式: split:分隔符|索引
```

#### 参数说明
- `separator`: 分隔符
- `index`: 要取的索引（从 0 开始）

#### 示例
```yaml
# 输入: "SKU-00123"
# separator: "-", index: 1
# 输出: "00123"

# 输入: "user_001@example.com"
# separator: "@", index: 0
# 输出: "user_001"
```

---

### 5. replace - 字符串替换

简单的字符串替换（不使用正则）。

#### 配置示例
```yaml
extract:
  cleaned_name:
    type: jsonpath
    expression: $.data[0].name
    process:
      type: replace
      old: ' '
      new: '_'  # 将空格替换为下划线
```

**字符串格式：**
```yaml
process: "replace: |_"  # 格式: replace:旧值|新值
```

---

### 6. upper - 转大写

将字符串转为大写。

#### 配置示例
```yaml
extract:
  uppercase_country:
    type: jsonpath
    expression: $.data[0].country
    process: upper  # 无需参数
```

#### 示例
```yaml
# 输入: "china"
# 输出: "CHINA"
```

---

### 7. lower - 转小写

将字符串转为小写。

#### 配置示例
```yaml
extract:
  lowercase_email:
    type: jsonpath
    expression: $.data[0].email
    process: lower
```

---

### 8. strip - 去除首尾空格

去除字符串首尾的空白字符。

#### 配置示例
```yaml
extract:
  trimmed_name:
    type: jsonpath
    expression: $.data[0].name
    process: strip
```

#### 相关方法
- `lstrip`: 仅去除左侧空格
- `rstrip`: 仅去除右侧空格

---

## 完整示例

### 场景1：提取国家代码并使用

```yaml
module_name: country_module
cases:
  - name: 获取国家列表并提取国家代码
    priority: p0
    method: GET
    url: /api/countries
    validate:
      - eq: ["status_code", 200]
    extract:
      # 从 [AC]Ascension Island 中提取 AC
      country_code:
        type: jsonpath
        expression: $.data[0].countryInfo
        process:
          type: regex_extract
          pattern: \[(.*?)\]
          group: 1

  - name: 使用国家代码查询详情
    priority: p0
    method: GET
    url: /api/countries/${extract.country_code}
    validate:
      - eq: ["status_code", 200]
      - eq: ["data.code", "${extract.country_code}"]
```

### 场景2：处理订单号

```yaml
cases:
  - name: 创建订单并提取订单号
    priority: p0
    method: POST
    url: /api/orders
    validate:
      - eq: ["status_code", 201]
    extract:
      # 从 "ORDER-20231201-00123" 中提取短订单号 "20231201-00123"
      short_order_id:
        type: jsonpath
        expression: $.data.order_id
        process:
          type: substring
          start: 6

      # 从 "ORDER-20231201-00123" 中提取日期 "20231201"
      order_date:
        type: jsonpath
        expression: $.data.order_id
        process:
          type: split
          separator: '-'
          index: 1
```

### 场景3：处理用户信息

```yaml
cases:
  - name: 获取用户信息并处理
    priority: p0
    method: GET
    url: /api/users/1
    validate:
      - eq: ["status_code", 200]
    extract:
      # 从 "  John Doe  " 去除空格
      cleaned_name:
        type: jsonpath
        expression: $.data.name
        process: strip

      # 从 "john.doe@example.com" 提取用户名
      username:
        type: jsonpath
        expression: $.data.email
        process: "split:@|0"

      # 国家代码转大写
      country_upper:
        type: jsonpath
        expression: $.data.country
        process: upper
```

---

## 高级技巧

### 1. 链式处理（多次处理）

虽然当前版本不支持直接链式处理，但可以通过多次提取实现：

```yaml
extract:
  # 第一步提取原始值
  raw_country:
    type: jsonpath
    expression: $.data[0].countryInfo

  # 第二步：从原始值中提取（需要在后续用例中使用 ${extract.raw_country}）
```

### 2. 复杂正则表达式

```yaml
extract:
  # 从 "Price: $123.45 USD" 中提取价格 "123.45"
  price:
    type: jsonpath
    expression: $.data.price_text
    process:
      type: regex_extract
      pattern: \$([\d.]+)
      group: 1

  # 从 "Order #12345 (Completed)" 中提取订单号 "12345"
  order_id:
    type: jsonpath
    expression: $.data.status
    process:
      type: regex_extract
      pattern: \#(\d+)
      group: 1
```

### 3. 组合使用

```yaml
extract:
  # 从 "USER_001:john.doe@example.com" 中提取 "john.doe"
  username:
    type: jsonpath
    expression: $.data.user_info
    process:
      type: split
      separator: ':'
      index: 1
  # 结果: "john.doe@example.com"
  # 需要再次处理提取 "john.doe"
  # 可以在后续提取中引用 ${extract.username} 并继续处理
```

---

## 注意事项

1. **正则表达式转义**：在 YAML 中使用特殊字符时需要转义，如 `\[(.*?)\]`
2. **Group 索引**：正则提取时，`group: 0` 返回整个匹配，`group: 1` 返回第一个捕获组
3. **字符串格式限制**：字符串格式不支持复杂的参数，推荐使用字典格式
4. **数据类型**：处理后的值始终是字符串类型，如需其他类型需在后续用例中转换
5. **错误处理**：如果处理失败，会返回原始值（不会中断测试）

---

## 测试验证

您可以在 `test_data/country_module.yaml` 中找到完整的使用示例。
