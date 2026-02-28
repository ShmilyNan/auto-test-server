"""
场景生成器
从一个 cURL 生成多个测试场景（正向和逆向）
支持两类查询接口识别：
1. 普通查询接口：GET 请求
2. 报表类查询接口：POST 请求 + body 中包含 options.basicFields/statisticsFields
"""
from typing import Dict, List, Any
from src.utils.logger import logger
from dataclasses import dataclass
from src.utils.curl_parser import CurlRequest


@dataclass
class Scenario:
    """测试场景"""
    name: str                      # 场景名称
    description: str               # 场景描述
    request: CurlRequest          # 请求对象
    expected_status: int = 200    # 期望状态码
    priority: str = "p1"          # 优先级
    tags: List[str] = None        # 标签
    is_query_interface: bool = False  # 是否为查询接口


class ScenarioGenerator:
    """场景生成器"""

    def __init__(self):
        self.default_priority = "p1"
        self.default_tags = ["daily", "regression"]

    def generate_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        method: str = "POST",
        is_new: bool = False
    ) -> List[Scenario]:
        """
        从 cURL 请求生成多个测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            method: HTTP 方法
            is_new: 是否为新增类接口（决定是否添加 smoke 标签）

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 设置标签
        tags = self.default_tags.copy()
        if is_new:
            tags.append("smoke")

        # 检查是否为查询接口
        is_query = self._is_query_interface(request, case_name)

        if is_query:
            # 查询接口：生成智能查询测试用例
            logger.info(f"检测到查询接口: {case_name}，启用智能测试用例生成")
            scenarios.extend(self._generate_query_scenarios(request, case_name, tags))
        else:
            # 1. 正向场景：正常流程
            normal_scenario = Scenario(
                name=f"{case_name}-正常流程",
                description=f"测试 {method} {case_name} 正常流程",
                request=request,
                expected_status=200,
                priority="p1",
                tags=tags.copy()
            )
            scenarios.append(normal_scenario)
            logger.debug(f"生成场景: {normal_scenario.name}")

            # 2. 根据方法生成不同的场景
            if method.upper() in ["POST", "PUT", "PATCH"]:
                # POST/PUT/PATCH 请求：参数校验场景
                scenarios.extend(self._generate_validation_scenarios(request, case_name, tags))
            elif method.upper() == "GET":
                # GET 请求：参数校验场景
                scenarios.extend(self._generate_get_scenarios(request, case_name, tags))
            elif method.upper() == "DELETE":
                # DELETE 请求：权限校验场景
                scenarios.extend(self._generate_delete_scenarios(request, case_name, tags))

        logger.info(f"用例 {case_name}: 生成 {len(scenarios)} 个场景")

        return scenarios

    def _is_query_interface(self, request: CurlRequest, case_name: str = "") -> bool:
        """
        判断是否为查询接口

        支持两类查询接口：
        1. 普通查询接口：GET 请求
        2. 报表类查询接口：POST 请求 + body 中包含 options.basicFields/statisticsFields

        Args:
            request: CurlRequest 对象
            case_name: 用例名称

        Returns:
            bool: 是否为查询接口
        """
        # 普通查询接口：GET 请求
        if request.method.upper() == 'GET':
            return True

        # 报表类查询接口：POST 请求 + options.basicFields/statisticsFields
        if request.method.upper() == 'POST':
            if request.data and isinstance(request.data, dict):
                body = request.data
                options = body.get('options', {})
                if isinstance(options, dict):
                    has_basic = 'basicFields' in options and isinstance(options['basicFields'], list)
                    has_stats = 'statisticsFields' in options and isinstance(options['statisticsFields'], list)
                    if has_basic and has_stats:
                        return True

        return False

    def _generate_query_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成查询接口的测试场景

        根据接口类型自动识别并生成对应的测试场景：
        1. 普通查询接口：GET 请求，生成单条件/组合条件查询场景
        2. 报表类查询接口：POST 请求，按字段规则生成场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []
        query_tags = tags + ["query", "auto-generated"]

        # 识别查询接口类型
        if self._is_report_query_interface(request):
            # 报表类查询接口
            scenarios = self._generate_report_query_scenarios(request, case_name, query_tags)
        elif self._is_simple_query_interface(request):
            # 普通查询接口
            scenarios = self._generate_simple_query_scenarios(request, case_name, query_tags)
        else:
            # 兜底：生成基础场景
            scenarios.append(Scenario(
                name=f"{case_name}-正常流程",
                description=f"测试查询接口 {case_name} 正常流程",
                request=request,
                expected_status=200,
                priority="p1",
                tags=query_tags.copy(),
                is_query_interface=True
            ))

        return scenarios

    def _is_simple_query_interface(self, request: CurlRequest) -> bool:
        """判断是否为普通查询接口（GET 请求）"""
        return request.method.upper() == 'GET'

    def _is_report_query_interface(self, request: CurlRequest) -> bool:
        """判断是否为报表类查询接口（POST + options.basicFields/statisticsFields）"""
        if request.method.upper() != 'POST':
            return False

        if not request.data or not isinstance(request.data, dict):
            return False

        body = request.data
        options = body.get('options', {})

        if not isinstance(options, dict):
            return False

        has_basic = 'basicFields' in options and isinstance(options['basicFields'], list)
        has_stats = 'statisticsFields' in options and isinstance(options['statisticsFields'], list)

        return has_basic and has_stats

    def _generate_simple_query_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成普通查询接口的测试场景

        规则：
        1. 必传字段：pageNum, pageSize
        2. 其他参数：选填，进行单条件和组合条件测试

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            tags: 标签列表

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 提取查询参数（排除必传的分页参数）
        all_params = request.params or {}
        pagination_fields = {'pageNum', 'pageSize'}
        query_fields = {k: v for k, v in all_params.items() if k not in pagination_fields}

        if not query_fields:
            scenarios.append(Scenario(
                name=f"{case_name}-正常流程",
                description=f"测试查询接口 {case_name} 正常流程",
                request=request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))
            return scenarios

        # 1. 完整条件查询场景
        scenarios.append(Scenario(
            name=f"{case_name}-完整条件查询",
            description="使用所有查询条件的完整查询",
            request=request,
            expected_status=200,
            priority="p1",
            tags=tags.copy(),
            is_query_interface=True
        ))

        # 2. 单条件查询场景
        for field_name, field_value in query_fields.items():
            single_request = self._create_simple_query_request_with_single_field(
                request, field_name, field_value
            )
            scenarios.append(Scenario(
                name=f"{case_name}-单条件查询-{field_name}",
                description=f"仅使用 {field_name} 作为查询条件",
                request=single_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        # 3. 组合条件查询场景
        if len(query_fields) > 1:
            scenarios.extend(self._generate_simple_query_combination_scenarios(
                request, case_name, query_fields, tags
            ))

        logger.info(f"生成普通查询场景 {len(scenarios)} 个")

        return scenarios

    def _create_simple_query_request_with_single_field(
        self,
        request: CurlRequest,
        field_name: str,
        field_value: Any
    ) -> CurlRequest:
        """创建普通查询接口的单字段请求（保留分页参数）"""
        from copy import deepcopy

        modified_request = deepcopy(request)
        modified_request.params = {
            'pageNum': request.params.get('pageNum', 1),
            'pageSize': request.params.get('pageSize', 100),
            field_name: field_value
        }
        return modified_request

    def _generate_simple_query_combination_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        query_fields: Dict[str, Any],
        tags: List[str]
    ) -> List[Scenario]:
        """生成普通查询接口的组合条件场景"""
        from copy import deepcopy
        import random
        from itertools import combinations

        scenarios = []
        field_names = list(query_fields.keys())

        all_combos = []
        for r in range(2, len(field_names) + 1):
            all_combos.extend(combinations(field_names, r))

        max_combos = 5
        if len(all_combos) > max_combos:
            selected_combos = random.sample(all_combos, max_combos)
        else:
            selected_combos = all_combos

        for combo in selected_combos:
            combo_fields = {name: query_fields[name] for name in combo}
            modified_request = deepcopy(request)
            modified_request.params = {
                'pageNum': request.params.get('pageNum', 1),
                'pageSize': request.params.get('pageSize', 100),
                **combo_fields
            }
            combo_str = '_'.join(combo)

            scenarios.append(Scenario(
                name=f"{case_name}-组合查询-{combo_str}",
                description=f"组合查询条件: {', '.join(combo)}",
                request=modified_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        return scenarios

    def _generate_report_query_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成报表类查询接口的测试场景

        规则：
        1. 必传字段：startTime, endTime, granularity, options, timeZone
        2. basicFields: 单条件/组合条件，与 filters 对应
        3. statisticsFields: 单条件/组合条件，至少传一个
        4. granularity: 单选 MONTH/DATE/HOUR

        Args:
            request: CurlRequest 对象
            case_name: 用例名称
            tags: 标签列表

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []
        body = request.data

        options = body.get('options', {})
        basic_fields = options.get('basicFields', [])
        statistics_fields = options.get('statisticsFields', [])
        filters = body.get('filters', {})

        # 1. 完整条件查询场景
        scenarios.append(Scenario(
            name=f"{case_name}-完整条件查询",
            description="使用所有查询条件的完整查询",
            request=request,
            expected_status=200,
            priority="p1",
            tags=tags.copy(),
            is_query_interface=True
        ))

        # 2. granularity 单选场景
        granularity_scenarios = self._generate_granularity_scenarios(request, case_name, tags)
        scenarios.extend(granularity_scenarios)

        # 3. basicFields 单条件/组合条件场景
        if basic_fields:
            basic_scenarios = self._generate_basic_fields_scenarios(request, case_name, tags)
            scenarios.extend(basic_scenarios)

        # 4. statisticsFields 单条件/组合条件场景
        if statistics_fields:
            stats_scenarios = self._generate_statistics_fields_scenarios(request, case_name, tags)
            scenarios.extend(stats_scenarios)

        # 5. filters 与 basicFields 对应场景
        if basic_fields and filters:
            filter_scenarios = self._generate_filter_scenarios(request, case_name, tags)
            scenarios.extend(filter_scenarios)

        # 6. 空 filters 场景
        empty_scenarios = self._generate_empty_filters_scenarios(request, case_name, tags)
        scenarios.extend(empty_scenarios)

        logger.info(f"生成报表查询场景 {len(scenarios)} 个")

        return scenarios

    def _generate_granularity_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """生成 granularity 单选场景"""
        from copy import deepcopy

        scenarios = []
        granularity_options = ['MONTH', 'DATE', 'HOUR']
        time_formats = {
            'MONTH': ('202602', '202602'),
            'DATE': ('20260227', '20260227'),
            'HOUR': ('2026022700', '2026022723')
        }

        for gran in granularity_options:
            start_time, end_time = time_formats[gran]
            modified_request = deepcopy(request)
            body = deepcopy(request.data)
            body['granularity'] = gran
            body['startTime'] = start_time
            body['endTime'] = end_time
            modified_request.data = body

            scenarios.append(Scenario(
                name=f"{case_name}-granularity-{gran}",
                description=f"时间粒度: {gran}, 时间格式: {start_time}",
                request=modified_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        return scenarios

    def _generate_basic_fields_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """生成 basicFields 单条件/组合条件场景"""
        from copy import deepcopy
        import random
        from itertools import combinations

        scenarios = []
        body = request.data
        options = body.get('options', {})
        basic_fields = options.get('basicFields', [])

        if not basic_fields:
            return scenarios

        # 单条件场景
        for field in basic_fields:
            modified_request = deepcopy(request)
            body = deepcopy(request.data)
            body['options']['basicFields'] = [field]

            original_filters = body.get('filters', {})
            if field in original_filters:
                body['filters'] = {field: original_filters[field]}
            else:
                body['filters'] = {}

            modified_request.data = body

            scenarios.append(Scenario(
                name=f"{case_name}-basicFields-单条件-{field}",
                description=f"basicFields 仅包含: {field}",
                request=modified_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        # 组合条件场景
        if len(basic_fields) > 1:
            all_combos = []
            for r in range(2, min(len(basic_fields) + 1, 4)):
                all_combos.extend(combinations(basic_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                modified_request = deepcopy(request)
                body = deepcopy(request.data)
                body['options']['basicFields'] = list(combo)

                original_filters = body.get('filters', {})
                new_filters = {f: original_filters[f] for f in combo if f in original_filters}
                body['filters'] = new_filters

                modified_request.data = body
                combo_str = '_'.join(combo)

                scenarios.append(Scenario(
                    name=f"{case_name}-basicFields-组合-{combo_str}",
                    description=f"basicFields 组合: {', '.join(combo)}",
                    request=modified_request,
                    expected_status=200,
                    priority="p1",
                    tags=tags.copy(),
                    is_query_interface=True
                ))

        return scenarios

    def _generate_statistics_fields_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """生成 statisticsFields 单条件/组合条件场景"""
        from copy import deepcopy
        import random
        from itertools import combinations

        scenarios = []
        body = request.data
        options = body.get('options', {})
        statistics_fields = options.get('statisticsFields', [])

        if not statistics_fields:
            return scenarios

        # 单条件场景
        for field in statistics_fields:
            modified_request = deepcopy(request)
            body = deepcopy(request.data)
            body['options']['statisticsFields'] = [field]
            modified_request.data = body

            scenarios.append(Scenario(
                name=f"{case_name}-statisticsFields-单条件-{field}",
                description=f"statisticsFields 仅包含: {field}",
                request=modified_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        # 组合条件场景
        if len(statistics_fields) > 1:
            all_combos = []
            for r in range(2, min(len(statistics_fields) + 1, 4)):
                all_combos.extend(combinations(statistics_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                modified_request = deepcopy(request)
                body = deepcopy(request.data)
                body['options']['statisticsFields'] = list(combo)
                modified_request.data = body
                combo_str = '_'.join(combo)

                scenarios.append(Scenario(
                    name=f"{case_name}-statisticsFields-组合-{combo_str}",
                    description=f"statisticsFields 组合: {', '.join(combo)}",
                    request=modified_request,
                    expected_status=200,
                    priority="p1",
                    tags=tags.copy(),
                    is_query_interface=True
                ))

        return scenarios

    def _generate_filter_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """生成 filters 单条件/组合条件场景"""
        from copy import deepcopy
        import random
        from itertools import combinations

        scenarios = []
        body = request.data
        filters = body.get('filters', {})

        if not filters:
            return scenarios

        # 单条件场景
        for field_name, field_value in filters.items():
            modified_request = deepcopy(request)
            body = deepcopy(request.data)
            body['filters'] = {field_name: field_value}

            original_basic_fields = body.get('options', {}).get('basicFields', [])
            if field_name in original_basic_fields:
                body['options']['basicFields'] = [field_name]

            modified_request.data = body

            scenarios.append(Scenario(
                name=f"{case_name}-filter-单条件-{field_name}",
                description=f"filter 仅包含: {field_name}",
                request=modified_request,
                expected_status=200,
                priority="p1",
                tags=tags.copy(),
                is_query_interface=True
            ))

        # 组合条件场景
        if len(filters) > 1:
            all_combos = []
            filter_fields = list(filters.keys())
            for r in range(2, min(len(filter_fields) + 1, 4)):
                all_combos.extend(combinations(filter_fields, r))

            max_combos = min(3, len(all_combos))
            selected_combos = random.sample(all_combos, max_combos) if len(all_combos) > max_combos else all_combos

            for combo in selected_combos:
                combo_filters = {name: filters[name] for name in combo}
                modified_request = deepcopy(request)
                body = deepcopy(request.data)
                body['filters'] = combo_filters

                original_basic_fields = body.get('options', {}).get('basicFields', [])
                new_basic_fields = [f for f in original_basic_fields if f in combo_filters]
                body['options']['basicFields'] = new_basic_fields

                modified_request.data = body
                combo_str = '_'.join(combo)

                scenarios.append(Scenario(
                    name=f"{case_name}-filter-组合-{combo_str}",
                    description=f"filter 组合: {', '.join(combo)}",
                    request=modified_request,
                    expected_status=200,
                    priority="p1",
                    tags=tags.copy(),
                    is_query_interface=True
                ))

        return scenarios

    def _generate_empty_filters_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """生成空 filters 场景"""
        from copy import deepcopy

        scenarios = []

        # filters 为空
        modified_request = deepcopy(request)
        body = deepcopy(request.data)
        body['filters'] = {}
        modified_request.data = body

        scenarios.append(Scenario(
            name=f"{case_name}-filters-空",
            description="filters 为空字典",
            request=modified_request,
            expected_status=200,
            priority="p1",
            tags=tags.copy(),
            is_query_interface=True
        ))

        # basicFields 为空
        modified_request = deepcopy(request)
        body = deepcopy(request.data)
        body['options']['basicFields'] = []
        body['filters'] = {}
        modified_request.data = body

        scenarios.append(Scenario(
            name=f"{case_name}-basicFields-空",
            description="basicFields 和 filters 均为空",
            request=modified_request,
            expected_status=200,
            priority="p1",
            tags=tags.copy(),
            is_query_interface=True
        ))

        return scenarios

    def _extract_all_query_fields(self, request: CurlRequest) -> Dict[str, Any]:
        """
        提取所有查询字段

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

        return query_fields

    def _create_request_with_single_field(
        self,
        request: CurlRequest,
        field_name: str,
        field_value: Any
    ) -> CurlRequest:
        """
        创建仅包含单个查询字段的请求
        """
        from copy import deepcopy

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
        """
        from copy import deepcopy

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

                original_filters = body.get('filters', {})
                for name, value in fields.items():
                    if name in original_filters:
                        filter_fields[name] = value

                # 更新 filters
                if filter_fields:
                    body['filters'] = filter_fields

                modified_request.data = body

        return modified_request

    def _generate_validation_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成参数校验场景（用于 POST/PUT/PATCH）

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 校验场景列表
        """
        scenarios = []

        if not request.data or not isinstance(request.data, dict):
            return scenarios

        # 找到关键字段用于生成测试场景
        key_fields = self._find_key_fields(request.data)

        # 生成必填参数缺失场景
        if key_fields:
            from copy import deepcopy
            for field in key_fields[:2]:  # 最多生成 2 个必填参数缺失场景
                modified_data = deepcopy(request.data)
                modified_data[field] = ""

                modified_request = CurlRequest(
                    method=request.method,
                    url=request.url,
                    headers=request.headers,
                    cookies=request.cookies,
                    data=modified_data,
                    params=request.params,
                    is_compressed=request.is_compressed,
                    insecure=request.insecure
                )

                scenario = Scenario(
                    name=f"{case_name}-{field}为空",
                    description=f"测试 {case_name} {field} 为空时的异常处理",
                    request=modified_request,
                    expected_status=400,  # 参数校验失败
                    priority="p2",
                    tags=tags.copy()
                )
                scenarios.append(scenario)
                logger.debug(f"生成场景: {scenario.name}")

        # 生成密码错误场景（如果是登录相关）
        if any(keyword in case_name.lower() for keyword in ["登录", "login", "auth", "认证"]):
            if request.data and isinstance(request.data, dict):
                from copy import deepcopy
                password_field = None
                for field in ["password", "passwd", "pwd"]:
                    if field in request.data:
                        password_field = field
                        break

                if password_field:
                    modified_data = deepcopy(request.data)
                    modified_data[password_field] = "wrong_password"

                    modified_request = CurlRequest(
                        method=request.method,
                        url=request.url,
                        headers=request.headers,
                        cookies=request.cookies,
                        data=modified_data,
                        params=request.params,
                        is_compressed=request.is_compressed,
                        insecure=request.insecure
                    )

                    scenario = Scenario(
                        name=f"{case_name}-密码错误",
                        description=f"测试 {case_name} 密码错误时的处理",
                        request=modified_request,
                        expected_status=401,  # 认证失败
                        priority="p2",
                        tags=tags.copy()
                    )
                    scenarios.append(scenario)
                    logger.debug(f"生成场景: {scenario.name}")

        return scenarios

    def _generate_get_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成 GET 请求的测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # GET 请求已按查询接口处理，这里返回空
        return scenarios

    def _generate_delete_scenarios(
        self,
        request: CurlRequest,
        case_name: str,
        tags: List[str]
    ) -> List[Scenario]:
        """
        生成 DELETE 请求的测试场景

        Args:
            request: cURL 请求对象
            case_name: 用例名称
            tags: 基础标签

        Returns:
            List[Scenario]: 测试场景列表
        """
        scenarios = []

        # 生成资源不存在场景
        modified_url = request.url
        if '?' in modified_url:
            modified_url = modified_url.split('?')[0]
        modified_url = modified_url.rstrip('/')
        modified_url = f"{modified_url}/999999"  # 使用不存在的 ID

        modified_request = CurlRequest(
            method=request.method,
            url=modified_url,
            headers=request.headers,
            cookies=request.cookies,
            data=request.data,
            params=request.params,
            is_compressed=request.is_compressed,
            insecure=request.insecure
        )

        scenario = Scenario(
            name=f"{case_name}-资源不存在",
            description=f"测试 {case_name} 删除不存在的资源",
            request=modified_request,
            expected_status=404,
            priority="p2",
            tags=tags.copy()
        )
        scenarios.append(scenario)
        logger.debug(f"生成场景: {scenario.name}")

        return scenarios

    def _find_key_fields(self, data: Dict[str, Any]) -> List[str]:
        """
        找出关键字段（用于生成测试场景）

        Args:
            data: 数据字典

        Returns:
            List[str]: 关键字段列表
        """
        key_fields = []

        # 常见的必填字段
        common_fields = [
            "username", "user_name", "account",
            "password", "passwd", "pwd",
            "email", "phone", "mobile",
            "id", "name", "title",
            "pid", "product_id", "user_id"
        ]

        for field in common_fields:
            if field in data:
                key_fields.append(field)

        return key_fields


