"""
多元化断言验证器
支持JSON断言、SQL断言、JSON-Schema断言、正则断言、Python assert断言
"""
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from jsonschema import validate, ValidationError as JsonSchemaValidationError
from src.utils.logger import logger


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
        'array_contains': '数组包含元素',
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
        elif assert_type == 'array_contains':
            return self._assert_array_contains(response, path, expected)
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

    @staticmethod
    def _extract_value(data: Any, path: str) -> Any:
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

    @staticmethod
    def _assert_equal(actual: Any, expected: Any) -> AssertionResult:
        """断言等于"""
        passed = actual == expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'==' if passed else '!='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='eq'
        )

    @staticmethod
    def _assert_not_equal(actual: Any, expected: Any) -> AssertionResult:
        """断言不等于"""
        passed = actual != expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'!=' if passed else '=='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='ne'
        )

    @staticmethod
    def _assert_greater(actual: Any, expected: Any) -> AssertionResult:
        """断言大于"""
        passed = actual > expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'>' if passed else '<='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='gt'
        )

    @staticmethod
    def _assert_less(actual: Any, expected: Any) -> AssertionResult:
        """断言小于"""
        passed = actual < expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'<' if passed else '>='} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='lt'
        )

    @staticmethod
    def _assert_greater_equal(actual: Any, expected: Any) -> AssertionResult:
        """断言大于等于"""
        passed = actual >= expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'>=' if passed else '<'} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='gte'
        )

    @staticmethod
    def _assert_less_equal(actual: Any, expected: Any) -> AssertionResult:
        """断言小于等于"""
        passed = actual <= expected
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'<=' if passed else '>'} {expected}",
            actual=actual,
            expected=expected,
            assertion_type='lte'
        )

    @staticmethod
    def _assert_in(actual: Any, expected: Any) -> AssertionResult:
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

    @staticmethod
    def _assert_not_in(actual: Any, expected: Any) -> AssertionResult:
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

    def _assert_array_contains(
            self,
            response: Dict[str, Any],
            path: str,
            expected: Any
    ) -> AssertionResult:
        """
        数组包含断言
        验证数组中是否存在符合条件的元素
        使用方式:
        - path: body.rows[*].offerId  # 提取所有 rows 中的 offerId
        - expected: "${$extract.offerId}"  # 验证是否包含这个值
        Args:
            response: 响应数据
            path: 提取路径，支持通配符 [*]
            expected: 期望包含的值
        Returns:
            AssertionResult: 断言结果
        """
        try:
            # 解析路径
            # 例如: body.rows[*].offerId
            # 需要提取 body.rows 数组中所有元素的 offerId

            if '[*]' not in path:
                # 如果没有通配符，回退到普通的 in 断言
                actual = self._extract_value(response, path)
                return AssertionResult(
                    passed=actual == expected,
                    message=f"{'通过' if actual == expected else '失败'}: {actual} {'==' if actual == expected else '!='} {expected}",
                    actual=actual,
                    expected=expected,
                    assertion_type='array_contains'
                )

            # 分割路径
            # body.rows[*].offerId -> ['body', 'rows', '[*]', 'offerId']
            parts = path.split('.')

            # 找到数组位置和字段位置
            array_path = []
            field_path = None
            found_wildcard = False

            for i, part in enumerate(parts):
                if '[*]' in part:
                    found_wildcard = True
                    # 保存通配符之前的路径（不包括通配符）
                    # 例如: rows[*] -> rows
                    array_key = part.replace('[*]', '')
                    array_path.append(array_key)
                    # 保存通配符之后的路径
                    # 例如: offerId
                    field_path = '.'.join(parts[i + 1:]) if i + 1 < len(parts) else None
                    break
                else:
                    array_path.append(part)

            if not found_wildcard:
                return AssertionResult(
                    passed=False,
                    message=f"无效的通配符路径: {path}",
                    assertion_type='array_contains'
                )

            # 提取数组
            array_data = response
            for key in array_path:
                if isinstance(array_data, dict):
                    array_data = array_data.get(key)
                else:
                    array_data = None
                    break

                if array_data is None:
                    break

            if not isinstance(array_data, (list, tuple)):
                return AssertionResult(
                    passed=False,
                    message=f"路径 {array_path} 不是数组: {type(array_data)}",
                    assertion_type='array_contains',
                    actual=None,
                    expected=expected
                )

            # 从数组中提取指定字段的值
            extracted_values = []
            for item in array_data:
                if not isinstance(item, dict):
                    continue

                # 提取字段
                value = item
                if field_path:
                    # 支持嵌套字段，例如 items[*].details.id
                    field_parts = field_path.split('.')
                    for field_key in field_parts:
                        if isinstance(value, dict):
                            value = value.get(field_key)
                        elif isinstance(value, (list, tuple)) and field_key.isdigit():
                            value = value[int(field_key)]
                        else:
                            value = None
                            break
                        if value is None:
                            break

                extracted_values.append(str(value))

            # 验证是否包含 expected
            passed = expected in extracted_values

            # 如果没有找到，提供更多信息
            message = f"{'通过' if passed else '失败'}: {expected} {'在' if passed else '不在'} 提取的值列表中"
            if not passed:
                message += f"\n提取的值列表: {extracted_values}"

            return AssertionResult(
                passed=passed,
                message=message,
                actual=extracted_values,
                expected=expected,
                assertion_type='array_contains',
                detail={
                    'array_length': len(array_data),
                    'extracted_count': len(extracted_values),
                    'sample_values': extracted_values[:10] if len(extracted_values) > 10 else extracted_values
                }
            )

        except Exception as e:
            return AssertionResult(
                passed=False,
                message=f"数组包含断言执行异常: {str(e)}",
                assertion_type='array_contains',
                expected=expected
            )

    @staticmethod
    def _assert_regex(actual: Any, pattern: str) -> AssertionResult:
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

    @staticmethod
    def _assert_json_schema(actual: Any, schema: Dict) -> AssertionResult:
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

    @staticmethod
    def _assert_sql(assertion: Dict, context: Optional[Dict]) -> AssertionResult:
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

        # 从context获取数据库配置
        db_config = context.get('db_config') if context else None

        if not db_config:
            return AssertionResult(
                passed=False,
                message="SQL断言缺少数据库配置，请在context中提供db_config",
                assertion_type='sql'
            )

        try:
            # 执行sql查询
            actual = Validator._execute_sql_query(sql, db_config)

            # 比较结果
            passed = (expected == actual) if expected is not None else True

            return AssertionResult(
                passed=passed,
                message=f"SQL断言: {sql}, 实际值: {actual}, 期望值: {expected}",
                actual=actual,
                expected=expected,
                assertion_type='sql'
            )
        except Exception as e:
            return AssertionResult(
                passed=False,
                message=f"SQL执行失败: {str(e)}",
                assertion_type='sql'
            )

    @staticmethod
    def _execute_sql_query(sql: str, db_config: Dict) -> Any:
        """执行SQL查询并返回结果"""
        from sqlalchemy import create_engine, text

        db_type = db_config.get('type', 'mysql')
        host = db_config.get('host')
        port = db_config.get('port', 3306)
        user = db_config.get('user')
        password = db_config.get('password')
        database = db_config.get('database')

        if db_type == 'mysql':
            url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == 'postgresql':
            url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        elif db_type == 'sqlite':
            url = f"sqlite:///{database}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            # 如果是SELECT，返回第一行第一列；否则返回影响的行数
            if sql.strip().upper().startswith('SELECT'):
                row = result.fetchone()
                return row[0] if row else None
            else:
                conn.commit()
                return result.rowcount

    @staticmethod
    def _assert_type(actual: Any, expected: Union[type, str]) -> AssertionResult:
        """类型断言"""
        type_mapping = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple
        }

        if isinstance(expected, str):
            if expected in type_mapping:
                expected_type = type_mapping[expected]
                expected_name = expected
            else:
                raise ValueError(f"不支持类型: {expected}")
        else:
            expected_type = expected
            # type_names = {
            #     str: 'str',
            #     int: 'int',
            #     float: 'float',
            #     bool: 'bool',
            #     list: 'list',
            #     dict: 'dict',
            #     tuple: 'tuple'
            # }
            # expected_name = type_names.get(expected_type, str(expected_type))
            expected_name = expected_type.__name__

        passed = isinstance(actual, expected_type)
        actual_type = type(actual).__name__
        
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: 类型 {actual_type} {'is' if passed else 'is not'} {expected_name}",
            actual=actual_type,
            expected=expected_name,
            assertion_type='type'
        )

    @staticmethod
    def _assert_length(actual: Any, min_len: Optional[int] = None, max_len: Optional[int] = None) -> AssertionResult:
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

    @staticmethod
    def _assert_is_none(actual: Any) -> AssertionResult:
        """断言为None"""
        passed = actual is None
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} None",
            actual=actual,
            expected=None,
            assertion_type='is_none'
        )

    @staticmethod
    def _assert_is_not_none(actual: Any) -> AssertionResult:
        """断言不为None"""
        passed = actual is not None
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is not' if passed else 'is'} None",
            actual=actual,
            expected=None,
            assertion_type='is_not_none'
        )

    @staticmethod
    def _assert_is_true(actual: Any) -> AssertionResult:
        """断言为True"""
        passed = bool(actual) is True
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} True",
            actual=actual,
            expected=True,
            assertion_type='is_true'
        )

    @staticmethod
    def _assert_is_false(actual: Any) -> AssertionResult:
        """断言为False"""
        passed = bool(actual) is False
        return AssertionResult(
            passed=passed,
            message=f"{'通过' if passed else '失败'}: {actual} {'is' if passed else 'is not'} False",
            actual=actual,
            expected=False,
            assertion_type='is_false'
        )

    @staticmethod
    def _assert_status_code(response: Dict[str, Any], expected: int) -> AssertionResult:
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
