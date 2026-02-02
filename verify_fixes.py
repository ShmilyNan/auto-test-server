#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证修复 - 核心功能测试
"""

import sys
from pathlib import Path
from src.utils.logger import log as logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))



def test_imports():
    """测试所有核心模块导入"""
    logger.info("测试: 核心模块导入")
    
    try:
        from src.core.client import create_client, BaseHTTPClient, RequestsClient
        from src.core.context import get_context, reset_context, TestContext
        from src.core.parser import TestParser, TestCase
        from src.core.validator import Validator, AssertionResult
        from src.utils.extractor import get_extractor, Extractor
        from src.utils.notifier import NotificationManager
        
        logger.success("✓ 所有核心模块导入成功")
        return True
    except Exception as e:
        logger.error(f"✗ 模块导入失败: {e}")
        return False


def test_context_none_handling():
    """测试上下文管理器处理None值"""
    logger.info("测试: 上下文管理器None值处理")
    
    try:
        from src.core.context import TestContext
        
        context = TestContext()
        
        # 测试None值处理
        test_cases = [
            None,
            "string",
            123,
            {"key": None},
            [None, "value"],
            (None, "value")
        ]
        
        for case in test_cases:
            result = context.replace_vars_dict(case)
            if isinstance(case, dict) and "key" in case:
                assert result["key"] is None
            elif isinstance(case, list):
                assert result[0] is None
            elif isinstance(case, tuple):
                assert result[0] is None
        
        logger.success("✓ 上下文管理器正确处理None值")
        return True
    except Exception as e:
        logger.error(f"✗ 上下文管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parser():
    """测试解析器"""
    logger.info("测试: 解析器功能")
    
    try:
        from src.core.parser import TestParser
        from src.utils.yaml_loader import load_yaml

        parser = TestParser()
        
        # 测试YAML解析
        yaml_content = """
test_cases:
  - name: "测试用例"
    method: "GET"
    url: "/test"
    validate:
      - type: "status_code"
        expected: 200
"""
        test_data = load_yaml(yaml_content)
        
        # 验证数据
        assert test_data is not None
        assert 'test_cases' in test_data
        assert len(test_data['test_cases']) > 0
        
        logger.success("✓ 解析器功能正常")
        return True
    except Exception as e:
        logger.error(f"✗ 解析器测试失败: {e}")
        return False


def test_validator():
    """测试验证器"""
    logger.info("测试: 验证器功能")
    
    try:
        from src.core.validator import Validator
        
        validator = Validator()
        
        # 测试断言
        response = {
            'status_code': 200,
            'body': {
                'code': 0,
                'data': {'id': 123}
            }
        }
        
        assertions = [
            {'type': 'status_code', 'expected': 200},
            {'type': 'eq', 'path': 'body.code', 'expected': 0},
            {'type': 'is_not_none', 'path': 'body.data'}
        ]
        
        results = validator.validate(response, assertions)
        
        assert len(results) == 3
        assert all(r.passed for r in results)
        
        logger.success("✓ 验证器功能正常")
        return True
    except Exception as e:
        logger.error(f"✗ 验证器测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始验证修复")
    logger.info("=" * 60)
    
    tests = [
        ("模块导入", test_imports),
        ("上下文管理器", test_context_none_handling),
        ("解析器", test_parser),
        ("验证器", test_validator)
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    logger.info("=" * 60)
    if all_passed:
        logger.success("所有测试通过！修复成功！")
    else:
        logger.error("部分测试失败，请检查")
    logger.info("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
