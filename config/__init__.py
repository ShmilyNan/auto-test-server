# -*- coding: utf-8 -*-
"""
配置模块
"""

from config.paths import (
    PROJECT_ROOT,
    SRC_DIR,
    CONFIG_DIR,
    TEST_DATA_DIR,
    LOGS_DIR,
    REPORTS_DIR,
    ALLURE_RESULTS_DIR,
    ALLURE_REPORT_DIR,
    CONFIG_FILE,
    GLOBAL_VARS_FILE,
    ENV_CONFIG_DIR,
    get_env_config_file,
    ensure_dir,
    init_project_dirs,
)

__all__ = [
    "PROJECT_ROOT",
    "SRC_DIR",
    "CONFIG_DIR",
    "TEST_DATA_DIR",
    "LOGS_DIR",
    "REPORTS_DIR",
    "ALLURE_RESULTS_DIR",
    "ALLURE_REPORT_DIR",
    "CONFIG_FILE",
    "GLOBAL_VARS_FILE",
    "ENV_CONFIG_DIR",
    "get_env_config_file",
    "ensure_dir",
    "init_project_dirs",
]
