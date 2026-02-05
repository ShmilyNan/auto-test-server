# YAML加载器使用指南

## 概述

`YAMLLoader` 是一个统一的YAML文件加载工具，提供了完整的YAML文件读取、写入、验证等功能。

## 特性

- ✅ 统一的YAML文件加载接口
- ✅ 支持默认值
- ✅ 类型安全的加载（字典、列表）
- ✅ 错误处理和日志记录
- ✅ 必填字段验证
- ✅ 批量加载支持
- ✅ 嵌套值获取
- ✅ YAML文件保存
- ✅ 字符串解析
- ✅ 单例模式

## 快速开始

### 1. 导入

```python
from src.utils.yaml_loader import (
    YAMLLoader,
    get_yaml_loader,
    load_yaml,
    load_yaml_dict,
    save_yaml
)
```

### 2. 基本使用

```python
# 使用便捷函数
config = load_yaml_dict("config/config.yaml", default={})

# 使用加载器实例
loader = YAMLLoader()
config = loader.load_dict("config/config.yaml", default={})

# 使用全局单例
loader = get_yaml_loader()
config = loader.load_dict("config/config.yaml", default={})
```

## API 参考

### YAMLLoader 类

#### load()

加载YAML文件，失败时返回默认值。

```python
data = loader.load("config.yaml", default={})
```

**参数：**
- `file_path`: YAML文件路径
- `default`: 文件不存在或解析失败时的默认值

**返回：** 解析后的数据

---

#### load_or_raise()

加载YAML文件，失败时抛出异常。

```python
try:
    data = loader.load_or_raise("config.yaml")
except FileNotFoundError:
    print("文件不存在")
except yaml.YAMLError as e:
    print(f"YAML解析错误: {e}")
```

**参数：**
- `file_path`: YAML文件路径

**返回：** 解析后的数据

**异常：**
- `FileNotFoundError`: 文件不存在
- `yaml.YAMLError`: YAML解析错误
- `IOError`: 文件读取错误

---

#### load_dict()

加载YAML文件并返回字典类型，如果不是字典则返回默认值。

```python
config = loader.load_dict("config.yaml", default={})
```

**参数：**
- `file_path`: YAML文件路径
- `default`: 默认值（空字典）

**返回：** 解析后的字典数据

---

#### load_list()

加载YAML文件并返回列表类型，如果不是列表则返回默认值。

```python
items = loader.load_list("data.yaml", default=[])
```

**参数：**
- `file_path`: YAML文件路径
- `default`: 默认值（空列表）

**返回：** 解析后的列表数据

---

#### load_from_string()

从字符串加载YAML数据。

```python
yaml_string = """
test:
  key1: value1
  key2: value2
"""
data = loader.load_from_string(yaml_string, default={})
```

**参数：**
- `yaml_string`: YAML格式字符串
- `default`: 解析失败时的默认值

**返回：** 解析后的数据

---

#### save()

保存数据到YAML文件。

```python
data = {
    "test": {
        "key1": "value1",
        "key2": "value2"
    }
}

result = loader.save(data, "output.yaml")
```

**参数：**
- `data`: 要保存的数据
- `file_path`: 目标文件路径
- `sort_keys`: 是否排序字典的键（默认False）

**返回：** bool，是否保存成功

---

#### load_with_validation()

加载YAML文件并验证必填字段。

```python
config = loader.load_with_validation(
    "config.yaml",
    required_fields=["project", "http_client"],
    default={}
)
```

**参数：**
- `file_path`: YAML文件路径
- `required_fields`: 必填字段列表
- `default`: 默认值（空字典）

**返回：** 解析后的字典数据

---

#### load_multi()

批量加载多个YAML文件。

```python
file_paths = ["config1.yaml", "config2.yaml", "config3.yaml"]

# 加载为列表
configs = loader.load_multi(file_paths, merge=False)

# 合并为一个字典
merged_config = loader.load_multi(file_paths, merge=True)
```

**参数：**
- `file_paths`: 文件路径列表
- `merge`: 是否合并所有文件的数据

**返回：** 加载的数据列表或合并后的字典

---

#### get_nested_value()

从嵌套字典中获取值。

```python
data = {
    "level1": {
        "level2": {
            "level3": "value"
        }
    }
}

value = loader.get_nested_value(data, "level1.level2.level3")
# 返回: "value"

value = loader.get_nested_value(data, "level1.nonexistent", default="default")
# 返回: "default"
```

**参数：**
- `data`: 字典数据
- `path`: 嵌套路径，如 "config.database.host"
- `default`: 默认值
- `separator`: 路径分隔符（默认 '.'）

**返回：** 获取的值

---

### 便捷函数

#### load_yaml()

便捷函数：加载YAML文件。

```python
from src.utils.yaml_loader import load_yaml

data = load_yaml("config.yaml", default={})
```

