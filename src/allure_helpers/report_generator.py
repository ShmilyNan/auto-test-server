# -*- coding: utf-8 -*-
"""
Allure 报告生成器模块
提供 Allure 报告生成的相关函数
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from config import ALLURE_RESULTS_DIR, ALLURE_REPORT_DIR
from src.utils.logger import logger


def generate_allure_report():
    """
    生成 Allure 测试报告
    """
    logger.info("=" * 60)
    logger.info("开始生成 Allure 测试报告...")
    logger.info(f"结果目录: {ALLURE_RESULTS_DIR}")
    logger.info(f"报告目录: {ALLURE_REPORT_DIR}")

    # 检查 allure 结果目录是否存在
    if not ALLURE_RESULTS_DIR.exists():
        logger.warning(f"Allure 结果目录不存在: {ALLURE_RESULTS_DIR}")
        return

    # 检查是否有测试结果
    result_files = list(ALLURE_RESULTS_DIR.glob("*.json"))
    if not result_files:
        logger.warning("Allure 结果目录中没有测试结果文件")
        return

    # 检查 allure 命令是否可用
    allure_cmd = _find_allure_command()

    if allure_cmd:
        # 使用 allure generate 命令生成报告
        _generate_with_command(allure_cmd)
    else:
        # 使用 Python 方式生成报告
        _generate_with_python()

    logger.info("=" * 60)


def _find_allure_command() -> str:
    """
    查找 allure 命令路径
    Returns:
        str: allure 命令路径，未找到返回空字符串
    """
    # Windows 下优先检查常见安装路径
    if sys.platform == "win32":
        # 检查 npm 全局安装路径
        npm_paths = [
            Path(os.environ.get("APPDATA", "")) / "npm" / "allure.cmd",
            Path(os.environ.get("LOCALAPPDATA", "")) / "npm" / "allure.cmd",
        ]
        for path in npm_paths:
            if path.exists():
                return str(path)

    # 检查 PATH 环境变量
    allure_cmd = shutil.which("allure")
    if allure_cmd:
        return allure_cmd
    return ""


def _generate_with_command(allure_cmd: str):
    """
    使用 allure 命令行工具生成报告
    Args:
        allure_cmd: allure 命令路径
    """
    try:
        # 清理旧报告目录
        if ALLURE_REPORT_DIR.exists():
            shutil.rmtree(ALLURE_REPORT_DIR)

        # 构建命令：禁用 Google Analytics
        cmd = [
            allure_cmd,
            "generate",
            str(ALLURE_RESULTS_DIR),
            "-o", str(ALLURE_REPORT_DIR),
            "--clean"
        ]

        # 设置环境变量禁用统计
        env = os.environ.copy()
        env["ALLURE_NO_ANALYTICS"] = "1"

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0:
            logger.info(f"✅ Allure 报告生成成功: {ALLURE_REPORT_DIR}")
            logger.info(f"   打开报告: {ALLURE_REPORT_DIR / 'index.html'}")
        else:
            logger.error(f"❌ Allure 报告生成失败: {result.stderr}")
            # 回退到 Python 方式
            _generate_with_python()

    except subprocess.TimeoutExpired:
        logger.error("❌ Allure 报告生成超时")
        _generate_with_python()
    except Exception as e:
        logger.error(f"❌ Allure 报告生成异常: {e}")
        _generate_with_python()


def _generate_with_python():
    """
    使用 Python 方式生成报告（作为 allure 命令不可用时的备选方案）
    """
    try:
        # 尝试安装并使用 allure-combine
        try:
            import allure_combine
        except ImportError:
            logger.info("正在安装 allure-combine...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "allure-combine", "-q"],
                capture_output=True
            )
            import allure_combine

        # 清理旧报告目录
        if ALLURE_REPORT_DIR.exists():
            shutil.rmtree(ALLURE_REPORT_DIR)
        ALLURE_REPORT_DIR.mkdir(parents=True, exist_ok=True)

        # 生成合并的 HTML 报告
        output_file = ALLURE_REPORT_DIR / "allure-report.html"
        allure_combine.combine(
            str(ALLURE_RESULTS_DIR),
            output_file=str(output_file),
            ignore_errors=True
        )

        logger.info(f"✅ Allure 报告生成成功（Python 方式）: {output_file}")

    except ImportError:
        logger.warning("⚠️ allure-combine 安装失败")
        logger.info(f"💡 请手动安装 allure 命令行工具或 allure-combine:")
        logger.info("   - npm install -g allure-commandline")
        logger.info("   - pip install allure-combine")
        logger.info(f"   或手动执行: allure generate {ALLURE_RESULTS_DIR} -o {ALLURE_REPORT_DIR} --clean")
    except Exception as e:
        logger.error(f"❌ Python 方式生成报告失败: {e}")
        logger.info(f"💡 请手动执行: allure generate {ALLURE_RESULTS_DIR} -o {ALLURE_REPORT_DIR} --clean")
