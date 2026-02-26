from datetime import datetime
from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    """
    获取项目根目录路径

    Returns:
        项目根目录的 Path 对象
    """
    return Path(__file__).parent.parent.parent


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_timestamp(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        dt: datetime 对象，默认当前时间
        fmt: 格式字符串

    Returns:
        格式化后的时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.5 MB"
    """
    if size_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def safe_filename(filename: str) -> str:
    """
    清理文件名中的非法字符

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, "_")
    return filename.strip()
