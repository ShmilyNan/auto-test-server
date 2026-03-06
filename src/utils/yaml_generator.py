"""
YAML 生成器
将 CurlRequest 对象转换为 YAML 格式的测试数据文件
支持两类查询接口智能测试用例生成：
1. 普通查询接口：GET 请求，必传 pageNum/pageSize，其他参数选填
2. 报表类查询接口：POST 请求，包含 options.basicFields/statisticsFields 等特殊字段
"""
import random
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from urllib.parse import urlparse
from itertools import combinations
from copy import deepcopy
from src.utils.logger import logger
from src.utils.curl_parser import CurlRequest
from src.utils.scenario_generator import Scenario

# 创建 YAML 实例（使用 rt 模式以支持 CommentedMap）
_yaml = YAML(typ='rt')
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


class YamlGenerator:
    """YAML 测试数据文件生成器"""

    def __init__(self, max_query_combinations: int = 5):
        """
        初始化
        Args:
            max_query_combinations: 查询条件最大组合数
        """
        self.max_query_combinations = max_query_combinations

    def generate(
        self,
        request: CurlRequest,
        module_name: Optional[str] = None,
        module_description: Optional[str] = None,
        test_case_name: Optional[str] = None,
        test_case_description: Optional[str] = None,
        priority: str = "p2",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成 YAML 数据结构
        Args:
            request: CurlRequest 对象
            module_name: 模块名称（默认从 URL 提取）
            module_description: 模块描述
            test_case_name: 测试用例名称
            test_case_description: 测试用例描述
            priority: 优先级
            tags: 标签列表
        Returns:
            Dict: YAML 数据字典
        """
        # 从 URL 提取模块名称
        if not module_name:
            module_name = self._extract_module_name(request.url)

        if not module_description:
            module_description = f"{module_name} 模块的测试用例（从 cURL 转换）"

        # 生成测试用例名称
        if not test_case_name:
            test_case_name = f"{request.method} {self._extract_endpoint(request.url)}"

        if not test_case_description:
            test_case_description = f"测试 {request.method} 请求：{request.get_path()}"

        # 默认标签
        if not tags:
            tags = ["smoke", "positive"]

        # 准备全局配置
        config = self._generate_config(request)

        # 准备测试用例
        test_case = self._generate_test_case(
            request,
            test_case_name,
            test_case_description,
            priority,
            tags
        )

        # 构建完整的 YAML 结构（使用 CommentedMap 保持顺序）
        yaml_data = CommentedMap()
        yaml_data['module'] = CommentedMap()
        yaml_data['module']['name'] = module_name
        yaml_data['module']['version'] = '1.0.0'
        yaml_data['module']['description'] = module_description
        yaml_data['module']['author'] = '从cURL转换'
        yaml_data['config'] = config
        yaml_data['test_cases'] = [test_case]

        logger.info(f"生成 YAML 数据: 模块={module_name}, 用例={test_case_name}")

        return yaml_data

    def generate_query_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str = "p1",
        tags: Optional[List[str]] = None
    ) -> List[CommentedMap]:
        """
        生成查询接口的测试用例
        根据接口类型自动识别并生成对应的测试用例：
        1. 普通查询接口：GET 请求，生成单条件/组合条件查询用例
        2. 报表类查询接口：POST 请求，按字段规则生成用例
        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表
        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []

        if not tags:
            tags = ["daily", "regression", "query", "auto-generated"]
        else:
            tags = tags + ["query", "auto-generated"]

        # 识别查询接口类型
        if self._is_report_query_interface(request):
            # 报表类查询接口
            logger.info(f"检测到报表类查询接口: {case_name}")
            test_cases = self._generate_report_query_test_cases(request, case_name, priority, tags)
        elif self._is_simple_query_interface(request):
            # 普通查询接口
            logger.info(f"检测到普通查询接口: {case_name}")
            test_cases = self._generate_simple_query_test_cases(request, case_name, priority, tags)
        else:
            # 兜底：生成基础用例
            logger.warning(f"未识别到查询接口类型，生成基础用例: {case_name}")
            test_cases.append(self._generate_test_case(
                request=request,
                name=f"{case_name}-正常流程",
                description=f"测试查询接口 {case_name} 正常流程",
                priority=priority,
                tags=tags
            ))

        return test_cases

    # ========================================
    # 查询接口类型识别方法
    # ========================================

    def _is_simple_query_interface(self, request: CurlRequest) -> bool:
        """
        判断是否为普通查询接口

        特征：GET 请求，参数在 URL query 中
        必传：pageNum, pageSize
        其他参数：选填
        Args:
            request: CurlRequest 对象
        Returns:
            bool: 是否为普通查询接口
        """
        return request.method.upper() == 'GET'

    def _is_report_query_interface(self, request: CurlRequest) -> bool:
        """
        判断是否为报表类查询接口
        特征：POST 请求，body 中包含 options.basicFields 和 options.statisticsFields
        Args:
            request: CurlRequest 对象
        Returns:
            bool: 是否为报表类查询接口
        """
        if request.method.upper() != 'POST':
            return False

        if not request.data or not isinstance(request.data, dict):
            return False

        body = request.data
        options = body.get('options', {})

        if not isinstance(options, dict):
            return False

        # 必须同时包含 basicFields 和 statisticsFields
        has_basic_fields = 'basicFields' in options and isinstance(options['basicFields'], list)
        has_statistics_fields = 'statisticsFields' in options and isinstance(options['statisticsFields'], list)

        return has_basic_fields and has_statistics_fields

    # ========================================
    # 普通查询接口用例生成
    # ========================================

    def _generate_simple_query_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成普通查询接口的测试用例

        规则：
        1. 必传字段：pageNum, pageSize
        2. 其他参数：选填，进行单条件和组合条件测试

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []

        # 提取查询参数（排除必传的分页参数）
        all_params = request.params or {}
        pagination_fields = {'pageNum', 'pageSize'}
        query_fields = {k: v for k, v in all_params.items() if k not in pagination_fields}

        if not query_fields:
            logger.warning(f"普通查询接口未发现可选查询字段: {case_name}")
            test_cases.append(self._generate_test_case(
                request=request,
                name=f"{case_name}-正常流程",
                description=f"测试查询接口 {case_name} 正常流程",
                priority=priority,
                tags=tags.copy()
            ))
            return test_cases

        # 1. 生成完整条件查询用例
        test_cases.append(self._generate_test_case(
            request=request,
            name=f"{case_name}-完整条件查询",
            description=f"使用所有查询条件的完整查询",
            priority=priority,
            tags=tags.copy()
        ))

        # 2. 生成单条件查询用例（保留分页参数）
        for field_name, field_value in query_fields.items():
            single_request = self._create_simple_query_request_with_single_field(
                request, field_name, field_value
            )
            test_cases.append(self._generate_test_case(
                request=single_request,
                name=f"{case_name}-单条件查询-{field_name}",
                description=f"仅使用 {field_name} 作为查询条件",
                priority=priority,
                tags=tags.copy()
            ))

        # 3. 生成组合条件查询用例（保留分页参数）
        if len(query_fields) > 1:
            combination_cases = self._generate_simple_query_combination_cases(
                request, case_name, query_fields, priority, tags
            )
            test_cases.extend(combination_cases)

        logger.info(f"生成普通查询测试用例 {len(test_cases)} 个: "
                   f"完整用例 1 个, 单条件用例 {len(query_fields)} 个, "
                   f"组合条件用例 {len(test_cases) - 1 - len(query_fields)} 个")

        return test_cases

    def _create_simple_query_request_with_single_field(
        self,
        request: CurlRequest,
        field_name: str,
        field_value: Any
    ) -> CurlRequest:
        """
        创建普通查询接口的单字段请求（保留分页参数）

        Args:
            request: 原始请求
            field_name: 字段名
            field_value: 字段值

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)

        # 保留分页参数，只修改查询条件
        modified_request.params = {
            'pageNum': request.params.get('pageNum', 1),
            'pageSize': request.params.get('pageSize', 100),
            field_name: field_value
        }

        return modified_request

    def _generate_simple_query_combination_cases(
        self,
        request: CurlRequest,
        case_name: str,
        query_fields: Dict[str, Any],
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成普通查询接口的组合条件用例

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            query_fields: 查询字段（不含分页参数）
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        field_names = list(query_fields.keys())

        # 生成所有可能的组合（2个到n个字段）
        all_combinations = []
        for r in range(2, len(field_names) + 1):
            all_combinations.extend(combinations(field_names, r))

        # 随机选择部分组合
        if len(all_combinations) > self.max_query_combinations:
            selected_combinations = random.sample(all_combinations, self.max_query_combinations)
        else:
            selected_combinations = all_combinations

        for combo in selected_combinations:
            combo_fields = {name: query_fields[name] for name in combo}
            modified_request = self._create_simple_query_request_with_fields(request, combo_fields)

            combo_str = '_'.join(combo)
            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-组合查询-{combo_str}",
                description=f"组合查询条件: {', '.join(combo)}",
                priority=priority,
                tags=tags.copy()
            ))

        return test_cases

    def _create_simple_query_request_with_fields(
        self,
        request: CurlRequest,
        fields: Dict[str, Any]
    ) -> CurlRequest:
        """
        创建普通查询接口的多字段请求（保留分页参数）

        Args:
            request: 原始请求
            fields: 字段名和值的映射

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)

        # 保留分页参数 + 新的查询条件
        modified_request.params = {
            'pageNum': request.params.get('pageNum', 1),
            'pageSize': request.params.get('pageSize', 100),
            **fields
        }

        return modified_request

    # ========================================
    # 报表类查询接口用例生成
    # ========================================

    def _generate_report_query_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成报表类查询接口的测试用例

        规则：
        1. 必传字段：startTime, endTime, granularity, options, timeZone
        2. options.basicFields: 可传空数组，与 filters 对应
        3. options.statisticsFields: 至少传一个
        4. filters: 字典类型，与 basicFields 对应
        5. granularity: 单选项 MONTH/DATE/HOUR
        6. 按字段规则进行单条件和组合条件测试

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        body = request.data

        # 提取关键字段
        options = body.get('options', {})
        basic_fields = options.get('basicFields', [])
        statistics_fields = options.get('statisticsFields', [])
        filters = body.get('filters', {})
        granularity = body.get('granularity', 'DAY')

        # 1. 生成完整条件查询用例
        test_cases.append(self._generate_test_case(
            request=request,
            name=f"{case_name}-完整条件查询",
            description=f"使用所有查询条件的完整查询",
            priority=priority,
            tags=tags.copy()
        ))

        # 2. 生成 granularity 单选用例
        granularity_cases = self._generate_granularity_test_cases(
            request, case_name, priority, tags
        )
        test_cases.extend(granularity_cases)

        # 3. 生成 basicFields 单条件/组合条件用例
        if basic_fields:
            basic_fields_cases = self._generate_basic_fields_test_cases(
                request, case_name, priority, tags
            )
            test_cases.extend(basic_fields_cases)

        # 4. 生成 statisticsFields 单条件/组合条件用例
        if statistics_fields:
            statistics_fields_cases = self._generate_statistics_fields_test_cases(
                request, case_name, priority, tags
            )
            test_cases.extend(statistics_fields_cases)

        # 5. 生成 filters 与 basicFields 对应的用例
        if basic_fields and filters:
            filter_cases = self._generate_filter_test_cases(
                request, case_name, priority, tags
            )
            test_cases.extend(filter_cases)

        # 6. 生成空 filters 用例（basicFields 为空或 filters 为空）
        empty_filter_cases = self._generate_empty_filters_test_cases(
            request, case_name, priority, tags
        )
        test_cases.extend(empty_filter_cases)

        logger.info(f"生成报表查询测试用例 {len(test_cases)} 个")

        return test_cases

    def _generate_granularity_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成 granularity 单选用例

        granularity 与时间格式对应：
        - MONTH → yyyymm
        - DATE → yyyymmdd
        - HOUR → yyyymmddhh

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        granularity_options = ['MONTH', 'DATE', 'HOUR']

        # 时间格式映射
        time_formats = {
            'MONTH': ('202602', '202602'),      # yyyymm
            'DATE': ('20260227', '20260227'),   # yyyymmdd
            'HOUR': ('2026022700', '2026022723') # yyyymmddhh
        }

        for gran in granularity_options:
            start_time, end_time = time_formats[gran]
            modified_request = self._create_report_request_with_granularity(
                request, gran, start_time, end_time
            )

            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-granularity-{gran}",
                description=f"时间粒度: {gran}, 时间格式: {start_time}",
                priority=priority,
                tags=tags.copy()
            ))

        return test_cases

    def _create_report_request_with_granularity(
        self,
        request: CurlRequest,
        granularity: str,
        start_time: str,
        end_time: str
    ) -> CurlRequest:
        """
        创建指定 granularity 的报表请求

        Args:
            request: 原始请求
            granularity: 时间粒度
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['granularity'] = granularity
        body['startTime'] = start_time
        body['endTime'] = end_time

        modified_request.data = body
        return modified_request

    def _generate_basic_fields_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成 basicFields 单条件/组合条件用例

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        body = request.data
        options = body.get('options', {})
        basic_fields = options.get('basicFields', [])

        if not basic_fields:
            return test_cases

        # 1. 单条件用例
        for field in basic_fields:
            modified_request = self._create_report_request_with_single_basic_field(
                request, field
            )
            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-basicFields-单条件-{field}",
                description=f"basicFields 仅包含: {field}",
                priority=priority,
                tags=tags.copy()
            ))

        # 2. 组合条件用例（随机选择最多 3 个组合）
        if len(basic_fields) > 1:
            all_combos = []
            for r in range(2, min(len(basic_fields) + 1, 4)):
                all_combos.extend(combinations(basic_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                modified_request = self._create_report_request_with_basic_fields(
                    request, list(combo)
                )
                combo_str = '_'.join(combo)
                test_cases.append(self._generate_test_case(
                    request=modified_request,
                    name=f"{case_name}-basicFields-组合-{combo_str}",
                    description=f"basicFields 组合: {', '.join(combo)}",
                    priority=priority,
                    tags=tags.copy()
                ))

        return test_cases

    def _create_report_request_with_single_basic_field(
        self,
        request: CurlRequest,
        field: str
    ) -> CurlRequest:
        """
        创建仅包含单个 basicField 的报表请求

        Args:
            request: 原始请求
            field: 字段名

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['options']['basicFields'] = [field]

        # 同步更新 filters（只保留该字段）
        original_filters = body.get('filters', {})
        if field in original_filters:
            body['filters'] = {field: original_filters[field]}
        else:
            body['filters'] = {}

        modified_request.data = body
        return modified_request

    def _create_report_request_with_basic_fields(
        self,
        request: CurlRequest,
        fields: List[str]
    ) -> CurlRequest:
        """
        创建包含指定 basicFields 的报表请求

        Args:
            request: 原始请求
            fields: 字段列表

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['options']['basicFields'] = fields

        # 同步更新 filters
        original_filters = body.get('filters', {})
        new_filters = {}
        for field in fields:
            if field in original_filters:
                new_filters[field] = original_filters[field]
        body['filters'] = new_filters

        modified_request.data = body
        return modified_request

    def _generate_statistics_fields_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成 statisticsFields 单条件/组合条件用例
        注意：statisticsFields 至少传一个

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        body = request.data
        options = body.get('options', {})
        statistics_fields = options.get('statisticsFields', [])

        if not statistics_fields:
            return test_cases

        # 1. 单条件用例
        for field in statistics_fields:
            modified_request = self._create_report_request_with_single_statistics_field(
                request, field
            )
            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-statisticsFields-单条件-{field}",
                description=f"statisticsFields 仅包含: {field}",
                priority=priority,
                tags=tags.copy()
            ))

        # 2. 组合条件用例（随机选择最多 3 个组合）
        if len(statistics_fields) > 1:
            all_combos = []
            for r in range(2, min(len(statistics_fields) + 1, 4)):
                all_combos.extend(combinations(statistics_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                modified_request = self._create_report_request_with_statistics_fields(
                    request, list(combo)
                )
                combo_str = '_'.join(combo)
                test_cases.append(self._generate_test_case(
                    request=modified_request,
                    name=f"{case_name}-statisticsFields-组合-{combo_str}",
                    description=f"statisticsFields 组合: {', '.join(combo)}",
                    priority=priority,
                    tags=tags.copy()
                ))

        return test_cases

    def _create_report_request_with_single_statistics_field(
        self,
        request: CurlRequest,
        field: str
    ) -> CurlRequest:
        """
        创建仅包含单个 statisticsField 的报表请求

        Args:
            request: 原始请求
            field: 字段名

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['options']['statisticsFields'] = [field]
        modified_request.data = body
        return modified_request

    def _create_report_request_with_statistics_fields(
        self,
        request: CurlRequest,
        fields: List[str]
    ) -> CurlRequest:
        """
        创建包含指定 statisticsFields 的报表请求

        Args:
            request: 原始请求
            fields: 字段列表

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['options']['statisticsFields'] = fields
        modified_request.data = body
        return modified_request

    def _generate_filter_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成 filters 单条件/组合条件用例
        filters 与 basicFields 对应

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        body = request.data
        filters = body.get('filters', {})

        if not filters:
            return test_cases

        # 1. 单条件用例
        for field_name, field_value in filters.items():
            modified_request = self._create_report_request_with_single_filter(
                request, field_name, field_value
            )
            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-filter-单条件-{field_name}",
                description=f"filter 仅包含: {field_name}",
                priority=priority,
                tags=tags.copy()
            ))

        # 2. 组合条件用例（随机选择最多 3 个组合）
        if len(filters) > 1:
            all_combos = []
            filter_fields = list(filters.keys())
            for r in range(2, min(len(filter_fields) + 1, 4)):
                all_combos.extend(combinations(filter_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                combo_filters = {name: filters[name] for name in combo}
                modified_request = self._create_report_request_with_filters(
                    request, combo_filters
                )
                combo_str = '_'.join(combo)
                test_cases.append(self._generate_test_case(
                    request=modified_request,
                    name=f"{case_name}-filter-组合-{combo_str}",
                    description=f"filter 组合: {', '.join(combo)}",
                    priority=priority,
                    tags=tags.copy()
                ))

        return test_cases

    def _create_report_request_with_single_filter(
        self,
        request: CurlRequest,
        field_name: str,
        field_value: Any
    ) -> CurlRequest:
        """
        创建仅包含单个 filter 的报表请求

        Args:
            request: 原始请求
            field_name: 字段名
            field_value: 字段值

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        # 只保留单个 filter
        body['filters'] = {field_name: field_value}

        # 同步更新 basicFields（只保留该字段对应的 basicField）
        original_basic_fields = body.get('options', {}).get('basicFields', [])
        if field_name in original_basic_fields:
            body['options']['basicFields'] = [field_name]

        modified_request.data = body
        return modified_request

    def _create_report_request_with_filters(
        self,
        request: CurlRequest,
        filters: Dict[str, Any]
    ) -> CurlRequest:
        """
        创建包含指定 filters 的报表请求

        Args:
            request: 原始请求
            filters: 过滤条件字典

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)
        body = deepcopy(request.data)

        body['filters'] = filters

        # 同步更新 basicFields
        original_basic_fields = body.get('options', {}).get('basicFields', [])
        new_basic_fields = [f for f in original_basic_fields if f in filters]
        body['options']['basicFields'] = new_basic_fields

        modified_request.data = body
        return modified_request

    def _generate_empty_filters_test_cases(
        self,
        request: CurlRequest,
        case_name: str,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成空 filters 用例

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []

        # 1. filters 为空
        modified_request = deepcopy(request)
        body = deepcopy(request.data)
        body['filters'] = {}
        modified_request.data = body

        test_cases.append(self._generate_test_case(
            request=modified_request,
            name=f"{case_name}-filters-空",
            description="filters 为空字典",
            priority=priority,
            tags=tags.copy()
        ))

        # 2. basicFields 为空
        modified_request = deepcopy(request)
        body = deepcopy(request.data)
        body['options']['basicFields'] = []
        body['filters'] = {}
        modified_request.data = body

        test_cases.append(self._generate_test_case(
            request=modified_request,
            name=f"{case_name}-basicFields-空",
            description="basicFields 和 filters 均为空",
            priority=priority,
            tags=tags.copy()
        ))

        return test_cases

    # ========================================
    # 通用方法（保留向后兼容）
    # ========================================

    def _extract_all_query_fields(self, request: CurlRequest) -> Dict[str, Any]:
        """
        提取所有查询字段（不区分类型）

        对于 GET 请求，从 params 中提取
        对于 POST 请求，从 body 中提取（包括 filters 内的字段）

        Args:
            request: CurlRequest 对象

        Returns:
            Dict[str, Any]: 字段名和值的映射
        """
        query_fields = {}

        # GET 请求：从 params 提取
        if request.method.upper() == 'GET':
            if request.params:
                query_fields.update(request.params)

        # POST/PUT 请求：从 body 提取
        if request.data and isinstance(request.data, dict):
            body = request.data

            # 提取 filters 中的字段
            if 'filters' in body and isinstance(body['filters'], dict):
                query_fields.update(body['filters'])

            # 提取 body 中其他字段（排除 filters、options 等配置类字段）
            config_fields = {'filters', 'options', 'pagination', 'orderAscFields', 'orderDescFields'}
            for key, value in body.items():
                if key not in config_fields:
                    query_fields[key] = value

        return query_fields

    def _generate_single_field_query_case(
        self,
        request: CurlRequest,
        case_name: str,
        field_name: str,
        field_value: Any,
        priority: str,
        tags: List[str]
    ) -> CommentedMap:
        """
        生成单字段查询测试用例

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            field_name: 字段名
            field_value: 字段值
            priority: 优先级
            tags: 标签列表

        Returns:
            CommentedMap: 测试用例
        """
        # 深拷贝请求对象，修改查询条件
        modified_request = self._create_request_with_single_field(request, field_name, field_value)

        return self._generate_test_case(
            request=modified_request,
            name=f"{case_name}-单条件查询-{field_name}",
            description=f"仅使用 {field_name} 作为查询条件",
            priority=priority,
            tags=tags
        )

    def _generate_combination_query_cases(
        self,
        request: CurlRequest,
        case_name: str,
        query_fields: Dict[str, Any],
        max_combinations: int,
        priority: str,
        tags: List[str]
    ) -> List[CommentedMap]:
        """
        生成组合条件查询测试用例

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            query_fields: 查询字段
            max_combinations: 最大组合数
            priority: 优先级
            tags: 标签列表

        Returns:
            List[CommentedMap]: 测试用例列表
        """
        test_cases = []
        field_names = list(query_fields.keys())

        # 生成所有可能的组合（2个到n个字段）
        all_combinations = []
        for r in range(2, len(field_names) + 1):
            all_combinations.extend(combinations(field_names, r))

        # 随机选择部分组合
        if len(all_combinations) > max_combinations:
            selected_combinations = random.sample(all_combinations, max_combinations)
        else:
            selected_combinations = all_combinations

        for combo in selected_combinations:
            # 构建组合查询条件
            combo_fields = {name: query_fields[name] for name in combo}
            modified_request = self._create_request_with_fields(request, combo_fields)

            combo_str = '_'.join(combo)
            test_cases.append(self._generate_test_case(
                request=modified_request,
                name=f"{case_name}-组合查询-{combo_str}",
                description=f"组合查询条件: {', '.join(combo)}",
                priority=priority,
                tags=tags.copy()
            ))

        return test_cases

    def _create_request_with_single_field(
        self,
        request: CurlRequest,
        field_name: str,
        field_value: Any
    ) -> CurlRequest:
        """
        创建仅包含单个查询字段的请求

        Args:
            request: 原始请求
            field_name: 字段名
            field_value: 字段值

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)

        # GET 请求：修改 params
        if request.method.upper() == 'GET':
            modified_request.params = {field_name: field_value}
        # POST 请求：修改 body
        else:
            if request.data and isinstance(request.data, dict):
                body = deepcopy(request.data)

                # 检查字段是否在 filters 中
                if 'filters' in body and isinstance(body['filters'], dict):
                    if field_name in body['filters']:
                        body['filters'] = {field_name: field_value}
                        modified_request.data = body
                        return modified_request

                # 字段在 body 顶层
                modified_request.data = {field_name: field_value}

        return modified_request

    def _create_request_with_fields(
        self,
        request: CurlRequest,
        fields: Dict[str, Any]
    ) -> CurlRequest:
        """
        创建包含多个查询字段的请求

        Args:
            request: 原始请求
            fields: 字段名和值的映射

        Returns:
            CurlRequest: 修改后的请求
        """
        modified_request = deepcopy(request)

        # GET 请求：修改 params
        if request.method.upper() == 'GET':
            modified_request.params = fields
        # POST 请求：修改 body
        else:
            if request.data and isinstance(request.data, dict):
                body = deepcopy(request.data)

                # 分离 filters 中的字段和其他字段
                filter_fields = {}
                other_fields = {}

                original_filters = body.get('filters', {})
                for name, value in fields.items():
                    if name in original_filters:
                        filter_fields[name] = value
                    else:
                        other_fields[name] = value

                # 更新 filters
                if filter_fields:
                    body['filters'] = filter_fields

                # 更新其他字段
                for name, value in other_fields.items():
                    body[name] = value

                modified_request.data = body

        return modified_request

    def is_query_interface(self, request: CurlRequest, case_name: str = "") -> bool:
        """
        判断是否为查询接口

        支持两类查询接口：
        1. 普通查询接口：GET 请求
        2. 报表类查询接口：POST 请求 + body 中包含 options.basicFields/statisticsFields

        Args:
            request: CurlRequest 对象
            case_name: 用例名称（用于日志）

        Returns:
            bool: 是否为查询接口
        """
        # 普通查询接口：GET 请求
        if self._is_simple_query_interface(request):
            return True

        # 报表类查询接口：POST 请求 + options.basicFields/statisticsFields
        if self._is_report_query_interface(request):
            return True

        return False

    def _extract_module_name(self, url: str) -> str:
        """
        从 URL 提取模块名称

        Args:
            url: URL 字符串

        Returns:
            str: 模块名称
        """
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        # 通常第二个路径段是模块名
        if len(path_parts) >= 2:
            return path_parts[1].replace('-', '_')

        return "test_module"

    def _extract_endpoint(self, url: str) -> str:
        """
        从 URL 提取端点名称

        Args:
            url: URL 字符串

        Returns:
            str: 端点名称
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        # 提取最后一段路径作为端点名
        if path:
            parts = path.split('/')
            return parts[-1]

        return "endpoint"

    def _generate_config(self, request: CurlRequest) -> CommentedMap:
        """
        生成全局配置

        Args:
            request: CurlRequest 对象

        Returns:
            CommentedMap: 配置字典（保持字段顺序）
        """
        config = CommentedMap()
        config['headers'] = CommentedMap()
        config['timeout'] = 30

        # 从请求头中提取有用的默认请求头
        important_headers = ['Content-Type', 'Accept', 'Authorization']

        for header in important_headers:
            if header in request.headers:
                config['headers'][header] = request.headers[header]

        # 如果没有 Content-Type，设置默认值
        if 'Content-Type' not in config['headers'] and request.method.upper() == 'POST':
            config['headers']['Content-Type'] = 'application/json'

        if 'Accept' not in config['headers']:
            config['headers']['Accept'] = 'application/json'

        return config

    def _generate_test_case(
        self,
        request: CurlRequest,
        name: str,
        description: str,
        priority: str,
        tags: List[str]
    ) -> CommentedMap:
        """
        生成测试用例

        Args:
            request: CurlRequest 对象
            name: 用例名称
            description: 用例描述
            priority: 优先级
            tags: 标签列表

        Returns:
            CommentedMap: 测试用例字典（字段顺序与 user_module.yaml 一致）
        """
        # 按照 user_module.yaml 的字段顺序构建（使用 CommentedMap 保持顺序）
        test_case = CommentedMap()

        # 1. name (必填)
        test_case['name'] = name

        # 2. description (必填)
        test_case['description'] = description

        # 3. order (可选，暂时不设置)
        # test_case['order'] = 0

        # 4. priority (必填)
        test_case['priority'] = priority

        # 5. tags (必填)
        test_case['tags'] = tags

        # 6. method (必填)
        test_case['method'] = request.method.upper()

        # 7. url (必填)
        test_case['url'] = request.get_path()

        # 8. headers (可选)
        config_headers = self._generate_config(request)['headers']
        case_headers = {}

        for key, value in request.headers.items():
            # 如果 header 值与全局配置不同，或者包含敏感信息，则添加到用例级别
            if key not in config_headers or config_headers[key] != value:
                # 过滤掉一些浏览器相关的 header
                if not self._is_browser_header(key):
                    case_headers[key] = value

        if case_headers:
            test_case['headers'] = case_headers

        # 9. params (可选)
        if request.params:
            test_case['params'] = request.params

        # 10. body (可选)
        if request.data is not None:
            test_case['body'] = request.data

        # 11. validate (必填)
        test_case['validate'] = [
            {
                'type': 'status_code',
                'expected': 200
            }
        ]

        # 如果有 JSON 响应，添加额外的断言
        if request.headers.get('Accept', '').lower() == 'application/json':
            # 添加通用的 JSON 断言
            test_case['validate'].append({
                'type': 'eq',
                'path': 'body.code',
                'expected': 0
            })

        # 12. extract (可选，暂时不添加)
        # 13. metadata (可选，暂时不添加)
        # 14. depends_on (可选，暂时不添加)

        return test_case

    def _is_browser_header(self, header_name: str) -> bool:
        """
        判断是否为浏览器相关的 header（通常不需要在测试中保留）

        Args:
            header_name: header 名称

        Returns:
            bool: 是否为浏览器 header
        """
        browser_headers = [
            'User-Agent',
            'Referer',
            'Origin',
            'Sec-Ch-Ua',
            'Sec-Ch-Ua-Mobile',
            'Sec-Ch-Ua-Platform',
            'Sec-Fetch-Dest',
            'Sec-Fetch-Mode',
            'Sec-Fetch-Site',
            'Sec-Fetch-User',
            'Priority'
        ]

        return header_name.lower() in [h.lower() for h in browser_headers]

    def save_to_file(
        self,
        yaml_data: Dict[str, Any],
        output_dir: str = "test_data",
        filename: Optional[str] = None
    ) -> str:
        """
        将 YAML 数据保存到文件

        Args:
            yaml_data: YAML 数据字典
            output_dir: 输出目录
            filename: 文件名（不包含扩展名）

        Returns:
            str: 保存的文件路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        if not filename:
            module_name = yaml_data['module']['name']
            filename = f"{module_name}_module"

        # 添加时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{filename}_{timestamp}"

        file_path = output_path / f"{filename_with_timestamp}.yaml"

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 从 cURL 转换的测试数据文件\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(yaml_data, f)

        logger.info(f"YAML 文件已保存: {file_path}")

        return str(file_path)

    def append_to_file(
        self,
        request: CurlRequest,
        file_path: str,
        test_case_name: Optional[str] = None,
        test_case_description: Optional[str] = None,
        priority: str = "p2",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        将测试用例追加到已有的 YAML 文件中

        Args:
            request: CurlRequest 对象
            file_path: 目标 YAML 文件路径
            test_case_name: 测试用例名称
            test_case_description: 测试用例描述
            priority: 优先级
            tags: 标签列表

        Returns:
            str: 文件路径

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        yaml_path = Path(file_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取现有文件
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()

        # 解析 YAML
        existing_data = _yaml.load(yaml_content) if yaml_content.strip() else None

        if not existing_data:
            raise ValueError(f"无法解析 YAML 文件: {file_path}")

        if 'test_cases' not in existing_data:
            existing_data['test_cases'] = []

        # 生成测试用例名称和描述
        if not test_case_name:
            test_case_name = f"{request.method} {self._extract_endpoint(request.url)}"

        if not test_case_description:
            test_case_description = f"测试 {request.method} 请求：{request.get_path()}"

        # 默认标签
        if not tags:
            tags = ["smoke", "positive"]

        # 生成新的测试用例
        new_test_case = self._generate_test_case(
            request,
            test_case_name,
            test_case_description,
            priority,
            tags
        )

        # 追加到 test_cases 列表
        existing_data['test_cases'].append(new_test_case)

        # 备份原文件
        backup_path = yaml_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        yaml_path.rename(backup_path)
        logger.debug(f"原文件已备份到: {backup_path}")

        # 写回文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 测试数据文件（追加模式）\n")
            f.write(f"# 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(existing_data, f)

        logger.info(f"测试用例已追加到文件: {file_path}")
        logger.info(f"文件中共有 {len(existing_data['test_cases'])} 个测试用例")

        return str(file_path)

    def append_scenarios_to_file(
        self,
        scenarios: List[Scenario],
        file_path: str,
        module_name: Optional[str] = None,
        module_description: Optional[str] = None
    ) -> Tuple[str, int, int]:
        """
        将多个场景追加到已有的 YAML 文件中（智能去重）

        Args:
            scenarios: 场景列表
            file_path: 目标 YAML 文件路径
            module_name: 模块名称（如果文件不存在）
            module_description: 模块描述

        Returns:
            Tuple[str, int, int]: (文件路径, 添加的场景数, 跳过的场景数)
        """
        yaml_path = Path(file_path)

        # 获取已存在的用例名称
        existing_cases = set()
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    existing_data = _yaml.load(f)

                if existing_data and 'test_cases' in existing_data:
                    existing_cases = {case.get('name', '') for case in existing_data['test_cases']}
            except Exception as e:
                logger.warning(f"读取现有 YAML 文件失败: {e}")

        # 准备要添加的场景（过滤已存在的）
        new_scenarios = []
        skipped_count = 0

        for scenario in scenarios:
            if scenario.name in existing_cases:
                logger.debug(f"场景已存在，跳过: {scenario.name}")
                skipped_count += 1
            else:
                new_scenarios.append(scenario)

        if not new_scenarios:
            logger.info(f"所有场景已存在，无需追加")
            return str(yaml_path), 0, skipped_count

        # 如果文件不存在，创建新文件
        if not yaml_path.exists():
            if not module_name:
                module_name = yaml_path.stem

            if not module_description:
                module_description = f"{module_name} 模块的测试用例"

            # 生成全局配置（使用第一个场景的请求）
            first_scenario = new_scenarios[0]
            config = self._generate_config(first_scenario.request)

            # 使用 CommentedMap 保持字段顺序
            yaml_data = CommentedMap()
            yaml_data['module'] = CommentedMap()
            yaml_data['module']['name'] = module_name
            yaml_data['module']['version'] = '1.0.0'
            yaml_data['module']['description'] = module_description
            yaml_data['module']['author'] = '从cURL转换'
            yaml_data['config'] = config
            yaml_data['test_cases'] = []
        else:
            # 读取现有文件
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

            existing_data = _yaml.load(yaml_content) if yaml_content.strip() else None

            if not existing_data:
                raise ValueError(f"无法解析 YAML 文件: {file_path}")

            if 'test_cases' not in existing_data:
                existing_data['test_cases'] = []

            yaml_data = existing_data

        # 将场景转换为测试用例
        for scenario in new_scenarios:
            test_case = self._generate_test_case(
                scenario.request,
                scenario.name,
                scenario.description,
                scenario.priority,
                scenario.tags
            )

            # 修改期望状态码
            for validate in test_case['validate']:
                if validate['type'] == 'status_code':
                    validate['expected'] = scenario.expected_status

            yaml_data['test_cases'].append(test_case)

        # 备份原文件（如果文件已存在）
        if yaml_path.exists():
            backup_path = yaml_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            yaml_path.rename(backup_path)
            logger.debug(f"原文件已备份到: {backup_path}")

        # 确保目录存在
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        # 写回文件
        with open(yaml_path, 'w', encoding='utf-8') as f:
            # 添加注释
            f.write(f"# 测试数据文件（批量追加模式）\n")
            f.write(f"# 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# ========================================\n\n")

            # 写入 YAML 内容
            _yaml.dump(yaml_data, f)

        logger.info(f"已追加 {len(new_scenarios)} 个场景到文件: {file_path}")
        logger.info(f"跳过 {skipped_count} 个已存在的场景")
        logger.info(f"文件中共有 {len(yaml_data['test_cases'])} 个测试用例")

        return str(yaml_path), len(new_scenarios), skipped_count


def convert_curl_to_yaml(
    curl_command: str,
    output_dir: str = "test_data",
    filename: Optional[str] = None,
    module_name: Optional[str] = None,
    module_description: Optional[str] = None,
    test_case_name: Optional[str] = None,
    test_case_description: Optional[str] = None,
    priority: str = "p2",
    tags: Optional[List[str]] = None
) -> str:
    """
    便捷函数：将 cURL 命令转换为 YAML 文件

    Args:
        curl_command: cURL 命令字符串
        output_dir: 输出目录
        filename: 文件名（不包含扩展名）
        module_name: 模块名称
        module_description: 模块描述
        test_case_name: 测试用例名称
        test_case_description: 测试用例描述
        priority: 优先级
        tags: 标签列表

    Returns:
        str: 保存的文件路径
    """
    from src.utils.curl_parser import CurlParser

    # 解析 cURL
    parser = CurlParser()
    request = parser.parse(curl_command)

    # 生成 YAML
    generator = YamlGenerator()
    yaml_data = generator.generate(
        request=request,
        module_name=module_name,
        module_description=module_description,
        test_case_name=test_case_name,
        test_case_description=test_case_description,
        priority=priority,
        tags=tags
    )

    # 保存文件
    return generator.save_to_file(yaml_data, output_dir, filename)


if __name__ == "__main__":
    # 测试 YAML 生成
    from src.utils.curl_parser import CurlParser

    # 测试登录接口
    login_curl = """curl 'https://api.example.com/login' -H 'content-type: application/json' --data-raw '{"username":"test","password":"test123"}'"""

    parser = CurlParser()
    request = parser.parse(login_curl)

    generator = YamlGenerator()

    # 测试查询接口检测
    print(f"是否为查询接口: {generator.is_query_interface(request)}")

    # 生成 YAML
    yaml_data = generator.generate(request, module_name="test_module")

    # 打印结果
    print(f"模块名称: {yaml_data['module']['name']}")
    print(f"测试用例数: {len(yaml_data['test_cases'])}")
