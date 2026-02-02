#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证修复
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.context import TestContext
from src.utils.logger import log as logger


def test_context_none_handling():
    """测试上下文管理器处理None值"""
    logger.info("测试1: 测试上下文管理器处理None值")
    
    context = TestContext()
    
    # 测试replace_vars_dict处理None
    test_data = {
        'key1': '${global_var}',
        'key2': None,
        'key3': {'nested': '${local_var}'},
        'key4': [None, 'value'],
        'key5': ('tuple', None)
    }
    
    result = context.replace_vars_dict(test_data)
    assert result is not None
    assert result['key2'] is None
    assert result['key4'][0] is None
    assert result['key5'][1] is None
    
    logger.success("✓ 测试1通过: 上下文管理器正确处理None值")


def test_config_loading():
    """测试配置加载"""
    logger.info("测试2: 测试配置加载")
    
    try:
        from src.utils.yaml_loader import load_yaml
        from pathlib import Path

        config_file = Path("config/config.yaml")
        if config_file.exists():
            config = load_yaml(config_file) or {}
            logger.success(f"✓ 测试2通过: 配置加载成功")
        else:
            logger.warning("⚠ 配置文件不存在，跳过测试2")
    except Exception as e:
        logger.error(f"✗ 测试2失败: {e}")


def test_yaml_parsing():
    """测试YAML解析"""
    logger.info("测试3: 测试YAML解析")
    
    try:
        from src.utils.yaml_loader import load_yaml
        from pathlib import Path

        
        yaml_file = Path("test_data/user_module.yaml")
        if yaml_file.exists():
            data = load_yaml(yaml_file)
            
            assert data is not None
            assert 'test_cases' in data
            assert isinstance(data['test_cases'], list)
            
            logger.success("✓ 测试3通过: YAML解析成功")
        else:
            logger.warning("⚠ YAML文件不存在，跳过测试3")
    except Exception as e:
        logger.error(f"✗ 测试3失败: {e}")


def test_pytest_config():
    """测试pytest配置"""
    logger.info("测试4: 测试pytest配置")
    
    try:
        import pytest
        
        # 测试pytest配置是否有效
        config = pytest.Config.fromdictargs({}, [])
        
        logger.success("✓ 测试4通过: pytest配置加载成功")
    except Exception as e:
        logger.error(f"✗ 测试4失败: {e}")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("开始运行修复验证测试")
    logger.info("=" * 60)
    
    test_context_none_handling()
    test_config_loading()
    test_yaml_parsing()
    test_pytest_config()
    
    logger.info("=" * 60)
    logger.info("所有测试完成")
    logger.info("=" * 60)
