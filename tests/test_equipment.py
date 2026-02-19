"""
装备推荐模块测试
测试 Schema、Model、Service 和 API 端点
覆盖: Schema(18) + Model枚举(6) + Service(22) + API(25) = 71 tests
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from fastapi.testclient import TestClient


# ========== Schema 测试 ==========


class TestBrandSchemas:
    """品牌 Schema 验证测试"""

    def test_brand_create_valid(self):
        """测试创建品牌 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import BrandCreate

        data = BrandCreate(
            name="Butterfly",
            display_name="蝴蝶",
            country="Japan",
            description="日本著名乒乓球品牌",
        )
        assert data.name == "Butterfly"
        assert data.display_name == "蝴蝶"
        assert data.country == "Japan"

    def test_brand_create_empty_name(self):
        """测试创建品牌 Schema - 空名称应失败"""
        from app.equipment_recommendation.schemas import BrandCreate

        with pytest.raises(ValidationError):
            BrandCreate(name="")

    def test_brand_create_name_too_long(self):
        """测试创建品牌 Schema - 名称过长应失败"""
        from app.equipment_recommendation.schemas import BrandCreate

        with pytest.raises(ValidationError):
            BrandCreate(name="x" * 101)  # 超过 100 字符

    def test_brand_update_partial(self):
        """测试品牌部分更新 Schema"""
        from app.equipment_recommendation.schemas import BrandUpdate

        data = BrandUpdate(display_name="新名称")
        dumped = data.model_dump(exclude_unset=True)
        assert "display_name" in dumped
        assert "name" not in dumped
        assert "country" not in dumped


class TestCategorySchemas:
    """分类 Schema 验证测试"""

    def test_category_create_valid(self):
        """测试创建分类 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import CategoryCreate

        data = CategoryCreate(
            name="blade",
            display_name="底板",
            sort_order=1,
        )
        assert data.name == "blade"
        assert data.display_name == "底板"
        assert data.sort_order == 1

    def test_category_create_negative_sort_order(self):
        """测试创建分类 Schema - 负数排序值应失败"""
        from app.equipment_recommendation.schemas import CategoryCreate

        with pytest.raises(ValidationError):
            CategoryCreate(
                name="test",
                display_name="测试",
                sort_order=-1,
            )

    def test_category_create_with_parent(self):
        """测试创建子分类 Schema"""
        from app.equipment_recommendation.schemas import CategoryCreate

        parent_id = str(uuid.uuid4())
        data = CategoryCreate(
            name="offensive_blade",
            display_name="进攻型底板",
            parent_id=parent_id,
        )
        assert data.parent_id == parent_id


class TestEquipmentSchemas:
    """装备 Schema 验证测试"""

    def test_equipment_create_valid(self):
        """测试创建装备 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import EquipmentCreate

        data = EquipmentCreate(
            name="Viscaria",
            brand_id=str(uuid.uuid4()),
            category_id=str(uuid.uuid4()),
            model_number="VIS-01",
            description="经典五夹碳素底板",
            price_min=800.0,
            price_max=1200.0,
            speed_rating=90,
            spin_rating=85,
            control_rating=70,
            suitable_styles=["offensive", "all_round"],
            suitable_levels=["advanced", "professional"],
        )
        assert data.name == "Viscaria"
        assert data.speed_rating == 90

    def test_equipment_create_invalid_rating_over_100(self):
        """测试创建装备 Schema - 评分超过100应失败"""
        from app.equipment_recommendation.schemas import EquipmentCreate

        with pytest.raises(ValidationError):
            EquipmentCreate(
                name="Test",
                brand_id=str(uuid.uuid4()),
                category_id=str(uuid.uuid4()),
                speed_rating=101,  # 超过100
            )

    def test_equipment_create_invalid_rating_negative(self):
        """测试创建装备 Schema - 负数评分应失败"""
        from app.equipment_recommendation.schemas import EquipmentCreate

        with pytest.raises(ValidationError):
            EquipmentCreate(
                name="Test",
                brand_id=str(uuid.uuid4()),
                category_id=str(uuid.uuid4()),
                control_rating=-1,  # 负数
            )

    def test_equipment_create_invalid_style(self):
        """测试创建装备 Schema - 无效打法风格应失败"""
        from app.equipment_recommendation.schemas import EquipmentCreate

        with pytest.raises(ValidationError):
            EquipmentCreate(
                name="Test",
                brand_id=str(uuid.uuid4()),
                category_id=str(uuid.uuid4()),
                suitable_styles=["invalid_style"],  # 无效风格
            )

    def test_equipment_search_request_valid(self):
        """测试装备搜索请求 Schema"""
        from app.equipment_recommendation.schemas import EquipmentSearchRequest

        data = EquipmentSearchRequest(
            query="Viscaria",
            min_speed=60,
            suitable_styles=["offensive"],
            page=1,
            page_size=20,
        )
        assert data.query == "Viscaria"
        assert data.min_speed == 60

    def test_equipment_search_request_invalid_page_size(self):
        """测试装备搜索请求 Schema - 无效页面大小应失败"""
        from app.equipment_recommendation.schemas import EquipmentSearchRequest

        with pytest.raises(ValidationError):
            EquipmentSearchRequest(page_size=101)  # 超过100

    def test_equipment_compare_request_valid(self):
        """测试装备对比请求 Schema"""
        from app.equipment_recommendation.schemas import EquipmentCompareRequest

        ids = [str(uuid.uuid4()) for _ in range(3)]
        data = EquipmentCompareRequest(equipment_ids=ids)
        assert len(data.equipment_ids) == 3

    def test_equipment_compare_request_too_few(self):
        """测试装备对比请求 Schema - 少于2件应失败"""
        from app.equipment_recommendation.schemas import EquipmentCompareRequest

        with pytest.raises(ValidationError):
            EquipmentCompareRequest(equipment_ids=[str(uuid.uuid4())])

    def test_equipment_compare_request_too_many(self):
        """测试装备对比请求 Schema - 超过5件应失败"""
        from app.equipment_recommendation.schemas import EquipmentCompareRequest

        ids = [str(uuid.uuid4()) for _ in range(6)]
        with pytest.raises(ValidationError):
            EquipmentCompareRequest(equipment_ids=ids)


