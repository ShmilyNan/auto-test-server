# -*- coding: utf-8 -*-
"""
文件下载工具
用于下载和保存导出文件
"""
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import unquote
from config.paths import DOWNLOADS_DIR
from src.utils.logger import logger


class FileDownloader:
    """文件下载器"""

    def __init__(self, download_dir: Path = DOWNLOADS_DIR):
        """
        初始化文件下载器
        Args:
            download_dir: 下载目录，默认为 docs/downloads
        """
        self.download_dir = download_dir
        logger.info(f"文件下载器初始化完成，下载目录: {self.download_dir}")

    def save_response_file(
        self,
        response: Dict[str, Any],
        filename: Optional[str] = None,
        sub_dir: Optional[str] = None
    ) -> str:
        """
        从响应中保存文件
        Args:
            response: HTTP 响应字典，必须包含 content 或 _response_obj
            filename: 文件名（可选，默认从响应头中提取）
            sub_dir: 子目录（可选）
        Returns:
            str: 保存的文件路径
        """
        # 获取二进制内容
        content = response.get('content')

        if content is None:
            # 如果响应中有原始响应对象
            raw_response = response.get('_response_obj')
            if raw_response is not None:
                content = raw_response.content
            else:
                # 尝试从 text 转换
                text = response.get('text')
                if text:
                    content = text.encode('utf-8')
                else:
                    raise ValueError("响应中没有可保存的内容")

        # 确定文件名
        if not filename:
            filename = self._extract_filename(response)

        # 确定保存路径
        save_dir = self.download_dir
        if sub_dir:
            save_dir = save_dir / sub_dir
            save_dir.mkdir(parents=True, exist_ok=True)

        # 如果文件名没有扩展名，根据 Content-Type 自动添加
        if '.' not in Path(filename).suffix:
            content_type = response.get('headers', {}).get('Content-Type', '')
            extension_map = {
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                'application/vnd.ms-excel': '.xls',
                'application/pdf': '.pdf',
                'application/zip': '.zip',
                'application/x-zip-compressed': '.zip',
                'application/json': '.json',
                'text/csv': '.csv',
                'text/plain': '.txt',
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
            }
            extension = extension_map.get(content_type.split(';')[0].strip(), '.bin')
            filename = f"{filename}{extension}"

        file_path = save_dir / filename

        # 处理文件名冲突
        if file_path.exists():
            base_name = file_path.stem
            extension = file_path.suffix
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_{timestamp}{extension}"
            file_path = save_dir / filename

        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(f"文件已保存: {file_path}")
        return str(file_path)

    @staticmethod
    def _extract_filename(response: Dict[str, Any]) -> str:
        """
        从响应头中提取文件名

        Args:
            response: HTTP 响应字典

        Returns:
            str: 文件名
        """
        headers = response.get('headers', {})

        # 尝试从 Content-Disposition 获取文件名
        content_disposition = headers.get('Content-Disposition', '')

        if content_disposition:
            # 尝试匹配 filename*=UTF-8''... 格式
            match = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", content_disposition)
            if match:
                filename = unquote(match.group(1))
                return filename

            # 尝试匹配 filename="..." 格式
            match = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disposition)
            if match:
                filename = unquote(match.group(1))
                return filename

            # 尝试匹配 filename=... 格式
            match = re.search(r'filename=([^\s;]+)', content_disposition)
            if match:
                filename = unquote(match.group(1))
                return filename

        # 根据 Content-Type 生成默认文件名
        content_type = headers.get('Content-Type', '')

        # 根据内容类型确定扩展名
        extension_map = {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-excel': '.xls',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/x-zip-compressed': '.zip',
            'application/json': '.json',
            'text/csv': '.csv',
            'text/plain': '.txt',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
        }

        extension = extension_map.get(content_type.split(';')[0].strip(), '.bin')

        # 生成默认文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"export_{timestamp}{extension}"

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        获取文件大小
        Args:
            file_path: 文件路径
        Returns:
            int: 文件大小（字节）
        """
        return os.path.getsize(file_path)

    def list_downloaded_files(self, sub_dir: Optional[str] = None) -> list:
        """
        列出已下载的文件

        Args:
            sub_dir: 子目录（可选）

        Returns:
            list: 文件路径列表
        """
        target_dir = self.download_dir
        if sub_dir:
            target_dir = target_dir / sub_dir

        if not target_dir.exists():
            return []

        return [str(f) for f in target_dir.iterdir() if f.is_file()]

    def clear_downloads(self, sub_dir: Optional[str] = None, older_than_days: Optional[int] = None):
        """
        清理下载文件

        Args:
            sub_dir: 子目录（可选）
            older_than_days: 清理多少天前的文件（可选）
        """
        target_dir = self.download_dir
        if sub_dir:
            target_dir = target_dir / sub_dir

        if not target_dir.exists():
            return

        current_time = time.time()
        deleted_count = 0

        for file_path in target_dir.iterdir():
            if file_path.is_file():
                if older_than_days is None:
                    file_path.unlink()
                    deleted_count += 1
                else:
                    file_mtime = file_path.stat().st_mtime
                    age_days = (current_time - file_mtime) / (24 * 3600)
                    if age_days > older_than_days:
                        file_path.unlink()
                        deleted_count += 1

        logger.info(f"清理了 {deleted_count} 个文件")


# 全局实例
_downloader = None


def get_downloader(download_dir: Path = DOWNLOADS_DIR) -> FileDownloader:
    """
    获取全局文件下载器实例
    Args:
        download_dir: 下载目录
    Returns:
        FileDownloader: 文件下载器实例
    """
    global _downloader

    if _downloader is None:
        _downloader = FileDownloader(download_dir)

    return _downloader


def save_response_file(
    response: Dict[str, Any],
    filename: Optional[str] = None,
    sub_dir: Optional[str] = None,
    download_dir: Path = DOWNLOADS_DIR
) -> str:
    """
    便捷函数：保存响应文件
    Args:
        response: HTTP 响应字典
        filename: 文件名（可选）
        sub_dir: 子目录（可选）
        download_dir: 下载目录
    Returns:
        str: 保存的文件路径
    """
    downloader = get_downloader(download_dir)
    return downloader.save_response_file(response, filename, sub_dir)


__all__ = ['FileDownloader', 'get_downloader', 'save_response_file']
