# 快速开始

欢迎使用接口自动化测试平台！本指南将帮助您在5分钟内运行第一个测试用例。

## 🚀 5分钟快速开始

### 步骤1：环境安装（2分钟）

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt
```

### 步骤2：配置环境（1分钟）

编辑 `config/config.yaml`，设置默认环境：

```yaml
default_env: dev
```

编辑 `config/env/dev.yaml`，配置您的API地址：

```yaml
base_url: "http://your-api-server.com/api"

auth:
  type: bearer
  token: "your_token_here"
```

### 步骤3：编写测试用例（1分钟）

创建 `test_data/quick_start.yaml`：

```yaml
test_cases:
  - name: "健康检查"
    priority: "p0"
    tags: ["smoke"]
    
    method: "GET"
    url: "/health"
    
    validate:
      - type: "status_code"
        expected: 200
```

### 步骤4：运行测试（1分钟）

```bash
# 运行测试
python run.py

# 查看报告
allure serve reports/allure
```

## 📝 下一步

恭喜！您已经成功运行了第一个测试用例。接下来可以：

1. 📖 阅读 [YAML模板说明](yaml_template.md) 学习更多用例编写技巧
2. 🚀 查看 [使用指南](usage_guide.md) 了解高级功能
3. 🏗️ 阅读 [架构设计](architecture.md) 了解框架设计
4. 💡 查看 `test_data/` 目录下的示例用例

## 🎯 核心功能速查

### 变量使用

```yaml
# 全局变量
"${auth.dev_token}"

# 上一个用例提取的变量
"${$extract.user_id}"

# 缓存变量
"${cache.token}"

# 内置函数
"${timestamp()}"
"${uuid()}"
```

### 断言类型

```yaml
validate:
  # 状态码
  - type: "status_code"
    expected: 200
  
  # 等于
  - type: "eq"
    path: "body.code"
    expected: 0
  
  # 包含
  - type: "in"
    path: "body.status"
    expected: ["success", "ok"]
  
  # 正则
  - type: "regex"
    path: "body.email"
    pattern: "^[^@]+@[^@]+$"
```

### 数据提取

```yaml
extract:
  user_id:
    type: "jsonpath"
    expression: "$.data.user_id"
  
  token:
    type: "regex"
    pattern: '"token":"([^"]+)"'
```

## 🛠️ 常用命令

```bash
# 运行所有测试
python run.py

# 指定环境
python run.py --env test

# 运行冒烟测试
python run.py -m smoke

# 并发执行
python run.py -n 4

# 查看帮助
python run.py --help

# 查看报告
allure serve reports/allure
```

## 📚 更多资源

- 📖 [完整文档](../README.md)
- 🎨 [YAML模板](yaml_template.md)
- 📚 [使用指南](usage_guide.md)
- 🏗️ [架构设计](architecture.md)

---

**有问题？** 查看 [常见问题](../README.md#常见问题) 或提 Issue。
