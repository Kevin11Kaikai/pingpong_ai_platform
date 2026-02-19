"""
用户装备偏好档案 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import get_profile_service
from app.equipment_recommendation.schemas import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
)

router = APIRouter()


@router.post("", response_model=UserProfileResponse)
async def create_profile(
    data: UserProfileCreate,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """
    创建用户装备偏好档案

    每个用户只能有一个偏好档案。
    包含打法风格、技术水平、装备偏好等信息。
    """
    service = get_profile_service()
    try:
        profile = await service.create_profile(db, data)
        return _to_profile_response(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=UserProfileResponse)
async def get_profile_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """
    通过用户ID获取偏好档案
    """
    service = get_profile_service()
    profile = await service.get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return _to_profile_response(profile)


@router.get("/{profile_id}", response_model=UserProfileResponse)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """
    通过档案ID获取偏好档案
    """
    service = get_profile_service()
    profile = await service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return _to_profile_response(profile)


@router.put("/{profile_id}", response_model=UserProfileResponse)
async def update_profile(
    profile_id: str,
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """
    更新用户偏好档案

    可以部分更新，只提供需要修改的字段即可。
    """
    service = get_profile_service()
    profile = await service.update_profile(db, profile_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return _to_profile_response(profile)


@router.put("/user/{user_id}", response_model=UserProfileResponse)
async def update_profile_by_user_id(
    user_id: str,
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """
    通过用户ID更新偏好档案
    """
    service = get_profile_service()
    profile = await service.update_profile_by_user_id(db, user_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return _to_profile_response(profile)


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除用户偏好档案
    """
    service = get_profile_service()
    success = await service.delete_profile(db, profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return {"message": "删除成功"}


@router.get("/{profile_id}/completeness")
async def get_profile_completeness(
    profile_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    获取档案完整度

    返回档案填写的完整程度（0-1），用于提示用户完善档案。
    完整的档案能获得更准确的推荐。
    """
    service = get_profile_service()
    profile = await service.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")

    completeness = service.calculate_profile_completeness(profile)
    return {
        "profile_id": profile_id,
        "completeness": round(completeness, 2),
        "percentage": f"{int(completeness * 100)}%",
    }


def _to_profile_response(profile) -> UserProfileResponse:
    """转换为响应模型"""
    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        nickname=profile.nickname,
        years_playing=profile.years_playing,
        playing_style=profile.playing_style.value if profile.playing_style else None,
        grip_style=profile.grip_style.value if profile.grip_style else None,
        skill_level=profile.skill_level.value if profile.skill_level else None,
        prefer_speed=profile.prefer_speed,
        prefer_spin=profile.prefer_spin,
        prefer_control=profile.prefer_control,
        budget_min=profile.budget_min,
        budget_max=profile.budget_max,
        budget_currency=profile.budget_currency,
        current_equipment=profile.current_equipment,
        additional_info=profile.additional_info,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