def generate_scenarios(
    request: CurlRequest,
    case_name: str,
    method: str = "POST",
    is_new: bool = False
) -> List[Scenario]:
    """
    便捷函数：生成测试场景

    Args:
        request: cURL 请求对象
        case_name: 用例名称
        method: HTTP 方法
        is_new: 是否为新增类接口

    Returns:
        List[Scenario]: 测试场景列表
    """
    generator = ScenarioGenerator()
    return generator.generate_scenarios(request, case_name, method, is_new)


if __name__ == "__main__":
    # 测试场景生成
    from src.utils.curl_parser import CurlParser

    # 测试登录接口
    login_curl = """curl 'https://api.example.com/login' -H 'content-type: application/json' --data-raw '{"username":"test","password":"test123"}'"""

    parser = CurlParser()
    request = parser.parse(login_curl)

    generator = ScenarioGenerator()
    scenarios = generator.generate_scenarios(request, "用户登录", "POST", is_new=True)

    print(f"生成 {len(scenarios)} 个场景:")
    for scenario in scenarios:
        print(f"  - {scenario.name}")
        print(f"    描述: {scenario.description}")
        print(f"    期望状态码: {scenario.expected_status}")
        print(f"    优先级: {scenario.priority}")
        print(f"    标签: {scenario.tags}")
