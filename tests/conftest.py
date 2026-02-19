"""
测试共享 Fixtures
提供测试用的客户端、数据库会话、数据工厂等
"""

import pytest
import uuid
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient


# ========== 数据库 Fixtures ==========


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建异步测试数据库会话
    使用 SQLite 内存数据库，每个测试独立
    """
    from app.shared.database import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
def mock_db_session() -> MagicMock:
    """模拟数据库会话，用于单元测试"""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ========== API 客户端 Fixtures ==========


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    创建测试客户端
    不引发服务器异常，用于测试 HTTP 状态码
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_with_exceptions() -> Generator[TestClient, None, None]:
    """
    创建测试客户端
    引发服务器异常，用于调试
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ========== 临时目录 Fixtures ==========


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """创建临时文件"""
    file_path = temp_dir / "test_file.txt"
    file_path.write_text("test content")
    return file_path


# ========== 数据工厂 ==========


class DataFactory:
    """测试数据工厂"""

    @staticmethod
    def brand_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def category_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def equipment_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def user_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def profile_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def review_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def brand_data(name: str = None, **kwargs) -> dict:
        """生成品牌数据"""
        return {
            "name": name or f"Brand_{uuid.uuid4().hex[:8]}",
            "display_name": kwargs.get("display_name", "测试品牌"),
            "country": kwargs.get("country", "China"),
            "description": kwargs.get("description", "测试品牌描述"),
            "logo_url": kwargs.get("logo_url"),
            "website_url": kwargs.get("website_url"),
        }

    @staticmethod
    def category_data(name: str = None, **kwargs) -> dict:
        """生成分类数据"""
        return {
            "name": name or f"cat_{uuid.uuid4().hex[:8]}",
            "display_name": kwargs.get("display_name", "测试分类"),
            "description": kwargs.get("description", "测试分类描述"),
            "parent_id": kwargs.get("parent_id"),
            "sort_order": kwargs.get("sort_order", 0),
        }

    @staticmethod
    def equipment_data(
        name: str = None,
        brand_id: str = None,
        category_id: str = None,
        **kwargs
    ) -> dict:
        """生成装备数据"""
        return {
            "name": name or f"Equipment_{uuid.uuid4().hex[:8]}",
            "brand_id": brand_id or str(uuid.uuid4()),
            "category_id": category_id or str(uuid.uuid4()),
            "model_number": kwargs.get("model_number", "TEST-001"),
            "description": kwargs.get("description", "测试装备描述"),
            "price_min": kwargs.get("price_min", 100.0),
            "price_max": kwargs.get("price_max", 200.0),
            "price_currency": kwargs.get("price_currency", "CNY"),
            "speed_rating": kwargs.get("speed_rating", 70),
            "spin_rating": kwargs.get("spin_rating", 75),
            "control_rating": kwargs.get("control_rating", 80),
            "suitable_styles": kwargs.get("suitable_styles", ["offensive", "all_round"]),
            "suitable_levels": kwargs.get("suitable_levels", ["intermediate", "advanced"]),
            "suitable_grips": kwargs.get("suitable_grips", ["shakehand"]),
            "specifications": kwargs.get("specifications", {"weight": "90g"}),
            "image_urls": kwargs.get("image_urls", ["https://example.com/img.jpg"]),
            "is_featured": kwargs.get("is_featured", False),
        }

    @staticmethod
    def user_profile_data(user_id: str = None, **kwargs) -> dict:
        """生成用户档案数据"""
        return {
            "user_id": user_id or str(uuid.uuid4()),
            "nickname": kwargs.get("nickname", "测试用户"),
            "years_playing": kwargs.get("years_playing", 3),
            "playing_style": kwargs.get("playing_style", "offensive"),
            "grip_style": kwargs.get("grip_style", "shakehand"),
            "skill_level": kwargs.get("skill_level", "intermediate"),
            "prefer_speed": kwargs.get("prefer_speed", 70),
            "prefer_spin": kwargs.get("prefer_spin", 60),
            "prefer_control": kwargs.get("prefer_control", 50),
            "budget_min": kwargs.get("budget_min", 100.0),
            "budget_max": kwargs.get("budget_max", 500.0),
            "budget_currency": kwargs.get("budget_currency", "CNY"),
            "current_equipment": kwargs.get("current_equipment"),
            "additional_info": kwargs.get("additional_info"),
        }

    @staticmethod
    def review_data(equipment_id: str = None, **kwargs) -> dict:
        """生成评价数据"""
        return {
            "equipment_id": equipment_id or str(uuid.uuid4()),
            "overall_rating": kwargs.get("overall_rating", 4),
            "speed_rating": kwargs.get("speed_rating", 4),
            "spin_rating": kwargs.get("spin_rating", 5),
            "control_rating": kwargs.get("control_rating", 4),
            "durability_rating": kwargs.get("durability_rating", 4),
            "value_rating": kwargs.get("value_rating", 5),
            "title": kwargs.get("title", "测试评价标题"),
            "content": kwargs.get("content", "这是一个测试评价内容，装备很好用。"),
            "pros": kwargs.get("pros", ["速度快", "旋转强"]),
            "cons": kwargs.get("cons", ["价格略高"]),
            "usage_duration": kwargs.get("usage_duration", "1-3 months"),
        }

    @staticmethod
    def recommendation_request_data(user_id: str = None, **kwargs) -> dict:
        """生成推荐请求数据"""
        return {
            "user_id": user_id or str(uuid.uuid4()),
            "recommendation_type": kwargs.get("recommendation_type", "full_setup"),
            "top_k": kwargs.get("top_k", 5),
            "override_style": kwargs.get("override_style"),
            "override_level": kwargs.get("override_level"),
            "override_budget_max": kwargs.get("override_budget_max"),
        }

    @staticmethod
    def search_request_data(**kwargs) -> dict:
        """生成搜索请求数据"""
        return {
            "query": kwargs.get("query"),
            "category_id": kwargs.get("category_id"),
            "brand_ids": kwargs.get("brand_ids"),
            "price_min": kwargs.get("price_min"),
            "price_max": kwargs.get("price_max"),
            "min_speed": kwargs.get("min_speed"),
            "min_spin": kwargs.get("min_spin"),
            "min_control": kwargs.get("min_control"),
            "suitable_styles": kwargs.get("suitable_styles"),
            "suitable_levels": kwargs.get("suitable_levels"),
            "is_featured": kwargs.get("is_featured"),
            "sort_by": kwargs.get("sort_by", "created_at"),
            "sort_order": kwargs.get("sort_order", "desc"),
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 20),
        }


