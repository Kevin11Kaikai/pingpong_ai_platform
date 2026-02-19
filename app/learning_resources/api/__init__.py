"""
学习资源模块 API 路由聚合
"""

from fastapi import APIRouter

from app.learning_resources.api.resources import router as resources_router
from app.learning_resources.api.curriculum import router as curriculum_router
from app.learning_resources.api.progress import router as progress_router
from app.learning_resources.api.knowledge import router as knowledge_router
from app.learning_resources.api.profiles import router as profiles_router
from app.learning_resources.api.recommendations import router as recommendations_router
from app.learning_resources.api.video_analysis import router as video_analysis_router

router = APIRouter()

# 聚合子路由
router.include_router(resources_router, prefix="/resources", tags=["学习资源"])
router.include_router(curriculum_router, prefix="/paths", tags=["学习路径"])
router.include_router(progress_router, prefix="/progress", tags=["学习进度"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["知识图谱"])
router.include_router(profiles_router, prefix="/profiles", tags=["用户档案"])
router.include_router(recommendations_router, prefix="/recommendations", tags=["智能推荐"])
router.include_router(video_analysis_router, prefix="/video-analysis", tags=["视频分析"])


@router.get("/health")
async def health_check():
    """
    学习资源模块健康检查

    返回模块状态和可用的功能列表。
    """
    return {
        "module": "learning_resources",
        "status": "healthy",
        "sub_modules": [
            "resources",
            "paths",
            "progress",
            "knowledge",
            "profiles",
            "recommendations",
            "video_analysis",
        ],
        "features": [
            "资源 CRUD 管理",
            "语义向量搜索",
            "学习路径管理",
            "用户进度追踪",
            "资源收藏",
            "知识图谱管理",
            "用户学习档案",
            "个性化学习推荐",
            "视频技术分析集成",
            "学习统计分析",
        ],
    }
