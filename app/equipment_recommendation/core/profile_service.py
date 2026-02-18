"""
用户装备偏好档案服务
管理用户的打法风格、技术水平和装备偏好
"""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.equipment_recommendation.models import (
    UserEquipmentProfile, PlayingStyle, GripStyle, SkillLevel
)
from app.equipment_recommendation.schemas import (
    UserProfileCreate, UserProfileUpdate
)


class ProfileService:
    """用户装备偏好档案服务"""

    async def create_profile(
        self, db: AsyncSession, data: UserProfileCreate
    ) -> UserEquipmentProfile:
        """创建用户偏好档案"""
        # 检查是否已存在
        existing = await self.get_profile_by_user_id(db, data.user_id)
        if existing:
            raise ValueError(f"用户 {data.user_id} 已有偏好档案")

        profile = UserEquipmentProfile(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            nickname=data.nickname,
            years_playing=data.years_playing,
            playing_style=PlayingStyle(data.playing_style) if data.playing_style else None,
            grip_style=GripStyle(data.grip_style) if data.grip_style else None,
            skill_level=SkillLevel(data.skill_level) if data.skill_level else None,
            prefer_speed=data.prefer_speed,
            prefer_spin=data.prefer_spin,
            prefer_control=data.prefer_control,
            budget_min=data.budget_min,
            budget_max=data.budget_max,
            budget_currency=data.budget_currency,
            current_equipment=data.current_equipment,
            additional_info=data.additional_info,
        )
        db.add(profile)
        await db.flush()
        logger.info(f"用户偏好档案创建成功: user_id={data.user_id}")
        return profile

    async def get_profile(
        self, db: AsyncSession, profile_id: str
    ) -> Optional[UserEquipmentProfile]:
        """通过档案ID获取偏好档案"""
        result = await db.execute(
            select(UserEquipmentProfile).where(UserEquipmentProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_profile_by_user_id(
        self, db: AsyncSession, user_id: str
    ) -> Optional[UserEquipmentProfile]:
        """通过用户ID获取偏好档案"""
        result = await db.execute(
            select(UserEquipmentProfile).where(UserEquipmentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self, db: AsyncSession, profile_id: str, data: UserProfileUpdate
    ) -> Optional[UserEquipmentProfile]:
        """更新用户偏好档案"""
        profile = await self.get_profile(db, profile_id)
        if not profile:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 处理枚举字段
        if "playing_style" in update_data and update_data["playing_style"]:
            update_data["playing_style"] = PlayingStyle(update_data["playing_style"])
        if "grip_style" in update_data and update_data["grip_style"]:
            update_data["grip_style"] = GripStyle(update_data["grip_style"])
        if "skill_level" in update_data and update_data["skill_level"]:
            update_data["skill_level"] = SkillLevel(update_data["skill_level"])

        for key, value in update_data.items():
            setattr(profile, key, value)

        await db.flush()
        logger.info(f"用户偏好档案更新成功: profile_id={profile_id}")
        return profile

    async def update_profile_by_user_id(
        self, db: AsyncSession, user_id: str, data: UserProfileUpdate
    ) -> Optional[UserEquipmentProfile]:
        """通过用户ID更新偏好档案"""
        profile = await self.get_profile_by_user_id(db, user_id)
        if not profile:
            return None
        return await self.update_profile(db, profile.id, data)

    async def delete_profile(self, db: AsyncSession, profile_id: str) -> bool:
        """删除用户偏好档案"""
        profile = await self.get_profile(db, profile_id)
        if not profile:
            return False

        await db.delete(profile)
        await db.flush()
        logger.info(f"用户偏好档案删除成功: profile_id={profile_id}")
        return True

    async def get_or_create_profile(
        self, db: AsyncSession, user_id: str
    ) -> UserEquipmentProfile:
        """获取或创建用户偏好档案（用于推荐时）"""
        profile = await self.get_profile_by_user_id(db, user_id)
        if profile:
            return profile

        # 创建默认档案
        default_data = UserProfileCreate(
            user_id=user_id,
            prefer_speed=50,
            prefer_spin=50,
            prefer_control=50,
        )
        return await self.create_profile(db, default_data)

    def calculate_profile_completeness(self, profile: UserEquipmentProfile) -> float:
        """计算档案完整度（0-1）"""
        fields = [
            profile.playing_style is not None,
            profile.grip_style is not None,
            profile.skill_level is not None,
            profile.years_playing is not None,
            profile.budget_min is not None or profile.budget_max is not None,
            profile.current_equipment is not None,
            profile.additional_info is not None,
        ]
        return sum(fields) / len(fields)


# 单例模式
_profile_service: Optional[ProfileService] = None


def get_profile_service() -> ProfileService:
    """获取用户档案服务单例"""
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService()
    return _profile_service
