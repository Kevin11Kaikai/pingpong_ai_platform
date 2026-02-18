"""
数据库基础设施模块
提供异步 SQLAlchemy 引擎和会话管理
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类"""
    pass


# 全局引擎和会话工厂
_engine = None
_session_factory = None


def get_engine():
    """获取数据库引擎单例"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        logger.info(f"数据库引擎已创建: {settings.database_url}")
    return _engine


def get_session_factory():
    """获取会话工厂单例"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# 别名，供后台任务使用
async_session_factory = property(lambda _: get_session_factory())


class _SessionFactoryProxy:
    """会话工厂代理，允许直接使用 async_session_factory() 创建会话"""
    def __call__(self):
        return get_session_factory()()

    def __aenter__(self):
        return get_session_factory().__aenter__()


async_session_factory = get_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    依赖注入：获取数据库会话

    用法:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """初始化数据库表结构"""
    # 延迟导入避免循环依赖
    from app.llm.models import Conversation, Message, Document
    from app.ball_tracking.models import ProcessingJob, BallTrack2D, VisualizationOutput
    from app.equipment_recommendation.models import (
        EquipmentCategory, Brand, Equipment,
        UserEquipmentProfile, EquipmentReview, EquipmentRecommendation
    )
    from app.social_media.models import (
        SocialPlatformConfig, ScrapeTask, SocialContent,
        ContentTag, ContentTagMapping, ReplySuggestion
    )

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表结构初始化完成")


async def close_db() -> None:
    """关闭数据库连接"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("数据库连接已关闭")