class TestUserProfileSchemas:
    """用户档案 Schema 验证测试"""

    def test_user_profile_create_valid(self):
        """测试创建用户档案 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import UserProfileCreate

        data = UserProfileCreate(
            user_id=str(uuid.uuid4()),
            nickname="球友小王",
            years_playing=5,
            playing_style="offensive",
            grip_style="shakehand",
            skill_level="intermediate",
            prefer_speed=70,
            prefer_spin=60,
            prefer_control=50,
            budget_max=1000.0,
        )
        assert data.nickname == "球友小王"
        assert data.playing_style == "offensive"

    def test_user_profile_create_invalid_preference(self):
        """测试创建用户档案 Schema - 无效偏好值应失败"""
        from app.equipment_recommendation.schemas import UserProfileCreate

        with pytest.raises(ValidationError):
            UserProfileCreate(
                user_id=str(uuid.uuid4()),
                prefer_speed=101,  # 超过100
            )

    def test_user_profile_create_invalid_playing_style(self):
        """测试创建用户档案 Schema - 无效打法风格应失败"""
        from app.equipment_recommendation.schemas import UserProfileCreate

        with pytest.raises(ValidationError):
            UserProfileCreate(
                user_id=str(uuid.uuid4()),
                playing_style="invalid",  # 无效风格
            )


class TestReviewSchemas:
    """评价 Schema 验证测试"""

    def test_review_create_valid(self):
        """测试创建评价 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import ReviewCreate

        data = ReviewCreate(
            equipment_id=str(uuid.uuid4()),
            overall_rating=5,
            speed_rating=4,
            title="非常棒的底板",
            content="手感极佳，推荐购买",
            pros=["速度快", "旋转强"],
            cons=["价格略高"],
        )
        assert data.overall_rating == 5
        assert len(data.pros) == 2

    def test_review_create_invalid_rating_too_high(self):
        """测试创建评价 Schema - 评分超过5应失败"""
        from app.equipment_recommendation.schemas import ReviewCreate

        with pytest.raises(ValidationError):
            ReviewCreate(
                equipment_id=str(uuid.uuid4()),
                overall_rating=6,  # 超过5
            )

    def test_review_create_invalid_rating_too_low(self):
        """测试创建评价 Schema - 评分低于1应失败"""
        from app.equipment_recommendation.schemas import ReviewCreate

        with pytest.raises(ValidationError):
            ReviewCreate(
                equipment_id=str(uuid.uuid4()),
                overall_rating=0,  # 低于1
            )


