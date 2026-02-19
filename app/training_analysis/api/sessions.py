"""
训练会话 API 路由
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.training_analysis.core import (
    get_session_service,
    get_metrics_service,
)
from app.training_analysis.schemas import (
    SessionCreate, SessionUpdate, SessionResponse, SessionBrief,
    SessionListResponse, SessionVideoCreate, SessionVideoResponse,
    TechniqueMetricsResponse, SessionDetailResponse,
    AnalyzeSessionRequest, AnalyzeSessionResponse,
)

router = APIRouter()


@router.post("", response_model=SessionResponse)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建训练会话

    记录一次训练的基本信息，包括时间、地点、练习技术等。
    """
    service = get_session_service()
    session = await service.create_session(db, data)
    return SessionResponse.model_validate(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: str = Query(..., description="用户ID"),
    session_type: Optional[str] = Query(None, description="会话类型"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取训练会话列表

    支持按类型、日期筛选和分页。
    """
    service = get_session_service()
    sessions, total = await service.list_sessions(
        db, user_id, session_type, start_date, end_date, page, page_size
    )

    briefs = []
    for s in sessions:
        brief = SessionBrief(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            session_type=s.session_type.value,
            started_at=s.started_at,
            duration_minutes=s.duration_minutes,
            total_strokes=s.total_strokes or 0,
            avg_ball_speed_kmh=s.avg_ball_speed_kmh,
            satisfaction_rating=s.satisfaction_rating,
            video_count=len(s.videos) if s.videos else 0,
        )
        briefs.append(brief)

    return SessionListResponse(
        sessions=briefs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取训练会话详情

    包含会话信息、关联视频和技术指标。
    """
    service = get_session_service()
    session = await service.get_session(db, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session_resp = SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        session_type=session.session_type.value,
        description=session.description,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        location=session.location,
        equipment_notes=session.equipment_notes,
        total_strokes=session.total_strokes or 0,
        avg_ball_speed_kmh=session.avg_ball_speed_kmh,
        max_ball_speed_kmh=session.max_ball_speed_kmh,
        accuracy_score=session.accuracy_score,
        consistency_score=session.consistency_score,
        practiced_techniques=session.practiced_techniques,
        notes=session.notes,
        satisfaction_rating=session.satisfaction_rating,
        fatigue_level=session.fatigue_level,
        tags=session.tags,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

    videos = [
        SessionVideoResponse(
            id=v.id,
            session_id=v.session_id,
            ball_tracking_job_id=v.ball_tracking_job_id,
            segment_title=v.segment_title,
            start_time_seconds=v.start_time_seconds,
            end_time_seconds=v.end_time_seconds,
            stroke_count=v.stroke_count,
            avg_speed_kmh=v.avg_speed_kmh,
            max_speed_kmh=v.max_speed_kmh,
            bounce_count=v.bounce_count,
            stroke_distribution=v.stroke_distribution,
            analysis_status=v.analysis_status,
            created_at=v.created_at,
        )
        for v in (session.videos or [])
    ]

    metrics = [
        TechniqueMetricsResponse.model_validate(m)
        for m in (session.metrics or [])
    ]

    return SessionDetailResponse(
        session=session_resp,
        videos=videos,
        metrics=metrics,
    )


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新训练会话

    可更新会话的基本信息和笔记。
    """
    service = get_session_service()
    session = await service.update_session(db, session_id, data)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return SessionResponse.model_validate(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除训练会话

    同时删除关联的视频和指标数据。
    """
    service = get_session_service()
    success = await service.delete_session(db, session_id)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"message": "会话已删除", "session_id": session_id}


@router.post("/{session_id}/videos", response_model=SessionVideoResponse)
async def add_video(
    session_id: str,
    data: SessionVideoCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    添加视频到会话

    关联 ball_tracking 任务与训练会话。
    """
    service = get_session_service()
    video = await service.add_video(db, session_id, data)

    if not video:
        raise HTTPException(status_code=404, detail="会话不存在")

    return SessionVideoResponse.model_validate(video)


@router.delete("/{session_id}/videos/{video_id}")
async def remove_video(
    session_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    从会话移除视频

    仅移除关联，不删除 ball_tracking 任务。
    """
    service = get_session_service()
    success = await service.remove_video(db, session_id, video_id)

    if not success:
        raise HTTPException(status_code=404, detail="视频不存在")

    return {"message": "视频已移除", "video_id": video_id}


@router.post("/{session_id}/analyze", response_model=AnalyzeSessionResponse)
async def analyze_session(
    session_id: str,
    request: AnalyzeSessionRequest = AnalyzeSessionRequest(),
    db: AsyncSession = Depends(get_db_session),
):
    """
    触发会话分析

    从关联的 ball_tracking 任务提取指标并更新会话。
    """
    session_service = get_session_service()
    metrics_service = get_metrics_service()

    session = await session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if not session.videos:
        return AnalyzeSessionResponse(
            session_id=session_id,
            status="completed",
            message="会话无关联视频",
            metrics_updated=0,
        )

    try:
        # 更新每个视频的指标
        updated_count = 0
        for video in session.videos:
            if video.analysis_status != "completed" or request.force_reanalyze:
                await metrics_service.update_video_metrics(db, video)
                updated_count += 1

        # 计算技术指标
        await metrics_service.calculate_technique_metrics(db, session_id)

        # 重新计算会话聚合指标
        await session_service.recalculate_session_metrics(db, session_id)

        return AnalyzeSessionResponse(
            session_id=session_id,
            status="completed",
            message="分析完成",
            metrics_updated=updated_count,
        )

    except Exception as e:
        logger.error(f"会话分析失败: {session_id}, {e}")
        return AnalyzeSessionResponse(
            session_id=session_id,
            status="failed",
            message=str(e),
            metrics_updated=0,
        )


@router.get("/{session_id}/metrics", response_model=list[TechniqueMetricsResponse])
async def get_session_metrics(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取会话的技术指标

    返回按技术类型分组的指标数据。
    """
    service = get_session_service()
    session = await service.get_session(db, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return [
        TechniqueMetricsResponse.model_validate(m)
        for m in (session.metrics or [])
    ]


@router.get("/user/{user_id}/recent", response_model=list[SessionBrief])
async def get_recent_sessions(
    user_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户最近的训练会话
    """
    service = get_session_service()
    sessions = await service.get_recent_sessions(db, user_id, limit)

    return [
        SessionBrief(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            session_type=s.session_type.value,
            started_at=s.started_at,
            duration_minutes=s.duration_minutes,
            total_strokes=s.total_strokes or 0,
            avg_ball_speed_kmh=s.avg_ball_speed_kmh,
            satisfaction_rating=s.satisfaction_rating,
            video_count=0,
        )
        for s in sessions
    ]
