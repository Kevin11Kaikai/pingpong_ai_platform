"""
装备推荐 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import (
    get_profile_service,
    get_recommendation_engine,
    get_equipment_service,
)
from app.equipment_recommendation.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    SimilarEquipmentRequest,
    SimilarEquipmentResponse,
    EquipmentBrief,
)

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RecommendationResponse:
    """
    获取个性化装备推荐

    根据用户的偏好档案（打法风格、技术水平、预算等）推荐合适的装备。

    推荐类型:
    - blade: 只推荐底板
    - rubber: 只推荐胶皮
    - full_setup: 推荐完整配置（默认）

    可以通过 override_* 参数临时覆盖用户档案中的设置。
    """
    profile_service = get_profile_service()
    engine = get_recommendation_engine()

    # 获取或创建用户档案
    profile = await profile_service.get_or_create_profile(db, request.user_id)

    try:
        items, explanation = await engine.get_recommendations(db, profile, request)

        return RecommendationResponse(
            id=str(profile.id),  # 使用 profile_id 作为推荐记录的关联
            user_profile_id=profile.id,
            recommendation_type=request.recommendation_type,
            recommended_items=items,
            explanation=explanation,
            created_at=profile.updated_at,
        )
    except Exception as e:
        logger.error(f"获取推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick")
async def get_quick_recommendations(
    playing_style: str = Query(None, description="打法风格: offensive/defensive/all_round/chopper"),
    skill_level: str = Query(None, description="技术水平: beginner/intermediate/advanced/professional"),
    budget_max: float = Query(None, ge=0, description="预算上限"),
    category: str = Query("blade", description="推荐类型: blade/rubber/full_setup"),
    top_k: int = Query(5, ge=1, le=20, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    快速推荐（无需用户档案）

    基于传入的参数直接进行推荐，适用于游客或快速查询场景。
    """
    from app.equipment_recommendation.models import (
        PlayingStyle, SkillLevel, UserEquipmentProfile
    )
    import uuid

    engine = get_recommendation_engine()

    # 构建临时档案
    temp_profile = UserEquipmentProfile(
        id=str(uuid.uuid4()),
        user_id="temp_user",
        playing_style=PlayingStyle(playing_style) if playing_style else None,
        skill_level=SkillLevel(skill_level) if skill_level else None,
        budget_max=budget_max,
        prefer_speed=70 if playing_style == "offensive" else 50,
        prefer_spin=50,
        prefer_control=70 if playing_style == "defensive" else 50,
    )

    # 构建请求
    request = RecommendationRequest(
        user_id="temp_user",
        recommendation_type=category,
        top_k=top_k,
    )

    try:
        items, explanation = await engine.get_recommendations(db, temp_profile, request)

        return {
            "recommendation_type": category,
            "recommended_items": [
                {
                    "equipment": item.equipment.model_dump(),
                    "score": item.score,
                    "reasons": item.reasons,
                }
                for item in items
            ],
            "explanation": explanation,
        }
    except Exception as e:
        logger.error(f"快速推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar", response_model=SimilarEquipmentResponse)
async def get_similar_equipment(
    request: SimilarEquipmentRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SimilarEquipmentResponse:
    """
    获取相似装备

    基于装备的描述和特性，使用向量相似度找到相似的装备。
    适用于"看了又看"、"同类推荐"等场景。
    """
    engine = get_recommendation_engine()

    ref_equipment, similar_list, scores = await engine.get_similar_equipment(
        db, request.equipment_id, request.top_k
    )

    if not ref_equipment:
        raise HTTPException(status_code=404, detail="装备不存在")

    return SimilarEquipmentResponse(
        reference_equipment=_to_equipment_brief(ref_equipment),
        similar_equipment=[_to_equipment_brief(e) for e in similar_list],
        similarity_scores=[round(s, 3) for s in scores],
    )


@router.get("/popular")
async def get_popular_equipment(
    category_id: str = Query(None, description="分类ID"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    获取热门装备

    按浏览量和评分综合排序，返回热门装备列表。
    """
    from app.equipment_recommendation.schemas import EquipmentSearchRequest

    service = get_equipment_service()

    params = EquipmentSearchRequest(
        category_id=category_id,
        sort_by="view_count",
        sort_order="desc",
        page=1,
        page_size=limit,
    )

    equipment_list, total = await service.search_equipment(db, params)

    return {
        "equipment": [_to_equipment_brief(e).model_dump() for e in equipment_list],
        "total": total,
    }


@router.get("/featured")
async def get_featured_equipment(
    category_id: str = Query(None, description="分类ID"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    获取精选装备

    返回编辑推荐的精选装备列表。
    """
    from app.equipment_recommendation.schemas import EquipmentSearchRequest

    service = get_equipment_service()

    params = EquipmentSearchRequest(
        category_id=category_id,
        is_featured=True,
        sort_by="avg_rating",
        sort_order="desc",
        page=1,
        page_size=limit,
    )

    equipment_list, total = await service.search_equipment(db, params)

    return {
        "equipment": [_to_equipment_brief(e).model_dump() for e in equipment_list],
        "total": total,
    }


def _to_equipment_brief(equipment) -> EquipmentBrief:
    """转换为简要信息"""
    return EquipmentBrief(
        id=equipment.id,
        name=equipment.name,
        brand_name=equipment.brand.name if equipment.brand else "",
        category_name=equipment.category.display_name if equipment.category else "",
        price_min=equipment.price_min,
        price_max=equipment.price_max,
        speed_rating=equipment.speed_rating,
        spin_rating=equipment.spin_rating,
        control_rating=equipment.control_rating,
        avg_rating=equipment.avg_rating,
        review_count=equipment.review_count,
        image_url=equipment.image_urls[0] if equipment.image_urls else None,
    )