@pytest.fixture
def data_factory() -> DataFactory:
    """数据工厂 fixture"""
    return DataFactory()


# ========== ORM 模型工厂 ==========


class ORMFactory:
    """ORM 模型工厂（用于数据库集成测试）"""

    @staticmethod
    def create_brand(**kwargs):
        """创建 Brand ORM 模型"""
        from app.equipment_recommendation.models import Brand

        return Brand(
            id=kwargs.get("id", str(uuid.uuid4())),
            name=kwargs.get("name", f"Brand_{uuid.uuid4().hex[:8]}"),
            display_name=kwargs.get("display_name", "测试品牌"),
            country=kwargs.get("country", "China"),
            description=kwargs.get("description"),
            logo_url=kwargs.get("logo_url"),
            website_url=kwargs.get("website_url"),
            is_active=kwargs.get("is_active", True),
        )

    @staticmethod
    def create_category(**kwargs):
        """创建 EquipmentCategory ORM 模型"""
        from app.equipment_recommendation.models import EquipmentCategory

        return EquipmentCategory(
            id=kwargs.get("id", str(uuid.uuid4())),
            name=kwargs.get("name", f"cat_{uuid.uuid4().hex[:8]}"),
            display_name=kwargs.get("display_name", "测试分类"),
            description=kwargs.get("description"),
            parent_id=kwargs.get("parent_id"),
            sort_order=kwargs.get("sort_order", 0),
        )

    @staticmethod
    def create_equipment(brand=None, category=None, **kwargs):
        """创建 Equipment ORM 模型"""
        from app.equipment_recommendation.models import Equipment

        equipment = Equipment(
            id=kwargs.get("id", str(uuid.uuid4())),
            name=kwargs.get("name", f"Equipment_{uuid.uuid4().hex[:8]}"),
            brand_id=kwargs.get("brand_id") or (brand.id if brand else str(uuid.uuid4())),
            category_id=kwargs.get("category_id") or (category.id if category else str(uuid.uuid4())),
            model_number=kwargs.get("model_number"),
            description=kwargs.get("description"),
            price_min=kwargs.get("price_min", 100.0),
            price_max=kwargs.get("price_max", 200.0),
            price_currency=kwargs.get("price_currency", "CNY"),
            speed_rating=kwargs.get("speed_rating", 70),
            spin_rating=kwargs.get("spin_rating", 75),
            control_rating=kwargs.get("control_rating", 80),
            suitable_styles=kwargs.get("suitable_styles", ["offensive"]),
            suitable_levels=kwargs.get("suitable_levels", ["intermediate"]),
            suitable_grips=kwargs.get("suitable_grips", ["shakehand"]),
            specifications=kwargs.get("specifications"),
            image_urls=kwargs.get("image_urls"),
            embedding=kwargs.get("embedding"),
            view_count=kwargs.get("view_count", 0),
            review_count=kwargs.get("review_count", 0),
            avg_rating=kwargs.get("avg_rating", 0.0),
            is_active=kwargs.get("is_active", True),
            is_featured=kwargs.get("is_featured", False),
        )
        if brand:
            equipment.brand = brand
        if category:
            equipment.category = category
        return equipment

    @staticmethod
    def create_user_profile(**kwargs):
        """创建 UserEquipmentProfile ORM 模型"""
        from app.equipment_recommendation.models import (
            UserEquipmentProfile, PlayingStyle, GripStyle, SkillLevel
        )

        playing_style = kwargs.get("playing_style")
        if isinstance(playing_style, str):
            playing_style = PlayingStyle(playing_style)

        grip_style = kwargs.get("grip_style")
        if isinstance(grip_style, str):
            grip_style = GripStyle(grip_style)

        skill_level = kwargs.get("skill_level")
        if isinstance(skill_level, str):
            skill_level = SkillLevel(skill_level)

        return UserEquipmentProfile(
            id=kwargs.get("id", str(uuid.uuid4())),
            user_id=kwargs.get("user_id", str(uuid.uuid4())),
            nickname=kwargs.get("nickname"),
            years_playing=kwargs.get("years_playing"),
            playing_style=playing_style,
            grip_style=grip_style,
            skill_level=skill_level,
            prefer_speed=kwargs.get("prefer_speed", 50),
            prefer_spin=kwargs.get("prefer_spin", 50),
            prefer_control=kwargs.get("prefer_control", 50),
            budget_min=kwargs.get("budget_min"),
            budget_max=kwargs.get("budget_max"),
            budget_currency=kwargs.get("budget_currency", "CNY"),
            current_equipment=kwargs.get("current_equipment"),
            additional_info=kwargs.get("additional_info"),
        )

    @staticmethod
    def create_review(equipment=None, user_profile=None, **kwargs):
        """创建 EquipmentReview ORM 模型"""
        from app.equipment_recommendation.models import EquipmentReview

        review = EquipmentReview(
            id=kwargs.get("id", str(uuid.uuid4())),
            equipment_id=kwargs.get("equipment_id") or (equipment.id if equipment else str(uuid.uuid4())),
            user_profile_id=kwargs.get("user_profile_id") or (user_profile.id if user_profile else None),
            overall_rating=kwargs.get("overall_rating", 4),
            speed_rating=kwargs.get("speed_rating"),
            spin_rating=kwargs.get("spin_rating"),
            control_rating=kwargs.get("control_rating"),
            durability_rating=kwargs.get("durability_rating"),
            value_rating=kwargs.get("value_rating"),
            title=kwargs.get("title"),
            content=kwargs.get("content"),
            pros=kwargs.get("pros"),
            cons=kwargs.get("cons"),
            usage_duration=kwargs.get("usage_duration"),
            helpful_count=kwargs.get("helpful_count", 0),
            is_verified=kwargs.get("is_verified", False),
            is_active=kwargs.get("is_active", True),
        )
        if equipment:
            review.equipment = equipment
        if user_profile:
            review.user_profile = user_profile
        return review