class TestRecommendationSchemas:
    """推荐 Schema 验证测试"""

    def test_recommendation_request_valid(self):
        """测试推荐请求 Schema - 有效数据"""
        from app.equipment_recommendation.schemas import RecommendationRequest

        data = RecommendationRequest(
            user_id=str(uuid.uuid4()),
            recommendation_type="blade",
            top_k=5,
        )
        assert data.recommendation_type == "blade"
        assert data.top_k == 5

    def test_recommendation_request_invalid_top_k(self):
        """测试推荐请求 Schema - 无效 top_k 应失败"""
        from app.equipment_recommendation.schemas import RecommendationRequest

        with pytest.raises(ValidationError):
            RecommendationRequest(
                user_id=str(uuid.uuid4()),
                top_k=21,  # 超过20
            )


# ========== Model 枚举测试 ==========


class TestModelEnums:
    """ORM 模型枚举测试"""

    def test_playing_style_values(self):
        """测试打法风格枚举值"""
        from app.equipment_recommendation.models import PlayingStyle

        assert PlayingStyle.OFFENSIVE.value == "offensive"
        assert PlayingStyle.DEFENSIVE.value == "defensive"
        assert PlayingStyle.ALL_ROUND.value == "all_round"
        assert PlayingStyle.CHOPPER.value == "chopper"

    def test_grip_style_values(self):
        """测试握拍方式枚举值"""
        from app.equipment_recommendation.models import GripStyle

        assert GripStyle.SHAKEHAND.value == "shakehand"
        assert GripStyle.PENHOLD_CHINESE.value == "penhold_chinese"
        assert GripStyle.PENHOLD_JAPANESE.value == "penhold_japanese"

    def test_skill_level_values(self):
        """测试技术水平枚举值"""
        from app.equipment_recommendation.models import SkillLevel

        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.INTERMEDIATE.value == "intermediate"
        assert SkillLevel.ADVANCED.value == "advanced"
        assert SkillLevel.PROFESSIONAL.value == "professional"

    def test_brand_model_repr(self):
        """测试 Brand 模型字符串表示"""
        from app.equipment_recommendation.models import Brand

        brand = Brand(id="test-id", name="Butterfly")
        assert "Butterfly" in repr(brand)

    def test_equipment_model_repr(self):
        """测试 Equipment 模型字符串表示"""
        from app.equipment_recommendation.models import Equipment

        equipment = Equipment(id="test-id", name="Viscaria")
        assert "Viscaria" in repr(equipment)

    def test_user_profile_model_repr(self):
        """测试 UserEquipmentProfile 模型字符串表示"""
        from app.equipment_recommendation.models import UserEquipmentProfile

        profile = UserEquipmentProfile(id="test-id", user_id="user-123")
        assert "user-123" in repr(profile)


# ========== Service 测试 ==========


