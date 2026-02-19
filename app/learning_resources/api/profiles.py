"""
用户学习档案 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.learning_resources.core import get_profile_service
from app.learning_resources.schemas import (
    UserLearningProfileCreate, UserLearningProfileUpdate, UserLearningProfileResponse,
    UserPathEnrollmentResponse, UserLearningStatsResponse,
)

router = APIRouter()


@router.post("", response_model=UserLearningProfileResponse)
async def create_profile(
    data: UserLearningProfileCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建用户学习档案

    为新用户创建学习档案，记录学习目标、偏好等信息。
    """
    service = get_profile_service()
    try:
        profile = await service.create_profile(db, data)
        return UserLearningProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户档案失败: {e}")
        raise HTTPException(status_code=500, detail="创建档案失败")


@router.get("/{user_id}", response_model=UserLearningProfileResponse)
async def get_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户学习档案

    返回用户的学习档案信息，包括学习统计。
    """
    service = get_profile_service()
    profile = await service.get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return UserLearningProfileResponse.model_validate(profile)


@router.put("/{user_id}", response_model=UserLearningProfileResponse)
async def update_profile(
    user_id: str,
    data: UserLearningProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新用户学习档案

    更新用户的学习目标、偏好等信息。
    """
    service = get_profile_service()
    profile = await service.update_profile(db, user_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="用户档案不存在")
    return UserLearningProfileResponse.model_validate(profile)


@router.post("/{user_id}/enroll/{path_id}", response_model=UserPathEnrollmentResponse)
async def enroll_path(
    user_id: str,
    path_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    报名学习路径

    用户报名参加学习路径，开始系统化学习。
    """
    service = get_profile_service()
    try:
        enrollment = await service.enroll_path(db, user_id, path_id)

        # 获取路径信息
        from app.learning_resources.models import LearningPath, LearningPathItem
        from sqlalchemy import select, func
        path_result = await db.execute(
            select(LearningPath).where(LearningPath.id == path_id)
        )
        path = path_result.scalar_one_or_none()

        item_count = (await db.execute(
            select(func.count()).select_from(LearningPathItem)
            .where(LearningPathItem.path_id == path_id)
        )).scalar_one()

        return UserPathEnrollmentResponse(
            id=enrollment.id,
            profile_id=enrollment.profile_id,
            path_id=enrollment.path_id,
            path_title=path.title if path else "",
            status=enrollment.status.value if enrollment.status else "not_started",
            progress_percent=enrollment.progress_percent or 0,
            current_item_index=enrollment.current_item_index or 0,
            completed_items=enrollment.completed_items or 0,
            total_items=item_count,
            total_study_minutes=enrollment.total_study_minutes or 0,
            started_at=enrollment.started_at,
            completed_at=enrollment.completed_at,
            created_at=enrollment.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}/enrollments", response_model=list[UserPathEnrollmentResponse])
async def get_user_enrollments(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户所有路径报名

    返回用户报名的所有学习路径及进度。
    """
    service = get_profile_service()
    enrollments = await service.get_user_enrollments(db, user_id)

    # 获取每个路径的项目数
    from app.learning_resources.models import LearningPathItem
    from sqlalchemy import select, func

    result = []
    for enrollment in enrollments:
        item_count = (await db.execute(
            select(func.count()).select_from(LearningPathItem)
            .where(LearningPathItem.path_id == enrollment.path_id)
        )).scalar_one()

        result.append(UserPathEnrollmentResponse(
            id=enrollment.id,
            profile_id=enrollment.profile_id,
            path_id=enrollment.path_id,
            path_title=enrollment.path.title if enrollment.path else "",
            status=enrollment.status.value if enrollment.status else "not_started",
            progress_percent=enrollment.progress_percent or 0,
            current_item_index=enrollment.current_item_index or 0,
            completed_items=enrollment.completed_items or 0,
            total_items=item_count,
            total_study_minutes=enrollment.total_study_minutes or 0,
            started_at=enrollment.started_at,
            completed_at=enrollment.completed_at,
            created_at=enrollment.created_at,
        ))

    return result


@router.post("/{user_id}/study-session")
async def record_study_session(
    user_id: str,
    study_minutes: int = Query(..., ge=1, le=480, description="学习时长（分钟）"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    记录学习时长

    记录用户的学习时长，自动更新连续学习天数。
    """
    service = get_profile_service()
    profile = await service.record_study_session(db, user_id, study_minutes)
    return {
        "message": "记录成功",
        "total_study_minutes": profile.total_study_minutes,
        "current_streak_days": profile.current_streak_days,
        "longest_streak_days": profile.longest_streak_days,
    }


@router.get("/{user_id}/stats", response_model=UserLearningStatsResponse)
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户学习统计

    返回用户的学习统计数据，包括按类型、分类的完成情况。
    """
    service = get_profile_service()
    stats = await service.get_user_stats(db, user_id)
    return stats
