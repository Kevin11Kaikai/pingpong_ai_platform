"""
内容分析 API 路由
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.social_media.core import get_analysis_service
from app.social_media.schemas import (
    ContentAnalysisRequest, ContentAnalysisResponse,
    BatchAnalysisRequest, BatchAnalysisResponse,
)

router = APIRouter()


@router.post("/analyze", response_model=ContentAnalysisResponse)
async def analyze_content(
    data: ContentAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ContentAnalysisResponse:
    """
    分析单个内容

    使用 LLM 分析内容，提取主题、情感、关键点等信息。
    分析结果会保存到数据库。
    """
    service = get_analysis_service()

    try:
        result = await service.analyze_content(
            db,
            content_id=data.content_id,
            force_reanalyze=data.force_reanalyze,
        )
        await db.commit()

        return ContentAnalysisResponse(
            content_id=data.content_id,
            topics=result.topics,
            question_type=result.question_type,
            difficulty_level=result.difficulty_level,
            sentiment=result.sentiment,
            key_points=result.key_points,
            suggested_tags=result.suggested_tags,
            quality_score=result.quality_score,
            relevance_score=result.relevance_score,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/batch-analyze", response_model=BatchAnalysisResponse)
async def batch_analyze_contents(
    data: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> BatchAnalysisResponse:
    """
    批量分析内容

    在后台批量分析内容，适合大量待处理内容的场景。
    返回任务 ID 可用于跟踪（当前实现为简化版）。
    """
    task_id = str(uuid.uuid4())

    # 添加后台任务
    background_tasks.add_task(
        _batch_analyze_background,
        task_id,
        data.content_ids,
        data.status_filter,
        data.limit,
    )

    return BatchAnalysisResponse(
        task_id=task_id,
        total_queued=data.limit,
        message="批量分析任务已创建，将在后台执行",
    )


async def _batch_analyze_background(
    task_id: str,
    content_ids: list,
    status_filter: str,
    limit: int,
):
    """后台执行批量分析"""
    from app.shared.database import async_session_factory
    from app.social_media.models import ContentStatus

    async with async_session_factory() as db:
        service = get_analysis_service()
        try:
            status = ContentStatus(status_filter) if status_filter else None
            success, fail = await service.batch_analyze(
                db,
                content_ids=content_ids,
                status_filter=status,
                limit=limit,
            )
            await db.commit()
            logger.info(f"批量分析完成: task_id={task_id}, 成功={success}, 失败={fail}")
        except Exception as e:
            logger.error(f"批量分析失败: {task_id}, {e}")
            await db.rollback()
