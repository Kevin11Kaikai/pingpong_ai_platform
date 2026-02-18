"""
学习资源核心业务逻辑
"""

from app.learning_resources.core.resource_service import ResourceService, get_resource_service
from app.learning_resources.core.curriculum_service import CurriculumService, get_curriculum_service
from app.learning_resources.core.progress_service import ProgressService, get_progress_service
from app.learning_resources.core.knowledge_service import KnowledgeService, get_knowledge_service
from app.learning_resources.core.profile_service import ProfileService, get_profile_service
from app.learning_resources.core.recommendation_engine import (
    LearningRecommendationEngine,
    get_recommendation_engine,
)
from app.learning_resources.core.video_analysis_service import (
    VideoAnalysisService,
    get_video_analysis_service,
)

__all__ = [
    # 资源服务
    "ResourceService",
    "get_resource_service",
    # 学习路径服务
    "CurriculumService",
    "get_curriculum_service",
    # 进度服务
    "ProgressService",
    "get_progress_service",
    # 知识图谱服务
    "KnowledgeService",
    "get_knowledge_service",
    # 用户档案服务
    "ProfileService",
    "get_profile_service",
    # 推荐引擎
    "LearningRecommendationEngine",
    "get_recommendation_engine",
    # 视频分析服务
    "VideoAnalysisService",
    "get_video_analysis_service",
]