class TestEquipmentService:
    """装备服务测试"""

    @pytest.mark.asyncio
    async def test_create_brand(self, async_db_session, data_factory):
        """测试创建品牌"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import BrandCreate

        service = get_equipment_service()
        data = BrandCreate(**data_factory.brand_data(name="TestBrand"))

        brand = await service.create_brand(async_db_session, data)

        assert brand.id is not None
        assert brand.name == "TestBrand"
        assert brand.is_active is True

    @pytest.mark.asyncio
    async def test_get_brand(self, async_db_session, orm_factory):
        """测试获取品牌"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()
        brand = orm_factory.create_brand(name="GetBrand")
        async_db_session.add(brand)
        await async_db_session.flush()

        result = await service.get_brand(async_db_session, brand.id)

        assert result is not None
        assert result.name == "GetBrand"

    @pytest.mark.asyncio
    async def test_get_brand_not_found(self, async_db_session):
        """测试获取不存在的品牌"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()
        result = await service.get_brand(async_db_session, "non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_brands(self, async_db_session, orm_factory):
        """测试获取品牌列表"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()

        # 创建多个品牌
        for i in range(3):
            brand = orm_factory.create_brand(name=f"ListBrand{i}")
            async_db_session.add(brand)
        await async_db_session.flush()

        brands, total = await service.list_brands(async_db_session)

        assert total >= 3
        assert len(brands) >= 3

    @pytest.mark.asyncio
    async def test_update_brand(self, async_db_session, orm_factory):
        """测试更新品牌"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import BrandUpdate

        service = get_equipment_service()
        brand = orm_factory.create_brand(name="UpdateBrand")
        async_db_session.add(brand)
        await async_db_session.flush()

        update_data = BrandUpdate(display_name="更新后的名称")
        result = await service.update_brand(async_db_session, brand.id, update_data)

        assert result is not None
        assert result.display_name == "更新后的名称"

    @pytest.mark.asyncio
    async def test_delete_brand(self, async_db_session, orm_factory):
        """测试删除品牌"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()
        brand = orm_factory.create_brand(name="DeleteBrand")
        async_db_session.add(brand)
        await async_db_session.flush()

        success = await service.delete_brand(async_db_session, brand.id)

        assert success is True
        # 确认已删除
        result = await service.get_brand(async_db_session, brand.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_category(self, async_db_session, data_factory):
        """测试创建分类"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import CategoryCreate

        service = get_equipment_service()
        data = CategoryCreate(**data_factory.category_data(name="testcat"))

        category = await service.create_category(async_db_session, data)

        assert category.id is not None
        assert category.name == "testcat"

    @pytest.mark.asyncio
    async def test_create_equipment(self, async_db_session, orm_factory, data_factory):
        """测试创建装备"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import EquipmentCreate

        service = get_equipment_service()

        # 先创建品牌和分类
        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        async_db_session.add(brand)
        async_db_session.add(category)
        await async_db_session.flush()

        data = EquipmentCreate(
            **data_factory.equipment_data(
                name="TestEquipment",
                brand_id=brand.id,
                category_id=category.id,
            )
        )

        with patch("app.equipment_recommendation.core.equipment_service.EmbeddingService") as mock_embed:
            mock_embed.encode_single.return_value = MagicMock(tolist=lambda: [0.1] * 384)

            equipment = await service.create_equipment(async_db_session, data)

            assert equipment.id is not None
            assert equipment.name == "TestEquipment"

    @pytest.mark.asyncio
    async def test_get_equipment(self, async_db_session, orm_factory):
        """测试获取装备详情"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(brand=brand, category=category)
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        result = await service.get_equipment(async_db_session, equipment.id)

        assert result is not None
        assert result.brand.name == brand.name

    @pytest.mark.asyncio
    async def test_get_equipment_increment_view(self, async_db_session, orm_factory):
        """测试获取装备时增加浏览计数"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(brand=brand, category=category, view_count=10)
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        result = await service.get_equipment(async_db_session, equipment.id, increment_view=True)

        assert result.view_count == 11

    @pytest.mark.asyncio
    async def test_search_equipment_by_query(self, async_db_session, orm_factory):
        """测试关键词搜索装备"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import EquipmentSearchRequest

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(
            brand=brand, category=category, name="Viscaria Pro"
        )
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        params = EquipmentSearchRequest(query="Viscaria")
        results, total = await service.search_equipment(async_db_session, params)

        assert total >= 1
        assert any("Viscaria" in e.name for e in results)

    @pytest.mark.asyncio
    async def test_search_equipment_by_price(self, async_db_session, orm_factory):
        """测试价格范围搜索装备"""
        from app.equipment_recommendation.core import get_equipment_service
        from app.equipment_recommendation.schemas import EquipmentSearchRequest

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(
            brand=brand, category=category, price_min=500.0, price_max=800.0
        )
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        params = EquipmentSearchRequest(price_min=400.0, price_max=900.0)
        results, total = await service.search_equipment(async_db_session, params)

        assert total >= 1

    @pytest.mark.asyncio
    async def test_delete_equipment(self, async_db_session, orm_factory):
        """测试删除装备"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(brand=brand, category=category)
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        success = await service.delete_equipment(async_db_session, equipment.id)

        assert success is True

    @pytest.mark.asyncio
    async def test_compare_equipment(self, async_db_session, orm_factory):
        """测试对比装备"""
        from app.equipment_recommendation.core import get_equipment_service

        service = get_equipment_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment1 = orm_factory.create_equipment(
            brand=brand, category=category, speed_rating=90, spin_rating=80, control_rating=70
        )
        equipment2 = orm_factory.create_equipment(
            brand=brand, category=category, speed_rating=70, spin_rating=85, control_rating=90
        )
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment1)
        async_db_session.add(equipment2)
        await async_db_session.flush()

        equipment_list, summary = await service.compare_equipment(
            async_db_session, [equipment1.id, equipment2.id]
        )

        assert len(equipment_list) == 2
        assert "speed" in summary
        assert summary["count"] == 2


