"""
用户学习档案服务
管理用户学习档案、路径报名和学习统计
"""

from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.learning_resources.models import (
    UserLearningProfile, UserPathEnrollment, UserProgress,
    LearningPath, LearningPathItem, LearningResource,
    DifficultyLevel, LearningStatus,
)
from app.learning_resources.schemas import (
    UserLearningProfileCreate, UserLearningProfileUpdate,
)


class ProfileService:
    """用户学习档案服务"""

    async def create_profile(
        self,
        db: AsyncSession,
        data: UserLearningProfileCreate,
    ) -> UserLearningProfile:
        """
        创建用户学习档案

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的档案对象
        """
        # 检查是否已存在
        existing = await self.get_profile_by_user_id(db, data.user_id)
        if existing:
            raise ValueError(f"用户 {data.user_id} 的档案已存在")

        profile = UserLearningProfile(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            nickname=data.nickname,
            current_level=DifficultyLevel(data.current_level),
            years_playing=data.years_playing,
            learning_goals=data.learning_goals,
            weak_points=data.weak_points,
            interests=data.interests,
            preferred_resource_types=data.preferred_resource_types,
            preferred_duration_minutes=data.preferred_duration_minutes,
            daily_goal_minutes=data.daily_goal_minutes,
        )

        db.add(profile)
        await db.flush()
        logger.info(f"创建用户学习档案: {profile.id} (user_id={data.user_id})")
        return profile

    async def get_profile(
        self,
        db: AsyncSession,
        profile_id: str,
    ) -> Optional[UserLearningProfile]:
        """按 ID 获取档案"""
        result = await db.execute(
            select(UserLearningProfile).where(UserLearningProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_profile_by_user_id(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> Optional[UserLearningProfile]:
        """按用户 ID 获取档案"""
        result = await db.execute(
            select(UserLearningProfile).where(UserLearningProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_profile(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> UserLearningProfile:
        """获取或创建用户档案"""
        profile = await self.get_profile_by_user_id(db, user_id)
        if profile:
            return profile

        # 创建默认档案
        profile = UserLearningProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            current_level=DifficultyLevel.BEGINNER,
        )
        db.add(profile)
        await db.flush()
        logger.info(f"自动创建用户学习档案: {profile.id} (user_id={user_id})")
        return profile

    async def update_profile(
        self,
        db: AsyncSession,
        user_id: str,
        data: UserLearningProfileUpdate,
    ) -> Optional[UserLearningProfile]:
        """更新用户档案"""
        profile = await self.get_profile_by_user_id(db, user_id)
        if not profile:
            return None

        update_fields = data.model_dump(exclude_unset=True)

        for field, value in update_fields.items():
            if field == "current_level" and value is not None:
                value = DifficultyLevel(value)
            setattr(profile, field, value)

        profile.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"更新用户学习档案: user_id={user_id}")
        return profile

    async def enroll_path(
        self,
        db: AsyncSession,
        user_id: str,
        path_id: str,
    ) -> UserPathEnrollment:
        """
        用户报名学习路径

        Args:
            db: 数据库会话
            user_id: 用户 ID
            path_id: 路径 ID

        Returns:
            报名记录
        """
        # 获取或创建用户档案
        profile = await self.get_or_create_profile(db, user_id)

        # 检查路径是否存在
        path_result = await db.execute(
            select(LearningPath).where(LearningPath.id == path_id)
        )
        path = path_result.scalar_one_or_none()
        if not path:
            raise ValueError(f"路径 {path_id} 不存在")

        # 检查是否已报名
        existing = await db.execute(
            select(UserPathEnrollment).where(
                and_(
                    UserPathEnrollment.profile_id == profile.id,
                    UserPathEnrollment.path_id == path_id,
                )
            )
        )
        enrollment = existing.scalar_one_or_none()

        if enrollment:
            return enrollment  # 已报名，直接返回

        # 获取路径项目数
        item_count = (await db.execute(
            select(func.count()).select_from(LearningPathItem)
            .where(LearningPathItem.path_id == path_id)
        )).scalar_one()

        # 创建报名记录
        enrollment = UserPathEnrollment(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            path_id=path_id,
            status=LearningStatus.NOT_STARTED,
        )

        db.add(enrollment)
        await db.flush()

        # 更新路径报名人数（如果有这个字段的话）
        logger.info(f"用户报名学习路径: user_id={user_id}, path_id={path_id}")
        return enrollment

    async def get_user_enrollments(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> List[UserPathEnrollment]:
        """获取用户所有路径报名"""
        profile = await self.get_profile_by_user_id(db, user_id)
        if not profile:
            return []

        result = await db.execute(
            select(UserPathEnrollment)
            .options(selectinload(UserPathEnrollment.path))
            .where(UserPathEnrollment.profile_id == profile.id)
            .order_by(UserPathEnrollment.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update_enrollment_progress(
        self,
        db: AsyncSession,
        enrollment_id: str,
    ) -> Optional[UserPathEnrollment]:
        """
        更新路径报名进度（自动计算）

        根据用户在路径资源上的学习进度自动更新报名进度
        """
        result = await db.execute(
            select(UserPathEnrollment)
            .options(selectinload(UserPathEnrollment.profile))
            .where(UserPathEnrollment.id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            return None

        # 获取路径项目
        items_result = await db.execute(
            select(LearningPathItem)
            .where(LearningPathItem.path_id == enrollment.path_id)
            .order_by(LearningPathItem.order_index)
        )
        items = list(items_result.scalars().all())

        if not items:
            return enrollment

        # 获取用户在这些资源上的进度
        resource_ids = [item.resource_id for item in items]
        progress_result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == enrollment.profile.user_id,
                    UserProgress.resource_id.in_(resource_ids),
                )
            )
        )
        progress_map = {p.resource_id: p for p in progress_result.scalars().all()}

        # 计算完成数和当前项目索引
        completed_items = 0
        current_index = 0
        total_study_minutes = 0

        for i, item in enumerate(items):
            prog = progress_map.get(item.resource_id)
            if prog:
                if prog.is_completed:
                    completed_items += 1
                    current_index = i + 1
                # 累计学习时间（简化：假设完成的资源贡献了其时长）

        # 更新报名记录
        enrollment.completed_items = completed_items
        enrollment.current_item_index = current_index
        enrollment.progress_percent = (completed_items / len(items) * 100) if items else 0

        # 更新状态
        if completed_items == 0:
            enrollment.status = LearningStatus.NOT_STARTED
        elif completed_items >= len(items):
            enrollment.status = LearningStatus.COMPLETED
            enrollment.completed_at = datetime.utcnow()
        else:
            enrollment.status = LearningStatus.IN_PROGRESS
            if not enrollment.started_at:
                enrollment.started_at = datetime.utcnow()

        enrollment.updated_at = datetime.utcnow()
        await db.flush()
        return enrollment

    async def record_study_session(
        self,
        db: AsyncSession,
        user_id: str,
        study_minutes: int,
    ) -> UserLearningProfile:
        """
        记录学习时长并更新连续学习天数

        Args:
            db: 数据库会话
            user_id: 用户 ID
            study_minutes: 学习时长（分钟）

        Returns:
            更新后的用户档案
        """
        profile = await self.get_or_create_profile(db, user_id)

        # 更新学习时长
        profile.total_study_minutes = (profile.total_study_minutes or 0) + study_minutes

        # 更新连续学习天数
        now = datetime.utcnow()
        if profile.last_study_at:
            days_since_last = (now.date() - profile.last_study_at.date()).days
            if days_since_last == 0:
                # 同一天，不更新连续天数
                pass
            elif days_since_last == 1:
                # 连续学习
                profile.current_streak_days = (profile.current_streak_days or 0) + 1
                if profile.current_streak_days > (profile.longest_streak_days or 0):
                    profile.longest_streak_days = profile.current_streak_days
            else:
                # 中断，重置
                profile.current_streak_days = 1
        else:
            # 首次学习
            profile.current_streak_days = 1

        profile.last_study_at = now
        profile.updated_at = now
        await db.flush()

        return profile

    async def get_user_stats(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        获取用户学习统计

        Returns:
            统计数据字典
        """
        profile = await self.get_profile_by_user_id(db, user_id)
        if not profile:
            return {
                "user_id": user_id,
                "total_study_minutes": 0,
                "total_resources_completed": 0,
                "total_paths_completed": 0,
                "current_streak_days": 0,
                "longest_streak_days": 0,
                "resources_by_type": {},
                "resources_by_category": {},
                "recent_activity": [],
                "daily_stats": [],
            }

        # 按类型统计完成的资源
        from app.learning_resources.models import ResourceType, ResourceCategory
        type_result = await db.execute(
            select(LearningResource.resource_type, func.count())
            .join(UserProgress, UserProgress.resource_id == LearningResource.id)
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_completed == True,
                )
            )
            .group_by(LearningResource.resource_type)
        )
        resources_by_type = {
            row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1]
            for row in type_result.all()
        }

        # 按分类统计
        cat_result = await db.execute(
            select(LearningResource.category, func.count())
            .join(UserProgress, UserProgress.resource_id == LearningResource.id)
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_completed == True,
                )
            )
            .group_by(LearningResource.category)
        )
        resources_by_category = {
            row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1]
            for row in cat_result.all()
        }

        # 最近学习记录
        recent_result = await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.resource))
            .where(UserProgress.user_id == user_id)
            .order_by(UserProgress.last_accessed_at.desc())
            .limit(10)
        )
        recent_activity = [
            {
                "resource_id": p.resource_id,
                "resource_title": p.resource.title if p.resource else "",
                "progress_percent": p.progress_percent,
                "is_completed": p.is_completed,
                "last_accessed_at": p.last_accessed_at.isoformat() if p.last_accessed_at else None,
            }
            for p in recent_result.scalars().all()
        ]

        return {
            "user_id": user_id,
            "total_study_minutes": profile.total_study_minutes or 0,
            "total_resources_completed": profile.total_resources_completed or 0,
            "total_paths_completed": profile.total_paths_completed or 0,
            "current_streak_days": profile.current_streak_days or 0,
            "longest_streak_days": profile.longest_streak_days or 0,
            "resources_by_type": resources_by_type,
            "resources_by_category": resources_by_category,
            "recent_activity": recent_activity,
            "daily_stats": [],  # 可以扩展为按天统计
        }


# 服务单例
_profile_service: Optional[ProfileService] = None


def get_profile_service() -> ProfileService:
    """获取档案服务单例"""
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService()
    return _profile_service
