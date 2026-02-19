"""
学习路径（课程计划）管理服务
提供学习路径的 CRUD 及资源条目管理
"""

from typing import List, Optional, Tuple
import uuid
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.learning_resources.models import (
    LearningPath, LearningPathItem, LearningResource,
    DifficultyLevel, ResourceCategory,
)
from app.learning_resources.schemas import (
    LearningPathCreate, LearningPathUpdate, LearningPathItemCreate,
)


class CurriculumService:
    """
    学习路径管理服务
    处理路径的增删改查及资源条目管理
    """

    async def create_path(
        self,
        db: AsyncSession,
        data: LearningPathCreate,
    ) -> LearningPath:
        """
        创建学习路径

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的路径对象
        """
        path = LearningPath(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            difficulty_level=DifficultyLevel(data.difficulty_level),
            category=ResourceCategory(data.category) if data.category else None,
            estimated_hours=data.estimated_hours,
            target_audience=data.target_audience,
            learning_objectives=data.learning_objectives,
            tags=data.tags,
            is_published=data.is_published,
            is_featured=data.is_featured,
        )
        db.add(path)
        await db.flush()
        logger.info(f"创建学习路径: {path.id} - {path.title}")
        return path

    async def get_path(
        self,
        db: AsyncSession,
        path_id: str,
        with_items: bool = False,
    ) -> Optional[LearningPath]:
        """
        获取学习路径详情

        Args:
            db: 数据库会话
            path_id: 路径 ID
            with_items: 是否加载路径条目

        Returns:
            路径对象，不存在则返回 None
        """
        stmt = select(LearningPath).where(LearningPath.id == path_id)
        if with_items:
            stmt = stmt.options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.resource)
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_path(
        self,
        db: AsyncSession,
        path_id: str,
        data: LearningPathUpdate,
    ) -> Optional[LearningPath]:
        """
        更新学习路径

        Returns:
            更新后的路径对象，不存在则返回 None
        """
        path = await self.get_path(db, path_id)
        if not path:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field == "difficulty_level" and value is not None:
                value = DifficultyLevel(value)
            elif field == "category" and value is not None:
                value = ResourceCategory(value)
            setattr(path, field, value)

        path.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"更新学习路径: {path_id}")
        return path

    async def delete_path(
        self,
        db: AsyncSession,
        path_id: str,
    ) -> bool:
        """
        删除学习路径（级联删除条目）

        Returns:
            成功返回 True，不存在返回 False
        """
        path = await self.get_path(db, path_id)
        if not path:
            return False
        await db.delete(path)
        await db.flush()
        logger.info(f"删除学习路径: {path_id}")
        return True

    async def list_paths(
        self,
        db: AsyncSession,
        difficulty_level: Optional[str] = None,
        category: Optional[str] = None,
        is_published: Optional[bool] = True,
        is_featured: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[LearningPath], int]:
        """
        分页查询学习路径列表

        Returns:
            (路径列表, 总数)
        """
        conditions = []
        if is_published is not None:
            conditions.append(LearningPath.is_published == is_published)
        if is_featured is not None:
            conditions.append(LearningPath.is_featured == is_featured)
        if difficulty_level:
            conditions.append(LearningPath.difficulty_level == DifficultyLevel(difficulty_level))
        if category:
            conditions.append(LearningPath.category == ResourceCategory(category))

        where_clause = and_(*conditions) if conditions else True

        total = (await db.execute(
            select(func.count()).select_from(LearningPath).where(where_clause)
        )).scalar_one()

        offset = (page - 1) * page_size
        rows = (await db.execute(
            select(LearningPath)
            .where(where_clause)
            .order_by(desc(LearningPath.created_at))
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return list(rows), total

    async def get_item_count(self, db: AsyncSession, path_id: str) -> int:
        """获取路径包含的资源数量"""
        result = await db.execute(
            select(func.count()).select_from(LearningPathItem)
            .where(LearningPathItem.path_id == path_id)
        )
        return result.scalar_one()

    async def add_resource_to_path(
        self,
        db: AsyncSession,
        path_id: str,
        data: LearningPathItemCreate,
    ) -> Tuple[LearningPathItem, bool]:
        """
        向学习路径添加资源（幂等）

        Returns:
            (条目对象, is_new)
        """
        # 检查路径存在
        path = await self.get_path(db, path_id)
        if not path:
            raise ValueError(f"学习路径不存在: {path_id}")

        # 检查资源存在
        resource = await db.execute(
            select(LearningResource).where(LearningResource.id == data.resource_id)
        )
        if not resource.scalar_one_or_none():
            raise ValueError(f"资源不存在: {data.resource_id}")

        # 检查是否已存在
        existing = await db.execute(
            select(LearningPathItem).where(
                and_(
                    LearningPathItem.path_id == path_id,
                    LearningPathItem.resource_id == data.resource_id,
                )
            )
        )
        item = existing.scalar_one_or_none()
        if item:
            return item, False

        item = LearningPathItem(
            id=str(uuid.uuid4()),
            path_id=path_id,
            resource_id=data.resource_id,
            order_index=data.order_index,
            notes=data.notes,
            is_required=data.is_required,
        )
        db.add(item)
        await db.flush()
        logger.info(f"添加资源 {data.resource_id} 到路径 {path_id}")
        return item, True

    async def remove_resource_from_path(
        self,
        db: AsyncSession,
        path_id: str,
        resource_id: str,
    ) -> bool:
        """从学习路径移除资源"""
        result = await db.execute(
            select(LearningPathItem).where(
                and_(
                    LearningPathItem.path_id == path_id,
                    LearningPathItem.resource_id == resource_id,
                )
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return False
        await db.delete(item)
        await db.flush()
        logger.info(f"从路径 {path_id} 移除资源 {resource_id}")
        return True

    async def reorder_path_items(
        self,
        db: AsyncSession,
        path_id: str,
        ordered_resource_ids: List[str],
    ) -> List[LearningPathItem]:
        """
        重新排序路径中的资源

        Args:
            ordered_resource_ids: 按期望顺序排列的资源 ID 列表

        Returns:
            更新后的条目列表
        """
        result = await db.execute(
            select(LearningPathItem).where(LearningPathItem.path_id == path_id)
        )
        items = {item.resource_id: item for item in result.scalars().all()}

        for idx, resource_id in enumerate(ordered_resource_ids):
            if resource_id in items:
                items[resource_id].order_index = idx

        await db.flush()
        return sorted(items.values(), key=lambda x: x.order_index)


# 服务单例
_curriculum_service: Optional[CurriculumService] = None


def get_curriculum_service() -> CurriculumService:
    """获取课程计划服务单例"""
    global _curriculum_service
    if _curriculum_service is None:
        _curriculum_service = CurriculumService()
    return _curriculum_service
