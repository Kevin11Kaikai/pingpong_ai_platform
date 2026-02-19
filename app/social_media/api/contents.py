"""
内容管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.social_media.core import get_content_service
from app.social_media.schemas import (
    ContentCreate, ContentUpdate, ContentResponse, ContentBrief,
    ContentListResponse, ContentSearchRequest,
    SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult,
    OverallStatsResponse,
)

router = APIRouter()


@router.post("", response_model=ContentResponse)
async def create_content(
    data: ContentCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ContentResponse:
    """
    创建内容（手动导入）

    用于手动导入社交媒体内容，适合小批量或测试场景。
    内容会自动生成向量嵌入用于语义搜索。
    """
    service = get_content_service()
    content = await service.create_content(db, data)
    await db.commit()
    return _to_content_response(content)


@router.get("/stats", response_model=OverallStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
) -> OverallStatsResponse:
    """
    获取内容统计信息

    返回各状态和类型的内容数量统计。
    """
    service = get_content_service()
    stats = await service.get_stats(db)

    return OverallStatsResponse(
        total_contents=stats["total"],
        total_platforms=0,  # TODO: 计算平台数
        total_tags=0,  # TODO: 计算标签数
        total_reply_suggestions=0,  # TODO: 计算回复数
        contents_by_status=stats["by_status"],
        contents_by_type=stats["by_type"],
        platform_stats=[],  # TODO: 平台统计
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ContentResponse:
    """
    获取内容详情

    返回内容的完整信息，包括分析结果和回复建议数量。
    """
    service = get_content_service()
    content = await service.get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    return _to_content_response(content)


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: str,
    data: ContentUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ContentResponse:
    """
    更新内容

    可更新标题、内容、标签和状态。
    如果内容变化会重新生成向量嵌入。
    """
    service = get_content_service()
    content = await service.update_content(db, content_id, data)
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    await db.commit()
    return _to_content_response(content)


@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除内容

    删除内容及其关联的回复建议。
    """
    service = get_content_service()
    if not await service.delete_content(db, content_id):
        raise HTTPException(status_code=404, detail="内容不存在")
    await db.commit()
    return {"message": "删除成功"}


@router.post("/search", response_model=ContentListResponse)
async def search_contents(
    params: ContentSearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ContentListResponse:
    """
    搜索内容

    支持关键词搜索、平台筛选、状态筛选、日期范围等多维度过滤。
    返回分页结果。
    """
    service = get_content_service()
    contents, total = await service.search_contents(db, params)

    return ContentListResponse(
        contents=[_to_content_brief(c) for c in contents],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    params: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SemanticSearchResponse:
    """
    语义搜索

    基于向量相似度进行语义搜索，找到与查询语义相似的内容。
    适合自然语言查询场景。
    """
    service = get_content_service()
    results = await service.semantic_search(db, params)

    return SemanticSearchResponse(
        results=[
            SemanticSearchResult(
                content=_to_content_brief(content),
                similarity_score=round(score, 3),
            )
            for content, score in results
        ],
        query=params.query,
        total=len(results),
    )


def _get_reply_count(content) -> int:
    """安全获取回复数量，处理未加载的关系"""
    from sqlalchemy.orm import attributes

    # 检查 reply_suggestions 是否已加载
    state = attributes.instance_state(content)
    if "reply_suggestions" in state.dict:
        return len(content.reply_suggestions) if content.reply_suggestions else 0
    return 0


def _get_platform(content) -> str:
    """安全获取平台名称"""
    from sqlalchemy.orm import attributes

    state = attributes.instance_state(content)
    if "platform_config" in state.dict and content.platform_config:
        return content.platform_config.platform.value
    return "unknown"


def _to_content_brief(content) -> ContentBrief:
    """转换为简要信息"""
    return ContentBrief(
        id=content.id,
        platform=_get_platform(content),
        content_type=content.content_type.value,
        title=content.title,
        content_preview=content.content[:100] + "..." if len(content.content) > 100 else content.content,
        author_name=content.author_name,
        status=content.status.value,
        quality_score=content.quality_score,
        like_count=content.like_count,
        comment_count=content.comment_count,
        reply_count=_get_reply_count(content),
        created_at=content.created_at,
    )


def _to_content_response(content) -> ContentResponse:
    """转换为完整响应"""
    return ContentResponse(
        id=content.id,
        platform=_get_platform(content),
        content_type=content.content_type.value,
        title=content.title,
        content=content.content,
        author_name=content.author_name,
        author_id=content.author_id,
        external_url=content.external_url,
        external_id=content.external_id,
        parent_id=content.parent_id,
        view_count=content.view_count,
        like_count=content.like_count,
        comment_count=content.comment_count,
        share_count=content.share_count,
        published_at=content.published_at,
        tags=content.tags,
        status=content.status.value,
        quality_score=content.quality_score,
        relevance_score=content.relevance_score,
        analysis_result=content.analysis_result,
        reply_suggestion_count=_get_reply_count(content),
        created_at=content.created_at,
        updated_at=content.updated_at,
    )
