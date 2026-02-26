"""
训练分析模块单元测试

测试覆盖:
- Schema 验证
- 模型创建
- 服务逻辑
- API 端点
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

# ========== Schema 测试 ==========


class TestSessionSchemas:
    """训练会话 Schema 测试"""

    def test_session_create_valid(self):
        """测试有效的会话创建请求"""
        from app.training_analysis.schemas import SessionCreate

        data = SessionCreate(
            user_id="user-123",
            session_type="practice",
            started_at=datetime.utcnow(),
            title="正手练习",
            description="专项正手拉球训练",
            location="球馆A",
            practiced_techniques=["forehand_loop", "forehand_drive"],
            satisfaction_rating=4,
            fatigue_level=3,
        )

        assert data.user_id == "user-123"
        assert data.session_type == "practice"
        assert data.satisfaction_rating == 4

    def test_session_create_invalid_rating(self):
        """测试无效的满意度评分"""
        from app.training_analysis.schemas import SessionCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SessionCreate(
                user_id="user-123",
                session_type="practice",
                started_at=datetime.utcnow(),
                satisfaction_rating=6,  # 超出 1-5 范围
            )

    def test_session_update_partial(self):
        """测试部分更新"""
        from app.training_analysis.schemas import SessionUpdate

        data = SessionUpdate(notes="新笔记")
        assert data.notes == "新笔记"
        assert data.title is None

    def test_session_type_enum(self):
        """测试会话类型枚举"""
        from app.training_analysis.schemas import SessionCreate

        for session_type in ["practice", "drill", "match", "video_analysis"]:
            data = SessionCreate(
                user_id="user-123",
                session_type=session_type,
                started_at=datetime.utcnow(),
            )
            assert data.session_type == session_type


class TestGoalSchemas:
    """训练目标 Schema 测试"""

    def test_goal_create_valid(self):
        """测试有效的目标创建请求"""
        from app.training_analysis.schemas import GoalCreate

        data = GoalCreate(
            user_id="user-123",
            title="提升正手速度",
            goal_type="speed",
            technique_category="forehand",
            target_value=30.0,
            baseline_value=25.0,
            unit="km/h",
            start_date=datetime.utcnow(),
            target_date=datetime.utcnow() + timedelta(days=30),
        )

        assert data.target_value == 30.0
        assert data.technique_category == "forehand"

    def test_goal_type_enum(self):
        """测试目标类型枚举"""
        from app.training_analysis.schemas import GoalCreate

        for goal_type in ["speed", "accuracy", "consistency", "technique_mastery", "session_count", "total_duration"]:
            data = GoalCreate(
                user_id="user-123",
                title="测试目标",
                goal_type=goal_type,
                target_value=100,
                start_date=datetime.utcnow(),
                target_date=datetime.utcnow() + timedelta(days=30),
            )
            assert data.goal_type == goal_type

    def test_milestone_create(self):
        """测试里程碑创建"""
        from app.training_analysis.schemas import MilestoneCreate

        data = MilestoneCreate(value=27.5, note="第一周进度")
        assert data.value == 27.5


class TestInsightSchemas:
    """AI 洞察 Schema 测试"""

    def test_insight_feedback(self):
        """测试洞察反馈"""
        from app.training_analysis.schemas import InsightFeedback

        data = InsightFeedback(is_helpful=True, feedback="非常有用的建议")
        assert data.is_helpful is True

    def test_generate_insights_request(self):
        """测试洞察生成请求"""
        from app.training_analysis.schemas import GenerateInsightsRequest

        data = GenerateInsightsRequest(
            user_id="user-123",
            context_type="session",
            session_id="session-456",
        )

        assert data.context_type == "session"
        assert data.session_id == "session-456"


class TestAnalysisSchemas:
    """统计分析 Schema 测试"""

    def test_comparison_request(self):
        """测试对比分析请求"""
        from app.training_analysis.schemas import ComparisonRequest

        now = datetime.utcnow()
        data = ComparisonRequest(
            period1_start=now - timedelta(days=14),
            period1_end=now - timedelta(days=7),
            period2_start=now - timedelta(days=7),
            period2_end=now,
        )

        assert data.period1_start < data.period1_end
        assert data.period2_start < data.period2_end

    def test_trend_data_point(self):
        """测试趋势数据点"""
        from app.training_analysis.schemas import TrendDataPoint

        data = TrendDataPoint(
            date=datetime.utcnow(),
            value=25.5,
            session_count=3,
        )

        assert data.value == 25.5
        assert data.session_count == 3


# ========== 模型测试 ==========


class TestModels:
    """ORM 模型测试"""

    def test_session_type_enum(self):
        """测试会话类型枚举"""
        from app.training_analysis.models import SessionType

        assert SessionType.PRACTICE.value == "practice"
        assert SessionType.DRILL.value == "drill"
        assert SessionType.MATCH.value == "match"
        assert SessionType.VIDEO_ANALYSIS.value == "video_analysis"

    def test_goal_status_enum(self):
        """测试目标状态枚举"""
        from app.training_analysis.models import GoalStatus

        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.ACHIEVED.value == "achieved"
        assert GoalStatus.EXPIRED.value == "expired"

    def test_goal_type_enum(self):
        """测试目标类型枚举"""
        from app.training_analysis.models import GoalType

        assert GoalType.SPEED.value == "speed"
        assert GoalType.ACCURACY.value == "accuracy"
        assert GoalType.SESSION_COUNT.value == "session_count"

    def test_insight_type_enum(self):
        """测试洞察类型枚举"""
        from app.training_analysis.models import InsightType

        assert InsightType.IMPROVEMENT.value == "improvement"
        assert InsightType.WARNING.value == "warning"
        assert InsightType.RECOMMENDATION.value == "recommendation"


# ========== 服务测试 ==========


class TestMetricsService:
    """指标服务测试"""

    def test_map_stroke_to_category(self):
        """测试击球类型到技术类别的映射"""
        from app.training_analysis.core.metrics_service import MetricsService

        service = MetricsService()

        assert service._map_stroke_to_category("loop") == "forehand"
        assert service._map_stroke_to_category("forehand_loop") == "forehand"
        assert service._map_stroke_to_category("backhand_drive") == "backhand"
        assert service._map_stroke_to_category("serve") == "serve"
        assert service._map_stroke_to_category("push") == "receive"
        assert service._map_stroke_to_category("unknown") == "other"

    def test_calculate_accuracy_score(self):
        """测试准确率计算"""
        from app.training_analysis.core.metrics_service import MetricsService

        service = MetricsService()

        # 基础数据
        data = {"stroke_count": 10, "speeds": [25, 26, 25, 24, 25]}
        score = service.calculate_accuracy_score(data)

        assert 0 <= score <= 100
        assert score > 50  # 有击球数应该高于基础分

    def test_calculate_consistency_score(self):
        """测试稳定性计算"""
        from app.training_analysis.core.metrics_service import MetricsService

        service = MetricsService()

        # 高稳定性数据（速度变化小）
        stable_data = {"speeds": [25.0, 25.1, 24.9, 25.0, 25.2]}
        stable_score = service.calculate_consistency_score(stable_data)

        # 低稳定性数据（速度变化大）
        unstable_data = {"speeds": [20.0, 30.0, 15.0, 35.0, 25.0]}
        unstable_score = service.calculate_consistency_score(unstable_data)

        assert stable_score > unstable_score
        assert 0 <= stable_score <= 100
        assert 0 <= unstable_score <= 100

    def test_consistency_insufficient_data(self):
        """测试数据不足时的稳定性计算"""
        from app.training_analysis.core.metrics_service import MetricsService

        service = MetricsService()

        data = {"speeds": [25.0]}  # 只有一个数据点
        score = service.calculate_consistency_score(data)

        assert score == 50.0  # 返回中等分数


class TestAnalysisService:
    """分析服务测试"""

    def test_get_period_range_daily(self):
        """测试日周期范围计算"""
        from app.training_analysis.core.analysis_service import AnalysisService

        service = AnalysisService()
        date = datetime(2024, 6, 15, 14, 30, 0)

        start, end = service._get_period_range(date, "daily")

        assert start == datetime(2024, 6, 15, 0, 0, 0)
        assert end == datetime(2024, 6, 16, 0, 0, 0)

    def test_get_period_range_weekly(self):
        """测试周周期范围计算"""
        from app.training_analysis.core.analysis_service import AnalysisService

        service = AnalysisService()
        # 2024-06-15 是周六
        date = datetime(2024, 6, 15, 14, 30, 0)

        start, end = service._get_period_range(date, "weekly")

        # 周一是 6月10日
        assert start == datetime(2024, 6, 10, 0, 0, 0)
        assert end == datetime(2024, 6, 17, 0, 0, 0)

    def test_get_period_range_monthly(self):
        """测试月周期范围计算"""
        from app.training_analysis.core.analysis_service import AnalysisService

        service = AnalysisService()
        date = datetime(2024, 6, 15, 14, 30, 0)

        start, end = service._get_period_range(date, "monthly")

        assert start == datetime(2024, 6, 1, 0, 0, 0)
        assert end == datetime(2024, 7, 1, 0, 0, 0)

    def test_generate_highlights_concerns(self):
        """测试亮点和问题生成"""
        from app.training_analysis.core.analysis_service import AnalysisService

        service = AnalysisService()

        # 好的表现
        highlights, concerns = service._generate_highlights_concerns(
            session_count=10,
            speed_change=10.0,
            accuracy_change=8.0,
            consistency_change=None,
        )

        assert len(highlights) > 0
        assert any("训练次数" in h for h in highlights)
        assert any("球速提升" in h for h in highlights)

        # 差的表现
        highlights2, concerns2 = service._generate_highlights_concerns(
            session_count=1,
            speed_change=-10.0,
            accuracy_change=-10.0,
            consistency_change=None,
        )

        assert len(concerns2) > 0
        assert any("训练频率" in c for c in concerns2)


class TestInsightService:
    """洞察服务测试"""

    def test_generate_default_insights(self):
        """测试默认洞察生成"""
        from app.training_analysis.core.insight_service import InsightService

        service = InsightService()
        insights = service._generate_default_insights()

        assert len(insights) > 0
        assert "type" in insights[0]
        assert "title" in insights[0]
        assert "content" in insights[0]

    def test_build_session_prompt(self):
        """测试会话洞察提示构建"""
        from app.training_analysis.core.insight_service import InsightService
        from app.training_analysis.models import TrainingSession, SessionType

        service = InsightService()

        # 创建模拟会话
        session = Mock(spec=TrainingSession)
        session.session_type = SessionType.PRACTICE
        session.duration_minutes = 60
        session.total_strokes = 200
        session.avg_ball_speed_kmh = 25.0
        session.max_ball_speed_kmh = 35.0
        session.accuracy_score = 75.0
        session.consistency_score = 80.0
        session.practiced_techniques = ["forehand_loop"]
        session.satisfaction_rating = 4
        session.fatigue_level = 3

        prompt = service._build_session_prompt(session, [])

        assert "本次训练" in prompt
        assert "practice" in prompt
        assert "25.0" in prompt


# ========== API 测试 ==========


@pytest.fixture
def test_client():
    """
    创建测试客户端

    注意：API 测试使用同步 TestClient，但应用使用 async 数据库会话。
    这里使用简化的 mock 方式进行测试。
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import StaticPool

    from app.main import app as fastapi_app
    from app.shared.database import Base, get_db_session

    # 使用内存 SQLite async
    SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
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

    # 创建表

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
    client = TestClient(fastapi_app)

    yield client

    fastapi_app.dependency_overrides.clear()


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, test_client):
        """测试健康检查端点"""
        response = test_client.get("/api/training/health")

        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "training_analysis"
        assert data["status"] == "healthy"
        assert "sessions" in data["sub_modules"]
        assert "goals" in data["sub_modules"]
        assert "analysis" in data["sub_modules"]
        assert "insights" in data["sub_modules"]


