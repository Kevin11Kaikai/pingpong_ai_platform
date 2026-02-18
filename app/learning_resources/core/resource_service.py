"""
学习资源管理服务
提供资源的 CRUD、语义搜索和收藏功能
"""

from typing import List, Optional, Tuple
import uuid
import math
import numpy as np
from datetime import datetime
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.learning_resources.models import (
    LearningResource, ResourceBookmark,
    ResourceType, ResourceCategory, DifficultyLevel, ResourceStatus,
)
from app.learning_resources.schemas import (
    ResourceCreate, ResourceUpdate, ResourceSearchRequest,
    SemanticSearchRequest, BookmarkCreate,
)
from app.shared.embedding_service import EmbeddingService


class ResourceService:
    """
    学习资源管理服务
    处理资源的增删改查、语义搜索和收藏
    """

    async def create_resource(
        self,
        db: AsyncSession,
        data: ResourceCreate,
    ) -> LearningResource:
        """
        创建学习资源

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的资源对象
        """
        resource = LearningResource(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            resource_type=ResourceType(data.resource_type),
            category=ResourceCategory(data.category),
            difficulty_level=DifficultyLevel(data.difficulty_level),
            url=data.url,
            thumbnail_url=data.thumbnail_url,
            duration_minutes=data.duration_minutes,
            author=data.author,
            source=data.source,
            language=data.language,
            tags=data.tags,
            is_featured=data.is_featured,
            status=ResourceStatus.PUBLISHED,
        )

        # 生成文本嵌入向量（标题 + 描述 + 标签）
        text_parts = [data.title]
        if data.description:
            text_parts.append(data.description)
        if data.tags:
            text_parts.extend(data.tags)
        resource.embedding = EmbeddingService.encode_single(" ".join(text_parts)).tolist()

        db.add(resource)
        await db.flush()
        logger.info(f"创建学习资源: {resource.id} - {resource.title}")
        return resource

    async def get_resource(
        self,
        db: AsyncSession,
        resource_id: str,
    ) -> Optional[LearningResource]:
        """
        获取资源详情

        Args:
            db: 数据库会话
            resource_id: 资源 ID

        Returns:
            资源对象，不存在则返回 None
        """
        result = await db.execute(
            select(LearningResource).where(LearningResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def update_resource(
        self,
        db: AsyncSession,
        resource_id: str,
        data: ResourceUpdate,
    ) -> Optional[LearningResource]:
        """
        更新学习资源

        Args:
            db: 数据库会话
            resource_id: 资源 ID
            data: 更新数据

        Returns:
            更新后的资源对象，不存在则返回 None
        """
        resource = await self.get_resource(db, resource_id)
        if not resource:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        rebuild_embedding = False

        for field, value in update_fields.items():
            if field in ("resource_type",) and value is not None:
                value = ResourceType(value)
            elif field == "category" and value is not None:
                value = ResourceCategory(value)
            elif field == "difficulty_level" and value is not None:
                value = DifficultyLevel(value)
            elif field == "status" and value is not None:
                value = ResourceStatus(value)
            setattr(resource, field, value)
            if field in ("title", "description", "tags"):
                rebuild_embedding = True

        # 重建嵌入向量
        if rebuild_embedding:
            text_parts = [resource.title]
            if resource.description:
                text_parts.append(resource.description)
            if resource.tags:
                text_parts.extend(resource.tags)
            resource.embedding = EmbeddingService.encode_single(" ".join(text_parts)).tolist()

        resource.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"更新学习资源: {resource_id}")
        return resource

    async def delete_resource(
        self,
        db: AsyncSession,
        resource_id: str,
    ) -> bool:
        """
        删除学习资源

        Args:
            db: 数据库会话
            resource_id: 资源 ID

        Returns:
            成功返回 True，不存在返回 False
        """
        resource = await self.get_resource(db, resource_id)
        if not resource:
            return False
        await db.delete(resource)
        await db.flush()
        logger.info(f"删除学习资源: {resource_id}")
        return True

    async def list_resources(
        self,
        db: AsyncSession,
        params: ResourceSearchRequest,
    ) -> Tuple[List[LearningResource], int]:
        """
        分页查询资源列表

        Args:
            db: 数据库会话
            params: 搜索过滤参数

        Returns:
            (资源列表, 总数)
        """
        conditions = [
            LearningResource.status == ResourceStatus(params.status)
        ]

        # 关键词全文搜索（标题 + 描述）
        if params.keyword:
            kw = f"%{params.keyword}%"
            conditions.append(
                or_(
                    LearningResource.title.ilike(kw),
                    LearningResource.description.ilike(kw),
                )
            )

        if params.resource_type:
            conditions.append(LearningResource.resource_type == ResourceType(params.resource_type))
        if params.category:
            conditions.append(LearningResource.category == ResourceCategory(params.category))
        if params.difficulty_level:
            conditions.append(LearningResource.difficulty_level == DifficultyLevel(params.difficulty_level))
        if params.is_featured is not None:
            conditions.append(LearningResource.is_featured == params.is_featured)

        # 排序
        sort_col = getattr(LearningResource, params.sort_by, LearningResource.created_at)
        order_fn = desc if params.sort_order == "desc" else asc

        # 计数
        count_stmt = select(func.count()).select_from(LearningResource).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar_one()

        # 查询
        offset = (params.page - 1) * params.page_size
        stmt = (
            select(LearningResource)
            .where(and_(*conditions))
            .order_by(order_fn(sort_col))
            .offset(offset)
            .limit(params.page_size)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows), total

    async def semantic_search(
        self,
        db: AsyncSession,
        params: SemanticSearchRequest,
    ) -> List[Tuple[LearningResource, float]]:
        """
        语义向量搜索

        Args:
            db: 数据库会话
            params: 语义搜索参数

        Returns:
            (资源, 相似度分数) 列表，按相似度降序
        """
        # 编码查询向量
        query_vec = EmbeddingService.encode_single(params.query)

        # 过滤条件
        conditions = [
            LearningResource.status == ResourceStatus.PUBLISHED,
            LearningResource.embedding.isnot(None),
        ]
        if params.category:
            conditions.append(LearningResource.category == ResourceCategory(params.category))
        if params.difficulty_level:
            conditions.append(LearningResource.difficulty_level == DifficultyLevel(params.difficulty_level))

        stmt = select(LearningResource).where(and_(*conditions))
        resources = (await db.execute(stmt)).scalars().all()

        if not resources:
            return []

        # 计算余弦相似度
        results = []
        for resource in resources:
            if resource.embedding is None:
                continue
            emb = np.array(resource.embedding, dtype=np.float32)
            score = float(np.dot(query_vec, emb) / (np.linalg.norm(query_vec) * np.linalg.norm(emb) + 1e-8))
            if score >= params.min_score:
                results.append((resource, score))

        # 按分数降序排列，取 top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[: params.top_k]

    async def increment_view_count(
        self,
        db: AsyncSession,
        resource_id: str,
    ) -> None:
        """增加资源浏览量"""
        resource = await self.get_resource(db, resource_id)
        if resource:
            resource.view_count = (resource.view_count or 0) + 1
            await db.flush()

    async def toggle_like(
        self,
        db: AsyncSession,
        resource_id: str,
        increment: bool = True,
    ) -> Optional[int]:
        """
        点赞 / 取消点赞

        Returns:
            更新后的点赞数，资源不存在返回 None
        """
        resource = await self.get_resource(db, resource_id)
        if not resource:
            return None
        if increment:
            resource.like_count = (resource.like_count or 0) + 1
        else:
            resource.like_count = max(0, (resource.like_count or 0) - 1)
        await db.flush()
        return resource.like_count

    async def create_bookmark(
        self,
        db: AsyncSession,
        data: BookmarkCreate,
    ) -> Tuple[ResourceBookmark, bool]:
        """
        创建收藏（幂等）

        Returns:
            (收藏对象, is_new) is_new=True 表示新建，False 表示已存在
        """
        # 检查是否已收藏
        existing = await db.execute(
            select(ResourceBookmark).where(
                and_(
                    ResourceBookmark.user_id == data.user_id,
                    ResourceBookmark.resource_id == data.resource_id,
                )
            )
        )
        bm = existing.scalar_one_or_none()
        if bm:
            return bm, False

        bm = ResourceBookmark(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            resource_id=data.resource_id,
        )
        db.add(bm)
        await db.flush()
        return bm, True

    async def delete_bookmark(
        self,
        db: AsyncSession,
        user_id: str,
        resource_id: str,
    ) -> bool:
        """删除收藏，返回是否成功"""
        result = await db.execute(
            select(ResourceBookmark).where(
                and_(
                    ResourceBookmark.user_id == user_id,
                    ResourceBookmark.resource_id == resource_id,
                )
            )
        )
        bm = result.scalar_one_or_none()
        if not bm:
            return False
        await db.delete(bm)
        await db.flush()
        return True

    async def list_bookmarks(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> List[ResourceBookmark]:
        """获取用户收藏列表"""
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(ResourceBookmark)
            .options(selectinload(ResourceBookmark.resource))
            .where(ResourceBookmark.user_id == user_id)
            .order_by(desc(ResourceBookmark.created_at))
        )
        return list(result.scalars().all())

    async def get_stats(self, db: AsyncSession) -> dict:
        """获取学习资源统计数据"""
        total = (await db.execute(
            select(func.count()).select_from(LearningResource)
            .where(LearningResource.status == ResourceStatus.PUBLISHED)
        )).scalar_one()

        featured = (await db.execute(
            select(func.count()).select_from(LearningResource)
            .where(
                and_(
                    LearningResource.status == ResourceStatus.PUBLISHED,
                    LearningResource.is_featured.is_(True),
                )
            )
        )).scalar_one()

        # 按类型统计
        type_rows = (await db.execute(
            select(LearningResource.resource_type, func.count())
            .where(LearningResource.status == ResourceStatus.PUBLISHED)
            .group_by(LearningResource.resource_type)
        )).all()
        by_type = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in type_rows}

        # 按分类统计
        cat_rows = (await db.execute(
            select(LearningResource.category, func.count())
            .where(LearningResource.status == ResourceStatus.PUBLISHED)
            .group_by(LearningResource.category)
        )).all()
        by_category = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in cat_rows}

        # 按难度统计
        diff_rows = (await db.execute(
            select(LearningResource.difficulty_level, func.count())
            .where(LearningResource.status == ResourceStatus.PUBLISHED)
            .group_by(LearningResource.difficulty_level)
        )).all()
        by_difficulty = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in diff_rows}

        return {
            "total": total,
            "featured": featured,
            "by_type": by_type,
            "by_category": by_category,
            "by_difficulty": by_difficulty,
        }


# 服务单例
_resource_service: Optional[ResourceService] = None


def get_resource_service() -> ResourceService:
    """获取资源服务单例"""
    global _resource_service
    if _resource_service is None:
        _resource_service = ResourceService()
    return _resource_service
