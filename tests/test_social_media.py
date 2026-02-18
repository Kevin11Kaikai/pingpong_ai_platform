"""
社交媒体模块测试
测试 Schema、Service 和 API 端点
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

# ========== Schema 测试 ==========


class TestSchemas:
    """Schema 验证测试"""

    def test_content_create_valid(self):
        """测试创建内容 Schema - 有效数据"""
        from app.social_media.schemas import ContentCreate

        data = ContentCreate(
            platform="zhihu",
            content_type="question",
            title="如何提高正手拉球的旋转？",
            content="我是初学者，正手拉球总是没有旋转，请问该怎么改进？",
            author_name="乒乓球爱好者",
            tags=["正手", "旋转", "技术"],
        )
        assert data.platform == "zhihu"
        assert data.content_type == "question"
        assert data.title == "如何提高正手拉球的旋转？"
        assert len(data.tags) == 3

    def test_content_create_invalid_platform(self):
        """测试创建内容 Schema - 无效平台"""
        from app.social_media.schemas import ContentCreate

        with pytest.raises(ValidationError):
            ContentCreate(
                platform="invalid_platform",  # 无效平台
                content_type="question",
                content="测试内容",
            )

    def test_content_create_empty_content(self):
        """测试创建内容 Schema - 空内容"""
        from app.social_media.schemas import ContentCreate

        with pytest.raises(ValidationError):
            ContentCreate(
                platform="zhihu",
                content_type="question",
                content="",  # 空内容应该失败
            )

    def test_content_search_request_defaults(self):
        """测试搜索请求默认值"""
        from app.social_media.schemas import ContentSearchRequest

        request = ContentSearchRequest()
        assert request.page == 1
        assert request.page_size == 20
        assert request.sort_by == "created_at"
        assert request.sort_order == "desc"

    def test_semantic_search_request(self):
        """测试语义搜索请求"""
        from app.social_media.schemas import SemanticSearchRequest

        request = SemanticSearchRequest(
            query="正手发球技术",
            top_k=5,
            min_score=0.5,
        )
        assert request.query == "正手发球技术"
        assert request.top_k == 5
        assert request.min_score == 0.5

    def test_reply_generate_request(self):
        """测试回复生成请求"""
        from app.social_media.schemas import ReplyGenerateRequest

        request = ReplyGenerateRequest(
            content_id="test-id",
            style="professional",
            use_rag=True,
            max_length=500,
            temperature=0.7,
        )
        assert request.style == "professional"
        assert request.use_rag is True

    def test_reply_generate_invalid_style(self):
        """测试回复生成请求 - 无效风格"""
        from app.social_media.schemas import ReplyGenerateRequest

        with pytest.raises(ValidationError):
            ReplyGenerateRequest(
                content_id="test-id",
                style="invalid_style",  # 无效风格
            )

    def test_platform_config_create(self):
        """测试平台配置创建"""
        from app.social_media.schemas import PlatformConfigCreate

        config = PlatformConfigCreate(
            platform="zhihu",
            display_name="知乎",
            scrape_enabled=True,
            scrape_interval_minutes=60,
            scrape_keywords=["乒乓球", "技术"],
            scrape_max_items=100,
        )
        assert config.platform == "zhihu"
        assert config.display_name == "知乎"
        assert len(config.scrape_keywords) == 2

    def test_scrape_task_create(self):
        """测试抓取任务创建"""
        from app.social_media.schemas import ScrapeTaskCreate

        task = ScrapeTaskCreate(
            platform="weibo",
            keywords=["乒乓球", "国乒"],
        )
        assert task.platform == "weibo"
        assert task.keywords == ["乒乓球", "国乒"]

    def test_content_analysis_request(self):
        """测试内容分析请求"""
        from app.social_media.schemas import ContentAnalysisRequest

        request = ContentAnalysisRequest(
            content_id="test-content-id",
            force_reanalyze=False,
        )
        assert request.content_id == "test-content-id"
        assert request.force_reanalyze is False

    def test_reply_feedback_request(self):
        """测试回复反馈请求"""
        from app.social_media.schemas import ReplyFeedbackRequest

        request = ReplyFeedbackRequest(
            suggestion_id="test-suggestion-id",
            feedback="helpful",
        )
        assert request.feedback == "helpful"

        request_with_edit = ReplyFeedbackRequest(
            suggestion_id="test-suggestion-id",
            feedback="edited",
            edited_content="修改后的回复内容",
        )
        assert request_with_edit.edited_content == "修改后的回复内容"


class TestModels:
    """ORM 模型测试"""

    def test_platform_enum(self):
        """测试平台枚举"""
        from app.social_media.models import Platform

        assert Platform.ZHIHU.value == "zhihu"
        assert Platform.WEIBO.value == "weibo"
        assert Platform.BILIBILI.value == "bilibili"

    def test_content_type_enum(self):
        """测试内容类型枚举"""
        from app.social_media.models import ContentType

        assert ContentType.QUESTION.value == "question"
        assert ContentType.ANSWER.value == "answer"
        assert ContentType.POST.value == "post"

    def test_content_status_enum(self):
        """测试内容状态枚举"""
        from app.social_media.models import ContentStatus

        assert ContentStatus.PENDING.value == "pending"
        assert ContentStatus.ANALYZED.value == "analyzed"
        assert ContentStatus.REPLIED.value == "replied"
        assert ContentStatus.PUBLISHED.value == "published"


class TestContentService:
    """内容服务测试"""

    @pytest.mark.asyncio
    async def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        import numpy as np
        from app.social_media.core.content_service import ContentService

        service = ContentService()

        # 相同向量，相似度为1
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        assert abs(service._cosine_similarity(v1, v2) - 1.0) < 0.001

        # 正交向量，相似度为0
        v3 = np.array([0.0, 1.0, 0.0])
        assert abs(service._cosine_similarity(v1, v3) - 0.0) < 0.001

        # 零向量处理
        v_zero = np.array([0.0, 0.0, 0.0])
        assert service._cosine_similarity(v1, v_zero) == 0.0


class TestReplyService:
    """回复服务测试"""

    def test_evaluate_reply_quality_short(self):
        """测试回复质量评估 - 短回复"""
        from app.social_media.core.reply_service import ReplyService

        service = ReplyService.__new__(ReplyService)
        # 太短的回复
        score = service._evaluate_reply_quality("问题", "好的")
        assert score < 0.3

    def test_evaluate_reply_quality_good(self):
        """测试回复质量评估 - 良好回复"""
        from app.social_media.core.reply_service import ReplyService

        service = ReplyService.__new__(ReplyService)
        # 包含乒乓球相关词汇的较长回复
        good_reply = """
        关于正手发球的技术要点，我来分享一下经验：
        1. 首先要注意站位，脚步要稳
        2. 发球时要注意摩擦球的旋转
        3. 控制好力量和落点
        4. 多加练习步法和击球时机
        """
        score = service._evaluate_reply_quality("发球问题", good_reply)
        assert score > 0.5

    def test_evaluate_reply_quality_structured(self):
        """测试回复质量评估 - 结构化回复"""
        from app.social_media.core.reply_service import ReplyService

        service = ReplyService.__new__(ReplyService)
        # 有结构的回复应该得分更高
        structured_reply = """
        首先，要提高正手拉球的旋转：
        1. 注意摩擦球的角度，胶皮要充分接触球
        2. 手腕要有加速动作
        3. 控制好力量，先小力练习
        最后，多看训练视频，模仿专业选手的动作。
        """
        score = service._evaluate_reply_quality("旋转问题", structured_reply)
        assert score > 0.6


class TestAnalysisService:
    """分析服务测试"""

    def test_parse_stored_result(self):
        """测试解析存储的分析结果"""
        from app.social_media.core.analysis_service import AnalysisService

        service = AnalysisService.__new__(AnalysisService)

        stored = {
            "topics": ["发球", "旋转"],
            "question_type": "technique",
            "difficulty_level": "beginner",
            "sentiment": "neutral",
            "key_points": ["要点1"],
            "suggested_tags": ["技术"],
            "quality_score": 0.8,
            "relevance_score": 0.9,
        }

        result = service._parse_stored_result(stored)
        assert result.topics == ["发球", "旋转"]
        assert result.question_type == "technique"
        assert result.quality_score == 0.8

    def test_parse_stored_result_empty(self):
        """测试解析空的分析结果"""
        from app.social_media.core.analysis_service import AnalysisService

        service = AnalysisService.__new__(AnalysisService)

        result = service._parse_stored_result({})
        assert result.topics == []
        assert result.sentiment == "neutral"
        assert result.quality_score == 0.5


class TestScraperService:
    """抓取服务测试"""

    def test_zhihu_scraper_parse_content(self):
        """测试知乎内容解析"""
        from app.social_media.core.scraper_service import ZhihuScraper

        # 创建简单的模拟配置对象
        class MockConfig:
            rate_limit_per_minute = 10

        scraper = ZhihuScraper(MockConfig())

        raw_data = {
            "id": "12345",
            "url": "https://www.zhihu.com/question/12345",
            "type": "question",
            "title": "乒乓球正手发球怎么练？",
            "content": "求教正手发球的练习方法",
            "author": {"name": "球友", "id": "user123"},
            "created_time": None,
            "visit_count": 100,
            "voteup_count": 50,
            "comment_count": 10,
        }

        parsed = scraper.parse_content(raw_data)

        assert parsed["external_id"] == "12345"
        assert parsed["content_type"] == "question"
        assert parsed["title"] == "乒乓球正手发球怎么练？"
        assert parsed["author_name"] == "球友"
        assert parsed["like_count"] == 50


# ========== 集成测试 (需要数据库) ==========


@pytest.fixture(scope="function")
def db_session(event_loop):
    """创建测试数据库会话（同步 fixture）"""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.shared.database import Base

    async def setup():
        # 使用内存数据库
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        return engine, session

    async def teardown(engine, session):
        await session.close()
        await engine.dispose()

    engine, session = event_loop.run_until_complete(setup())
    yield session
    event_loop.run_until_complete(teardown(engine, session))


@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
class TestContentServiceIntegration:
    """内容服务集成测试"""

    async def test_create_and_get_content(self, db_session):
        """测试创建和获取内容"""
        from app.social_media.core.content_service import ContentService
        from app.social_media.schemas import ContentCreate

        service = ContentService()

        # 创建内容
        data = ContentCreate(
            platform="custom",  # 使用 custom 避免需要平台配置
            content_type="question",
            title="测试问题",
            content="这是一个测试内容",
        )

        content = await service.create_content(db_session, data)
        await db_session.flush()

        assert content.id is not None
        assert content.title == "测试问题"
        assert content.embedding is not None  # 应该生成了嵌入向量

        # 获取内容
        retrieved = await service.get_content(db_session, content.id)
        assert retrieved is not None
        assert retrieved.title == "测试问题"

    async def test_update_content(self, db_session):
        """测试更新内容"""
        from app.social_media.core.content_service import ContentService
        from app.social_media.schemas import ContentCreate, ContentUpdate

        service = ContentService()

        # 创建内容
        data = ContentCreate(
            platform="custom",
            content_type="post",
            title="原标题",
            content="原内容",
        )
        content = await service.create_content(db_session, data)
        await db_session.flush()

        # 更新内容
        update_data = ContentUpdate(title="新标题")
        updated = await service.update_content(db_session, content.id, update_data)

        assert updated.title == "新标题"
        assert updated.content == "原内容"  # 未修改的字段保持不变

    async def test_delete_content(self, db_session):
        """测试删除内容"""
        from app.social_media.core.content_service import ContentService
        from app.social_media.schemas import ContentCreate

        service = ContentService()

        # 创建内容
        data = ContentCreate(
            platform="custom",
            content_type="comment",
            content="待删除的评论",
        )
        content = await service.create_content(db_session, data)
        await db_session.flush()

        # 删除内容
        result = await service.delete_content(db_session, content.id)
        assert result is True

        # 确认已删除
        deleted = await service.get_content(db_session, content.id)
        assert deleted is None

    async def test_search_contents(self, db_session):
        """测试搜索内容"""
        from app.social_media.core.content_service import ContentService
        from app.social_media.schemas import ContentCreate, ContentSearchRequest

        service = ContentService()

        # 创建多个内容
        for i in range(3):
            data = ContentCreate(
                platform="custom",
                content_type="question",
                title=f"乒乓球问题 {i}",
                content=f"关于乒乓球的问题内容 {i}",
            )
            await service.create_content(db_session, data)
        await db_session.flush()

        # 搜索
        params = ContentSearchRequest(query="乒乓球")
        contents, total = await service.search_contents(db_session, params)

        assert total == 3
        assert len(contents) == 3

    async def test_get_stats(self, db_session):
        """测试获取统计信息"""
        from app.social_media.core.content_service import ContentService
        from app.social_media.schemas import ContentCreate

        service = ContentService()

        # 创建一些内容
        for content_type in ["question", "answer", "post"]:
            data = ContentCreate(
                platform="custom",
                content_type=content_type,
                content=f"内容 {content_type}",
            )
            await service.create_content(db_session, data)
        await db_session.flush()

        # 获取统计
        stats = await service.get_stats(db_session)

        assert stats["total"] == 3
        assert "by_status" in stats
        assert "by_type" in stats
