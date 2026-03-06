#!/usr/bin/env python3
"""
cURL 转 YAML 工具（重构版）
支持自动扫描、场景生成和智能追加
"""
import sys
import argparse
from config.paths import get_test_data_file
from src.utils.logger import logger
from src.utils.curl_scanner import CurlScanner
from src.utils.curl_parser import CurlParser
from src.utils.scenario_generator import ScenarioGenerator
from src.utils.yaml_generator import YamlGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='cURL 转 YAML 工具（重构版）- 支持自动扫描、场景生成和智能追加',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
目录结构:
  test_data/
  ├── curl/              # cURL 文件目录
  │   ├── user_module/   # 模块目录（对应 user_module.yaml）
  │   │   ├── 用户登录.txt
  │   │   └── 用户注册.txt
  │   └── order_module/
  │       └── 创建订单.txt
  └── user_module.yaml   # 生成的测试数据文件

使用模式:
1. 批量扫描模式（推荐）:
   python scripts/curl_to_yaml.py --scan

2. 扫描指定模块:
   python scripts/curl_to_yaml.py --scan --module user_module

3. 单文件转换模式:
   python scripts/curl_to_yaml.py -f test_data/curl/user_module/用户登录.txt

4. 追加模式:
   python scripts/curl_to_yaml.py -f curl.txt -a test_data/user_module.yaml
        """
    )

    # 工作模式
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        '--scan',
        action='store_true',
        help='自动扫描 test_data/curl/ 目录，批量转换所有 cURL 文件'
    )
    mode_group.add_argument(
        '-f', '--file',
        type=str,
        help='从文件读取 cURL 命令'
    )
    mode_group.add_argument(
        '-c', '--curl',
        type=str,
        help='直接指定 cURL 命令'
    )

    # 扫描模式参数
    parser.add_argument(
        '--module',
        type=str,
        help='只扫描指定的模块（用于 --scan 模式）'
    )
    parser.add_argument(
        '--curl-dir',
        type=str,
        default='test_data/curl',
        help='cURL 文件目录，默认为 test_data/curl'
    )
    parser.add_argument(
        '--yaml-dir',
        type=str,
        default='test_data',
        help='YAML 文件输出目录，默认为 test_data'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新转换所有 cURL 文件（忽略已存在的场景）'
    )

    # 单文件/追加模式参数
    parser.add_argument(
        '-a', '--append',
        type=str,
        metavar='FILE',
        help='追加到已有的 YAML 文件'
    )
    parser.add_argument(
        '--case-module',
        type=str,
        help='模块名称（用于单文件模式）'
    )
    parser.add_argument(
        '-n', '--name',
        type=str,
        help='用例名称（用于单文件模式）'
    )
    parser.add_argument(
        '-p', '--priority',
        type=str,
        choices=['p0', 'p1', 'p2', 'p3'],
        default='p1',
        help='优先级，默认为 p1'
    )
    parser.add_argument(
        '-t', '--tags',
        type=str,
        nargs='+',
        default=['daily', 'regression'],
        help='标签列表，默认为 daily regression'
    )
    parser.add_argument(
        '--new',
        action='store_true',
        help='标记为新增类接口，自动添加 smoke 标签'
    )

    # 其他选项
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，只显示转换结果，不保存文件'
    )

    return parser.parse_args()


def scan_and_convert(args):
    """扫描并批量转换 cURL 文件"""
    logger.info("=" * 60)
    logger.info("开始批量扫描和转换")
    logger.info("=" * 60)

    # 初始化扫描器
    scanner = CurlScanner(args.curl_dir)

    # 扫描 cURL 文件
    result = scanner.scan()

    if not result:
        logger.warning("未找到任何 cURL 文件")
        return

    # 过滤模块
    if args.module:
        if args.module not in result:
            logger.warning(f"未找到模块: {args.module}")
            return
        result = {args.module: result[args.module]}

    # 统计信息
    total_files = 0
    total_scenarios = 0
    total_added = 0
    total_skipped = 0
    processed_modules = set()

    # 初始化生成器
    curl_parser = CurlParser()
    scenario_generator = ScenarioGenerator()
    yaml_generator = YamlGenerator()

    # 遍历所有模块
    for module_name, curl_files in result.items():
        logger.info(f"\n处理模块: {module_name}")
        logger.info("-" * 40)

        # 获取对应的 YAML 文件路径
        # yaml_file = scanner.get_yaml_file_path(module_name, args.yaml_dir)
        yaml_file = get_test_data_file(module_name)
        logger.info(f"目标文件: {yaml_file}")

        module_added = 0
        module_skipped = 0

        # 遍历所有 cURL 文件
        for curl_info in curl_files:
            logger.debug(f"\n处理文件: {curl_info.case_name}")
            total_files += 1

            try:
                # 解析 cURL
                request = curl_parser.parse(curl_info.curl_content)

                # 生成场景
                scenarios = scenario_generator.generate_scenarios(
                    request,
                    case_name=curl_info.case_name,
                    method=request.method,
                    is_new=args.new
                )

                logger.debug(f"生成 {len(scenarios)} 个场景")
                total_scenarios += len(scenarios)

                # 检查是否需要转换
                if not args.force:
                    should_convert, missing = scanner.should_convert(
                        curl_info,
                        args.yaml_dir,
                        [s.name.replace(f"{curl_info.case_name}-", "") for s in scenarios]
                    )

                    if not should_convert:
                        logger.info(f"  ✓ {curl_info.case_name}: 已存在，跳过")
                        module_skipped += len(scenarios)
                        total_skipped += len(scenarios)
                        continue
                    elif missing:
                        # 过滤只转换缺失的场景
                        missing_names = [f"{curl_info.case_name}-{m}" for m in missing]
                        scenarios = [s for s in scenarios if s.name in missing_names]
                        logger.info(f"  {curl_info.case_name}: 补充 {len(scenarios)} 个场景")

                # 追加场景到 YAML 文件
                if args.dry_run:
                    logger.info(f"  [预览] {curl_info.case_name}: 将添加 {len(scenarios)} 个场景")
                    for scenario in scenarios:
                        logger.info(f"    - {scenario.name}")
                else:
                    file_path, added, skipped = yaml_generator.append_scenarios_to_file(
                        scenarios,
                        str(yaml_file),
                        module_name=module_name,
                        module_description=f"{module_name} 模块的测试用例"
                    )

                    logger.info(f"  ✓ {curl_info.case_name}: 添加 {added} 个，跳过 {skipped} 个")
                    module_added += added
                    module_skipped += skipped
                    total_added += added
                    total_skipped += skipped

            except Exception as e:
                logger.error(f"  ✗ {curl_info.case_name}: 转换失败 - {str(e)}")

        if module_added > 0 or module_skipped > 0:
            processed_modules.add(module_name)
            logger.info(f"模块 {module_name} 完成: 添加 {module_added} 个，跳过 {module_skipped} 个")

    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("转换完成")
    logger.info("=" * 60)
    logger.info(f"处理模块数: {len(processed_modules)}")
    logger.info(f"处理文件数: {total_files}")
    logger.info(f"生成场景数: {total_scenarios}")
    logger.info(f"实际添加: {total_added}")
    logger.info(f"跳过场景: {total_skipped}")
    logger.info("=" * 60)


def convert_single_file(args):
    """转换单个 cURL 文件"""
    from src.utils.yaml_generator import convert_curl_to_yaml

    # 读取文件
    with open(args.file, 'r', encoding='utf-8') as f:
        curl_command = f.read().strip()

    # 转换
    if args.append:
        # 追加模式
        from src.utils.yaml_generator import append_curl_to_yaml
        file_path = append_curl_to_yaml(
            curl_command,
            args.append,
            test_case_name=args.name,
            priority=args.priority,
            tags=args.tags
        )
        logger.success(f"✓ 已追加到: {file_path}")
    else:
        # 新建模式
        file_path = convert_curl_to_yaml(
            curl_command,
            output_dir=args.yaml_dir,
            filename=args.case_module,
            test_case_name=args.name,
            priority=args.priority,
            tags=args.tags
        )
        logger.success(f"✓ 已生成: {file_path}")


def convert_curl_command(args):
    """转换 cURL 命令"""
    from src.utils.yaml_generator import convert_curl_to_yaml

    file_path = convert_curl_to_yaml(
        args.curl,
        output_dir=args.yaml_dir,
        filename=args.case_module,
        test_case_name=args.name,
        priority=args.priority,
        tags=args.tags
    )
    logger.success(f"✓ 已生成: {file_path}")


def main():
    """主函数"""
    args = parse_args()

    # 配置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

    try:
        # 根据模式执行
        if args.scan:
            scan_and_convert(args)
        elif args.file:
            convert_single_file(args)
        elif args.curl:
            convert_curl_command(args)
        else:
            logger.error("请指定工作模式: --scan, -f 或 -c")
            sys.exit(1)

    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
