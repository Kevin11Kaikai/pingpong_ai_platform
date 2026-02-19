"""
学习资源 REST API 路由
"""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.learning_resources.core.resource_service import get_resource_service
from app.learning_resources.schemas import (
    ResourceCreate, ResourceUpdate, ResourceResponse, ResourceBrief,
    ResourceListResponse, ResourceSearchRequest,
    SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult,
    LearningStatsResponse, BookmarkCreate, BookmarkResponse, BookmarkListResponse,
)

router = APIRouter()


# ========== 工具函数 ==========

def _to_resource_brief(resource) -> ResourceBrief:
    """ORM 对象 → ResourceBrief"""
    return ResourceBrief(
        id=resource.id,
        title=resource.title,
        resource_type=resource.resource_type.value if hasattr(resource.resource_type, "value") else str(resource.resource_type),
        category=resource.category.value if hasattr(resource.category, "value") else str(resource.category),
        difficulty_level=resource.difficulty_level.value if hasattr(resource.difficulty_level, "value") else str(resource.difficulty_level),
        duration_minutes=resource.duration_minutes,
        author=resource.author,
        source=resource.source,
        tags=resource.tags,
        view_count=resource.view_count or 0,
        like_count=resource.like_count or 0,
        is_featured=resource.is_featured or False,
        status=resource.status.value if hasattr(resource.status, "value") else str(resource.status),
        created_at=resource.created_at,
    )


