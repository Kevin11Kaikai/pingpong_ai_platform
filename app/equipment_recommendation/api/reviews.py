"""
装备评价 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import get_review_service, get_profile_service
from app.equipment_recommendation.schemas import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewListResponse,
)

router = APIRouter()


@router.post("", response_model=ReviewResponse)
async def create_review(
    data: ReviewCreate,
    user_id: str = Query(None, description="用户ID（用于关联用户档案）"),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """
    创建装备评价

    评分为 1-5 分。可以评价整体、速度、旋转、控制、耐用性和性价比。
    提供 user_id 可将评价关联到用户档案。
    """
    review_service = get_review_service()
    profile_service = get_profile_service()

    # 获取用户档案ID
    user_profile_id = None
    if user_id:
        profile = await profile_service.get_profile_by_user_id(db, user_id)
        if profile:
            user_profile_id = profile.id

    try:
        review = await review_service.create_review(db, data, user_profile_id)
        return await _to_review_response(db, review)
    except Exception as e:
        logger.error(f"创建评价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/{equipment_id}", response_model=ReviewListResponse)
async def list_reviews_by_equipment(
    equipment_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewListResponse:
    """
    获取装备的评价列表

    支持按创建时间、评分等排序。
    """
    service = get_review_service()
    reviews, total = await service.list_reviews_by_equipment(
        db, equipment_id, page, page_size, sort_by, sort_order
    )

    return ReviewListResponse(
        reviews=[await _to_review_response(db, r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/equipment/{equipment_id}/summary")
async def get_review_summary(
    equipment_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    获取装备的评分汇总

    返回各项评分的平均值和评分分布。
    """
    service = get_review_service()
    summary = await service.get_rating_summary(db, equipment_id)
    return summary


@router.get("/user/{user_profile_id}", response_model=ReviewListResponse)
async def list_reviews_by_user(
    user_profile_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewListResponse:
    """
    获取用户的评价列表
    """
    service = get_review_service()
    reviews, total = await service.list_reviews_by_user(
        db, user_profile_id, page, page_size
    )

    return ReviewListResponse(
        reviews=[await _to_review_response(db, r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """
    获取评价详情
    """
    service = get_review_service()
    review = await service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")
    return await _to_review_response(db, review)


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """
    更新评价

    可以修改评分和评价内容。
    """
    service = get_review_service()
    review = await service.update_review(db, review_id, data)
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")
    return await _to_review_response(db, review)


@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除评价

    执行软删除，评价不会真正删除，但不会再显示。
    """
    service = get_review_service()
    success = await service.delete_review(db, review_id)
    if not success:
        raise HTTPException(status_code=404, detail="评价不存在")
    return {"message": "删除成功"}


@router.post("/{review_id}/helpful")
async def mark_review_helpful(
    review_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    标记评价为有帮助

    增加评价的"有帮助"计数。
    """
    service = get_review_service()
    review = await service.mark_helpful(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")
    return {
        "message": "标记成功",
        "helpful_count": review.helpful_count,
    }


async def _to_review_response(db: AsyncSession, review) -> ReviewResponse:
    """转换为响应模型"""
    # 获取装备名称
    equipment_name = ""
    if review.equipment:
        equipment_name = review.equipment.name

    # 获取用户昵称
    user_nickname = None
    if review.user_profile:
        user_nickname = review.user_profile.nickname

    return ReviewResponse(
        id=review.id,
        equipment_id=review.equipment_id,
        equipment_name=equipment_name,
        user_profile_id=review.user_profile_id,
        user_nickname=user_nickname,
        overall_rating=review.overall_rating,
        speed_rating=review.speed_rating,
        spin_rating=review.spin_rating,
        control_rating=review.control_rating,
        durability_rating=review.durability_rating,
        value_rating=review.value_rating,
        title=review.title,
        content=review.content,
        pros=review.pros,
        cons=review.cons,
        usage_duration=review.usage_duration,
        helpful_count=review.helpful_count,
        is_verified=review.is_verified,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )
