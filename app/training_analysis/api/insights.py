"""
AI 洞察 API 路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.training_analysis.core import get_insight_service
from app.training_analysis.schemas import (
    InsightResponse, InsightFeedback, InsightListResponse,
    GenerateInsightsRequest,
)

router = APIRouter()


@router.get("/user/{user_id}", response_model=InsightListResponse)
async def get_user_insights(
    user_id: str,
    insight_type: Optional[str] = Query(None, description="洞察类型"),
    unread_only: bool = Query(False, description="仅未读"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户洞察列表

    返回 AI 生成的训练洞察和建议。
    """
    service = get_insight_service()
    insights = await service.get_user_insights(
        db, user_id, insight_type, unread_only, limit
    )
    unread_count = await service.get_unread_count(db, user_id)

    return InsightListResponse(
        insights=[InsightResponse.model_validate(i) for i in insights],
        total=len(insights),
        unread_count=unread_count,
    )


@router.post("/generate", response_model=list[InsightResponse])
async def generate_insights(
    request: GenerateInsightsRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    生成 AI 洞察

    根据上下文类型生成训练洞察和建议。
    """
    service = get_insight_service()
    insights = await service.generate_insights(db, request)

    return [InsightResponse.model_validate(i) for i in insights]


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取洞察详情
    """
    service = get_insight_service()
    insight = await service.get_insight(db, insight_id)

    if not insight:
        raise HTTPException(status_code=404, detail="洞察不存在")

    return InsightResponse.model_validate(insight)


@router.post("/{insight_id}/read")
async def mark_as_read(
    insight_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    标记洞察为已读
    """
    service = get_insight_service()
    success = await service.mark_as_read(db, insight_id)

    if not success:
        raise HTTPException(status_code=404, detail="洞察不存在")

    return {"message": "已标记为已读", "insight_id": insight_id}


@router.post("/{insight_id}/dismiss")
async def dismiss_insight(
    insight_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    忽略洞察

    洞察将不再显示在列表中。
    """
    service = get_insight_service()
    success = await service.dismiss_insight(db, insight_id)

    if not success:
        raise HTTPException(status_code=404, detail="洞察不存在")

    return {"message": "洞察已忽略", "insight_id": insight_id}


@router.post("/{insight_id}/feedback", response_model=InsightResponse)
async def submit_feedback(
    insight_id: str,
    feedback: InsightFeedback,
    db: AsyncSession = Depends(get_db_session),
):
    """
    提交洞察反馈

    帮助改进 AI 洞察的质量。
    """
    service = get_insight_service()
    insight = await service.submit_feedback(db, insight_id, feedback)

    if not insight:
        raise HTTPException(status_code=404, detail="洞察不存在")

    return InsightResponse.model_validate(insight)


@router.get("/user/{user_id}/unread-count")
async def get_unread_count(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取未读洞察数量
    """
    service = get_insight_service()
    count = await service.get_unread_count(db, user_id)

    return {"user_id": user_id, "unread_count": count}