---

#### load_yaml_dict()

便捷函数：加载YAML文件为字典。

```python
from src.utils.yaml_loader import load_yaml_dict

config = load_yaml_dict("config.yaml", default={})
```

---

#### save_yaml()

便捷函数：保存数据到YAML文件。

```python
from src.utils.yaml_loader import save_yaml

save_yaml(data, "output.yaml")
```

---

#### get_yaml_loader()

获取全局YAML加载器实例（单例模式）。

```python
from src.utils.yaml_loader import get_yaml_loader

loader = get_yaml_loader()
```

---

## 使用示例

### 示例1：加载配置文件

```python
from src.utils.yaml_loader import load_yaml_dict

# 加载主配置
config = load_yaml_dict("config/config.yaml", default={})

# 加载环境配置
env_config = load_yaml_dict("config/env/dev.yaml", default={})

# 获取嵌套配置值
base_url = env_config.get("base_url", "")
```

---

### 示例2：带验证的配置加载

```python
from src.utils.yaml_loader import get_yaml_loader

loader = get_yaml_loader()

config = loader.load_with_validation(
    "config/config.yaml",
    required_fields=["project", "http_client", "logging"],
    default={}
)
```

---

### 示例3：批量加载配置

```python
from src.utils.yaml_loader import get_yaml_loader

loader = get_yaml_loader()

# 加载多个配置文件
file_paths = [
    "config/base.yaml",
    "config/database.yaml",
    "config/cache.yaml"
]

# 合并为一个配置
config = loader.load_multi(file_paths, merge=True)
```

---

### 示例4：保存配置

```python
from src.utils.yaml_loader import save_yaml

config = {
    "test": {
        "enabled": True,
        "timeout": 30
    }
}

save_yaml(config, "config/test.yaml")
```

---

### 示例5：从字符串加载

```python
from src.utils.yaml_loader import get_yaml_loader

loader = get_yaml_loader()

yaml_string = """
test:
  cases:
    - name: "测试用例1"
      priority: "p0"
    - name: "测试用例2"
      priority: "p1"
"""

data = loader.load_from_string(yaml_string, default={})
```

---

## 错误处理

所有加载方法都内置了错误处理：

```python
from src.utils.yaml_loader import load_yaml_dict

# 文件不存在时返回默认值
config = load_yaml_dict("nonexistent.yaml", default={})
# 返回: {}

# YAML格式错误时返回默认值
config = load_yaml_dict("invalid.yaml", default={})
# 返回: {}，并记录错误日志
```

如果需要在失败时抛出异常，使用 `load_or_raise()`：

```python
from src.utils.yaml_loader import get_yaml_loader

loader = get_yaml_loader()

try:
    config = loader.load_or_raise("config.yaml")
except FileNotFoundError:
    print("配置文件不存在")
except yaml.YAMLError as e:
    print(f"YAML格式错误: {e}")
```

---

## 日志记录

YAMLLoader 使用 loguru 记录日志：

- **DEBUG**: 成功加载文件
- **WARNING**: 文件不存在、数据类型不匹配、缺少必填字段
- **ERROR**: YAML解析错误、文件读取错误、保存失败
- **INFO**: 成功保存文件、使用 load_or_raise 加载文件

---

## 最佳实践

1. **使用默认值**：始终提供合理的默认值
   ```python
   config = load_yaml_dict("config.yaml", default={})
   ```

2. **类型安全**：使用类型化的加载方法
   ```python
   config = load_yaml_dict("config.yaml", default={})  # 确保返回字典
   ```

3. **验证必填字段**：对配置文件进行验证
   ```python
   config = loader.load_with_validation(
       "config.yaml",
       required_fields=["project", "http_client"]
   )
   ```

4. **使用便捷函数**：简单场景使用便捷函数
   ```python
   from src.utils.yaml_loader import load_yaml_dict
   
   config = load_yaml_dict("config.yaml")
   ```

5. **复用加载器实例**：使用全局单例或创建实例复用
   ```python
   from src.utils.yaml_loader import get_yaml_loader
   
   loader = get_yaml_loader()  # 单例模式
   ```

---

## 迁移指南

### 从旧的代码迁移

**旧代码：**
```python
import yaml
from pathlib import Path

config_file = Path("config.yaml")
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {}
```

**新代码：**
```python
from src.utils.yaml_loader import load_yaml_dict

config = load_yaml_dict("config.yaml", default={})
```

---

## 总结

YAMLLoader 提供了一个简单、安全、功能完整的YAML文件加载方案。使用它可以让代码更简洁、更易维护。

**主要优势：**
- 统一的接口
- 自动错误处理
- 类型安全
- 丰富的功能
- 详细的日志记录
- 单例模式减少资源消耗

建议在项目中所有需要加载YAML文件的地方都使用 YAMLLoader。