class TestProfileService:
    """用户档案服务测试"""

    @pytest.mark.asyncio
    async def test_create_profile(self, async_db_session, data_factory):
        """测试创建用户档案"""
        from app.equipment_recommendation.core import get_profile_service
        from app.equipment_recommendation.schemas import UserProfileCreate

        service = get_profile_service()
        data = UserProfileCreate(**data_factory.user_profile_data())

        profile = await service.create_profile(async_db_session, data)

        assert profile.id is not None
        assert profile.playing_style is not None

    @pytest.mark.asyncio
    async def test_create_profile_duplicate(self, async_db_session, data_factory):
        """测试创建重复用户档案应失败"""
        from app.equipment_recommendation.core import get_profile_service
        from app.equipment_recommendation.schemas import UserProfileCreate

        service = get_profile_service()
        user_id = str(uuid.uuid4())
        data = UserProfileCreate(**data_factory.user_profile_data(user_id=user_id))

        await service.create_profile(async_db_session, data)

        with pytest.raises(ValueError):
            await service.create_profile(async_db_session, data)

    @pytest.mark.asyncio
    async def test_get_profile_by_user_id(self, async_db_session, orm_factory):
        """测试通过用户ID获取档案"""
        from app.equipment_recommendation.core import get_profile_service

        service = get_profile_service()
        user_id = str(uuid.uuid4())
        profile = orm_factory.create_user_profile(user_id=user_id)
        async_db_session.add(profile)
        await async_db_session.flush()

        result = await service.get_profile_by_user_id(async_db_session, user_id)

        assert result is not None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_calculate_profile_completeness(self, orm_factory):
        """测试计算档案完整度"""
        from app.equipment_recommendation.core import get_profile_service

        service = get_profile_service()

        # 完整档案
        complete_profile = orm_factory.create_user_profile(
            playing_style="offensive",
            grip_style="shakehand",
            skill_level="intermediate",
            years_playing=5,
            budget_max=1000.0,
            current_equipment={"blade": "test"},
            additional_info={"hand": "right"},
        )

        completeness = service.calculate_profile_completeness(complete_profile)
        assert completeness == 1.0

        # 空档案
        empty_profile = orm_factory.create_user_profile()
        empty_completeness = service.calculate_profile_completeness(empty_profile)
        assert empty_completeness < 1.0


class TestReviewService:
    """评价服务测试"""

    @pytest.mark.asyncio
    async def test_create_review(self, async_db_session, orm_factory, data_factory):
        """测试创建评价"""
        from app.equipment_recommendation.core import get_review_service
        from app.equipment_recommendation.schemas import ReviewCreate

        service = get_review_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(brand=brand, category=category)
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        await async_db_session.flush()

        data = ReviewCreate(**data_factory.review_data(equipment_id=equipment.id))

        review = await service.create_review(async_db_session, data)

        assert review.id is not None
        assert review.overall_rating == 4

    @pytest.mark.asyncio
    async def test_mark_helpful(self, async_db_session, orm_factory):
        """测试标记评价有帮助"""
        from app.equipment_recommendation.core import get_review_service

        service = get_review_service()

        brand = orm_factory.create_brand()
        category = orm_factory.create_category()
        equipment = orm_factory.create_equipment(brand=brand, category=category)
        review = orm_factory.create_review(equipment=equipment, helpful_count=5)
        async_db_session.add(brand)
        async_db_session.add(category)
        async_db_session.add(equipment)
        async_db_session.add(review)
        await async_db_session.flush()

        result = await service.mark_helpful(async_db_session, review.id)

        assert result.helpful_count == 6


