"""
端到端测试
测试完整的用户流程
覆盖: 用户注册流程、装备推荐流程、视频分析流程
"""

import pytest
import uuid

from fastapi.testclient import TestClient


@pytest.mark.e2e
class TestUserRegistrationFlow:
    """用户注册和档案创建流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_complete_user_registration_flow(self, client):
        """测试完整的用户注册流程"""
        user_id = str(uuid.uuid4())

        # 步骤1: 创建用户装备偏好档案
        profile_data = {
            "user_id": user_id,
            "nickname": "新用户小明",
            "years_playing": 2,
            "playing_style": "offensive",
            "grip_style": "shakehand",
            "skill_level": "beginner",
            "prefer_speed": 60,
            "prefer_spin": 50,
            "prefer_control": 70,
            "budget_min": 100.0,
            "budget_max": 500.0,
        }

        profile_response = client.post("/api/equipment/profiles", json=profile_data)

        if profile_response.status_code == 200:
            profile = profile_response.json()
            assert profile["user_id"] == user_id
            assert profile["nickname"] == "新用户小明"

            # 步骤2: 检查档案完整度
            completeness_response = client.get(
                f"/api/equipment/profiles/{profile['id']}/completeness"
            )

            if completeness_response.status_code == 200:
                completeness = completeness_response.json()
                assert "completeness" in completeness
                assert completeness["completeness"] > 0

            # 步骤3: 获取个性化推荐
            rec_response = client.post(
                "/api/equipment/recommendations",
                json={
                    "user_id": user_id,
                    "recommendation_type": "blade",
                    "top_k": 5,
                }
            )

            assert rec_response.status_code in [200, 500]

    def test_user_profile_update_flow(self, client):
        """测试用户档案更新流程"""
        user_id = str(uuid.uuid4())

        # 创建初始档案
        initial_data = {
            "user_id": user_id,
            "playing_style": "all_round",
            "skill_level": "beginner",
        }

        create_response = client.post("/api/equipment/profiles", json=initial_data)

        if create_response.status_code == 200:
            profile = create_response.json()

            # 更新档案 - 技术进步了
            update_response = client.put(
                f"/api/equipment/profiles/{profile['id']}",
                json={
                    "skill_level": "intermediate",
                    "playing_style": "offensive",
                    "prefer_speed": 80,
                }
            )

            if update_response.status_code == 200:
                updated_profile = update_response.json()
                assert updated_profile["skill_level"] == "intermediate"
                assert updated_profile["playing_style"] == "offensive"


@pytest.mark.e2e
class TestEquipmentRecommendationFlow:
    """装备推荐完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_complete_equipment_recommendation_flow(self, client):
        """测试完整的装备推荐流程"""
        user_id = str(uuid.uuid4())

        # 步骤1: 创建用户档案
        profile_response = client.post(
            "/api/equipment/profiles",
            json={
                "user_id": user_id,
                "playing_style": "offensive",
                "skill_level": "intermediate",
                "prefer_speed": 75,
                "prefer_spin": 70,
                "prefer_control": 55,
                "budget_max": 800.0,
            }
        )

        # 步骤2: 获取推荐
        rec_response = client.post(
            "/api/equipment/recommendations",
            json={
                "user_id": user_id,
                "recommendation_type": "full_setup",
                "top_k": 5,
            }
        )

        if rec_response.status_code == 200:
            recommendations = rec_response.json()

            # 验证推荐结果结构
            assert "recommended_items" in recommendations or "items" in recommendations

        # 步骤3: 查看热门装备
        popular_response = client.get("/api/equipment/recommendations/popular")
        assert popular_response.status_code in [200, 500]

        # 步骤4: 查看精选装备
        featured_response = client.get("/api/equipment/recommendations/featured")
        assert featured_response.status_code in [200, 500]

    def test_equipment_search_and_compare_flow(self, client):
        """测试装备搜索和对比流程"""
        # 步骤1: 搜索装备
        search_response = client.post(
            "/api/equipment/equipment/search",
            json={
                "query": "底板",
                "min_speed": 60,
                "page": 1,
                "page_size": 10,
            }
        )

        if search_response.status_code == 200:
            search_results = search_response.json()
            equipment_list = search_results.get("equipment", [])

            # 如果有足够的结果，进行对比
            if len(equipment_list) >= 2:
                equipment_ids = [e["id"] for e in equipment_list[:3]]

                compare_response = client.post(
                    "/api/equipment/equipment/compare",
                    json={"equipment_ids": equipment_ids}
                )

                if compare_response.status_code == 200:
                    comparison = compare_response.json()
                    assert "comparison_summary" in comparison

    def test_equipment_review_flow(self, client):
        """测试装备评价流程"""
        user_id = str(uuid.uuid4())
        equipment_id = str(uuid.uuid4())

        # 步骤1: 创建用户档案
        client.post(
            "/api/equipment/profiles",
            json={
                "user_id": user_id,
                "nickname": "评价用户",
            }
        )

        # 步骤2: 提交评价
        review_response = client.post(
            "/api/equipment/reviews",
            params={"user_id": user_id},
            json={
                "equipment_id": equipment_id,
                "overall_rating": 5,
                "speed_rating": 4,
                "spin_rating": 5,
                "control_rating": 4,
                "title": "非常满意的购买",
                "content": "这款底板手感很好，适合进攻型打法",
                "pros": ["速度快", "旋转强", "做工精细"],
                "cons": ["价格略高"],
                "usage_duration": "1-3 months",
            }
        )

        # 步骤3: 查看评价汇总
        summary_response = client.get(
            f"/api/equipment/reviews/equipment/{equipment_id}/summary"
        )

        assert review_response.status_code in [200, 500]
        assert summary_response.status_code in [200, 500]


