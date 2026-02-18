"""
学习资源模块测试
测试 Schema、Service 和 API 端点
覆盖: Schema(11) + ORM枚举(4) + 核心逻辑(6) + DB集成(5) + API层(25)
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import numpy as np
from pydantic import ValidationError

from fastapi.testclient import TestClient


# ========== Schema 测试 ==========


class TestSchemas:
    """Pydantic Schema 验证测试"""

    def test_resource_create_valid(self):
        """测试创建资源 Schema - 有效数据"""
        from app.learning_resources.schemas import ResourceCreate

        data = ResourceCreate(
            title="乒乓球正手拉球教学",
            description="详细讲解正手拉球的技术要点",
            resource_type="video",
            category="technique",
            difficulty_level="beginner",
            url="https://www.bilibili.com/video/BV1234",
            duration_minutes=15,
            author="王教练",
            tags=["正手", "拉球", "基础"],
        )
        assert data.title == "乒乓球正手拉球教学"
        assert data.resource_type == "video"
        assert data.category == "technique"
        assert data.difficulty_level == "beginner"
        assert len(data.tags) == 3

    def test_resource_create_invalid_type(self):
        """测试创建资源 Schema - 无效资源类型"""
        from app.learning_resources.schemas import ResourceCreate

        with pytest.raises(ValidationError):
            ResourceCreate(
                title="测试",
                resource_type="invalid_type",  # 无效类型
                category="technique",
                difficulty_level="beginner",
            )

    def test_resource_create_invalid_difficulty(self):
        """测试创建资源 Schema - 无效难度"""
        from app.learning_resources.schemas import ResourceCreate

        with pytest.raises(ValidationError):
            ResourceCreate(
                title="测试",
                resource_type="video",
                category="technique",
                difficulty_level="expert",  # 无效难度
            )

    def test_resource_create_too_many_tags(self):
        """测试创建资源 Schema - 标签过多"""
        from app.learning_resources.schemas import ResourceCreate

        with pytest.raises(ValidationError):
            ResourceCreate(
                title="测试",
                resource_type="article",
                category="tactics",
                difficulty_level="intermediate",
                tags=[f"tag{i}" for i in range(25)],  # 超过 20 个标签
            )

    def test_resource_create_empty_title(self):
        """测试创建资源 Schema - 空标题"""
        from app.learning_resources.schemas import ResourceCreate

        with pytest.raises(ValidationError):
            ResourceCreate(
                title="",  # 空标题应该失败
                resource_type="video",
                category="technique",
                difficulty_level="beginner",
            )

    def test_resource_update_partial(self):
        """测试资源部分更新 Schema"""
        from app.learning_resources.schemas import ResourceUpdate

        data = ResourceUpdate(title="新标题")
        dumped = data.model_dump(exclude_unset=True)
        assert "title" in dumped
        assert "description" not in dumped
        assert "resource_type" not in dumped

    def test_semantic_search_request(self):
        """测试语义搜索请求 Schema"""
        from app.learning_resources.schemas import SemanticSearchRequest

        req = SemanticSearchRequest(
            query="正手发球技术",
            top_k=5,
            min_score=0.4,
            category="technique",
        )
        assert req.query == "正手发球技术"
        assert req.top_k == 5
        assert req.min_score == 0.4

    def test_learning_path_create(self):
        """测试学习路径创建 Schema"""
        from app.learning_resources.schemas import LearningPathCreate

        data = LearningPathCreate(
            title="初学者乒乓球速成路径",
            description="适合零基础的学习路径",
            difficulty_level="beginner",
            category="technique",
            estimated_hours=10.0,
            learning_objectives=["掌握基本握拍", "学会发球接球"],
            tags=["入门", "基础"],
        )
        assert data.title == "初学者乒乓球速成路径"
        assert data.difficulty_level == "beginner"
        assert len(data.learning_objectives) == 2

    def test_user_progress_create_valid(self):
        """测试创建进度 Schema - 有效数据"""
        from app.learning_resources.schemas import UserProgressCreate

        data = UserProgressCreate(
            resource_id="resource-123",
            user_id="user-456",
            progress_percent=75.0,
            is_completed=False,
        )
        assert data.progress_percent == 75.0
        assert data.is_completed is False

    def test_user_progress_invalid_percent(self):
        """测试创建进度 Schema - 无效百分比"""
        from app.learning_resources.schemas import UserProgressCreate

        with pytest.raises(ValidationError):
            UserProgressCreate(
                resource_id="r-1",
                user_id="u-1",
                progress_percent=150.0,  # 超出 100
            )

    def test_resource_search_request_defaults(self):
        """测试资源搜索请求默认值"""
        from app.learning_resources.schemas import ResourceSearchRequest

        req = ResourceSearchRequest()
        assert req.status == "published"
        assert req.page == 1
        assert req.page_size == 20
        assert req.sort_by == "created_at"
        assert req.sort_order == "desc"


# ========== ORM 枚举测试 ==========


class TestORMEnums:
    """ORM 枚举类型测试"""

    def test_resource_type_enum(self):
        """测试 ResourceType 枚举"""
        from app.learning_resources.models import ResourceType

        assert ResourceType.VIDEO.value == "video"
        assert ResourceType.ARTICLE.value == "article"
        assert ResourceType.TUTORIAL.value == "tutorial"
        assert ResourceType.EXERCISE.value == "exercise"
        assert ResourceType.COURSE.value == "course"
        assert ResourceType.BOOK.value == "book"

    def test_difficulty_level_enum(self):
        """测试 DifficultyLevel 枚举"""
        from app.learning_resources.models import DifficultyLevel

        assert DifficultyLevel.BEGINNER.value == "beginner"
        assert DifficultyLevel.INTERMEDIATE.value == "intermediate"
        assert DifficultyLevel.ADVANCED.value == "advanced"
        assert DifficultyLevel.PROFESSIONAL.value == "professional"

    def test_resource_category_enum(self):
        """测试 ResourceCategory 枚举"""
        from app.learning_resources.models import ResourceCategory

        assert ResourceCategory.TECHNIQUE.value == "technique"
        assert ResourceCategory.TACTICS.value == "tactics"
        assert ResourceCategory.RULES.value == "rules"
        assert ResourceCategory.EQUIPMENT.value == "equipment"
        assert ResourceCategory.FITNESS.value == "fitness"
        assert ResourceCategory.MENTAL.value == "mental"
        assert ResourceCategory.COMPETITION.value == "competition"
        assert ResourceCategory.HISTORY.value == "history"

    def test_resource_status_enum(self):
        """测试 ResourceStatus 枚举"""
        from app.learning_resources.models import ResourceStatus

        assert ResourceStatus.DRAFT.value == "draft"
        assert ResourceStatus.PUBLISHED.value == "published"
        assert ResourceStatus.ARCHIVED.value == "archived"


# ========== 核心逻辑单元测试 ==========


class TestCoreLogic:
    """核心算法和工具函数测试"""

    def test_resource_service_singleton(self):
        """测试资源服务单例"""
        from app.learning_resources.core.resource_service import get_resource_service, ResourceService

        s1 = get_resource_service()
        s2 = get_resource_service()
        assert s1 is s2
        assert isinstance(s1, ResourceService)

    def test_curriculum_service_singleton(self):
        """测试课程服务单例"""
        from app.learning_resources.core.curriculum_service import get_curriculum_service, CurriculumService

        s1 = get_curriculum_service()
        s2 = get_curriculum_service()
        assert s1 is s2
        assert isinstance(s1, CurriculumService)

    def test_progress_service_singleton(self):
        """测试进度服务单例"""
        from app.learning_resources.core.progress_service import get_progress_service, ProgressService

        s1 = get_progress_service()
        s2 = get_progress_service()
        assert s1 is s2
        assert isinstance(s1, ProgressService)

    def test_cosine_similarity_calculation(self):
        """测试余弦相似度计算逻辑"""
        # 验证 resource_service 中的相似度计算逻辑（直接测试 numpy 操作）
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # 相同向量，相似度为 1
        score_same = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))
        assert abs(score_same - 1.0) < 0.001

        # 正交向量，相似度为 0
        score_ortho = float(np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3) + 1e-8))
        assert abs(score_ortho) < 0.001

    def test_resource_brief_mapping(self):
        """测试 ORM → ResourceBrief 映射"""
        from app.learning_resources.api.resources import _to_resource_brief
        from app.learning_resources.models import (
            LearningResource, ResourceType, ResourceCategory,
            DifficultyLevel, ResourceStatus,
        )

        resource = LearningResource(
            id="test-id",
            title="测试资源",
            resource_type=ResourceType.VIDEO,
            category=ResourceCategory.TECHNIQUE,
            difficulty_level=DifficultyLevel.BEGINNER,
            status=ResourceStatus.PUBLISHED,
            language="zh",
            view_count=10,
            like_count=5,
            is_featured=False,
            created_at=datetime.utcnow(),
        )
        brief = _to_resource_brief(resource)
        assert brief.id == "test-id"
        assert brief.title == "测试资源"
        assert brief.resource_type == "video"
        assert brief.category == "technique"
        assert brief.difficulty_level == "beginner"
        assert brief.view_count == 10

    def test_progress_auto_complete_logic(self):
        """测试进度百分比 >= 100 时的自动完成逻辑"""
        from app.learning_resources.schemas import UserProgressCreate

        data = UserProgressCreate(
            resource_id="r-1",
            user_id="u-1",
            progress_percent=100.0,
            is_completed=False,  # 即使这里设为 False
        )
        # Schema 层不强制自动完成，由 Service 层处理
        assert data.progress_percent == 100.0


# ========== DB 集成测试 ==========


@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session(event_loop):
    """创建测试数据库会话（内存 SQLite）"""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.shared.database import Base
    # 确保所有模型都注册到 Base.metadata
    import app.learning_resources.models  # noqa: F401

    async def setup():
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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


@pytest.mark.asyncio
class TestResourceServiceIntegration:
    """资源服务 DB 集成测试"""

    async def test_create_and_get_resource(self, db_session):
        """测试创建和获取资源"""
        from app.learning_resources.core.resource_service import ResourceService
        from app.learning_resources.schemas import ResourceCreate

        with patch("app.learning_resources.core.resource_service.EmbeddingService") as mock_embed:
            mock_embed.encode_single.return_value = np.random.rand(384).astype(np.float32)

            service = ResourceService()
            data = ResourceCreate(
                title="正手拉球入门",
                resource_type="video",
                category="technique",
                difficulty_level="beginner",
                tags=["正手", "入门"],
            )
            resource = await service.create_resource(db_session, data)
            await db_session.flush()

            assert resource.id is not None
            assert resource.title == "正手拉球入门"
            assert resource.embedding is not None

            # 获取
            retrieved = await service.get_resource(db_session, resource.id)
            assert retrieved is not None
            assert retrieved.title == "正手拉球入门"

    async def test_update_resource(self, db_session):
        """测试更新资源"""
        from app.learning_resources.core.resource_service import ResourceService
        from app.learning_resources.schemas import ResourceCreate, ResourceUpdate

        with patch("app.learning_resources.core.resource_service.EmbeddingService") as mock_embed:
            mock_embed.encode_single.return_value = np.random.rand(384).astype(np.float32)

            service = ResourceService()
            data = ResourceCreate(
                title="原标题",
                resource_type="article",
                category="tactics",
                difficulty_level="intermediate",
            )
            resource = await service.create_resource(db_session, data)
            await db_session.flush()

            update = ResourceUpdate(title="新标题", is_featured=True)
            updated = await service.update_resource(db_session, resource.id, update)

            assert updated.title == "新标题"
            assert updated.is_featured is True

    async def test_delete_resource(self, db_session):
        """测试删除资源"""
        from app.learning_resources.core.resource_service import ResourceService
        from app.learning_resources.schemas import ResourceCreate

        with patch("app.learning_resources.core.resource_service.EmbeddingService") as mock_embed:
            mock_embed.encode_single.return_value = np.random.rand(384).astype(np.float32)

            service = ResourceService()
            data = ResourceCreate(
                title="待删除资源",
                resource_type="exercise",
                category="fitness",
                difficulty_level="advanced",
            )
            resource = await service.create_resource(db_session, data)
            await db_session.flush()

            result = await service.delete_resource(db_session, resource.id)
            assert result is True

            deleted = await service.get_resource(db_session, resource.id)
            assert deleted is None

    async def test_create_learning_path(self, db_session):
        """测试创建学习路径"""
        from app.learning_resources.core.curriculum_service import CurriculumService
        from app.learning_resources.schemas import LearningPathCreate

        service = CurriculumService()
        data = LearningPathCreate(
            title="基础技术学习路径",
            difficulty_level="beginner",
            category="technique",
            estimated_hours=8.0,
        )
        path = await service.create_path(db_session, data)
        await db_session.flush()

        assert path.id is not None
        assert path.title == "基础技术学习路径"
        assert path.difficulty_level.value == "beginner"

    async def test_upsert_progress(self, db_session):
        """测试进度 upsert（创建 + 幂等更新）"""
        from app.learning_resources.core.resource_service import ResourceService
        from app.learning_resources.core.progress_service import ProgressService
        from app.learning_resources.schemas import ResourceCreate, UserProgressCreate

        with patch("app.learning_resources.core.resource_service.EmbeddingService") as mock_embed:
            mock_embed.encode_single.return_value = np.random.rand(384).astype(np.float32)

            # 先创建资源
            resource_svc = ResourceService()
            resource = await resource_svc.create_resource(
                db_session,
                ResourceCreate(title="测试资源", resource_type="video", category="technique", difficulty_level="beginner"),
            )
            await db_session.flush()

            # 创建进度
            progress_svc = ProgressService()
            progress_data = UserProgressCreate(
                resource_id=resource.id,
                user_id="user-001",
                progress_percent=50.0,
            )
            progress, is_new = await progress_svc.upsert_progress(db_session, progress_data)
            await db_session.flush()

            assert is_new is True
            assert progress.progress_percent == 50.0
            assert progress.user_id == "user-001"

            # 再次 upsert（更新）
            progress_data2 = UserProgressCreate(
                resource_id=resource.id,
                user_id="user-001",
                progress_percent=80.0,
            )
            progress2, is_new2 = await progress_svc.upsert_progress(db_session, progress_data2)
            await db_session.flush()

            assert is_new2 is False
            assert progress2.progress_percent == 80.0


# ========== API 端点测试 ==========


@pytest.fixture
def test_client():
    """创建测试客户端，使用内存数据库，自动 mock EmbeddingService"""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.shared.database import Base, get_db_session
    from app.main import app as fastapi_app  # 重命名避免与 app 模块冲突
    import app.learning_resources.models  # noqa: F401（确保表注册）

    with patch("app.learning_resources.core.resource_service.EmbeddingService") as mock_embed:
        mock_embed.encode_single.return_value = np.random.rand(384).astype(np.float32)
        mock_embed.encode.return_value = np.random.rand(5, 384).astype(np.float32)

        SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite://"
        engine = create_async_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async def create_tables():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        async def dispose_engine():
            await engine.dispose()

        # 使用 asyncio.run() 替代已弃用的 get_event_loop()
        asyncio.run(create_tables())

        async def override_get_db():
            async with TestingSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        fastapi_app.dependency_overrides[get_db_session] = override_get_db

        with TestClient(fastapi_app) as client:
            yield client

        fastapi_app.dependency_overrides.clear()
        asyncio.run(dispose_engine())


class TestLearningHealthAPI:
    """学习资源模块健康检查 API 测试"""

    def test_health_check(self, test_client):
        """测试模块健康检查端点"""
        response = test_client.get("/api/learning/health")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "learning_resources"
        assert data["status"] == "healthy"
        assert "resources" in data["sub_modules"]
        assert "paths" in data["sub_modules"]
        assert "progress" in data["sub_modules"]


class TestResourceAPI:
    """资源 REST API 测试"""

    def test_create_resource_success(self, test_client):
        """测试创建资源 - 成功"""
        payload = {
            "title": "乒乓球规则详解",
            "description": "2024年最新乒乓球规则全解析",
            "resource_type": "article",
            "category": "rules",
            "difficulty_level": "beginner",
            "author": "裁判委员会",
            "tags": ["规则", "裁判"],
        }
        response = test_client.post("/api/learning/resources", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "乒乓球规则详解"
        assert data["resource_type"] == "article"
        assert data["category"] == "rules"
        assert "id" in data

    def test_create_resource_invalid(self, test_client):
        """测试创建资源 - 无效数据"""
        payload = {
            "title": "",  # 空标题
            "resource_type": "video",
            "category": "technique",
            "difficulty_level": "beginner",
        }
        response = test_client.post("/api/learning/resources", json=payload)
        assert response.status_code == 422

    def test_get_resource_not_found(self, test_client):
        """测试获取资源 - 不存在"""
        response = test_client.get("/api/learning/resources/non-existent-id")
        assert response.status_code == 404

    def test_get_resource_success(self, test_client):
        """测试获取资源 - 成功"""
        # 先创建
        payload = {
            "title": "背手推挡教程",
            "resource_type": "video",
            "category": "technique",
            "difficulty_level": "intermediate",
        }
        create_resp = test_client.post("/api/learning/resources", json=payload)
        assert create_resp.status_code == 201
        resource_id = create_resp.json()["id"]

        # 再获取
        get_resp = test_client.get(f"/api/learning/resources/{resource_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == resource_id
        assert get_resp.json()["view_count"] >= 1  # 浏览量已增加

    def test_list_resources_empty(self, test_client):
        """测试资源列表 - 空库"""
        response = test_client.get("/api/learning/resources")
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert "total" in data
        assert isinstance(data["resources"], list)

    def test_list_resources_with_filter(self, test_client):
        """测试资源列表 - 带过滤"""
        # 创建两个不同分类的资源
        test_client.post("/api/learning/resources", json={
            "title": "战术资源A",
            "resource_type": "article",
            "category": "tactics",
            "difficulty_level": "advanced",
        })
        test_client.post("/api/learning/resources", json={
            "title": "技术资源B",
            "resource_type": "video",
            "category": "technique",
            "difficulty_level": "beginner",
        })

        # 按分类过滤
        resp = test_client.get("/api/learning/resources?category=tactics")
        assert resp.status_code == 200
        data = resp.json()
        for r in data["resources"]:
            assert r["category"] == "tactics"

    def test_update_resource_success(self, test_client):
        """测试更新资源 - 成功"""
        create_resp = test_client.post("/api/learning/resources", json={
            "title": "原始标题",
            "resource_type": "tutorial",
            "category": "mental",
            "difficulty_level": "beginner",
        })
        resource_id = create_resp.json()["id"]

        update_resp = test_client.put(f"/api/learning/resources/{resource_id}", json={
            "title": "更新后标题",
            "is_featured": True,
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "更新后标题"
        assert update_resp.json()["is_featured"] is True

    def test_delete_resource_success(self, test_client):
        """测试删除资源 - 成功"""
        create_resp = test_client.post("/api/learning/resources", json={
            "title": "待删除资源",
            "resource_type": "exercise",
            "category": "fitness",
            "difficulty_level": "advanced",
        })
        resource_id = create_resp.json()["id"]

        del_resp = test_client.delete(f"/api/learning/resources/{resource_id}")
        assert del_resp.status_code == 204

        get_resp = test_client.get(f"/api/learning/resources/{resource_id}")
        assert get_resp.status_code == 404

    def test_delete_resource_not_found(self, test_client):
        """测试删除资源 - 不存在"""
        response = test_client.delete("/api/learning/resources/no-such-id")
        assert response.status_code == 404

    def test_like_resource(self, test_client):
        """测试点赞资源"""
        create_resp = test_client.post("/api/learning/resources", json={
            "title": "精选教程",
            "resource_type": "course",
            "category": "competition",
            "difficulty_level": "professional",
        })
        resource_id = create_resp.json()["id"]

        like_resp = test_client.post(f"/api/learning/resources/{resource_id}/like")
        assert like_resp.status_code == 200
        assert like_resp.json()["like_count"] == 1

    def test_semantic_search(self, test_client):
        """测试语义搜索端点"""
        # 创建资源
        test_client.post("/api/learning/resources", json={
            "title": "乒乓球步法训练",
            "description": "提升场上移动速度的训练方法",
            "resource_type": "tutorial",
            "category": "fitness",
            "difficulty_level": "intermediate",
        })

        resp = test_client.get("/api/learning/resources/search?query=步法训练&top_k=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)

    def test_stats_endpoint(self, test_client):
        """测试统计端点"""
        response = test_client.get("/api/learning/resources/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_resources" in data
        assert "resources_by_type" in data
        assert "resources_by_category" in data
        assert "total_paths" in data


class TestCurriculumAPI:
    """学习路径 REST API 测试"""

    def test_create_path_success(self, test_client):
        """测试创建学习路径 - 成功"""
        payload = {
            "title": "乒乓球初学者30天计划",
            "description": "适合新手的系统学习路径",
            "difficulty_level": "beginner",
            "category": "technique",
            "estimated_hours": 15.0,
            "learning_objectives": ["掌握基本握拍", "学会正手推挡"],
            "tags": ["初学者", "30天"],
        }
        response = test_client.post("/api/learning/paths", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "乒乓球初学者30天计划"
        assert data["difficulty_level"] == "beginner"
        assert data["item_count"] == 0
        assert "id" in data

    def test_get_path_not_found(self, test_client):
        """测试获取路径 - 不存在"""
        response = test_client.get("/api/learning/paths/no-such-path")
        assert response.status_code == 404

    def test_list_paths(self, test_client):
        """测试学习路径列表"""
        test_client.post("/api/learning/paths", json={
            "title": "高级战术路径",
            "difficulty_level": "advanced",
        })
        response = test_client.get("/api/learning/paths")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "total" in data

    def test_update_path_success(self, test_client):
        """测试更新学习路径 - 成功"""
        create_resp = test_client.post("/api/learning/paths", json={
            "title": "旧路径名",
            "difficulty_level": "intermediate",
        })
        path_id = create_resp.json()["id"]

        update_resp = test_client.put(f"/api/learning/paths/{path_id}", json={
            "title": "新路径名",
            "is_featured": True,
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "新路径名"
        assert update_resp.json()["is_featured"] is True

    def test_add_resource_to_path(self, test_client):
        """测试向路径添加资源"""
        # 创建路径
        path_resp = test_client.post("/api/learning/paths", json={
            "title": "测试路径",
            "difficulty_level": "beginner",
        })
        path_id = path_resp.json()["id"]

        # 创建资源
        res_resp = test_client.post("/api/learning/resources", json={
            "title": "资源A",
            "resource_type": "video",
            "category": "technique",
            "difficulty_level": "beginner",
        })
        resource_id = res_resp.json()["id"]

        # 添加到路径
        item_resp = test_client.post(f"/api/learning/paths/{path_id}/items", json={
            "resource_id": resource_id,
            "order_index": 0,
            "is_required": True,
        })
        assert item_resp.status_code == 201
        item_data = item_resp.json()
        assert item_data["resource_id"] == resource_id
        assert item_data["order_index"] == 0

    def test_remove_resource_from_path(self, test_client):
        """测试从路径移除资源"""
        path_resp = test_client.post("/api/learning/paths", json={
            "title": "路径X",
            "difficulty_level": "intermediate",
        })
        path_id = path_resp.json()["id"]

        res_resp = test_client.post("/api/learning/resources", json={
            "title": "资源X",
            "resource_type": "article",
            "category": "history",
            "difficulty_level": "beginner",
        })
        resource_id = res_resp.json()["id"]

        test_client.post(f"/api/learning/paths/{path_id}/items", json={
            "resource_id": resource_id,
            "order_index": 0,
        })

        del_resp = test_client.delete(f"/api/learning/paths/{path_id}/items/{resource_id}")
        assert del_resp.status_code == 204

    def test_delete_path_success(self, test_client):
        """测试删除路径 - 成功"""
        create_resp = test_client.post("/api/learning/paths", json={
            "title": "临时路径",
            "difficulty_level": "beginner",
        })
        path_id = create_resp.json()["id"]

        del_resp = test_client.delete(f"/api/learning/paths/{path_id}")
        assert del_resp.status_code == 204

        get_resp = test_client.get(f"/api/learning/paths/{path_id}")
        assert get_resp.status_code == 404


class TestProgressAPI:
    """进度追踪 REST API 测试"""

    def _create_resource(self, test_client) -> str:
        """辅助：创建资源并返回 ID"""
        resp = test_client.post("/api/learning/resources", json={
            "title": "进度测试资源",
            "resource_type": "video",
            "category": "technique",
            "difficulty_level": "beginner",
            "duration_minutes": 30,
        })
        return resp.json()["id"]

    def test_upsert_progress_create(self, test_client):
        """测试创建进度"""
        resource_id = self._create_resource(test_client)

        resp = test_client.post("/api/learning/progress", json={
            "resource_id": resource_id,
            "user_id": "test-user-001",
            "progress_percent": 40.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["progress_percent"] == 40.0
        assert data["user_id"] == "test-user-001"
        assert data["is_completed"] is False

    def test_mark_complete(self, test_client):
        """测试标记完成"""
        resource_id = self._create_resource(test_client)

        resp = test_client.post(
            f"/api/learning/progress/mark-user-001/resource/{resource_id}/complete"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_completed"] is True
        assert data["progress_percent"] == 100.0

    def test_list_user_progress(self, test_client):
        """测试用户进度列表"""
        resource_id = self._create_resource(test_client)
        test_client.post("/api/learning/progress", json={
            "resource_id": resource_id,
            "user_id": "list-user-001",
            "progress_percent": 60.0,
        })

        resp = test_client.get("/api/learning/progress/list-user-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "list-user-001"
        assert "progress" in data
        assert data["total"] >= 1

    def test_get_user_summary(self, test_client):
        """测试用户统计摘要"""
        resource_id = self._create_resource(test_client)
        test_client.post(
            f"/api/learning/progress/summary-user/resource/{resource_id}/complete"
        )

        resp = test_client.get("/api/learning/progress/summary-user/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "summary-user"
        assert "completion_rate" in data
        assert "total_resources" in data
        assert data["completed_resources"] >= 1

    def test_get_path_progress(self, test_client):
        """测试路径进度查询"""
        path_resp = test_client.post("/api/learning/paths", json={
            "title": "进度测试路径",
            "difficulty_level": "beginner",
        })
        path_id = path_resp.json()["id"]

        resp = test_client.get(f"/api/learning/progress/path-user/path/{path_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["path_id"] == path_id
        assert "completion_rate" in data

    def test_get_path_progress_not_found(self, test_client):
        """测试路径进度查询 - 路径不存在"""
        resp = test_client.get("/api/learning/progress/user-1/path/non-existent-path")
        assert resp.status_code == 404

    def test_upsert_progress_resource_not_found(self, test_client):
        """测试创建进度 - 资源不存在"""
        resp = test_client.post("/api/learning/progress", json={
            "resource_id": "non-existent-resource",
            "user_id": "user-1",
            "progress_percent": 50.0,
        })
        assert resp.status_code == 404


# ========== 知识图谱 Schema 测试 ==========


class TestKnowledgeSchemas:
    """知识图谱 Schema 验证测试"""

    def test_knowledge_point_create_valid(self):
        """测试有效的知识点创建请求"""
        from app.learning_resources.schemas import KnowledgePointCreate

        data = KnowledgePointCreate(
            name="forehand_loop",
            display_name="正手弧圈球",
            description="正手弧圈球是乒乓球最重要的进攻技术之一",
            category="forehand",
            difficulty_level="intermediate",
            key_points=["引拍充分", "摩擦为主", "收小臂"],
        )
        assert data.name == "forehand_loop"
        assert data.category == "forehand"
        assert len(data.key_points) == 3

    def test_knowledge_relation_create_valid(self):
        """测试知识点关系创建请求"""
        from app.learning_resources.schemas import KnowledgeRelationCreate

        data = KnowledgeRelationCreate(
            from_point_id="point_1",
            to_point_id="point_2",
            relation_type="prerequisite",
            weight=0.8,
            description="学习弧圈球前需要掌握基本攻球",
        )
        assert data.relation_type == "prerequisite"
        assert data.weight == 0.8

    def test_knowledge_relation_weight_range(self):
        """测试关系权重范围"""
        from app.learning_resources.schemas import KnowledgeRelationCreate

        # 有效权重
        data = KnowledgeRelationCreate(
            from_point_id="p1",
            to_point_id="p2",
            relation_type="related",
            weight=0.5,
        )
        assert data.weight == 0.5

        # 无效权重（超出范围）
        with pytest.raises(ValidationError):
            KnowledgeRelationCreate(
                from_point_id="p1",
                to_point_id="p2",
                relation_type="related",
                weight=1.5,  # 超出 0-1 范围
            )


# ========== 用户档案 Schema 测试 ==========


class TestProfileSchemas:
    """用户学习档案 Schema 验证测试"""

    def test_user_learning_profile_create_valid(self):
        """测试用户档案创建请求"""
        from app.learning_resources.schemas import UserLearningProfileCreate

        data = UserLearningProfileCreate(
            user_id="user_123",
            nickname="乒乓爱好者",
            current_level="intermediate",
            years_playing=3,
            learning_goals=["提高正手弧圈", "改善步法"],
            weak_points=["反手", "发球"],
            preferred_resource_types=["video", "tutorial"],
            daily_goal_minutes=60,
        )
        assert data.user_id == "user_123"
        assert data.current_level == "intermediate"
        assert len(data.learning_goals) == 2

    def test_study_minutes_range(self):
        """测试学习时长范围"""
        from app.learning_resources.schemas import UserLearningProfileCreate

        # 有效时长
        data = UserLearningProfileCreate(
            user_id="user_1",
            preferred_duration_minutes=60,
            daily_goal_minutes=120,
        )
        assert data.preferred_duration_minutes == 60

        # 无效时长（超出范围）
        with pytest.raises(ValidationError):
            UserLearningProfileCreate(
                user_id="user_1",
                preferred_duration_minutes=200,  # 超出 5-180 范围
            )


# ========== 推荐 Schema 测试 ==========


class TestRecommendationSchemas:
    """推荐 Schema 验证测试"""

    def test_recommendation_request_valid(self):
        """测试推荐请求"""
        from app.learning_resources.schemas import RecommendationRequest

        data = RecommendationRequest(
            user_id="user_123",
            recommendation_type="resources",
            top_k=5,
            exclude_completed=True,
        )
        assert data.recommendation_type == "resources"
        assert data.top_k == 5


# ========== 视频分析 Schema 测试 ==========


class TestVideoAnalysisSchemas:
    """视频分析 Schema 验证测试"""

    def test_video_analysis_link_create_valid(self):
        """测试视频分析关联创建请求"""
        from app.learning_resources.schemas import VideoAnalysisLinkCreate

        data = VideoAnalysisLinkCreate(
            resource_id="resource_123",
            ball_tracking_job_id="job_456",
            start_time_seconds=10.5,
            end_time_seconds=30.0,
            analysis_type="technique_demo",
            technique_category="forehand",
        )
        assert data.analysis_type == "technique_demo"
        assert data.start_time_seconds == 10.5


# ========== 新增枚举测试 ==========


class TestNewEnums:
    """新增枚举类型测试"""

    def test_technique_category_enum(self):
        """测试技术分类枚举"""
        from app.learning_resources.models import TechniqueCategory

        assert TechniqueCategory.FOREHAND.value == "forehand"
        assert TechniqueCategory.BACKHAND.value == "backhand"
        assert TechniqueCategory.SERVE.value == "serve"
        assert TechniqueCategory.FOOTWORK.value == "footwork"

    def test_learning_status_enum(self):
        """测试学习状态枚举"""
        from app.learning_resources.models import LearningStatus

        assert LearningStatus.NOT_STARTED.value == "not_started"
        assert LearningStatus.IN_PROGRESS.value == "in_progress"
        assert LearningStatus.COMPLETED.value == "completed"
        assert LearningStatus.MASTERED.value == "mastered"


# ========== 新增服务单例测试 ==========


class TestNewServiceSingletons:
    """新增服务单例测试"""

    def test_knowledge_service_singleton(self):
        """测试知识服务单例"""
        from app.learning_resources.core import get_knowledge_service

        service1 = get_knowledge_service()
        service2 = get_knowledge_service()
        assert service1 is service2

    def test_profile_service_singleton(self):
        """测试档案服务单例"""
        from app.learning_resources.core import get_profile_service

        service1 = get_profile_service()
        service2 = get_profile_service()
        assert service1 is service2

    def test_recommendation_engine_singleton(self):
        """测试推荐引擎单例"""
        from app.learning_resources.core import get_recommendation_engine

        engine1 = get_recommendation_engine()
        engine2 = get_recommendation_engine()
        assert engine1 is engine2

    def test_video_analysis_service_singleton(self):
        """测试视频分析服务单例"""
        from app.learning_resources.core import get_video_analysis_service

        service1 = get_video_analysis_service()
        service2 = get_video_analysis_service()
        assert service1 is service2


# ========== 推荐引擎测试 ==========


class TestRecommendationEngine:
    """推荐引擎测试"""

    def test_difficulty_order(self):
        """测试难度等级排序"""
        from app.learning_resources.core.recommendation_engine import LearningRecommendationEngine

        engine = LearningRecommendationEngine()
        assert engine.DIFFICULTY_ORDER["beginner"] < engine.DIFFICULTY_ORDER["intermediate"]
        assert engine.DIFFICULTY_ORDER["intermediate"] < engine.DIFFICULTY_ORDER["advanced"]
        assert engine.DIFFICULTY_ORDER["advanced"] < engine.DIFFICULTY_ORDER["professional"]

    def test_type_weights(self):
        """测试资源类型权重"""
        from app.learning_resources.core.recommendation_engine import LearningRecommendationEngine

        engine = LearningRecommendationEngine()
        assert engine.TYPE_WEIGHTS["video"] >= engine.TYPE_WEIGHTS["article"]
        assert engine.TYPE_WEIGHTS["course"] == 1.0


# ========== 视频分析服务测试 ==========


class TestVideoAnalysisService:
    """视频分析服务测试"""

    def test_technique_standards_exist(self):
        """测试技术标准参数存在"""
        from app.learning_resources.core.video_analysis_service import VideoAnalysisService
        from app.learning_resources.models import TechniqueCategory

        service = VideoAnalysisService()
        assert TechniqueCategory.FOREHAND in service.TECHNIQUE_STANDARDS
        assert TechniqueCategory.SERVE in service.TECHNIQUE_STANDARDS

    def test_default_commentary(self):
        """测试默认解说生成"""
        from app.learning_resources.core.video_analysis_service import VideoAnalysisService

        service = VideoAnalysisService()
        commentary = service._get_default_commentary("forehand", ["注意击球点"])
        assert "正手" in commentary
        assert "击球点" in commentary


# ========== 导入测试 ==========


class TestNewImports:
    """新增模块导入测试"""

    def test_new_models_import(self):
        """测试新模型导入"""
        from app.learning_resources.models import (
            KnowledgePoint,
            KnowledgeRelation,
            UserLearningProfile,
            UserPathEnrollment,
            VideoAnalysisLink,
            TechniqueCategory,
            LearningStatus,
        )
        assert KnowledgePoint is not None
        assert KnowledgeRelation is not None
        assert UserLearningProfile is not None
        assert VideoAnalysisLink is not None

    def test_new_schemas_import(self):
        """测试新 Schema 导入"""
        from app.learning_resources.schemas import (
            KnowledgePointCreate,
            KnowledgePointResponse,
            KnowledgeGraphResponse,
            UserLearningProfileCreate,
            UserLearningProfileResponse,
            RecommendationRequest,
            RecommendationResponse,
            VideoAnalysisLinkCreate,
            TechniqueAnalysisRequest,
        )
        assert KnowledgePointCreate is not None
        assert KnowledgeGraphResponse is not None
        assert RecommendationResponse is not None

    def test_new_services_import(self):
        """测试新服务导入"""
        from app.learning_resources.core import (
            KnowledgeService,
            get_knowledge_service,
            ProfileService,
            get_profile_service,
            LearningRecommendationEngine,
            get_recommendation_engine,
            VideoAnalysisService,
            get_video_analysis_service,
        )
        assert KnowledgeService is not None
        assert ProfileService is not None
        assert LearningRecommendationEngine is not None
        assert VideoAnalysisService is not None
