"""
社交媒体内容抓取服务
负责从各平台抓取问答内容

注意: 此模块提供抓取框架，具体平台的抓取实现需要根据各平台的
API 和反爬策略进行定制开发。
"""

from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.social_media.models import (
    Platform, ScrapeTask, SocialContent, SocialPlatformConfig, ContentType, ContentStatus
)


class BaseScraper(ABC):
    """
    抓取器基类

    所有平台特定的抓取器都需要继承此类并实现抽象方法
    """

    def __init__(self, config: SocialPlatformConfig):
        """
        初始化抓取器

        Args:
            config: 平台配置
        """
        self.config = config
        self.rate_limit = config.rate_limit_per_minute

    @abstractmethod
    async def scrape(
        self,
        keywords: List[str],
        max_items: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行抓取

        Args:
            keywords: 搜索关键词列表
            max_items: 最大抓取数量
            **kwargs: 其他参数

        Returns:
            抓取到的原始数据列表
        """
        pass

    @abstractmethod
    async def scrape_url(
        self,
        url: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        抓取指定 URL

        Args:
            url: 目标 URL
            **kwargs: 其他参数

        Returns:
            抓取到的原始数据列表
        """
        pass

    @abstractmethod
    def parse_content(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析原始数据为标准格式

        Args:
            raw_data: 原始抓取数据

        Returns:
            标准化的内容数据，包含以下字段:
            - external_id: 平台原始 ID
            - external_url: 原始链接
            - content_type: 内容类型
            - title: 标题
            - content: 正文
            - author_name: 作者名
            - author_id: 作者 ID
            - published_at: 发布时间
            - view_count: 浏览数
            - like_count: 点赞数
            - comment_count: 评论数
        """
        pass


class ZhihuScraper(BaseScraper):
    """
    知乎抓取器

    注意: 这是一个框架实现，实际使用需要:
    1. 处理知乎的反爬机制
    2. 使用有效的认证信息
    3. 遵守知乎的服务条款
    """

    async def scrape(
        self,
        keywords: List[str],
        max_items: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        搜索知乎问答

        实际实现需要:
        - 使用 httpx 发送异步请求
        - 处理分页
        - 处理速率限制
        - 解析 HTML 或调用 API
        """
        logger.warning("ZhihuScraper.scrape 尚未实现具体抓取逻辑")
        # TODO: 实现知乎搜索抓取
        return []

    async def scrape_url(
        self,
        url: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        抓取指定知乎页面
        """
        logger.warning("ZhihuScraper.scrape_url 尚未实现具体抓取逻辑")
        # TODO: 实现知乎页面抓取
        return []

    def parse_content(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析知乎内容格式
        """
        # 知乎内容解析示例
        return {
            "external_id": raw_data.get("id", ""),
            "external_url": raw_data.get("url", ""),
            "content_type": "question" if raw_data.get("type") == "question" else "answer",
            "title": raw_data.get("title", ""),
            "content": raw_data.get("content", ""),
            "author_name": raw_data.get("author", {}).get("name", ""),
            "author_id": raw_data.get("author", {}).get("id", ""),
            "published_at": raw_data.get("created_time"),
            "view_count": raw_data.get("visit_count", 0),
            "like_count": raw_data.get("voteup_count", 0),
            "comment_count": raw_data.get("comment_count", 0),
        }


class ScraperService:
    """
    抓取服务

    管理各平台抓取器的调度和执行
    """

    # 注册的抓取器类
    SCRAPER_CLASSES: Dict[Platform, type] = {
        Platform.ZHIHU: ZhihuScraper,
        # 其他平台抓取器在实现后添加
        # Platform.WEIBO: WeiboScraper,
        # Platform.TIEBA: TiebaScraper,
        # Platform.BILIBILI: BilibiliScraper,
    }

    def __init__(self):
        self._scrapers: Dict[str, BaseScraper] = {}

    def get_scraper(
        self,
        platform: Platform,
        config: SocialPlatformConfig,
    ) -> Optional[BaseScraper]:
        """
        获取平台对应的抓取器

        Args:
            platform: 平台类型
            config: 平台配置

        Returns:
            抓取器实例，不支持的平台返回 None
        """
        cache_key = f"{platform.value}_{config.id}"
        if cache_key not in self._scrapers:
            scraper_class = self.SCRAPER_CLASSES.get(platform)
            if scraper_class:
                self._scrapers[cache_key] = scraper_class(config)
        return self._scrapers.get(cache_key)

    async def create_task(
        self,
        db: AsyncSession,
        platform: Platform,
        keywords: Optional[List[str]] = None,
        target_url: Optional[str] = None,
    ) -> ScrapeTask:
        """
        创建抓取任务

        Args:
            db: 数据库会话
            platform: 目标平台
            keywords: 搜索关键词
            target_url: 指定 URL

        Returns:
            创建的任务对象
        """
        # 获取平台配置
        config = await self._get_platform_config(db, platform)
        if not config:
            raise ValueError(f"平台 {platform.value} 未配置")
        if not config.is_active:
            raise ValueError(f"平台 {platform.value} 已禁用")
        if not config.scrape_enabled:
            raise ValueError(f"平台 {platform.value} 抓取功能已关闭")

        task = ScrapeTask(
            id=str(uuid.uuid4()),
            platform_config_id=config.id,
            keywords=keywords or config.scrape_keywords,
            target_url=target_url,
            status="pending",
        )
        db.add(task)
        await db.flush()

        logger.info(f"创建抓取任务: {task.id}, 平台: {platform.value}")
        return task

    async def execute_task(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> ScrapeTask:
        """
        执行抓取任务

        Args:
            db: 数据库会话
            task_id: 任务 ID

        Returns:
            执行后的任务对象
        """
        # 获取任务
        task = await self._get_task(db, task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        # 获取配置
        config = await self._get_config_by_id(db, task.platform_config_id)
        if not config:
            raise ValueError(f"平台配置不存在")

        # 更新任务状态
        task.status = "running"
        task.started_at = datetime.utcnow()

        try:
            # 获取抓取器
            scraper = self.get_scraper(Platform(config.platform), config)
            if not scraper:
                raise ValueError(f"不支持的平台: {config.platform}")

            # 执行抓取
            if task.target_url:
                raw_items = await scraper.scrape_url(task.target_url)
            else:
                raw_items = await scraper.scrape(
                    keywords=task.keywords or [],
                    max_items=config.scrape_max_items,
                )

            task.items_found = len(raw_items)

            # 解析并保存内容
            saved_count = 0
            for raw_item in raw_items:
                parsed = scraper.parse_content(raw_item)
                if await self._save_content(db, config.id, parsed):
                    saved_count += 1

            task.items_saved = saved_count
            task.status = "completed"
            task.completed_at = datetime.utcnow()

            logger.info(f"任务完成: {task_id}, 抓取 {task.items_found}, 保存 {saved_count}")

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            logger.error(f"任务失败: {task_id}, 错误: {e}")

        return task

    async def get_task(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Optional[ScrapeTask]:
        """
        获取任务详情

        Args:
            db: 数据库会话
            task_id: 任务 ID

        Returns:
            任务对象
        """
        return await self._get_task(db, task_id)

    async def list_tasks(
        self,
        db: AsyncSession,
        platform: Optional[Platform] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[ScrapeTask]:
        """
        获取任务列表

        Args:
            db: 数据库会话
            platform: 平台筛选
            status: 状态筛选
            limit: 返回数量

        Returns:
            任务列表
        """
        from sqlalchemy.orm import selectinload

        query = select(ScrapeTask).options(
            selectinload(ScrapeTask.platform_config)
        )

        if platform:
            subquery = select(SocialPlatformConfig.id).where(
                SocialPlatformConfig.platform == platform
            )
            query = query.where(ScrapeTask.platform_config_id.in_(subquery))

        if status:
            query = query.where(ScrapeTask.status == status)

        query = query.order_by(ScrapeTask.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def _save_content(
        self,
        db: AsyncSession,
        platform_config_id: str,
        parsed_data: Dict[str, Any],
    ) -> bool:
        """
        保存解析后的内容

        Args:
            db: 数据库会话
            platform_config_id: 平台配置 ID
            parsed_data: 解析后的数据

        Returns:
            是否保存成功（False 表示已存在）
        """
        # 检查是否已存在（通过 external_id 去重）
        external_id = parsed_data.get("external_id")
        if external_id:
            existing = await db.execute(
                select(SocialContent).where(
                    SocialContent.external_id == external_id,
                    SocialContent.platform_config_id == platform_config_id,
                )
            )
            if existing.scalar_one_or_none():
                return False

        # 转换内容类型
        content_type_str = parsed_data.get("content_type", "post")
        try:
            content_type = ContentType(content_type_str)
        except ValueError:
            content_type = ContentType.POST

        # 创建内容记录
        content = SocialContent(
            id=str(uuid.uuid4()),
            platform_config_id=platform_config_id,
            external_id=external_id,
            external_url=parsed_data.get("external_url"),
            content_type=content_type,
            title=parsed_data.get("title"),
            content=parsed_data.get("content", ""),
            author_name=parsed_data.get("author_name"),
            author_id=parsed_data.get("author_id"),
            published_at=parsed_data.get("published_at"),
            view_count=parsed_data.get("view_count", 0),
            like_count=parsed_data.get("like_count", 0),
            comment_count=parsed_data.get("comment_count", 0),
            status=ContentStatus.PENDING,
        )
        db.add(content)

        return True

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

    async def _get_config_by_id(
        self,
        db: AsyncSession,
        config_id: str,
    ) -> Optional[SocialPlatformConfig]:
        """根据 ID 获取配置"""
        result = await db.execute(
            select(SocialPlatformConfig).where(
                SocialPlatformConfig.id == config_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_task(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Optional[ScrapeTask]:
        """获取任务"""
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(ScrapeTask)
            .options(selectinload(ScrapeTask.platform_config))
            .where(ScrapeTask.id == task_id)
        )
        return result.scalar_one_or_none()


# 单例
_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """获取抓取服务单例"""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service