def _to_resource_response(resource) -> ResourceResponse:
    """ORM 对象 → ResourceResponse"""
    return ResourceResponse(
        id=resource.id,
        title=resource.title,
        description=resource.description,
        resource_type=resource.resource_type.value if hasattr(resource.resource_type, "value") else str(resource.resource_type),
        category=resource.category.value if hasattr(resource.category, "value") else str(resource.category),
        difficulty_level=resource.difficulty_level.value if hasattr(resource.difficulty_level, "value") else str(resource.difficulty_level),
        url=resource.url,
        thumbnail_url=resource.thumbnail_url,
        duration_minutes=resource.duration_minutes,
        author=resource.author,
        source=resource.source,
        language=resource.language,
        tags=resource.tags,
        view_count=resource.view_count or 0,
        like_count=resource.like_count or 0,
        is_featured=resource.is_featured or False,
        status=resource.status.value if hasattr(resource.status, "value") else str(resource.status),
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


# ========== 资源 CRUD ==========

@router.post("", response_model=ResourceResponse, status_code=201)
async def create_resource(
    data: ResourceCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ResourceResponse:
    """
    创建学习资源

    创建新的乒乓球学习资源并自动生成语义向量用于后续搜索。
    """
    service = get_resource_service()
    resource = await service.create_resource(db, data)
    await db.commit()
    return _to_resource_response(resource)


@router.get("/stats", response_model=LearningStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
) -> LearningStatsResponse:
    """
    获取学习资源统计信息

    返回按类型、分类、难度分组的资源数量统计。
    """
    service = get_resource_service()
    stats = await service.get_stats(db)
    # 获取路径总数
    from sqlalchemy import select, func
    from app.learning_resources.models import LearningPath
    total_paths = (await db.execute(
        select(func.count()).select_from(LearningPath)
        .where(LearningPath.is_published.is_(True))
    )).scalar_one()

    return LearningStatsResponse(
        total_resources=stats["total"],
        resources_by_type=stats["by_type"],
        resources_by_category=stats["by_category"],
        resources_by_difficulty=stats["by_difficulty"],
        total_paths=total_paths,
        featured_resources=stats["featured"],
    )


@router.get("/search", response_model=SemanticSearchResponse)
async def semantic_search(
    query: str = Query(..., min_length=1, description="搜索文本"),
    top_k: int = Query(10, ge=1, le=50),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    category: Optional[str] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> SemanticSearchResponse:
    """
    语义搜索学习资源

    基于向量相似度搜索与查询文本最相关的学习资源。
    """
    service = get_resource_service()
    params = SemanticSearchRequest(
        query=query,
        top_k=top_k,
        min_score=min_score,
        category=category,
        difficulty_level=difficulty_level,
    )
    results = await service.semantic_search(db, params)
    return SemanticSearchResponse(
        query=query,
        results=[
            SemanticSearchResult(resource=_to_resource_brief(r), score=round(s, 4))
            for r, s in results
        ],
        total=len(results),
    )


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    keyword: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    status: str = Query("published"),
    is_featured: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db_session),
) -> ResourceListResponse:
    """
    分页查询学习资源列表

    支持关键词过滤、类型/分类/难度过滤和排序。
    """
    service = get_resource_service()
    params = ResourceSearchRequest(
        keyword=keyword,
        resource_type=resource_type,
        category=category,
        difficulty_level=difficulty_level,
        status=status,
        is_featured=is_featured,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    resources, total = await service.list_resources(db, params)
    return ResourceListResponse(
        resources=[_to_resource_brief(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ResourceResponse:
    """
    获取学习资源详情

    返回资源的完整信息，同时增加浏览量计数。
    """
    service = get_resource_service()
    resource = await service.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    # 增加浏览量
    await service.increment_view_count(db, resource_id)
    await db.commit()
    return _to_resource_response(resource)


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    data: ResourceUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ResourceResponse:
    """
    更新学习资源

    支持部分更新，仅修改请求中提供的字段。
    """
    service = get_resource_service()
    resource = await service.update_resource(db, resource_id, data)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    await db.commit()
    return _to_resource_response(resource)


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    删除学习资源

    同时级联删除路径条目、进度记录和收藏。
    """
    service = get_resource_service()
    deleted = await service.delete_resource(db, resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="资源不存在")
    await db.commit()


@router.post("/{resource_id}/like", response_model=dict)
async def like_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    点赞学习资源

    返回更新后的点赞总数。
    """
    service = get_resource_service()
    count = await service.toggle_like(db, resource_id, increment=True)
    if count is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    await db.commit()
    return {"resource_id": resource_id, "like_count": count}


# ========== 收藏 ==========

@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
async def create_bookmark(
    data: BookmarkCreate,
    db: AsyncSession = Depends(get_db_session),
) -> BookmarkResponse:
    """
    收藏学习资源（幂等）

    重复收藏不报错，直接返回已有收藏记录。
    """
    # 验证资源存在
    service = get_resource_service()
    resource = await service.get_resource(db, data.resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    bm, _ = await service.create_bookmark(db, data)
    await db.commit()
    # 重新加载确保 resource 关系可用
    await db.refresh(bm)
    # 需要手动加载 resource 到 bm
    bm_resource = await service.get_resource(db, bm.resource_id)
    return BookmarkResponse(
        id=bm.id,
        user_id=bm.user_id,
        resource_id=bm.resource_id,
        resource=_to_resource_brief(bm_resource),
        created_at=bm.created_at,
    )


@router.get("/bookmarks/{user_id}", response_model=BookmarkListResponse)
async def list_bookmarks(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> BookmarkListResponse:
    """
    获取用户收藏列表

    返回指定用户的所有收藏资源，按收藏时间降序排列。
    """
    service = get_resource_service()
    bookmarks = await service.list_bookmarks(db, user_id)
    items = []
    for bm in bookmarks:
        res = bm.resource or await service.get_resource(db, bm.resource_id)
        if res:
            items.append(
                BookmarkResponse(
                    id=bm.id,
                    user_id=bm.user_id,
                    resource_id=bm.resource_id,
                    resource=_to_resource_brief(res),
                    created_at=bm.created_at,
                )
            )
    return BookmarkListResponse(bookmarks=items, total=len(items))


@router.delete("/bookmarks/{user_id}/{resource_id}", status_code=204)
async def delete_bookmark(
    user_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    取消收藏学习资源
    """
    service = get_resource_service()
    deleted = await service.delete_bookmark(db, user_id, resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="收藏记录不存在")
    await db.commit()
