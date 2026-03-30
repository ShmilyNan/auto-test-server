"""
数据提取器
从响应中提取数据，支持多种提取方式
"""
import re
from typing import Dict, Any, Optional
from jsonpath_ng.ext import parse as jsonpath_parse
from lxml import etree
from src.utils.logger import logger


class Extractor:
    """数据提取器"""
    
    def __init__(self):
        self._cache = {}
    
    def extract(
        self,
        response: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据规则提取数据
        支持的提取方式:
        - jsonpath: JSONPath表达式
        - regex: 正则表达式
        - header: 响应头
        - cookie: Cookie
        - xpath: XPath（HTML/XML响应）
        Args:
            response: HTTP响应数据
            rules: 提取规则 {变量名: {type: "jsonpath", expression: "$.data.id"}}
        Returns:
            Dict: 提取的数据 {变量名: 值}
        """
        extracted = {}
        
        for var_name, rule in rules.items():
            if isinstance(rule, str):
                # 简化写法，默认使用jsonpath
                rule = {'type': 'jsonpath', 'expression': rule}
            
            try:
                value = self._extract_single(response, rule)
                extracted[var_name] = value
                logger.debug(f"提取变量 {var_name} = {value}")
            except Exception as e:
                logger.error(f"提取变量 {var_name} 失败: {str(e)}")
                extracted[var_name] = None
        
        return extracted
    
    def _extract_single(self, response: Dict[str, Any], rule: Dict[str, Any]) -> Any:
        """
        单次提取
        Args:
            response: 响应数据
            rule: 提取规则
        Returns:
            Any: 提取的值
        """
        extract_type = rule.get('type', 'jsonpath')
        expression = rule.get('expression', rule.get('pattern', ''))
        
        if not expression:
            raise ValueError("提取规则缺少expression字段")
        
        if extract_type == 'jsonpath':
            return self._extract_jsonpath(response, expression)
        elif extract_type == 'regex':
            return self._extract_regex(response, expression, rule.get('group', 0))
        elif extract_type == 'header':
            return self._extract_header(response, expression)
        elif extract_type == 'cookie':
            return self._extract_cookie(response, expression)
        elif extract_type == 'xpath':
            return self._extract_xpath(response, expression)
        else:
            raise ValueError(f"不支持的提取类型: {extract_type}")

    @staticmethod
    def _extract_jsonpath(response: Dict[str, Any], expression: str) -> Any:
        """
        使用JSONPath提取数据
        Args:
            response: 响应数据
            expression: JSONPath表达式
        Returns:
            Any: 提取的值
        """
        try:
            # 默认从body中提取
            data = response.get('body', response)

            jsonpath_expr = jsonpath_parse(expression)
            matches = jsonpath_expr.find(data)

            if not matches:
                logger.warning(f"JSONPath未匹配到数据: {expression}")
                return None

            # 如果有多个匹配，返回列表
            if len(matches) > 1:
                return [match.value for match in matches]

            # 单个匹配，返回值
            return matches[0].value

        except Exception as e:
            logger.error(f"JSONPath提取失败: {expression}, 错误: {str(e)}")
            raise

    @staticmethod
    def _extract_regex(
            response: Dict[str, Any],
        pattern: str,
        group: int = 0
    ) -> Any:
        """
        使用正则表达式提取数据
        Args:
            response: 响应数据
            pattern: 正则表达式
            group: 捕获组索引
        Returns:
            Any: 提取的值
        """
        try:
            # 默认从text中提取
            text = response.get('text', str(response))
            
            matches = re.findall(pattern, text)
            
            if not matches:
                logger.warning(f"正则未匹配到数据: {pattern}")
                return None
            
            # 返回所有匹配
            if group is None:
                return matches
            
            # 返回指定组
            if isinstance(matches[0], tuple):
                return matches[0][group] if group < len(matches[0]) else None
            else:
                return matches[0]
            
        except Exception as e:
            logger.error(f"正则提取失败: {pattern}, 错误: {str(e)}")
            raise
    
    @staticmethod
    def _extract_header(response: Dict[str, Any], header_name: str) -> Optional[str]:
        """
        从响应头中提取数据
        Args:
            response: 响应数据
            header_name: 请求头名称
        Returns:
            Optional[str]: 请求头值
        """
        headers = response.get('headers', {})
        return headers.get(header_name)
    
    @staticmethod
    def _extract_cookie(response: Dict[str, Any], cookie_name: str) -> Optional[str]:
        """
        从Cookie中提取数据
        Args:
            response: 响应数据
            cookie_name: Cookie名称
        Returns:
            Optional[str]: Cookie值
        """
        cookies = response.get('cookies', {})
        return cookies.get(cookie_name)
    
    @staticmethod
    def _extract_xpath(response: Dict[str, Any], xpath_expr: str) -> Any:
        """
        使用XPath提取数据（HTML/XML）
        Args:
            response: 响应数据
            xpath_expr: XPath表达式
        Returns:
            Any: 提取的值
        """
        try:
            # 从text中提取
            html = response.get('text', '')
            
            # 解析HTML/XML
            tree = etree.HTML(html)
            
            # 执行XPath查询
            nodes = tree.xpath(xpath_expr)
            
            if not nodes:
                logger.warning(f"XPath未匹配到数据: {xpath_expr}")
                return None
            
            # 返回结果
            if len(nodes) == 1:
                node = nodes[0]
                if isinstance(node, str):
                    return node
                else:
                    return etree.tostring(node, encoding='unicode')
            else:
                return [etree.tostring(node, encoding='unicode') if not isinstance(node, str) else node for node in nodes]
                
        except Exception as e:
            logger.error(f"XPath提取失败: {xpath_expr}, 错误: {str(e)}")
            raise
    
    @staticmethod
    def extract_by_path(data: Any, path: str) -> Any:
        """
        通过点号路径提取数据
        
        示例: data.users[0].name
        Args:
            data: 数据源
            path: 路径字符串
        Returns:
            Any: 提取的值
        """
        keys = path.split('.')
        current = data
        
        for key in keys:
            # 处理数组索引: users[0]
            match = re.match(r'(\w+)\[(\d+)\]', key)
            if match:
                attr_name = match.group(1)
                index = int(match.group(2))
                
                if isinstance(current, dict):
                    current = current.get(attr_name, [])
                else:
                    current = []
                
                if isinstance(current, list) and len(current) > index:
                    current = current[index]
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None
            
            if current is None:
                break
        
        return current


# 全局提取器实例
_extractor = None


def get_extractor() -> Extractor:
    """获取全局提取器实例"""
    global _extractor
    
    if _extractor is None:
        _extractor = Extractor()
    
    return _extractor
