"""
上下文管理器
管理全局变量、局部变量、缓存变量、关联变量
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from threading import Lock
from src.utils.logger import log as logger


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
    
    # 测试元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 线程锁（用于并发安全）
    _lock: Lock = field(default_factory=Lock)
    
    def set_global(self, key: str, value: Any):
        """设置全局变量"""
        with self._lock:
            self.global_vars[key] = value
            self.global_vars[f'{key}_updated_at'] = time.time()
    
    def get_global(self, key: str, default: Any = None) -> Any:
        """获取全局变量"""
        return self.global_vars.get(key, default)
    
    def set_local(self, key: str, value: Any):
        """设置局部变量"""
        self.local_vars[key] = value
    
    def get_local(self, key: str, default: Any = None) -> Any:
        """获取局部变量"""
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
        
        Args:
            text: 包含变量占位符的字符串
            
        Returns:
            str: 替换后的字符串
        """
        if not isinstance(text, str):
            return text
        
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_match(match):
            var_expr = match.group(1)
            
            # 缓存变量: ${cache.key}
            if var_expr.startswith('cache.'):
                key = var_expr[6:]
                value = self.get_cache(key)
                return str(value) if value is not None else match.group(0)
            
            # 关联变量: ${$extract.key}
            if var_expr.startswith('$extract.'):
                key = var_expr[9:]
                value = self.get_extract(key)
                return str(value) if value is not None else match.group(0)
            
            # 先尝试从局部变量获取
            value = self.get_local(var_expr)
            if value is not None:
                return str(value)
            
            # 再尝试从全局变量获取
            value = self.get_global(var_expr)
            if value is not None:
                return str(value)
            
            # 最后尝试从缓存获取
            value = self.get_cache(var_expr)
            if value is not None:
                return str(value)
            
            # 都找不到，返回原值
            logger.warning(f"变量未找到: {var_expr}")
            return match.group(0)
        
        return re.sub(pattern, replace_match, text)
    
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
    """重置全局上下文"""
    global _context
    
    with _context_lock:
        if _context is not None:
            _context.clear_all()


# 别名
context = get_context
