"""
YAML/JSON测试数据解析器
支持自动解析、校验、错误定位
"""

import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from src.utils.logger import log as logger
from src.utils.yaml_loader import load_yaml


@dataclass
class TestCase:
    """测试用例数据结构"""
    # 用例基本信息
    name: str                          # 用例名称
    module: str                        # 所属模块
    description: Optional[str] = None  # 用例描述
    priority: str = "p2"               # 优先级: p0/p1/p2/p3
    tags: List[str] = None             # 标签
    
    # 请求信息
    method: str = "GET"                # 请求方法
    url: str = ""                      # 请求URL
    headers: Dict[str, str] = None     # 请求头
    params: Dict[str, Any] = None      # URL参数
    body: Any = None                   # 请求体（JSON/表单/文本）
    files: Dict[str, str] = None       # 上传文件
    
    # 预处理/后处理
    setup: List[Dict] = None           # 前置处理
    teardown: List[Dict] = None        # 后置处理
    hooks: List[str] = None            # 钩子函数
    
    # 提取与依赖
    extract: Dict[str, Any] = None     # 数据提取规则
    depends_on: Optional[str] = None   # 依赖的用例ID
    
    # 验证
    validate: List[Dict] = None        # 断言规则
    
    # 期望结果
    expect: Dict[str, Any] = None      # 期望结果（简化版断言）
    
    # 其他配置
    timeout: int = 30                  # 超时时间
    skip: bool = False                 # 是否跳过
    skip_reason: Optional[str] = None  # 跳过原因
    retry: int = 0                     # 重试次数
    metadata: Dict[str, Any] = None    # 元数据

    def __post_init__(self):
        """初始化后处理"""
        if self.tags is None:
            self.tags = []
        if self.headers is None:
            self.headers = {}
        if self.params is None:
            self.params = {}
        if self.validate is None:
            self.validate = []
        if self.setup is None:
            self.setup = []
        if self.teardown is None:
            self.teardown = []
        if self.extract is None:
            self.extract = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'module': self.module,
            'description': self.description,
            'priority': self.priority,
            'tags': self.tags,
            'method': self.method,
            'url': self.url,
            'headers': self.headers,
            'params': self.params,
            'body': self.body,
            'files': self.files,
            'setup': self.setup,
            'teardown': self.teardown,
            'hooks': self.hooks,
            'extract': self.extract,
            'depends_on': self.depends_on,
            'validate': self.validate,
            'expect': self.expect,
            'timeout': self.timeout,
            'skip': self.skip,
            'skip_reason': self.skip_reason,
            'retry': self.retry,
            'metadata': self.metadata
        }