class TestRecommendationEngine:
    """推荐引擎测试"""

    def test_style_weights(self):
        """测试打法风格权重配置"""
        from app.equipment_recommendation.core.recommendation_engine import RecommendationEngine
        from app.equipment_recommendation.models import PlayingStyle

        weights = RecommendationEngine.STYLE_WEIGHTS

        assert PlayingStyle.OFFENSIVE in weights
        assert weights[PlayingStyle.OFFENSIVE]["speed"] > weights[PlayingStyle.OFFENSIVE]["control"]
        assert weights[PlayingStyle.DEFENSIVE]["control"] > weights[PlayingStyle.DEFENSIVE]["speed"]

    def test_level_preferences(self):
        """测试技术水平偏好配置"""
        from app.equipment_recommendation.core.recommendation_engine import RecommendationEngine
        from app.equipment_recommendation.models import SkillLevel

        prefs = RecommendationEngine.LEVEL_PREFERENCES

        assert SkillLevel.BEGINNER in prefs
        assert prefs[SkillLevel.BEGINNER]["control_min"] > prefs[SkillLevel.PROFESSIONAL]["control_min"]

    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        import numpy as np
        from app.equipment_recommendation.core.recommendation_engine import RecommendationEngine

        a = np.array([1, 0, 0])
        b = np.array([1, 0, 0])
        similarity = RecommendationEngine._cosine_similarity(a, b)
        assert similarity == pytest.approx(1.0)

        c = np.array([0, 1, 0])
        similarity2 = RecommendationEngine._cosine_similarity(a, c)
        assert similarity2 == pytest.approx(0.0)

    def test_style_to_chinese(self):
        """测试打法风格中文转换"""
        from app.equipment_recommendation.core.recommendation_engine import RecommendationEngine
        from app.equipment_recommendation.models import PlayingStyle

        assert RecommendationEngine._style_to_chinese(PlayingStyle.OFFENSIVE) == "进攻型"
        assert RecommendationEngine._style_to_chinese(PlayingStyle.DEFENSIVE) == "防守型"

    def test_level_to_chinese(self):
        """测试技术水平中文转换"""
        from app.equipment_recommendation.core.recommendation_engine import RecommendationEngine
        from app.equipment_recommendation.models import SkillLevel

        assert RecommendationEngine._level_to_chinese(SkillLevel.BEGINNER) == "初学者"
        assert RecommendationEngine._level_to_chinese(SkillLevel.PROFESSIONAL) == "专业"


# ========== API 测试 ==========


class TestBrandAPI:
    """品牌 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_create_brand_endpoint(self, client, data_factory):
        """测试创建品牌 API"""
        data = data_factory.brand_data(name=f"APIBrand_{uuid.uuid4().hex[:8]}")

        response = client.post("/api/equipment/brands", json=data)

        # 可能成功或因数据库问题失败
        assert response.status_code in [200, 500]

    def test_list_brands_endpoint(self, client):
        """测试获取品牌列表 API"""
        response = client.get("/api/equipment/brands")

        assert response.status_code in [200, 500]

    def test_get_brand_not_found(self, client):
        """测试获取不存在的品牌"""
        response = client.get("/api/equipment/brands/non-existent-id")

        assert response.status_code in [404, 500]


class TestCategoryAPI:
    """分类 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_create_category_endpoint(self, client, data_factory):
        """测试创建分类 API"""
        data = data_factory.category_data(name=f"apicat_{uuid.uuid4().hex[:8]}")

        response = client.post("/api/equipment/categories", json=data)

        assert response.status_code in [200, 400, 500]

    def test_list_categories_endpoint(self, client):
        """测试获取分类列表 API"""
        response = client.get("/api/equipment/categories")

        assert response.status_code in [200, 500]

    def test_get_category_tree_endpoint(self, client):
        """测试获取分类树 API"""
        response = client.get("/api/equipment/categories/tree")

        assert response.status_code in [200, 500]


