"""
用户学习进度追踪服务
提供进度记录的 CRUD 和统计功能
"""

from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.learning_resources.models import (
    UserProgress, LearningResource, LearningPath, LearningPathItem,
)
from app.learning_resources.schemas import (
    UserProgressCreate, UserProgressUpdate, UserProgressSummary, UserPathProgress,
)


class ProgressService:
    """
    用户学习进度追踪服务
    """

    async def upsert_progress(
        self,
        db: AsyncSession,
        data: UserProgressCreate,
    ) -> tuple:
        """
        创建或更新进度（upsert）

        Args:
            db: 数据库会话
            data: 进度数据

        Returns:
            (进度对象, is_new)
        """
        # 查找是否已存在
        result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == data.user_id,
                    UserProgress.resource_id == data.resource_id,
                )
            )
        )
        progress = result.scalar_one_or_none()
        is_new = progress is None

        if is_new:
            progress = UserProgress(
                id=str(uuid.uuid4()),
                user_id=data.user_id,
                resource_id=data.resource_id,
                progress_percent=data.progress_percent,
                is_completed=data.is_completed,
                rating=data.rating,
                notes=data.notes,
                last_accessed_at=datetime.utcnow(),
            )
            # 完成百分比到 100 时自动标记为完成
            if data.progress_percent >= 100.0:
                progress.is_completed = True
            db.add(progress)
        else:
            # 更新现有记录
            if data.progress_percent > (progress.progress_percent or 0.0):
                progress.progress_percent = data.progress_percent
            progress.is_completed = data.is_completed or progress.progress_percent >= 100.0
            if data.rating is not None:
                progress.rating = data.rating
            if data.notes is not None:
                progress.notes = data.notes
            progress.last_accessed_at = datetime.utcnow()
            progress.updated_at = datetime.utcnow()

        await db.flush()
        logger.info(
            f"{'创建' if is_new else '更新'}进度记录: user={data.user_id}, "
            f"resource={data.resource_id}, pct={progress.progress_percent:.1f}%"
        )
        return progress, is_new

    async def update_progress(
        self,
        db: AsyncSession,
        progress_id: str,
        data: UserProgressUpdate,
    ) -> Optional[UserProgress]:
        """
        按 ID 更新进度记录

        Returns:
            更新后的进度，不存在返回 None
        """
        result = await db.execute(
            select(UserProgress).where(UserProgress.id == progress_id)
        )
        progress = result.scalar_one_or_none()
        if not progress:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(progress, field, value)

        progress.last_accessed_at = datetime.utcnow()
        progress.updated_at = datetime.utcnow()

        # 百分比达到 100 时自动完成
        if progress.progress_percent >= 100.0:
            progress.is_completed = True

        await db.flush()
        return progress

    async def mark_complete(
        self,
        db: AsyncSession,
        user_id: str,
        resource_id: str,
    ) -> UserProgress:
        """
        标记资源为已完成（不存在则创建）

        Returns:
            进度对象
        """
        result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.resource_id == resource_id,
                )
            )
        )
        progress = result.scalar_one_or_none()

        if progress:
            progress.is_completed = True
            progress.progress_percent = 100.0
            progress.last_accessed_at = datetime.utcnow()
            progress.updated_at = datetime.utcnow()
        else:
            progress = UserProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                resource_id=resource_id,
                progress_percent=100.0,
                is_completed=True,
                last_accessed_at=datetime.utcnow(),
            )
            db.add(progress)

        await db.flush()
        logger.info(f"标记完成: user={user_id}, resource={resource_id}")
        return progress

    async def get_user_progress(
        self,
        db: AsyncSession,
        user_id: str,
        resource_id: str,
    ) -> Optional[UserProgress]:
        """获取某用户对某资源的进度"""
        result = await db.execute(
            select(UserProgress).where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.resource_id == resource_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_user_progress(
        self,
        db: AsyncSession,
        user_id: str,
        only_completed: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple:
        """
        查询用户所有进度记录（分页）

        Returns:
            (进度列表, 总数)
        """
        from sqlalchemy import desc as _desc
        conditions = [UserProgress.user_id == user_id]
        if only_completed:
            conditions.append(UserProgress.is_completed.is_(True))

        total = (await db.execute(
            select(func.count()).select_from(UserProgress).where(and_(*conditions))
        )).scalar_one()

        offset = (page - 1) * page_size
        rows = (await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.resource))
            .where(and_(*conditions))
            .order_by(_desc(UserProgress.last_accessed_at))
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return list(rows), total

    async def get_user_summary(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> UserProgressSummary:
        """
        获取用户学习统计摘要

        Returns:
            统计摘要对象
        """
        total = (await db.execute(
            select(func.count()).select_from(UserProgress)
            .where(UserProgress.user_id == user_id)
        )).scalar_one()

        completed = (await db.execute(
            select(func.count()).select_from(UserProgress)
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_completed.is_(True),
                )
            )
        )).scalar_one()

        in_progress = (await db.execute(
            select(func.count()).select_from(UserProgress)
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_completed.is_(False),
                    UserProgress.progress_percent > 0,
                )
            )
        )).scalar_one()

        avg_rating_row = (await db.execute(
            select(func.avg(UserProgress.rating))
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.rating.isnot(None),
                )
            )
        )).scalar_one()

        # 预计完成总时长（关联资源的 duration_minutes）
        duration_rows = (await db.execute(
            select(func.sum(LearningResource.duration_minutes))
            .join(UserProgress, UserProgress.resource_id == LearningResource.id)
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.is_completed.is_(True),
                    LearningResource.duration_minutes.isnot(None),
                )
            )
        )).scalar_one()
        total_hours = round((duration_rows or 0) / 60.0, 2)

        return UserProgressSummary(
            user_id=user_id,
            total_resources=total,
            completed_resources=completed,
            in_progress_resources=in_progress,
            completion_rate=round(completed / total, 4) if total > 0 else 0.0,
            total_hours_estimated=total_hours,
            average_rating=round(float(avg_rating_row), 2) if avg_rating_row else None,
        )

    async def get_path_progress(
        self,
        db: AsyncSession,
        user_id: str,
        path_id: str,
    ) -> Optional[UserPathProgress]:
        """
        获取用户在某学习路径的进度

        Returns:
            路径进度对象，路径不存在返回 None
        """
        # 获取路径及其资源
        path_result = await db.execute(
            select(LearningPath)
            .options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.resource)
            )
            .where(LearningPath.id == path_id)
        )
        path = path_result.scalar_one_or_none()
        if not path:
            return None

        resource_ids = [item.resource_id for item in path.items]
        if not resource_ids:
            return UserPathProgress(
                path_id=path_id,
                path_title=path.title,
                total_items=0,
                completed_items=0,
                completion_rate=0.0,
                progress_details=[],
            )

        # 获取用户对这些资源的进度
        progress_result = await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.resource))
            .where(
                and_(
                    UserProgress.user_id == user_id,
                    UserProgress.resource_id.in_(resource_ids),
                )
            )
        )
        progress_map = {p.resource_id: p for p in progress_result.scalars().all()}

        completed_items = sum(
            1 for rid in resource_ids
            if rid in progress_map and progress_map[rid].is_completed
        )

        from app.learning_resources.schemas import UserProgressResponse
        details = []
        for item in sorted(path.items, key=lambda x: x.order_index):
            prog = progress_map.get(item.resource_id)
            if prog:
                details.append(
                    UserProgressResponse(
                        id=prog.id,
                        user_id=prog.user_id,
                        resource_id=prog.resource_id,
                        resource_title=prog.resource.title if prog.resource else "",
                        progress_percent=prog.progress_percent,
                        is_completed=prog.is_completed,
                        rating=prog.rating,
                        notes=prog.notes,
                        last_accessed_at=prog.last_accessed_at,
                        created_at=prog.created_at,
                        updated_at=prog.updated_at,
                    )
                )

        return UserPathProgress(
            path_id=path_id,
            path_title=path.title,
            total_items=len(resource_ids),
            completed_items=completed_items,
            completion_rate=round(completed_items / len(resource_ids), 4) if resource_ids else 0.0,
            progress_details=details,
        )


# 服务单例
_progress_service: Optional[ProgressService] = None


def get_progress_service() -> ProgressService:
    """获取进度服务单例"""
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressService()
    return _progress_service