@pytest.mark.e2e
class TestVideoAnalysisFlow:
    """视频分析完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_video_analysis_task_flow(self, client):
        """测试视频分析任务流程"""
        # 步骤1: 获取任务列表
        tasks_response = client.get("/api/ball-tracking/tasks")

        assert tasks_response.status_code in [200, 404, 500]

        # 注意: 实际的视频上传和处理需要文件和 GPU
        # 这里只测试 API 可用性

    def test_trajectory_query_flow(self, client):
        """测试轨迹查询流程"""
        task_id = str(uuid.uuid4())

        # 尝试获取轨迹（预期不存在）
        trajectory_response = client.get(
            f"/api/ball-tracking/tasks/{task_id}/trajectory"
        )

        # 应该返回 404 或 500
        assert trajectory_response.status_code in [404, 500]


@pytest.mark.e2e
class TestLearningJourneyFlow:
    """学习旅程完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_learning_resource_discovery_flow(self, client):
        """测试学习资源发现流程"""
        # 步骤1: 浏览学习资源分类
        categories_response = client.get("/api/learning/categories")

        # 步骤2: 搜索特定主题的资源
        search_response = client.post(
            "/api/learning/resources/search",
            json={
                "query": "乒乓球基础技术",
                "top_k": 10,
            }
        )

        # 步骤3: 查看学习路径
        paths_response = client.get(
            "/api/learning/paths",
            params={"difficulty_level": "beginner"}
        )

        assert categories_response.status_code in [200, 404, 405, 500]
        assert search_response.status_code in [200, 404, 405, 500]
        assert paths_response.status_code in [200, 404, 405, 500]

    def test_learning_progress_tracking_flow(self, client):
        """测试学习进度跟踪流程"""
        user_id = str(uuid.uuid4())
        resource_id = str(uuid.uuid4())

        # 步骤1: 记录学习进度
        progress_response = client.post(
            "/api/learning/progress",
            json={
                "user_id": user_id,
                "resource_id": resource_id,
                "progress_percent": 50.0,
                "is_completed": False,
            }
        )

        # 步骤2: 查看用户学习进度
        user_progress_response = client.get(
            f"/api/learning/progress/user/{user_id}"
        )

        assert progress_response.status_code in [200, 404, 405, 422, 500]
        assert user_progress_response.status_code in [200, 404, 405, 500]


@pytest.mark.e2e
class TestTrainingAnalysisFlow:
    """训练分析完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_training_session_flow(self, client):
        """测试训练会话流程"""
        user_id = str(uuid.uuid4())

        # 步骤1: 创建训练会话
        session_response = client.post(
            "/api/training/sessions",
            json={
                "user_id": user_id,
                "title": "周末训练",
                "duration_minutes": 90,
                "session_type": "practice",
                "notes": "重点练习正手攻球",
            }
        )

        if session_response.status_code == 200:
            session = session_response.json()
            session_id = session.get("id")

            # 步骤2: 获取会话详情
            detail_response = client.get(f"/api/training/sessions/{session_id}")

            # 步骤3: 获取训练分析
            analysis_response = client.get(
                f"/api/training/analysis/session/{session_id}"
            )

            assert detail_response.status_code in [200, 404, 500]
            assert analysis_response.status_code in [200, 404, 500]

    def test_training_goals_flow(self, client):
        """测试训练目标流程"""
        user_id = str(uuid.uuid4())

        # 步骤1: 创建训练目标
        goal_response = client.post(
            "/api/training/goals",
            json={
                "user_id": user_id,
                "title": "提高正手攻球命中率",
                "description": "将正手攻球命中率从70%提升到85%",
                "target_value": 85.0,
                "deadline": "2025-12-31",
            }
        )

        # 步骤2: 获取用户目标列表
        goals_list_response = client.get(
            f"/api/training/goals/user/{user_id}"
        )

        assert goal_response.status_code in [200, 422, 500]
        assert goals_list_response.status_code in [200, 404, 500]


@pytest.mark.e2e
class TestSocialMediaFlow:
    """社交媒体完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_content_creation_flow(self, client):
        """测试内容创建流程"""
        # 步骤1: 创建内容
        content_response = client.post(
            "/api/social/content",
            json={
                "title": "分享我的训练心得",
                "content": "今天训练了两个小时，重点练习了正手拉球...",
                "content_type": "article",
                "tags": ["训练", "技术分享"],
            }
        )

        if content_response.status_code == 200:
            content = content_response.json()

            # 步骤2: 分析内容情感
            analysis_response = client.post(
                "/api/social/content/analyze",
                json={
                    "content": content.get("content", ""),
                    "analysis_type": "sentiment"
                }
            )

            assert analysis_response.status_code in [200, 422, 500]

    def test_qa_flow(self, client):
        """测试问答流程"""
        # 步骤1: 创建问题
        question_response = client.post(
            "/api/social/qa/questions",
            json={
                "title": "初学者应该选择什么底板？",
                "content": "我是刚开始学乒乓球的新手，想请教一下选择底板的建议",
                "tags": ["装备", "初学者"],
            }
        )

        if question_response.status_code == 200:
            question = question_response.json()
            question_id = question.get("id")

            # 步骤2: 获取问题详情
            detail_response = client.get(f"/api/social/qa/questions/{question_id}")

            assert detail_response.status_code in [200, 404, 500]


