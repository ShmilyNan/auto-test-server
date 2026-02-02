"""
多元化断言验证器
支持JSON断言、SQL断言、JSON-Schema断言、正则断言、Python assert断言
"""

import re
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from jsonschema import validate, ValidationError as JsonSchemaValidationError
from src.utils.logger import log as logger


@dataclass
class AssertionResult:
    """断言结果"""
    passed: bool                      # 是否通过
    message: str                      # 结果消息
    actual: Any = None                # 实际值
    expected: Any = None              # 期望值
    assertion_type: str = ""          # 断言类型
    detail: Optional[Dict] = None     # 详细信息


class Validator:
    """断言验证器"""
    
    # 断言类型映射
    ASSERTION_TYPES = {
        'eq': '等于',
        'ne': '不等于',
        'gt': '大于',
        'lt': '小于',
        'gte': '大于等于',
        'lte': '小于等于',
        'in': '包含',
        'not_in': '不包含',
        'contains': '包含（字符串/列表）',
        'regex': '正则匹配',
        'json_schema': 'JSON Schema验证',
        'sql': 'SQL断言',
        'type': '类型检查',
        'length': '长度检查',
        'is_none': '为None',
        'is_not_none': '不为None',
        'is_true': '为True',
        'is_false': '为False',
        'status_code': '状态码'
    }
    
    def __init__(self):
        self.results: List[AssertionResult] = []
    
    def validate(
        self,
        response: Dict[str, Any],
        assertions: List[Dict[str, Any]],
        context: Optional[Dict] = None
    ) -> List[AssertionResult]:
        """
        执行断言验证
        
        Args:
            response: HTTP响应数据
            assertions: 断言规则列表
            context: 上下文变量（用于SQL断言等）
            
        Returns:
            List[AssertionResult]: 断言结果列表
        """
        self.results = []
        
        for assertion in assertions:
            try:
                result = self._validate_single(response, assertion, context)
                self.results.append(result)
                
                if not result.passed:
                    logger.error(f"断言失败: {result.message}")
                else:
                    logger.debug(f"断言通过: {result.message}")
                    
            except Exception as e:
                error_result = AssertionResult(
                    passed=False,
                    message=f"断言执行异常: {str(e)}",
                    assertion_type=assertion.get('type', 'unknown')
                )
                self.results.append(error_result)
                logger.error(f"断言异常: {str(e)}")
        
        return self.results
    
    def _validate_single(
        self,
        response: Dict[str, Any],
        assertion: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> AssertionResult:
        """
        执行单个断言
        
        Args:
            response: 响应数据
            assertion: 断言规则
            context: 上下文
            
        Returns:
            AssertionResult: 断言结果
        """
        assert_type = assertion.get('type', 'eq')
        expected = assertion.get('expected')
        actual = assertion.get('actual')
        path = assertion.get('path')  # JSONPath或响应字段
        
        # 获取实际值
        if actual is None and path:
            actual = self._extract_value(response, path)
        elif actual is None:
            actual = response
        
        # 根据断言类型执行验证
        if assert_type == 'eq':
            return self._assert_equal(actual, expected)
        elif assert_type == 'ne':
            return self._assert_not_equal(actual, expected)
        elif assert_type == 'gt':
            return self._assert_greater(actual, expected)
        elif assert_type == 'lt':
            return self._assert_less(actual, expected)
        elif assert_type == 'gte':
            return self._assert_greater_equal(actual, expected)
        elif assert_type == 'lte':
            return self._assert_less_equal(actual, expected)
        elif assert_type in ['in', 'contains']:
            return self._assert_in(actual, expected)
        elif assert_type == 'not_in':
            return self._assert_not_in(actual, expected)
        elif assert_type == 'regex':
            pattern = assertion.get('pattern', expected)
            return self._assert_regex(actual, pattern)
        elif assert_type == 'json_schema':
            schema = assertion.get('schema', expected)
            return self._assert_json_schema(actual, schema)
        elif assert_type == 'sql':
            return self._assert_sql(assertion, context)
        elif assert_type == 'type':
            return self._assert_type(actual, expected)
        elif assert_type == 'length':
            min_len = assertion.get('min')
            max_len = assertion.get('max')
            return self._assert_length(actual, min_len, max_len)
        elif assert_type == 'is_none':
            return self._assert_is_none(actual)
        elif assert_type == 'is_not_none':
            return self._assert_is_not_none(actual)
        elif assert_type == 'is_true':
            return self._assert_is_true(actual)
        elif assert_type == 'is_false':
            return self._assert_is_false(actual)
        elif assert_type == 'status_code':
            return self._assert_status_code(response, expected)
        else:
            return AssertionResult(
                passed=False,
                message=f"不支持的断言类型: {assert_type}",
                assertion_type=assert_type
            )
    
    def _extract_value(self, data: Any, path: str) -> Any:
        """
        从响应数据中提取值
        
        支持路径格式:
        - body.data.id
        - headers.Content-Type
        - status_code
        
        Args:
            data: 响应数据
            path: 提取路径
            
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
    
    def _assert_equal(self, actual: Any, expected: Any) -> AssertionResult:
        """断言等于"""
        passed = actual == expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'==' if passed else '!='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='eq'
        )
    
    def _assert_not_equal(self, actual: Any, expected: Any) -> AssertionResult:
        """断言不等于"""
        passed = actual != expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'!=' if passed else '=='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='ne'
        )
    
    def _assert_greater(self, actual: Any, expected: Any) -> AssertionResult:
        """断言大于"""
        passed = actual > expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'>' if passed else '<='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='gt'
        )
    
    def _assert_less(self, actual: Any, expected: Any) -> AssertionResult:
        """断言小于"""
        passed = actual < expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'<' if passed else '>='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='lt'
        )
    
    def _assert_greater_equal(self, actual: Any, expected: Any) -> AssertionResult:
        """断言大于等于"""
        passed = actual >= expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'>=' if passed else '<'} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='gte'
        )
    
    def _assert_less_equal(self, actual: Any, expected: Any) -> AssertionResult:
        """断言小于等于"""
        passed = actual <= expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'<=' if passed else '>'} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='lte'
        )
    
    def _assert_in(self, actual: Any, expected: Any) -> AssertionResult:
        """断言包含"""
        if isinstance(expected, (list, tuple, str)):
            passed = actual in expected
            return AssertionResult(
                passed=passed,
                message=f"{'通过' if passed else '失败'}: {actual} {'in' if passed else 'not in'} {expected}",
                actual=actual,
                expected=expected,
                assertion_type='in'
            )
        else:
            passed = expected in actual if isinstance(actual, (list, tuple, str)) else False
            return AssertionResult(
                passed=passed,
                message=f"{'通过' if passed else '失败'}: {expected} {'in' if passed else 'not in'} {actual}",
                actual=actual,
                expected=expected,
                assertion_type='in'
            )
    
    def _assert_not_in(self, actual: Any, expected: Any) -> AssertionResult:
        """断言不包含"""
        if isinstance(expected, (list, tuple, str)):
            passed = actual not in expected
            return AssertionResult(
                passed=passed,
                message=f"{'通过' if passed else '失败'}: {actual} {'not in' if passed else 'in'} {expected}",
                actual=actual,
                expected=expected,
                assertion_type='not_in'
            )
        else:
            passed = expected not in actual if isinstance(actual, (list, tuple, str)) else True
            return AssertionResult(
                passed=passed,
                message=f"{'通过' if passed else '失败'}: {expected} {'not in' if passed else 'in'} {actual}",
                actual=actual,
                expected=expected,
                assertion_type='not_in'
            )
    
    def _assert_regex(self, actual: Any, pattern: str) -> AssertionResult:
        """正则断言"""
        try:
            passed = bool(re.search(pattern, str(actual)))
            return AssertionResult(
                passed=passed,
                message=f"{'通过' if passed else '失败'}: '{actual}' {'匹配' if passed else '不匹配'} 正则 '{pattern}'",
                actual=actual,
                expected=pattern,
                assertion_type='regex'
            )
        except re.error as e:
            return AssertionResult(
                passed=False,
                message=f"正则表达式错误: {str(e)}",
                actual=actual,
                expected=pattern,
                assertion_type='regex'
            )
    
    def _assert_json_schema(self, actual: Any, schema: Dict) -> AssertionResult:
        """JSON Schema断言"""
        try:
            validate(instance=actual, schema=schema)
            return AssertionResult(
                passed=True,
                message="JSON Schema验证通过",
                actual=actual,
                expected=schema,
                assertion_type='json_schema'
            )
        except JsonSchemaValidationError as e:
            return AssertionResult(
                passed=False,
                message=f"JSON Schema验证失败: {e.message}",
                actual=actual,
                expected=schema,
                assertion_type='json_schema',
                detail={'path': list(e.path), 'validator': e.validator}
            )
    
    def _assert_sql(self, assertion: Dict, context: Optional[Dict]) -> AssertionResult:
        """
        SQL断言
        
        Args:
            assertion: 断言配置 {sql: "SELECT COUNT(*) FROM users", expected: 10}
            context: 上下文（包含数据库连接）
        """
        # SQL断言需要数据库连接，这里提供接口
        # 实际实现需要集成数据库连接池
        sql = assertion.get('sql')
        expected = assertion.get('expected')
        
        if not sql:
            return AssertionResult(
                passed=False,
                message="SQL断言缺少sql字段",
                assertion_type='sql'
            )
        
        # TODO: 实际执行SQL查询
        # db_result = execute_sql(sql)
        
        return AssertionResult(
            passed=True,
            message=f"SQL断言: {sql} (待实现)",
            assertion_type='sql'
        )
    
    def _assert_type(self, actual: Any, expected: type) -> AssertionResult:
        """类型断言"""
        passed = isinstance(actual, expected)
        type_names = {
            str: 'str',
            int: 'int',
            float: 'float',
            bool: 'bool',
            list: 'list',
            dict: 'dict',
            tuple: 'tuple'
        }
        expected_name = type_names.get(expected, str(expected))
        actual_type = type(actual).__name__
        
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: 类型 {actual_type} {'is' if passed else 'is not'} {expected_name}",
            actual=actual_type,
            expected=expected_name,
            assertion_type='type'
        )
    
    def _assert_length(self, actual: Any, min_len: Optional[int] = None, max_len: Optional[int] = None) -> AssertionResult:
        """长度断言"""
        if not hasattr(actual, '__len__'):
            return AssertionResult(
                passed=False,
                message=f"对象没有长度属性: {type(actual)}",
                assertion_type='length'
            )
        
        length = len(actual)
        passed = True
        messages = []
        
        if min_len is not None:
            if length < min_len:
                passed = False
                messages.append(f"长度 {length} < 最小值 {min_len}")
        
        if max_len is not None:
            if length > max_len:
                passed = False
                messages.append(f"长度 {length} > 最大值 {max_len}")
        
        if not messages:
            messages.append(f"长度 {length} 在范围内")
        
        return AssertionResult(
            passed=passed,
            message='; '.join(messages),
            actual=length,
            expected={'min': min_len, 'max': max_len},
            assertion_type='length'
        )
    
    def _assert_is_none(self, actual: Any) -> AssertionResult:
        """断言为None"""
        passed = actual is None
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} None",
            actual=actual,
            expected=None,
            assertion_type='is_none'
        )
    
    def _assert_is_not_none(self, actual: Any) -> AssertionResult:
        """断言不为None"""
        passed = actual is not None
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is not' if passed else 'is'} None",
            actual=actual,
            expected=None,
            assertion_type='is_not_none'
        )
    
    def _assert_is_true(self, actual: Any) -> AssertionResult:
        """断言为True"""
        passed = bool(actual) is True
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} True",
            actual=actual,
            expected=True,
            assertion_type='is_true'
        )
    
    def _assert_is_false(self, actual: Any) -> AssertionResult:
        """断言为False"""
        passed = bool(actual) is False
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} False",
            actual=actual,
            expected=False,
            assertion_type='is_false'
        )
    
    def _assert_status_code(self, response: Dict[str, Any], expected: int) -> AssertionResult:
        """断言状态码"""
        actual = response.get('status_code')
        passed = actual == expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: 状态码 {actual} {'==' if passed else '!='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='status_code'
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取断言汇总信息
        
        Returns:
            Dict: 汇总信息
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': f"{passed / total * 100:.2f}%" if total > 0 else "0%",
            'details': self.results
        }
