"""
学习推荐 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.learning_resources.core import (
    get_recommendation_engine,
    get_profile_service,
    get_resource_service,
)
from app.learning_resources.models import DifficultyLevel, ResourceCategory, ResourceType
from app.learning_resources.schemas import (
    RecommendationRequest, RecommendationResponse,
    QuickRecommendationRequest, ResourceBrief,
)

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取个性化推荐

    根据用户学习档案、学习历史和兴趣，推荐合适的学习资源或路径。

    推荐类型:
    - resources: 推荐学习资源
    - paths: 推荐学习路径
    - next_step: 推荐下一步学习内容
    """
    engine = get_recommendation_engine()
    profile_service = get_profile_service()

    # 获取用户档案
    profile = await profile_service.get_or_create_profile(db, request.user_id)

    if request.recommendation_type == "resources":
        recommendations, explanation = await engine.get_resource_recommendations(
            db, profile,
            top_k=request.top_k,
            exclude_completed=request.exclude_completed,
        )
        return RecommendationResponse(
            user_id=request.user_id,
            recommendation_type="resources",
            resources=recommendations,
            explanation=explanation,
        )

    elif request.recommendation_type == "paths":
        recommendations, explanation = await engine.get_path_recommendations(
            db, profile,
            top_k=request.top_k,
        )
        return RecommendationResponse(
            user_id=request.user_id,
            recommendation_type="paths",
            paths=recommendations,
            explanation=explanation,
        )

    elif request.recommendation_type == "next_step":
        resource, explanation = await engine.get_next_step(db, profile)
        next_step = None
        if resource:
            next_step = ResourceBrief(
                id=resource.id,
                title=resource.title,
                resource_type=resource.resource_type.value if resource.resource_type else "video",
                category=resource.category.value if resource.category else "technique",
                difficulty_level=resource.difficulty_level.value if resource.difficulty_level else "beginner",
                duration_minutes=resource.duration_minutes,
                author=resource.author,
                source=resource.source,
                tags=resource.tags,
                view_count=resource.view_count or 0,
                like_count=resource.like_count or 0,
                is_featured=resource.is_featured or False,
                status=resource.status.value if resource.status else "published",
                created_at=resource.created_at,
            )
        return RecommendationResponse(
            user_id=request.user_id,
            recommendation_type="next_step",
            next_step=next_step,
            explanation=explanation,
        )

    else:
        raise HTTPException(status_code=400, detail="无效的推荐类型")


@router.get("/quick")
async def get_quick_recommendations(
    current_level: str = Query("beginner", description="当前水平"),
    category: str = Query(None, description="感兴趣分类"),
    resource_type: str = Query(None, description="偏好资源类型"),
    top_k: int = Query(5, ge=1, le=20, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    快速推荐

    无需用户档案，根据基本参数快速获取推荐资源。
    适合匿名用户或首次访问。
    """
    from app.learning_resources.models import LearningResource, ResourceStatus
    from sqlalchemy import select, and_, desc

    # 构建查询条件
    conditions = [
        LearningResource.status == ResourceStatus.PUBLISHED,
    ]

    # 难度过滤
    try:
        level = DifficultyLevel(current_level)
        conditions.append(LearningResource.difficulty_level == level)
    except ValueError:
        pass

    # 分类过滤
    if category:
        try:
            cat = ResourceCategory(category)
            conditions.append(LearningResource.category == cat)
        except ValueError:
            pass

    # 类型过滤
    if resource_type:
        try:
            res_type = ResourceType(resource_type)
            conditions.append(LearningResource.resource_type == res_type)
        except ValueError:
            pass

    # 查询
    result = await db.execute(
        select(LearningResource)
        .where(and_(*conditions))
        .order_by(desc(LearningResource.is_featured), desc(LearningResource.view_count))
        .limit(top_k)
    )
    resources = list(result.scalars().all())

    return {
        "recommendations": [
            ResourceBrief(
                id=r.id,
                title=r.title,
                resource_type=r.resource_type.value if r.resource_type else "video",
                category=r.category.value if r.category else "technique",
                difficulty_level=r.difficulty_level.value if r.difficulty_level else "beginner",
                duration_minutes=r.duration_minutes,
                author=r.author,
                source=r.source,
                tags=r.tags,
                view_count=r.view_count or 0,
                like_count=r.like_count or 0,
                is_featured=r.is_featured or False,
                status=r.status.value if r.status else "published",
                created_at=r.created_at,
            )
            for r in resources
        ],
        "total": len(resources),
        "filters": {
            "current_level": current_level,
            "category": category,
            "resource_type": resource_type,
        },
    }


@router.get("/popular")
async def get_popular_resources(
    category: str = Query(None, description="分类过滤"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取热门资源

    按浏览量和点赞数排序的热门资源。
    """
    from app.learning_resources.models import LearningResource, ResourceStatus
    from sqlalchemy import select, desc

    conditions = [LearningResource.status == ResourceStatus.PUBLISHED]

    if category:
        try:
            cat = ResourceCategory(category)
            conditions.append(LearningResource.category == cat)
        except ValueError:
            pass

    result = await db.execute(
        select(LearningResource)
        .where(*conditions)
        .order_by(desc(LearningResource.view_count + LearningResource.like_count * 10))
        .limit(limit)
    )
    resources = list(result.scalars().all())

    return {
        "resources": [
            ResourceBrief(
                id=r.id,
                title=r.title,
                resource_type=r.resource_type.value if r.resource_type else "video",
                category=r.category.value if r.category else "technique",
                difficulty_level=r.difficulty_level.value if r.difficulty_level else "beginner",
                duration_minutes=r.duration_minutes,
                author=r.author,
                source=r.source,
                tags=r.tags,
                view_count=r.view_count or 0,
                like_count=r.like_count or 0,
                is_featured=r.is_featured or False,
                status=r.status.value if r.status else "published",
                created_at=r.created_at,
            )
            for r in resources
        ],
        "total": len(resources),
    }


@router.get("/featured")
async def get_featured_resources(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取精选资源

    返回标记为精选的高质量资源。
    """
    from app.learning_resources.models import LearningResource, ResourceStatus
    from sqlalchemy import select, desc

    result = await db.execute(
        select(LearningResource)
        .where(
            LearningResource.status == ResourceStatus.PUBLISHED,
            LearningResource.is_featured == True,
        )
        .order_by(desc(LearningResource.created_at))
        .limit(limit)
    )
    resources = list(result.scalars().all())

    return {
        "resources": [
            ResourceBrief(
                id=r.id,
                title=r.title,
                resource_type=r.resource_type.value if r.resource_type else "video",
                category=r.category.value if r.category else "technique",
                difficulty_level=r.difficulty_level.value if r.difficulty_level else "beginner",
                duration_minutes=r.duration_minutes,
                author=r.author,
                source=r.source,
                tags=r.tags,
                view_count=r.view_count or 0,
                like_count=r.like_count or 0,
                is_featured=r.is_featured or False,
                status=r.status.value if r.status else "published",
                created_at=r.created_at,
            )
            for r in resources
        ],
        "total": len(resources),
    }