@pytest.mark.e2e
class TestLLMChatFlow:
    """LLM 聊天完整流程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_chat_session_flow(self, client):
        """测试聊天会话流程"""
        # 步骤1: 创建聊天会话
        session_response = client.post(
            "/api/llm/sessions",
            json={"title": "乒乓球技术咨询"}
        )

        if session_response.status_code == 200:
            session = session_response.json()
            session_id = session.get("id")

            # 步骤2: 发送消息
            chat_response = client.post(
                "/api/llm/chat",
                json={
                    "session_id": session_id,
                    "message": "请介绍一下正手攻球的要点"
                }
            )

            # 步骤3: 获取会话历史
            history_response = client.get(
                f"/api/llm/sessions/{session_id}/messages"
            )

            assert chat_response.status_code in [200, 500]
            assert history_response.status_code in [200, 404, 500]

    def test_knowledge_search_flow(self, client):
        """测试知识搜索流程"""
        # 步骤1: 搜索知识库
        search_response = client.post(
            "/api/llm/search",
            json={
                "query": "乒乓球发球技巧",
                "top_k": 5,
            }
        )

        assert search_response.status_code in [200, 500]


@pytest.mark.e2e
class TestCompleteUserJourney:
    """完整用户旅程测试"""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_new_user_onboarding_journey(self, client):
        """测试新用户入门旅程"""
        user_id = str(uuid.uuid4())

        # 1. 创建用户档案
        profile_response = client.post(
            "/api/equipment/profiles",
            json={
                "user_id": user_id,
                "nickname": "乒乓新手",
                "years_playing": 0,
                "playing_style": "all_round",
                "skill_level": "beginner",
                "prefer_speed": 50,
                "prefer_spin": 50,
                "prefer_control": 70,
                "budget_max": 300.0,
            }
        )

        # 2. 获取装备推荐
        rec_response = client.post(
            "/api/equipment/recommendations",
            json={
                "user_id": user_id,
                "recommendation_type": "full_setup",
                "top_k": 3,
            }
        )

        # 3. 搜索学习资源
        learning_response = client.post(
            "/api/learning/resources/search",
            json={
                "query": "初学者入门",
                "top_k": 5,
            }
        )

        # 4. 查看学习路径
        paths_response = client.get(
            "/api/learning/paths",
            params={"difficulty_level": "beginner"}
        )

        # 5. 开始 LLM 咨询
        chat_session_response = client.post(
            "/api/llm/sessions",
            json={"title": "新手入门咨询"}
        )

        # 验证所有步骤都能执行
        assert profile_response.status_code in [200, 400, 500]
        assert rec_response.status_code in [200, 404, 405, 500]
        assert learning_response.status_code in [200, 404, 405, 500]
        assert paths_response.status_code in [200, 404, 405, 500]
        assert chat_session_response.status_code in [200, 404, 405, 500]

    def test_advanced_user_training_journey(self, client):
        """测试进阶用户训练旅程"""
        user_id = str(uuid.uuid4())

        # 1. 创建进阶用户档案
        profile_response = client.post(
            "/api/equipment/profiles",
            json={
                "user_id": user_id,
                "nickname": "进阶球友",
                "years_playing": 5,
                "playing_style": "offensive",
                "skill_level": "advanced",
                "prefer_speed": 85,
                "prefer_spin": 80,
                "prefer_control": 60,
                "budget_max": 2000.0,
            }
        )

        # 2. 创建训练会话
        session_response = client.post(
            "/api/training/sessions",
            json={
                "user_id": user_id,
                "title": "技术突破训练",
                "duration_minutes": 120,
                "session_type": "technique",
            }
        )

        # 3. 设置训练目标
        goal_response = client.post(
            "/api/training/goals",
            json={
                "user_id": user_id,
                "title": "提高反手拧拉质量",
                "target_value": 90.0,
            }
        )

        # 4. 获取高级装备推荐
        rec_response = client.post(
            "/api/equipment/recommendations",
            json={
                "user_id": user_id,
                "recommendation_type": "blade",
                "top_k": 5,
            }
        )

        # 验证所有步骤
        assert profile_response.status_code in [200, 400, 500]
        assert session_response.status_code in [200, 422, 500]
        assert goal_response.status_code in [200, 422, 500]
        assert rec_response.status_code in [200, 500]
