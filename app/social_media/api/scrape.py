"""
内容抓取 API 路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.social_media.core import get_scraper_service
from app.social_media.models import Platform
from app.social_media.schemas import (
    ScrapeTaskCreate, ScrapeTaskResponse, ScrapeTaskListResponse,
    PlatformConfigCreate, PlatformConfigUpdate, PlatformConfigResponse, PlatformConfigListResponse,
)

router = APIRouter()


# ========== 抓取任务 API ==========

@router.post("/tasks", response_model=ScrapeTaskResponse)
async def create_scrape_task(
    data: ScrapeTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> ScrapeTaskResponse:
    """
    创建抓取任务

    创建一个新的抓取任务并在后台执行。
    可以指定关键词搜索或指定目标 URL。
    """
    service = get_scraper_service()

    try:
        task = await service.create_task(
            db,
            platform=Platform(data.platform),
            keywords=data.keywords,
            target_url=data.target_url,
        )
        await db.commit()

        # 后台执行任务
        background_tasks.add_task(
            _execute_task_background,
            task.id,
        )

        return _to_task_response(task)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}", response_model=ScrapeTaskResponse)
async def get_scrape_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ScrapeTaskResponse:
    """
    获取任务状态

    查询抓取任务的执行状态和结果统计。
    """
    service = get_scraper_service()
    task = await service.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return _to_task_response(task)


@router.get("/tasks", response_model=ScrapeTaskListResponse)
async def list_scrape_tasks(
    platform: Optional[str] = Query(None, description="平台筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
) -> ScrapeTaskListResponse:
    """
    获取任务列表

    返回最近的抓取任务列表，支持按平台和状态筛选。
    """
    service = get_scraper_service()

    platform_enum = None
    if platform:
        try:
            platform_enum = Platform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的平台: {platform}")

    tasks = await service.list_tasks(
        db,
        platform=platform_enum,
        status=status,
        limit=limit,
    )

    return ScrapeTaskListResponse(
        tasks=[_to_task_response(t) for t in tasks],
        total=len(tasks),
    )


# ========== 平台配置 API ==========

@router.get("/platforms", response_model=PlatformConfigListResponse)
async def list_platform_configs(
    db: AsyncSession = Depends(get_db_session),
) -> PlatformConfigListResponse:
    """
    获取平台配置列表

    返回所有已配置的社交媒体平台。
    """
    from sqlalchemy import select
    from app.social_media.models import SocialPlatformConfig

    result = await db.execute(
        select(SocialPlatformConfig).order_by(SocialPlatformConfig.created_at)
    )
    configs = list(result.scalars().all())

    return PlatformConfigListResponse(
        platforms=[_to_platform_config_response(c) for c in configs],
        total=len(configs),
    )


@router.post("/platforms", response_model=PlatformConfigResponse)
async def create_platform_config(
    data: PlatformConfigCreate,
    db: AsyncSession = Depends(get_db_session),
) -> PlatformConfigResponse:
    """
    创建平台配置

    添加新的社交媒体平台配置，设置抓取参数。
    """
    import uuid
    from sqlalchemy import select
    from app.social_media.models import SocialPlatformConfig

    # 检查是否已存在
    existing = await db.execute(
        select(SocialPlatformConfig).where(
            SocialPlatformConfig.platform == data.platform
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"平台 {data.platform} 配置已存在")

    config = SocialPlatformConfig(
        id=str(uuid.uuid4()),
        platform=Platform(data.platform),
        display_name=data.display_name,
        base_url=data.base_url,
        scrape_enabled=data.scrape_enabled,
        scrape_interval_minutes=data.scrape_interval_minutes,
        scrape_keywords=data.scrape_keywords,
        scrape_max_items=data.scrape_max_items,
        rate_limit_per_minute=data.rate_limit_per_minute,
    )
    db.add(config)
    await db.commit()

    return _to_platform_config_response(config)


@router.put("/platforms/{platform}", response_model=PlatformConfigResponse)
async def update_platform_config(
    platform: str,
    data: PlatformConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> PlatformConfigResponse:
    """
    更新平台配置

    更新指定平台的配置参数。
    """
    from sqlalchemy import select
    from app.social_media.models import SocialPlatformConfig

    try:
        platform_enum = Platform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的平台: {platform}")

    result = await db.execute(
        select(SocialPlatformConfig).where(
            SocialPlatformConfig.platform == platform_enum
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail=f"平台 {platform} 配置不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    return _to_platform_config_response(config)


async def _execute_task_background(task_id: str):
    """后台执行抓取任务"""
    from app.shared.database import async_session_factory

    async with async_session_factory() as db:
        service = get_scraper_service()
        try:
            await service.execute_task(db, task_id)
            await db.commit()
        except Exception as e:
            logger.error(f"后台任务执行失败: {task_id}, {e}")
            await db.rollback()


def _to_task_response(task) -> ScrapeTaskResponse:
    """转换为任务响应"""
    platform = "unknown"
    if task.platform_config:
        platform = task.platform_config.platform.value

    return ScrapeTaskResponse(
        id=task.id,
        platform=platform,
        keywords=task.keywords,
        target_url=task.target_url,
        status=task.status,
        started_at=task.started_at,
        completed_at=task.completed_at,
        items_found=task.items_found,
        items_saved=task.items_saved,
        error_message=task.error_message,
        created_at=task.created_at,
    )


def _to_platform_config_response(config) -> PlatformConfigResponse:
    """转换为平台配置响应"""
    return PlatformConfigResponse(
        id=config.id,
        platform=config.platform.value,
        display_name=config.display_name,
        base_url=config.base_url,
        scrape_enabled=config.scrape_enabled,
        scrape_interval_minutes=config.scrape_interval_minutes,
        scrape_keywords=config.scrape_keywords,
        scrape_max_items=config.scrape_max_items,
        rate_limit_per_minute=config.rate_limit_per_minute,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )
