"""
装备评价服务
管理用户对装备的评价和评分
"""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.equipment_recommendation.models import (
    EquipmentReview, Equipment, UserEquipmentProfile
)
from app.equipment_recommendation.schemas import (
    ReviewCreate, ReviewUpdate
)


class ReviewService:
    """装备评价服务"""

    async def create_review(
        self,
        db: AsyncSession,
        data: ReviewCreate,
        user_profile_id: Optional[str] = None,
    ) -> EquipmentReview:
        """创建评价"""
        review = EquipmentReview(
            id=str(uuid.uuid4()),
            equipment_id=data.equipment_id,
            user_profile_id=user_profile_id,
            overall_rating=data.overall_rating,
            speed_rating=data.speed_rating,
            spin_rating=data.spin_rating,
            control_rating=data.control_rating,
            durability_rating=data.durability_rating,
            value_rating=data.value_rating,
            title=data.title,
            content=data.content,
            pros=data.pros,
            cons=data.cons,
            usage_duration=data.usage_duration,
        )
        db.add(review)
        await db.flush()

        # 更新装备的评价统计
        await self._update_equipment_rating_stats(db, data.equipment_id)

        logger.info(f"评价创建成功: equipment_id={data.equipment_id}")
        return review

    async def get_review(
        self, db: AsyncSession, review_id: str
    ) -> Optional[EquipmentReview]:
        """获取评价详情"""
        result = await db.execute(
            select(EquipmentReview)
            .options(
                selectinload(EquipmentReview.equipment),
                selectinload(EquipmentReview.user_profile),
            )
            .where(EquipmentReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def list_reviews_by_equipment(
        self,
        db: AsyncSession,
        equipment_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[EquipmentReview], int]:
        """获取装备的评价列表"""
        query = (
            select(EquipmentReview)
            .options(selectinload(EquipmentReview.user_profile))
            .where(
                EquipmentReview.equipment_id == equipment_id,
                EquipmentReview.is_active == True,
            )
        )

        # 排序
        sort_column = getattr(EquipmentReview, sort_by, EquipmentReview.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 计数
        count_query = select(func.count(EquipmentReview.id)).where(
            EquipmentReview.equipment_id == equipment_id,
            EquipmentReview.is_active == True,
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        reviews = list(result.scalars().all())

        return reviews, total

    async def list_reviews_by_user(
        self,
        db: AsyncSession,
        user_profile_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[EquipmentReview], int]:
        """获取用户的评价列表"""
        query = (
            select(EquipmentReview)
            .options(selectinload(EquipmentReview.equipment))
            .where(
                EquipmentReview.user_profile_id == user_profile_id,
                EquipmentReview.is_active == True,
            )
            .order_by(EquipmentReview.created_at.desc())
        )

        # 计数
        count_query = select(func.count(EquipmentReview.id)).where(
            EquipmentReview.user_profile_id == user_profile_id,
            EquipmentReview.is_active == True,
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        reviews = list(result.scalars().all())

        return reviews, total

    async def update_review(
        self, db: AsyncSession, review_id: str, data: ReviewUpdate
    ) -> Optional[EquipmentReview]:
        """更新评价"""
        review = await self.get_review(db, review_id)
        if not review:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(review, key, value)

        await db.flush()

        # 如果评分有变化，更新装备统计
        if any(k.endswith("_rating") for k in update_data.keys()):
            await self._update_equipment_rating_stats(db, review.equipment_id)

        logger.info(f"评价更新成功: review_id={review_id}")
        return review

    async def delete_review(self, db: AsyncSession, review_id: str) -> bool:
        """删除评价（软删除）"""
        review = await self.get_review(db, review_id)
        if not review:
            return False

        equipment_id = review.equipment_id
        review.is_active = False
        await db.flush()

        # 更新装备统计
        await self._update_equipment_rating_stats(db, equipment_id)

        logger.info(f"评价删除成功: review_id={review_id}")
        return True

    async def mark_helpful(
        self, db: AsyncSession, review_id: str
    ) -> Optional[EquipmentReview]:
        """标记评价为有帮助"""
        review = await self.get_review(db, review_id)
        if not review:
            return None

        review.helpful_count += 1
        await db.flush()
        return review

    async def get_rating_summary(
        self, db: AsyncSession, equipment_id: str
    ) -> dict:
        """获取装备的评分汇总"""
        result = await db.execute(
            select(
                func.count(EquipmentReview.id).label("count"),
                func.avg(EquipmentReview.overall_rating).label("avg_overall"),
                func.avg(EquipmentReview.speed_rating).label("avg_speed"),
                func.avg(EquipmentReview.spin_rating).label("avg_spin"),
                func.avg(EquipmentReview.control_rating).label("avg_control"),
                func.avg(EquipmentReview.durability_rating).label("avg_durability"),
                func.avg(EquipmentReview.value_rating).label("avg_value"),
            ).where(
                EquipmentReview.equipment_id == equipment_id,
                EquipmentReview.is_active == True,
            )
        )
        row = result.one()

        # 获取评分分布
        distribution_result = await db.execute(
            select(
                EquipmentReview.overall_rating,
                func.count(EquipmentReview.id).label("count"),
            )
            .where(
                EquipmentReview.equipment_id == equipment_id,
                EquipmentReview.is_active == True,
            )
            .group_by(EquipmentReview.overall_rating)
        )
        distribution = {r[0]: r[1] for r in distribution_result.all()}

        return {
            "total_reviews": row.count or 0,
            "avg_overall": round(float(row.avg_overall or 0), 2),
            "avg_speed": round(float(row.avg_speed or 0), 2) if row.avg_speed else None,
            "avg_spin": round(float(row.avg_spin or 0), 2) if row.avg_spin else None,
            "avg_control": round(float(row.avg_control or 0), 2) if row.avg_control else None,
            "avg_durability": round(float(row.avg_durability or 0), 2) if row.avg_durability else None,
            "avg_value": round(float(row.avg_value or 0), 2) if row.avg_value else None,
            "rating_distribution": {
                1: distribution.get(1, 0),
                2: distribution.get(2, 0),
                3: distribution.get(3, 0),
                4: distribution.get(4, 0),
                5: distribution.get(5, 0),
            },
        }

    async def _update_equipment_rating_stats(
        self, db: AsyncSession, equipment_id: str
    ) -> None:
        """更新装备的评价统计信息"""
        # 计算平均评分和评价数量
        result = await db.execute(
            select(
                func.count(EquipmentReview.id).label("count"),
                func.avg(EquipmentReview.overall_rating).label("avg"),
            ).where(
                EquipmentReview.equipment_id == equipment_id,
                EquipmentReview.is_active == True,
            )
        )
        row = result.one()

        # 更新装备记录
        await db.execute(
            update(Equipment)
            .where(Equipment.id == equipment_id)
            .values(
                review_count=row.count or 0,
                avg_rating=round(float(row.avg or 0), 2),
            )
        )


# 单例模式
_review_service: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """获取评价服务单例"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