class TestSessionsAPI:
    """会话 API 测试"""

    def test_list_sessions_empty(self, test_client):
        """测试空会话列表"""
        response = test_client.get("/api/training/sessions?user_id=test-user")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_get_session_not_found(self, test_client):
        """测试获取不存在的会话"""
        response = test_client.get("/api/training/sessions/non-existent-id")

        assert response.status_code == 404


class TestGoalsAPI:
    """目标 API 测试"""

    def test_list_goals_empty(self, test_client):
        """测试空目标列表"""
        response = test_client.get("/api/training/goals?user_id=test-user")

        assert response.status_code == 200
        data = response.json()
        assert data["goals"] == []
        assert data["total"] == 0

    def test_get_goal_not_found(self, test_client):
        """测试获取不存在的目标"""
        response = test_client.get("/api/training/goals/non-existent-id")

        assert response.status_code == 404


class TestInsightsAPI:
    """洞察 API 测试"""

    def test_list_insights_empty(self, test_client):
        """测试空洞察列表"""
        response = test_client.get("/api/training/insights/user/test-user")

        assert response.status_code == 200
        data = response.json()
        assert data["insights"] == []
        assert data["unread_count"] == 0

    def test_get_insight_not_found(self, test_client):
        """测试获取不存在的洞察"""
        response = test_client.get("/api/training/insights/non-existent-id")

        assert response.status_code == 404

    def test_get_unread_count(self, test_client):
        """测试未读数量"""
        response = test_client.get("/api/training/insights/user/test-user/unread-count")

        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 0


class TestAnalysisAPI:
    """分析 API 测试"""

    def test_get_user_stats_empty(self, test_client):
        """测试空用户统计"""
        response = test_client.get("/api/training/analysis/user/test-user/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0
        assert data["total_duration_minutes"] == 0

    def test_get_streak(self, test_client):
        """测试连续天数"""
        response = test_client.get("/api/training/analysis/user/test-user/streak")

        assert response.status_code == 200
        data = response.json()
        assert data["current_streak_days"] == 0
        assert data["longest_streak_days"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