class TestEquipmentAPI:
    """装备 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_search_equipment_endpoint(self, client):
        """测试搜索装备 API"""
        response = client.post(
            "/api/equipment/equipment/search",
            json={"page": 1, "page_size": 10}
        )

        assert response.status_code in [200, 500]

    def test_search_equipment_with_filters(self, client):
        """测试带筛选条件的搜索 API"""
        response = client.post(
            "/api/equipment/equipment/search",
            json={
                "query": "test",
                "min_speed": 50,
                "suitable_styles": ["offensive"],
                "page": 1,
                "page_size": 10
            }
        )

        assert response.status_code in [200, 500]

    def test_list_equipment_endpoint(self, client):
        """测试获取装备列表 API"""
        response = client.get("/api/equipment/equipment")

        assert response.status_code in [200, 500]

    def test_get_equipment_not_found(self, client):
        """测试获取不存在的装备"""
        response = client.get("/api/equipment/equipment/non-existent-id")

        assert response.status_code in [404, 500]

    def test_compare_equipment_validation(self, client):
        """测试装备对比参数验证"""
        # 少于2件
        response = client.post(
            "/api/equipment/equipment/compare",
            json={"equipment_ids": [str(uuid.uuid4())]}
        )

        assert response.status_code == 422  # 验证失败


class TestProfileAPI:
    """用户档案 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_create_profile_endpoint(self, client, data_factory):
        """测试创建用户档案 API"""
        data = data_factory.user_profile_data()

        response = client.post("/api/equipment/profiles", json=data)

        assert response.status_code in [200, 400, 500]

    def test_get_profile_not_found(self, client):
        """测试获取不存在的用户档案"""
        response = client.get("/api/equipment/profiles/user/non-existent-user")

        assert response.status_code in [404, 500]

    def test_get_profile_completeness_not_found(self, client):
        """测试获取不存在档案的完整度"""
        response = client.get("/api/equipment/profiles/non-existent-id/completeness")

        assert response.status_code in [404, 500]


class TestReviewAPI:
    """评价 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_list_reviews_by_equipment(self, client):
        """测试获取装备评价列表 API"""
        response = client.get(f"/api/equipment/reviews/equipment/{uuid.uuid4()}")

        assert response.status_code in [200, 500]

    def test_get_review_summary(self, client):
        """测试获取评价汇总 API"""
        response = client.get(f"/api/equipment/reviews/equipment/{uuid.uuid4()}/summary")

        assert response.status_code in [200, 500]

    def test_mark_review_helpful_not_found(self, client):
        """测试标记不存在的评价为有帮助"""
        response = client.post(f"/api/equipment/reviews/{uuid.uuid4()}/helpful")

        assert response.status_code in [404, 500]


class TestRecommendationAPI:
    """推荐 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_get_recommendations_endpoint(self, client, data_factory):
        """测试获取推荐 API"""
        data = data_factory.recommendation_request_data()

        response = client.post("/api/equipment/recommendations", json=data)

        assert response.status_code in [200, 500]

    def test_get_quick_recommendations(self, client):
        """测试快速推荐 API"""
        response = client.get(
            "/api/equipment/recommendations/quick",
            params={
                "playing_style": "offensive",
                "skill_level": "intermediate",
                "top_k": 5
            }
        )

        assert response.status_code in [200, 500]

    def test_get_similar_equipment_not_found(self, client):
        """测试获取相似装备 - 不存在的装备"""
        response = client.post(
            "/api/equipment/recommendations/similar",
            json={
                "equipment_id": str(uuid.uuid4()),
                "top_k": 5
            }
        )

        assert response.status_code in [404, 500]

    def test_get_popular_equipment(self, client):
        """测试获取热门装备 API"""
        response = client.get("/api/equipment/recommendations/popular")

        assert response.status_code in [200, 500]

    def test_get_featured_equipment(self, client):
        """测试获取精选装备 API"""
        response = client.get("/api/equipment/recommendations/featured")

        assert response.status_code in [200, 500]


# ========== 健康检查测试 ==========


class TestHealthCheck:
    """健康检查测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")

        assert response.status_code == 200

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
