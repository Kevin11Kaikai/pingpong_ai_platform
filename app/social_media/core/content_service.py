"""
内容管理服务
提供内容的 CRUD 和搜索功能
"""

from typing import List, Optional, Tuple
import uuid
import numpy as np
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.social_media.models import (
    SocialContent, ContentTag, ContentTagMapping,
    SocialPlatformConfig, Platform, ContentType, ContentStatus
)
from app.social_media.schemas import (
    ContentCreate, ContentUpdate, ContentSearchRequest, SemanticSearchRequest
)
from app.shared.embedding_service import EmbeddingService


class ContentService:
    """
    内容管理服务
    处理内容的增删改查和搜索
    """

    async def create_content(
        self,
        db: AsyncSession,
        data: ContentCreate,
    ) -> SocialContent:
        """
        创建内容（手动导入）

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的内容对象
        """
        # 获取平台配置
        platform_config = await self._get_platform_config(db, Platform(data.platform))

        content = SocialContent(
            id=str(uuid.uuid4()),
            platform_config_id=platform_config.id if platform_config else None,
            content_type=ContentType(data.content_type),
            title=data.title,
            content=data.content,
            author_name=data.author_name,
            external_url=data.external_url,
            external_id=data.external_id,
            published_at=data.published_at,
            tags=data.tags,
            status=ContentStatus.PENDING,
        )

        # 生成嵌入向量
        text = f"{data.title or ''} {data.content}"
        content.embedding = EmbeddingService.encode_single(text).tolist()

        db.add(content)
        await db.flush()

        logger.info(f"创建内容: {content.id}")
        return content

    async def get_content(
        self,
        db: AsyncSession,
        content_id: str,
    ) -> Optional[SocialContent]:
        """
        获取内容详情

        Args:
            db: 数据库会话
            content_id: 内容 ID

        Returns:
            内容对象，不存在则返回 None
        """
        result = await db.execute(
            select(SocialContent)
            .options(
                selectinload(SocialContent.platform_config),
                selectinload(SocialContent.reply_suggestions),
            )
            .where(SocialContent.id == content_id)
        )
        return result.scalar_one_or_none()

    async def update_content(
        self,
        db: AsyncSession,
        content_id: str,
        data: ContentUpdate,
    ) -> Optional[SocialContent]:
        """
        更新内容

        Args:
            db: 数据库会话
            content_id: 内容 ID
            data: 更新数据

        Returns:
            更新后的内容对象
        """
        content = await self.get_content(db, content_id)
        if not content:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "status" and value:
                value = ContentStatus(value)
            setattr(content, key, value)

        # 如果内容变化，重新生成嵌入
        if "content" in update_data or "title" in update_data:
            text = f"{content.title or ''} {content.content}"
            content.embedding = EmbeddingService.encode_single(text).tolist()

        logger.info(f"更新内容: {content_id}")
        return content

    async def delete_content(
        self,
        db: AsyncSession,
        content_id: str,
    ) -> bool:
        """
        删除内容

        Args:
            db: 数据库会话
            content_id: 内容 ID

        Returns:
            是否删除成功
        """
        content = await self.get_content(db, content_id)
        if not content:
            return False

        await db.delete(content)
        logger.info(f"删除内容: {content_id}")
        return True

    async def search_contents(
        self,
        db: AsyncSession,
        params: ContentSearchRequest,
    ) -> Tuple[List[SocialContent], int]:
        """
        搜索内容

        Args:
            db: 数据库会话
            params: 搜索参数

        Returns:
            (内容列表, 总数)
        """
        query = select(SocialContent).options(
            selectinload(SocialContent.platform_config),
            selectinload(SocialContent.reply_suggestions),
        )

        # 构建过滤条件
        filters = []

        if params.query:
            filters.append(
                or_(
                    SocialContent.title.ilike(f"%{params.query}%"),
                    SocialContent.content.ilike(f"%{params.query}%"),
                )
            )

        if params.platform:
            # 需要 join 平台配置表
            subquery = select(SocialPlatformConfig.id).where(
                SocialPlatformConfig.platform == params.platform
            )
            filters.append(SocialContent.platform_config_id.in_(subquery))

        if params.content_type:
            filters.append(SocialContent.content_type == params.content_type)

        if params.status:
            filters.append(SocialContent.status == params.status)

        if params.min_quality_score is not None:
            filters.append(SocialContent.quality_score >= params.min_quality_score)

        if params.date_from:
            filters.append(SocialContent.created_at >= params.date_from)

        if params.date_to:
            filters.append(SocialContent.created_at <= params.date_to)

        if filters:
            query = query.where(and_(*filters))

        # 计算总数
        count_query = select(func.count(SocialContent.id)).where(and_(*filters)) if filters else select(func.count(SocialContent.id))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序
        sort_column = getattr(SocialContent, params.sort_by, SocialContent.created_at)
        if params.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 分页
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await db.execute(query)
        contents = list(result.scalars().all())

        return contents, total

    async def semantic_search(
        self,
        db: AsyncSession,
        params: SemanticSearchRequest,
    ) -> List[Tuple[SocialContent, float]]:
        """
        语义搜索

        Args:
            db: 数据库会话
            params: 搜索参数

        Returns:
            [(内容对象, 相似度分数), ...]
        """
        # 生成查询向量
        query_embedding = EmbeddingService.encode_single(params.query)

        # 获取所有有嵌入的内容
        query = select(SocialContent).options(
            selectinload(SocialContent.platform_config),
            selectinload(SocialContent.reply_suggestions),
        ).where(
            SocialContent.embedding.isnot(None)
        )

        if params.platform:
            subquery = select(SocialPlatformConfig.id).where(
                SocialPlatformConfig.platform == params.platform
            )
            query = query.where(SocialContent.platform_config_id.in_(subquery))

        if params.content_type:
            query = query.where(SocialContent.content_type == params.content_type)

        result = await db.execute(query)
        contents = list(result.scalars().all())

        # 计算相似度并排序
        scored_contents = []
        for content in contents:
            if content.embedding:
                content_embedding = np.array(content.embedding)
                similarity = self._cosine_similarity(query_embedding, content_embedding)
                if similarity >= params.min_score:
                    scored_contents.append((content, float(similarity)))

        # 按相似度排序
        scored_contents.sort(key=lambda x: x[1], reverse=True)

        return scored_contents[:params.top_k]

    async def get_stats(
        self,
        db: AsyncSession,
    ) -> dict:
        """
        获取统计信息

        Returns:
            统计数据字典
        """
        # 总数
        total_result = await db.execute(select(func.count(SocialContent.id)))
        total = total_result.scalar() or 0

        # 按状态统计
        status_result = await db.execute(
            select(SocialContent.status, func.count(SocialContent.id))
            .group_by(SocialContent.status)
        )
        by_status = dict(status_result.all())

        # 按类型统计
        type_result = await db.execute(
            select(SocialContent.content_type, func.count(SocialContent.id))
            .group_by(SocialContent.content_type)
        )
        by_type = dict(type_result.all())

        return {
            "total": total,
            "by_status": {k.value if k else "unknown": v for k, v in by_status.items()},
            "by_type": {k.value if k else "unknown": v for k, v in by_type.items()},
        }

    async def _get_platform_config(
        self,
        db: AsyncSession,
        platform: Platform,
    ) -> Optional[SocialPlatformConfig]:
        """获取平台配置"""
        result = await db.execute(
            select(SocialPlatformConfig).where(
                SocialPlatformConfig.platform == platform
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


# 单例
_content_service: Optional[ContentService] = None


def get_content_service() -> ContentService:
    """获取内容服务单例"""
    global _content_service
    if _content_service is None:
        _content_service = ContentService()
    return _content_service
