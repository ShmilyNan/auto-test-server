"""
上下文管理器
管理全局变量、局部变量、缓存变量、关联变量
"""
import string
import time
import random
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from threading import Lock
from src.utils.logger import logger


@dataclass
class TestContext:
    """测试上下文"""
    
    # 全局变量（整个测试会话共享）
    global_vars: Dict[str, Any] = field(default_factory=dict)
    
    # 缓存变量（带过期时间）
    cached_vars: Dict[str, tuple] = field(default_factory=dict)  # {key: (value, expire_time)}
    
    # 局部变量（当前用例私有）
    local_vars: Dict[str, Any] = field(default_factory=dict)
    
    # 关联变量（从响应中提取的数据）
    extract_vars: Dict[str, Any] = field(default_factory=dict)
    
    # 上一个响应数据
    last_response: Optional[Dict[str, Any]] = None

    # 默认请求头
    default_headers: Dict[str, str] = field(default_factory=dict)
    
    # 测试元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 线程锁（用于并发安全）
    _lock: Lock = field(default_factory=Lock)

    def set_default_headers(self, headers: Dict[str, str]):
        """设置默认请求头"""
        self.default_headers = headers.copy()

    def get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        return self.default_headers.copy()

    def set_global(self, key: str, value: Any):
        """设置全局变量"""
        with self._lock:
            self.global_vars[key] = value
            self.global_vars[f'{key}_updated_at'] = time.time()
    
    def get_global(self, key: str, default: Any = None) -> Any:
        """获取全局变量"""
        with self._lock:
            return self.global_vars.get(key, default)
    
    def set_local(self, key: str, value: Any):
        """设置局部变量"""
        with self._lock:
            self.local_vars[key] = value
    
    def get_local(self, key: str, default: Any = None) -> Any:
        """获取局部变量"""
        with self._lock:
            return self.local_vars.get(key, default)
    
    def set_cache(self, key: str, value: Any, ttl: int = 3600):
        """
        设置缓存变量
        Args:
            key: 键
            value: 值
            ttl: 过期时间（秒）
        """
        expire_time = time.time() + ttl
        with self._lock:
            self.cached_vars[key] = (value, expire_time)
    
    def get_cache(self, key: str, default: Any = None) -> Any:
        """
        获取缓存变量
        Args:
            key: 键
            default: 默认值
        Returns:
            Any: 缓存值，如果过期则返回默认值
        """
        if key not in self.cached_vars:
            return default
        
        value, expire_time = self.cached_vars[key]
        
        # 检查是否过期
        if time.time() > expire_time:
            del self.cached_vars[key]
            return default
        
        return value
    
    def set_extract(self, key: str, value: Any):
        """设置关联变量（从响应提取）"""
        self.extract_vars[key] = value
    
    def get_extract(self, key: str, default: Any = None) -> Any:
        """获取关联变量"""
        return self.extract_vars.get(key, default)
    
    def set_last_response(self, response: Dict[str, Any]):
        """设置上一个响应"""
        self.last_response = response
    
    def get_last_response(self) -> Optional[Dict[str, Any]]:
        """获取上一个响应"""
        return self.last_response

    def _get_array_length(self, path: str) -> Optional[int]:
        """
        从响应中提取数组长度
        支持的路径格式:
        - body.data
        - body.rows
        - data.items
        Args:
            path: 数组路径，例如 "body.data"
        Returns:
            int: 数组长度，如果不存在或不是数组则返回 None
        """
        if not self.last_response:
            logger.warning(f"无法获取数组长度: 没有可用的响应数据")
            return None

        try:
            # 提取数组
            array = self._extract_value_by_path(self.last_response, path)

            if isinstance(array, (list, tuple)):
                length = len(array)
                logger.debug(f"获取数组长度: {path} = {length}")
                return length
            else:
                logger.warning(f"路径 {path} 不是数组: {type(array)}")
                return None
        except Exception as e:
            logger.error(f"获取数组长度失败: {path}, 错误: {str(e)}")
            return None

    @staticmethod
    def _extract_value_by_path(data: Any, path: str) -> Any:
        """
        根据路径提取值
        Args:
            data: 数据
            path: 路径，例如 "body.data.items"
        Returns:
            Any: 提取的值
        """
        if not path:
            return data

        parts = path.split('.')

        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            elif isinstance(data, (list, tuple)) and part.isdigit():
                data = data[int(part)]
            else:
                return None

            if data is None:
                break

        return data
    
    def clear_local(self):
        """清空局部变量"""
        self.local_vars.clear()

    def clear_local_all(self):
        """清空所有局部变量"""
        self.local_vars.clear()
        self.extract_vars.clear()
    
    def clear_cache(self):
        """清空缓存"""
        with self._lock:
            self.cached_vars.clear()
    
    def clear_all(self):
        """清空所有变量"""
        with self._lock:
            self.global_vars.clear()
            self.local_vars.clear()
            self.extract_vars.clear()
            self.cached_vars.clear()
            self.last_response = None
    
    def replace_vars(self, text: str) -> str:
        """
        替换字符串中的变量占位符
        支持的变量格式:
        - ${global_var} - 全局变量
        - ${local_var} - 局部变量
        - ${cache.var} - 缓存变量
        - ${$extract.var} - 关联变量
        支持的函数:
        - ${random()} - 生成 0 到 1 之间的随机小数
        - ${random(min, max)} - 生成 min 到 max 之间的随机整数
        - ${random_int(min, max)} - 同 random
        - ${random_mixed()
        - ${random_mixed(digital: bool = True,
                         upper: bool = True,
                         lower: bool = True,
                         special: bool = False,
                         length: int = 10)} - 按条件生成指定长度的随机字符串，不传参则使用默认值
        - ${uuid()} - 生成 UUID
        - ${timestamp()} - 生成当前时间戳（秒）
        - ${timestamp_ms()} - 生成当前时间戳（毫秒）
        支持的特殊语法:
        - ${length.path} - 获取数组长度
        - ${length.path - n} - 获取数组长度并减去 n（n 为数字）
        Args:
            text: 包含变量占位符的字符串
        Returns:
            str: 替换后的字符串
        """
        if not isinstance(text, str):
            return text

        # 多次替换直到没有变量为止（支持嵌套）
        max_iterations = 20  # 防止无限循环
        for _ in range(max_iterations):
            # 查找所有 ${...} 变量（包括嵌套的）
            # 使用栈来正确匹配括号
            variables = self._find_variables(text)

            if not variables:
                break

            # 替换变量
            for var_match in variables:
                var_expr = var_match
                full_match = f"${{{var_expr}}}"

                # 处理 ${length.path} 和 ${length.path - n} 语法
                if var_expr.startswith('length.'):
                    # 检查是否包含 - 运算
                    if ' - ' in var_expr:
                        # ${length.body.data - 1}
                        parts = var_expr.split(' - ', 1)
                        path = parts[0][7:]  # 去掉 "length." 前缀
                        try:
                            offset = int(parts[1].strip())
                            length_value = self._get_array_length(path)
                            if length_value is not None:
                                text = text.replace(full_match, str(length_value - offset), 1)
                                continue
                        except ValueError:
                            pass
                        text = text.replace(full_match, full_match, 1)
                    else:
                        # ${length.body.data}
                        path = var_expr[7:]  # 去掉 "length." 前缀
                        length_value = self._get_array_length(path)
                        if length_value is not None:
                            text = text.replace(full_match, str(length_value), 1)
                        else:
                            text = text.replace(full_match, full_match, 1)

                # 处理函数调用
                # ${random(min, max)}
                elif var_expr.startswith('random(') or var_expr.startswith('random_int('):
                    try:
                        # 提取参数
                        if '(' in var_expr and ')' in var_expr:
                            inner = var_expr[var_expr.index('(') + 1:var_expr.rindex(')')]
                            if inner:
                                # ${random(0, 10)}
                                parts = [p.strip() for p in inner.split(',')]
                                if len(parts) == 2:
                                    # 检查参数是否已经被替换为数字
                                    if parts[0].isdigit() and parts[1].isdigit():
                                        min_val = int(parts[0])
                                        max_val = int(parts[1])
                                        result = str(random.randint(min_val, max_val))
                                        text = text.replace(full_match, result, 1)
                                    # 参数还包含变量，等待下次迭代
                                    continue
                            else:
                                # ${random()} - 0 到 1 之间的随机小数
                                result = str(random.random())
                                text = text.replace(full_match, result, 1)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"随机数生成失败: {var_expr}, 错误: {e}")
                        text = text.replace(full_match, full_match, 1)

                # ${random_mixed()}
                # 在变量替换循环中，处理 ${site_id_generate(...)} 表达式
                elif var_expr.startswith('random_mixed('):
                    try:
                        inner = var_expr[var_expr.index('(') + 1:var_expr.rindex(')')]
                        # 默认参数值
                        params = {
                            'digital': True,
                            'upper': True,
                            'lower': True,
                            'special': False,
                            'length': 10
                        }
                        if inner.strip() == '':
                            # 无参数：全部使用默认值
                            result = self._random_string_generator(**params)
                            text = text.replace(full_match, result, 1)
                        else:
                            need_continue = False
                            # 分割多个参数项（key=value）
                            items = [item.strip() for item in inner.split(',') if item.strip()]
                            for item in items:
                                if '=' not in item:
                                    raise ValueError(f"参数格式错误，缺少等号: {item}")
                                key, val = [x.strip() for x in item.split('=', 1)]
                                if key not in params:
                                    raise ValueError(f"未知参数: {key}")
                                # 如果值是未解析的变量（如 ${var}），则跳过本次替换，等待下次迭代
                                if val.startswith('${') and val.endswith('}'):
                                    need_continue = True
                                    break
                                # 解析具体值
                                if key == 'length':
                                    params[key] = int(val)  # length 为整数
                                else:
                                    # digital/upper/lower/special 为布尔值
                                    val_low = val.lower()
                                    if val_low == 'true':
                                        params[key] = True
                                    elif val_low == 'false':
                                        params[key] = False
                                    else:
                                        raise ValueError(f"布尔参数值必须为 true/false: {val}")
                            if need_continue:
                                continue  # 等待变量解析后下次再处理
                            # 所有参数解析成功，生成结果并替换
                            result = self._random_string_generator(**params)
                            text = text.replace(full_match, result, 1)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"随机字符串生成失败: {var_expr}, 错误: {e}")
                        text = text.replace(full_match, full_match, 1)

                # ${uuid()}
                elif var_expr == 'uuid()' or var_expr == 'uuid':
                    text = text.replace(full_match, str(uuid.uuid4()), 1)

                # ${timestamp()}
                elif var_expr == 'timestamp()' or var_expr == 'timestamp':
                    text = text.replace(full_match, str(int(time.time())), 1)

                # ${timestamp_ms()}
                elif var_expr == 'timestamp_ms()' or var_expr == 'timestamp_ms':
                    text = text.replace(full_match, str(int(time.time() * 1000)), 1)

                # 缓存变量: ${cache.key}
                elif var_expr.startswith('cache.'):
                    key = var_expr[6:]
                    value = self.get_cache(key)
                    if value is not None:
                        text = text.replace(full_match, str(value), 1)
                    else:
                        text = text.replace(full_match, full_match, 1)

                # 关联变量: ${$extract.key}
                elif var_expr.startswith('$extract.'):
                    key = var_expr[9:]
                    value = self.get_extract(key)
                    if value is not None:
                        text = text.replace(full_match, str(value), 1)
                    else:
                        text = text.replace(full_match, full_match, 1)

                # 普通变量
                else:
                    # 先尝试从局部变量获取
                    value = self.get_local(var_expr)
                    if value is not None:
                        text = text.replace(full_match, str(value), 1)
                        continue

                    # 再尝试从全局变量获取
                    value = self.get_global(var_expr)
                    if value is not None:
                        text = text.replace(full_match, str(value), 1)
                        continue

                    # 最后尝试从缓存获取
                    value = self.get_cache(var_expr)
                    if value is not None:
                        text = text.replace(full_match, str(value), 1)
                        continue

                    # 都找不到，记录警告但保留原值
                    logger.warning(f"变量未找到: {var_expr}")
                    text = text.replace(full_match, full_match, 1)
        return text

    @staticmethod
    def _find_variables(text: str) -> list:
        """
        查找所有 ${...} 变量（返回最内层的变量优先）
        Args:
            text: 文本
        Returns:
            list: 变量表达式列表（最内层优先）
        """
        variables = []
        stack = []

        for i, char in enumerate(text):
            if char == '$' and i + 1 < len(text) and text[i + 1] == '{':
                stack.append(i)
            elif char == '}' and stack:
                start_pos = stack.pop()
                if not stack:  # 栈空，说明是最外层的闭合括号
                    var_expr = text[start_pos + 2:i]  # 去掉 ${ 和 }
                    variables.append((start_pos, i, var_expr))

        # 按起始位置排序，从后往前（最内层优先）
        variables.sort(key=lambda x: x[0], reverse=True)

        result = [var[2] for var in variables]
        logger.debug(f"找到变量（最内层优先）: {result}")
        return result

    @staticmethod
    def _random_string_generator(
            digital: bool = True,
            upper: bool = True,
            lower: bool = True,
            special: bool = False,
            length: int = 10) -> str:
        """
        生成包含指定类型字符的随机字符串。
        参数:
            digital (bool): 是否包含数字 0-9，默认 True
            upper (bool): 是否包含大写字母 A-Z，默认 True
            lower (bool): 是否包含小写字母 a-z，默认 True
            special (bool): 是否包含特殊字符，默认 False
            length (int): 生成的字符串长度，默认 10
        返回:
            str: 随机生成的字符串
        异常:
            ValueError: 当所有字符类型都被禁用时抛出
        """
        # 构建字符集
        chars = ""
        if digital:
            chars += string.digits  # '0123456789'
        if upper:
            chars += string.ascii_uppercase  # 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if lower:
            chars += string.ascii_lowercase  # 'abcdefghijklmnopqrstuvwxyz'
        if special:
            chars += string.punctuation  # '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'

        if not chars:
            raise ValueError("至少需要选择一种字符类型（digital/upper/lower/special）")

        # 从字符集中随机选取 length 个字符（可重复）
        return ''.join(random.choices(chars, k=length))

    def replace_vars_dict(self, data: Any) -> Any:
        """
        递归替换字典/列表中的变量
        Args:
            data: 数据（字典/列表/字符串/其他）
        Returns:
            Any: 替换后的数据
        """
        if data is None:
            return None
        elif isinstance(data, str):
            return self.replace_vars(data)
        elif isinstance(data, dict):
            return {k: self.replace_vars_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.replace_vars_dict(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.replace_vars_dict(item) for item in data)
        else:
            return data
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'global_vars': self.global_vars.copy(),
            'local_vars': self.local_vars.copy(),
            'extract_vars': self.extract_vars.copy(),
            'cached_vars': {k: v[0] for k, v in self.cached_vars.items()},
            'last_response': self.last_response
        }


# 全局上下文实例（单例）
_context = None
_context_lock = Lock()


def get_context() -> TestContext:
    """
    获取全局上下文实例
    Returns:
        TestContext: 上下文实例
    """
    global _context
    
    if _context is None:
        with _context_lock:
            if _context is None:
                _context = TestContext()
    
    return _context


def reset_context():
    """重置全局上下文（重新创建实例）"""
    global _context
    
    with _context_lock:
        if _context is not None:
            _context.clear_all()
        _context = TestContext()


# 别名
context = get_context
