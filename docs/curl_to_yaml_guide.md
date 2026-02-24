# cURL 转 YAML 功能使用指南

## 功能概述

cURL 转 YAML 功能提供了一套自动化的工具链，可以将 cURL 命令转换为 YAML 格式的测试用例，支持自动扫描、场景生成和智能追加。

## 核心组件

### 1. CurlScanner (扫描器)
- 路径: `src/utils/curl_scanner.py`
- 功能: 扫描 `test_data/curl/` 目录结构，自动识别模块和测试用例
- 支持增量检测: 只处理新增的 cURL 文件

### 2. ScenarioGenerator (场景生成器)
- 路径: `src/utils/scenario_generator.py`
- 功能: 从单个 cURL 生成正向和逆向测试场景
- 支持的场景类型:
  - 正常流程 (normal)
  - 参数为空 (missing_params)
  - 参数错误 (invalid_params)
  - 特殊字符 (special_chars)
  - 数据类型错误 (wrong_type)

### 3. YamlGenerator (YAML 生成器)
- 路径: `src/utils/yaml_generator.py`
- 功能: 将场景转换为 YAML 格式
- 支持智能去重: 自动跳过已存在的场景
- 支持批量追加: 将多个场景追加到已有文件

### 4. curl_to_yaml.py (命令行工具)
- 路径: `scripts/curl_to_yaml.py`
- 功能: 提供统一的命令行接口

## 使用方式

### 方式一：自动扫描模式（推荐）

```bash
# 扫描所有 cURL 文件并转换
python scripts/curl_to_yaml.py --scan

# 预览模式（不实际修改文件）
python scripts/curl_to_yaml.py --scan --dry-run

# 强制转换所有文件（忽略去重）
python scripts/curl_to_yaml.py --scan --force
```

### 方式二：单文件转换模式

```bash
# 转换单个 cURL 文件
python scripts/curl_to_yaml.py -f test_data/curl/user_module/用户登录.txt

# 指定模块名称
python scripts/curl_to_yaml.py -f test_data/curl/user_module/用户登录.txt --case-module user_module

# 指定用例名称
python scripts/curl_to_yaml.py -f test_data/curl/user_module/用户登录.txt --name "用户登录接口"

# 追加到已有 YAML 文件
python scripts/curl_to_yaml.py -f test_data/curl/user_module/用户登录.txt -a test_data/user_module.yaml
```

### 方式三：cURL 命令直接转换

```bash
# 直接输入 cURL 命令
python scripts/curl_to_yaml.py -c "curl -X POST 'https://api.example.com/login' -H 'Content-Type: application/json' -d '{\"username\":\"test\",\"password\":\"test\"}'"

# 指定输出目录
python scripts/curl_to_yaml.py -c "curl ..." --yaml-dir test_data
```

## 目录结构规范

```
test_data/
└── curl/                     # cURL 文件存放目录
    ├── user_module/          # 用户模块目录
    │   ├── 用户登录.txt
    │   ├── 获取用户信息.txt
    │   └── 更新用户.txt
    └── product_module/       # 产品模块目录
        ├── 创建产品.txt
        └── 查询产品.txt
```

### 规则说明

1. **模块命名**: 一级子目录作为模块名（如 `user_module`）
2. **用例命名**: 文件名（不含扩展名）作为用例名（如 `用户登录`）
3. **场景命名**: 自动生成 `{用例名}-{场景类型}` 格式（如 `用户登录-正常流程`）

## cURL 文件示例

### 基础示例

```curl
curl -X POST 'https://dev-aly-us-ad-web.cdcicd.com/prod-api/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "Lee",
    "password": "Working@1130"
  }'
```

### 包含请求头

```curl
curl -X POST 'https://api.example.com/user/update' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ${token}' \
  -d '{
    "username": "new_username",
    "email": "new@example.com"
  }'
```

## 生成的 YAML 示例

```yaml
module:
  name: user_module
  version: 1.0.0
  description: user_module 模块的测试用例
  author: 从cURL转换

config:
  headers:
    Content-Type: application/json
    Accept: application/json
  timeout: 30

test_cases:
- name: 用户登录-正常流程
  description: 测试 POST 用户登录 正常流程
  priority: p1
  tags:
  - daily
  - regression
  method: POST
  url: /prod-api/login
  validate:
  - type: status_code
    expected: 200
  body:
    username: Lee
    password: Working@1130

- name: 用户登录-username为空
  description: 测试 用户登录 username 为空时的异常处理
  priority: p2
  tags:
  - daily
  - regression
  method: POST
  url: /prod-api/login
  validate:
  - type: status_code
    expected: 400
  body:
    username: ''
    password: test123
```

