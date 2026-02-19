"""
训练分析模块 API 路由聚合
"""

from fastapi import APIRouter

from app.training_analysis.api.sessions import router as sessions_router
from app.training_analysis.api.goals import router as goals_router
from app.training_analysis.api.analysis import router as analysis_router
from app.training_analysis.api.insights import router as insights_router

router = APIRouter()

# 聚合子路由
router.include_router(sessions_router, prefix="/sessions", tags=["训练会话"])
router.include_router(goals_router, prefix="/goals", tags=["训练目标"])
router.include_router(analysis_router, prefix="/analysis", tags=["统计分析"])
router.include_router(insights_router, prefix="/insights", tags=["AI洞察"])


@router.get("/health")
async def health_check():
    """
    训练分析模块健康检查

    返回模块状态和可用功能列表。
    """
    return {
        "module": "training_analysis",
        "status": "healthy",
        "sub_modules": [
            "sessions",
            "goals",
            "analysis",
            "insights",
        ],
        "features": [
            "训练会话管理",
            "视频分析集成",
            "技术指标追踪",
            "训练目标管理",
            "进度快照生成",
            "趋势统计分析",
            "周期对比分析",
            "AI 训练建议",
            "学习连续天数统计",
        ],
    }
