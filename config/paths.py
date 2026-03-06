# -*- coding: utf-8 -*-
"""
路径配置模块
统一管理项目中所有路径配置
"""
from pathlib import Path

# ========================================
# 项目根路径
# ========================================
PROJECT_ROOT = Path(__file__).parent.parent

# ========================================
# 目录配置
# ========================================
# 源码目录
SRC_DIR = PROJECT_ROOT / "src"

# 配置目录
CONFIG_DIR = PROJECT_ROOT / "config"

# 测试数据目录
TEST_DATA_DIR = PROJECT_ROOT / "test_data"

# 文件目录
DOCS_DIR = PROJECT_ROOT / "docs"

# 文件上传目录
UPLOADS_DIR = DOCS_DIR / "uploads"

# 文件下载目录
DOWNLOADS_DIR = DOCS_DIR / "downloads"

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs"

# 报告目录
REPORTS_DIR = PROJECT_ROOT / "reports"

# ========================================
# Allure 报告路径
# ========================================
ALLURE_RESULTS_DIR = REPORTS_DIR / "allure"
ALLURE_REPORT_DIR = REPORTS_DIR / "allure-report"

# ========================================
# 配置文件路径
# ========================================
CONFIG_FILE = CONFIG_DIR / "config.yaml"
GLOBAL_VARS_FILE = CONFIG_DIR / "global_vars.yaml"

# ========================================
# 环境配置目录
# ========================================
ENV_CONFIG_DIR = CONFIG_DIR / "env"


def get_env_config_file(env: str) -> Path:
    """
    获取指定环境的配置文件路径
    Args:
        env: 环境名称 (如: dev, test, prod)
    Returns:
        Path: 环境配置文件路径
    """
    return ENV_CONFIG_DIR / f"{env}.yaml"


def get_test_data_file(module_name: str) -> Path:
    """
    获取指定环境的配置文件路径
    Args:
        module_name: 文件名 (如: dev, test, prod)
    Returns:
        Path: 测试数据文件路径
    """
    return TEST_DATA_DIR / f"{module_name}.yaml"


def ensure_dir(dir_path: Path) -> Path:
    """
    确保目录存在，不存在则创建
    Args:
        dir_path: 目录路径
    Returns:
        Path: 目录路径
    """
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


# ========================================
# 项目初始化时确保必要目录存在
# ========================================
def init_project_dirs():
    """
    初始化项目目录
    确保必要的目录存在
    """
    ensure_dir(LOGS_DIR)
    ensure_dir(REPORTS_DIR)
    ensure_dir(ALLURE_RESULTS_DIR)
    ensure_dir(ALLURE_REPORT_DIR)
    ensure_dir(UPLOADS_DIR)
    ensure_dir(DOWNLOADS_DIR)
    ensure_dir(DOCS_DIR)
    ensure_dir(CONFIG_DIR)
    ensure_dir(ENV_CONFIG_DIR)
    ensure_dir(TEST_DATA_DIR)
    print(f"项目初始化完成，项目根目录: {PROJECT_ROOT}")


# 模块导入时自动初始化
init_project_dirs()
