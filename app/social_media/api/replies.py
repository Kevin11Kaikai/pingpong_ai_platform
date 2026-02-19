"""
回复建议 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.social_media.core import get_reply_service
from app.social_media.schemas import (
    ReplyGenerateRequest, ReplySuggestionResponse, ReplySuggestionListResponse,
    ReplyFeedbackRequest, ReplyPublishRequest,
)

router = APIRouter()


@router.post("/generate", response_model=ReplySuggestionResponse)
async def generate_reply(
    data: ReplyGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReplySuggestionResponse:
    """
    生成回复建议

    基于 RAG 为指定内容生成回复建议。
    支持多种回复风格：professional（专业）, friendly（友好）, concise（简洁）。
    """
    service = get_reply_service()

    try:
        suggestion = await service.generate_reply(
            db,
            content_id=data.content_id,
            style=data.style,
            use_rag=data.use_rag,
            max_length=data.max_length,
            temperature=data.temperature,
        )
        await db.commit()

        return _to_suggestion_response(suggestion)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/content/{content_id}", response_model=ReplySuggestionListResponse)
async def get_content_suggestions(
    content_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReplySuggestionListResponse:
    """
    获取内容的回复建议列表

    返回为该内容生成的所有回复建议，按创建时间倒序排列。
    """
    service = get_reply_service()
    suggestions = await service.get_suggestions(db, content_id)

    return ReplySuggestionListResponse(
        suggestions=[_to_suggestion_response(s) for s in suggestions],
        total=len(suggestions),
    )


@router.get("/{suggestion_id}", response_model=ReplySuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReplySuggestionResponse:
    """
    获取单个回复建议

    返回指定 ID 的回复建议详情。
    """
    service = get_reply_service()
    suggestion = await service.get_suggestion(db, suggestion_id)

    if not suggestion:
        raise HTTPException(status_code=404, detail="回复建议不存在")

    return _to_suggestion_response(suggestion)


@router.post("/feedback")
async def submit_feedback(
    data: ReplyFeedbackRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    提交回复反馈

    用户可以对回复建议提供反馈，支持编辑修改。
    反馈类型：helpful（有帮助）, not_helpful（没帮助）, edited（已编辑）
    """
    service = get_reply_service()

    try:
        await service.submit_feedback(
            db,
            suggestion_id=data.suggestion_id,
            feedback=data.feedback,
            edited_content=data.edited_content,
        )
        await db.commit()
        return {"message": "反馈已提交"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/publish")
async def publish_reply(
    data: ReplyPublishRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    标记回复为已发布

    当用户将回复发布到原平台后，调用此接口更新状态。
    同时会更新关联内容的状态为已发布。
    """
    service = get_reply_service()

    try:
        await service.mark_published(db, data.suggestion_id)
        await db.commit()
        return {"message": "已标记为发布"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _to_suggestion_response(suggestion) -> ReplySuggestionResponse:
    """转换为建议响应"""
    return ReplySuggestionResponse(
        id=suggestion.id,
        content_id=suggestion.content_id,
        reply_content=suggestion.reply_content,
        style=suggestion.style,
        model_used=suggestion.model_used,
        sources=suggestion.sources,
        quality_score=suggestion.quality_score,
        is_selected=suggestion.is_selected,
        is_published=suggestion.is_published,
        user_feedback=suggestion.user_feedback,
        edited_content=suggestion.edited_content,
        created_at=suggestion.created_at,
    )
