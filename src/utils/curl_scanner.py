"""
cURL 文件扫描器
扫描 /test_data/curl/ 目录下的所有模块和 cURL 文件
"""
from ruamel.yaml import YAML
from pathlib import Path
from typing import Dict, List, Tuple
from config.paths import get_test_data_file
from src.utils.logger import logger
from dataclasses import dataclass

# 创建 YAML 实例
_yaml = YAML(typ='rt')
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True
_yaml.sort_keys = False


@dataclass
class CurlFileInfo:
    """cURL 文件信息"""
    module_name: str  # 模块名称（目录名）
    case_name: str  # 用例名称（文件名，不含扩展名）
    file_path: Path  # 完整文件路径
    curl_content: str  # cURL 内容


class CurlScanner:
    """cURL 文件扫描器"""

    def __init__(self, curl_dir: str = "test_data/curl"):
        """
        初始化扫描器
        Args:
            curl_dir: cURL 文件目录，默认为 test_data/curl
        """
        self.curl_dir = Path(curl_dir)

    def scan(self) -> Dict[str, List[CurlFileInfo]]:
        """
        扫描 cURL 目录，返回按模块分组的 cURL 文件
        Returns:
            Dict[str, List[CurlFileInfo]]: {模块名: [cURL文件列表]}
        """
        if not self.curl_dir.exists():
            logger.warning(f"cURL 目录不存在: {self.curl_dir}")
            return {}

        logger.info(f"开始扫描 cURL 目录: {self.curl_dir}")

        result = {}

        # 遍历 cURL 目录下的所有子目录（模块目录）
        for module_dir in self.curl_dir.iterdir():
            if not module_dir.is_dir():
                continue

            module_name = module_dir.name
            logger.debug(f"扫描模块: {module_name}")

            # 扫描模块目录下的所有 .txt 文件
            curl_files = []
            for curl_file in module_dir.glob("*.txt"):
                # 读取 cURL 内容
                try:
                    with open(curl_file, 'r', encoding='utf-8') as f:
                        curl_content = f.read().strip()

                    if not curl_content:
                        logger.warning(f"文件为空，跳过: {curl_file}")
                        continue

                    # 提取用例名称（文件名，不含扩展名）
                    case_name = curl_file.stem

                    curl_info = CurlFileInfo(
                        module_name=module_name,
                        case_name=case_name,
                        file_path=curl_file,
                        curl_content=curl_content
                    )

                    curl_files.append(curl_info)
                    logger.debug(f"  找到 cURL 文件: {case_name}")

                except Exception as e:
                    logger.error(f"读取文件失败: {curl_file}, 错误: {str(e)}")

            if curl_files:
                result[module_name] = curl_files
                logger.info(f"模块 {module_name}: 找到 {len(curl_files)} 个 cURL 文件")

        total_files = sum(len(files) for files in result.values())
        logger.info(f"扫描完成: 共 {len(result)} 个模块, {total_files} 个 cURL 文件")

        return result

    def get_yaml_file_path(self, module_name: str) -> Path:
        """
        获取对应的 YAML 文件路径
        Args:
            module_name: 模块名称
        Returns:
            Path: YAML 文件路径
        """
        yaml_file = get_test_data_file(module_name)
        return yaml_file

    def should_convert(
            self,
            curl_info: CurlFileInfo,
            yaml_dir: str = "test_data",
            scenarios: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        检查是否需要转换（YAML 文件中是否已存在对应的场景）
        Args:
            curl_info: cURL 文件信息
            yaml_dir: YAML 文件目录
            scenarios: 要检查的场景名称列表
        Returns:
            Tuple[bool, List[str]]: (是否需要转换, 缺失的场景列表)
        """
        if scenarios is None:
            scenarios = ["正常流程"]

        # yaml_file = self.get_yaml_file_path(curl_info.module_name, yaml_dir)
        yaml_file = get_test_data_file(curl_info.module_name)

        if not yaml_file.exists():
            # YAML 文件不存在，需要转换
            return True, scenarios.copy()

        # 读取 YAML 文件
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_data = _yaml.load(f)

            if not yaml_data or 'test_cases' not in yaml_data:
                return True, scenarios.copy()

            # 获取已有的用例名称
            existing_cases = [case.get('name', '') for case in yaml_data['test_cases']]

            # 检查哪些场景还未添加
            missing_scenarios = []
            case_prefix = curl_info.case_name

            for scenario in scenarios:
                expected_name = f"{case_prefix}-{scenario}"
                if expected_name not in existing_cases:
                    missing_scenarios.append(scenario)

            if missing_scenarios:
                logger.debug(
                    f"模块 {curl_info.module_name} 用例 {case_prefix}: 缺少 {len(missing_scenarios)} 个场景: {missing_scenarios}")
                return True, missing_scenarios
            else:
                logger.debug(f"模块 {curl_info.module_name} 用例 {case_prefix}: 所有场景已存在，跳过")
                return False, []

        except Exception as e:
            logger.error(f"读取 YAML 文件失败: {yaml_file}, 错误: {str(e)}")
            # 出错时保守处理，仍然转换
            return True, scenarios.copy()


def scan_curl_files(curl_dir: str = "test_data/curl") -> Dict[str, List[CurlFileInfo]]:
    """
    便捷函数：扫描 cURL 文件
    Args:
        curl_dir: cURL 文件目录
    Returns:
        Dict[str, List[CurlFileInfo]]: 按模块分组的 cURL 文件
    """
    scanner = CurlScanner(curl_dir)
    return scanner.scan()


if __name__ == "__main__":
    # 测试扫描
    scanner = CurlScanner("test_data/curl")
    result = scanner.scan()

    for module_name, curl_files in result.items():
        print(f"\n模块: {module_name}")
        for curl_info in curl_files:
            print(f"  用例: {curl_info.case_name}")
            print(f"  文件: {curl_info.file_path}")
            print(f"  cURL: {curl_info.curl_content[:50]}...")