@pytest.fixture
def orm_factory() -> ORMFactory:
    """ORM 工厂 fixture"""
    return ORMFactory()


# ========== Mock Fixtures ==========


@pytest.fixture
def mock_embedding_service():
    """模拟 Embedding 服务"""
    with patch("app.shared.embedding_service.EmbeddingService") as mock:
        mock.encode_single.return_value = [0.1] * 384  # all-MiniLM-L6-v2 维度
        mock.encode_batch.return_value = [[0.1] * 384]
        yield mock


@pytest.fixture
def mock_openai_client():
    """模拟 OpenAI 客户端"""
    with patch("openai.AsyncOpenAI") as mock:
        client = MagicMock()
        client.chat.completions.create = AsyncMock()
        mock.return_value = client
        yield mock


# ========== 清理 Fixtures ==========


@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试后重置单例"""
    yield
    # 重置服务单例
    try:
        from app.equipment_recommendation.core import equipment_service
        equipment_service._equipment_service = None
    except (ImportError, AttributeError):
        pass

    try:
        from app.equipment_recommendation.core import profile_service
        profile_service._profile_service = None
    except (ImportError, AttributeError):
        pass

    try:
        from app.equipment_recommendation.core import review_service
        review_service._review_service = None
    except (ImportError, AttributeError):
        pass

    try:
        from app.equipment_recommendation.core import recommendation_engine
        recommendation_engine._recommendation_engine = None
    except (ImportError, AttributeError):
        pass