## 场景类型说明

| 场景类型 | 描述 | 示例 |
|---------|------|------|
| normal | 正常流程 | 用户登录-正常流程 |
| missing_params | 必填参数为空 | 用户登录-username为空 |
| invalid_params | 参数值错误 | 用户登录-password错误 |
| special_chars | 特殊字符测试 | 用户名包含特殊字符 |
| wrong_type | 数据类型错误 | 用户ID传字符串 |

## 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| --scan | -s | 自动扫描模式 |
| --file | -f | 指定 cURL 文件路径 |
| --curl | -c | 直接输入 cURL 命令 |
| --append | -a | 追加到已有 YAML 文件 |
| --yaml-dir | -y | YAML 输出目录 |
| --case-module | -m | 模块名称 |
| --name | -n | 用例名称 |
| --priority | -p | 优先级 (p0/p1/p2/p3) |
| --tags | -t | 标签列表（逗号分隔） |
| --dry-run | -d | 预览模式（不实际修改） |
| --force | -f | 强制转换（忽略去重） |
| --verbose | -v | 详细输出 |
| --help | -h | 帮助信息 |

## 工作流程

```
1. 开发人员将 cURL 命令保存到 test_data/curl/{module_name}/{case_name}.txt

2. 运行转换脚本
   python scripts/curl_to_yaml.py --scan

3. 脚本自动执行:
   ├─ 扫描 test_data/curl/ 目录
   ├─ 识别模块和用例
   ├─ 解析 cURL 命令
   ├─ 生成测试场景
   ├─ 检查 YAML 文件是否存在
   ├─ 智能去重（跳过已存在的场景）
   └─ 追加新场景到 YAML 文件

4. 运行 pytest 执行测试
   pytest -k "用户登录"
```

## 智能去重机制

系统会自动检测以下情况，避免重复生成：

1. **用例名称重复**: 相同名称的场景会被跳过
2. **参数组合重复**: 相同参数组合的场景会被跳过
3. **YAML 文件已存在**: 自动追加到已有文件，而不是覆盖

## 最佳实践

1. **模块组织**: 按功能模块组织 cURL 文件
2. **命名规范**: 使用有意义的中文文件名
3. **批量处理**: 使用 `--scan` 模式批量处理所有 cURL
4. **版本控制**: cURL 文件和 YAML 文件都纳入版本控制
5. **定期更新**: 新增接口时同步添加 cURL 文件

## 注意事项

1. cURL 文件必须是纯文本格式
2. 文件名不含扩展名部分作为用例名称
3. 同一 cURL 文件多次扫描只会追加新场景，不会重复
4. 需要手动修改 YAML 文件中的断言逻辑和预期值

## 故障排查

### 问题：ModuleNotFoundError: No module named 'src'
**解决方案**: 脚本已支持从任意位置运行，会自动查找项目根目录

### 问题：NameError: name 'Tuple' is not defined
**解决方案**: 已在 yaml_generator.py 中添加类型导入

### 问题：场景未生成
**解决方案**:
1. 检查 cURL 文件格式是否正确
2. 查看日志中的错误信息
3. 使用 `--verbose` 参数获取详细输出

### 问题：测试用例无法收集
**解决方案**:
1. 确认 YAML 文件在 test_data 目录下
2. 检查 YAML 格式是否正确
3. 运行 `pytest --collect-only` 查看收集情况

## 示例输出

```
============================================================
开始批量扫描和转换
============================================================
开始扫描 cURL 目录: test_data/curl
模块 user_module: 找到 2 个 cURL 文件
扫描完成: 共 1 个模块, 2 个 cURL 文件

处理模块: user_module
----------------------------------------
目标文件: test_data/user_module.yaml
成功解析 cURL 命令: POST https://api.example.com/login
用例 用户登录: 生成 4 个场景
  用户登录: 补充 2 个场景
已追加 2 个场景到文件: test_data/user_module.yaml
跳过 0 个已存在的场景
文件中共有 14 个测试用例
  ✓ 用户登录: 添加 2 个，跳过 0 个
模块 user_module 完成: 添加 2 个，跳过 0 个

============================================================
转换完成
============================================================
处理模块数: 1
处理文件数: 2
生成场景数: 6
实际添加: 4
跳过场景: 2
============================================================
```
