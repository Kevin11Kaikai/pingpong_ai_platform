"""
社交媒体问答模块 API 路由聚合
"""

from fastapi import APIRouter

from app.social_media.api.contents import router as contents_router
from app.social_media.api.analysis import router as analysis_router
from app.social_media.api.replies import router as replies_router
from app.social_media.api.scrape import router as scrape_router

router = APIRouter()

# 聚合子路由
router.include_router(contents_router, prefix="/contents", tags=["内容管理"])
router.include_router(analysis_router, prefix="/analysis", tags=["内容分析"])
router.include_router(replies_router, prefix="/replies", tags=["回复建议"])
router.include_router(scrape_router, prefix="/scrape", tags=["内容抓取"])


@router.get("/health")
async def health_check():
    """
    社交媒体问答模块健康检查

    返回模块状态和可用的功能列表。
    """
    return {
        "module": "social_media",
        "status": "healthy",
        "sub_modules": [
            "contents",
            "analysis",
            "replies",
            "scrape",
        ],
        "features": [
            "内容 CRUD 管理",
            "多平台内容抓取",
            "AI 内容分析",
            "语义搜索",
            "RAG 回复生成",
            "回复质量评估",
        ],
    }
