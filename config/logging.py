import sys
from pathlib import Path
from loguru import logger

from config.settings import get_settings


def setup_logging() -> None:
    """
    配置 loguru 日志系统
    - 按模块分文件输出
    - 控制台彩色输出
    - 文件轮转（每天/10MB）
    """
    settings = get_settings()

    # 移除默认 handler
    logger.remove()

    # 日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # 全局日志文件（轮转：每天或 10MB）
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # 错误日志单独文件
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # 各模块独立日志文件
    modules = ["llm", "ball_tracking", "equipment", "social_media", "learning", "training"]
    for module in modules:
        logger.add(
            log_dir / f"{module}_{{time:YYYY-MM-DD}}.log",
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            filter=lambda record, m=module: m in record["name"],
            rotation="10 MB",
            retention="14 days",
            compression="zip",
            encoding="utf-8",
        )

    logger.info("日志系统初始化完成")