class TestParser:
    """测试数据解析器"""
    
    def __init__(self, data_dir: str = "test_data"):
        """
        初始化解析器
        
        Args:
            data_dir: 测试数据目录
        """
        self.data_dir = Path(data_dir)
        self._test_cases: Dict[str, List[TestCase]] = {}
    
    def parse_file(self, file_path: Union[str, Path]) -> List[TestCase]:
        """
        解析单个测试数据文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[TestCase]: 测试用例列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"测试数据文件不存在: {file_path}")

        try:
            # 根据扩展名选择解析方式
            if file_path.suffix in ['.yaml', '.yml']:
                data = load_yaml(file_path)
            elif file_path.suffix == '.json':
                # 读取文件内容
                content = file_path.read_text(encoding='utf-8')
                data = json.loads(content)
            else:
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")

            # 验证数据格式
            if not isinstance(data, dict):
                raise ValueError("文件根元素必须是字典")

            # 解析测试用例
            test_cases = self._parse_data(data, file_path.stem)

            logger.info(f"成功解析文件: {file_path}, 共 {len(test_cases)} 个用例")

            return test_cases

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析错误: {str(e)}")
        except Exception as e:
            logger.error(f"解析文件失败: {file_path}, 错误: {str(e)}")
            raise
    
    def _parse_data(self, data: Dict[str, Any], module: str) -> List[TestCase]:
        """
        解析测试数据
        Args:
            data: 测试数据字典
            module: 模块名称
        Returns:
            List[TestCase]: 测试用例列表
        """
        test_cases = []
        
        # 获取测试用例列表
        cases = data.get('test_cases', [])
        
        if not cases:
            logger.warning(f"模块 {module} 没有定义测试用例")
            return test_cases
        
        # 解析每个测试用例
        for idx, case_data in enumerate(cases):
            try:
                case = self._parse_case(case_data, module)
                test_cases.append(case)
            except Exception as e:
                logger.error(f"解析第 {idx + 1} 个用例失败: {str(e)}")
                raise
        
        return test_cases
    
    def _parse_case(self, case_data: Dict[str, Any], module: str) -> TestCase:
        """
        解析单个测试用例
        Args:
            case_data: 用例数据
            module: 模块名称
        Returns:
            TestCase: 测试用例对象
        Raises:
            ValueError: 必填字段缺失
        """
        # 检查必填字段
        if 'name' not in case_data:
            raise ValueError("测试用例缺少 name 字段")
        if 'url' not in case_data and 'path' not in case_data:
            raise ValueError("测试用例缺少 url 或 path 字段")
        
        # 创建用例对象
        case = TestCase(
            name=case_data['name'],
            module=module,
            description=case_data.get('description'),
            priority=case_data.get('priority', 'p2'),
            tags=case_data.get('tags', []),
            method=case_data.get('method', 'GET').upper(),
            url=case_data.get('url', case_data.get('path', '')),
            headers=case_data.get('headers', {}),
            params=case_data.get('params', {}),
            body=case_data.get('body'),
            files=case_data.get('files'),
            setup=case_data.get('setup', []),
            teardown=case_data.get('teardown', []),
            hooks=case_data.get('hooks'),
            extract=case_data.get('extract', {}),
            depends_on=case_data.get('depends_on'),
            validate=case_data.get('validate', []),
            expect=case_data.get('expect'),
            timeout=case_data.get('timeout', 30),
            skip=case_data.get('skip', False),
            skip_reason=case_data.get('skip_reason'),
            retry=case_data.get('retry', 0),
            metadata=case_data.get('metadata', {})
        )
        
        return case
    
    def parse_dir(self, dir_path: Optional[Union[str, Path]] = None) -> Dict[str, List[TestCase]]:
        """
        解析目录下所有测试数据文件
        Args:
            dir_path: 目录路径，默认为初始化时指定的目录
        Returns:
            Dict[str, List[TestCase]]: {模块名: 用例列表}
        """
        if dir_path:
            dir_path = Path(dir_path)
        else:
            dir_path = self.data_dir
        
        if not dir_path.exists():
            logger.warning(f"测试数据目录不存在: {dir_path}")
            return {}
        
        all_cases = {}
        
        # 支持的文件扩展名
        extensions = ['.yaml', '.yml', '.json']
        
        # 遍历目录
        for file_path in dir_path.iterdir():
            if file_path.suffix in extensions:
                try:
                    cases = self.parse_file(file_path)
                    module = file_path.stem
                    all_cases[module] = cases
                except Exception as e:
                    logger.error(f"解析文件失败: {file_path}, {str(e)}")
        
        self._test_cases = all_cases
        
        total_cases = sum(len(cases) for cases in all_cases.values())
        logger.info(f"共解析 {len(all_cases)} 个模块, {total_cases} 个测试用例")
        
        return all_cases
    
    def get_cases_by_module(self, module: str) -> List[TestCase]:
        """
        获取指定模块的测试用例
        Args:
            module: 模块名称
        Returns:
            List[TestCase]: 测试用例列表
        """
        return self._test_cases.get(module, [])
    
    def get_all_cases(self) -> List[TestCase]:
        """
        获取所有测试用例
        
        Returns:
            List[TestCase]: 测试用例列表
        """
        all_cases = []
        for cases in self._test_cases.values():
            all_cases.extend(cases)
        return all_cases
    
    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        验证数据格式是否符合规范
        Args:
            data: 测试数据字典
        Returns:
            bool: 是否合法
        """
        required_fields = ['test_cases']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"缺少必填字段: {field}")
                return False
        
        test_cases = data.get('test_cases', [])
        
        if not isinstance(test_cases, list):
            logger.error("test_cases 必须是列表")
            return False
        
        for idx, case in enumerate(test_cases):
            if not isinstance(case, dict):
                logger.error(f"第 {idx + 1} 个用例必须是字典")
                return False
            
            if 'name' not in case:
                logger.error(f"第 {idx + 1} 个用例缺少 name 字段")
                return False
        
        return True
