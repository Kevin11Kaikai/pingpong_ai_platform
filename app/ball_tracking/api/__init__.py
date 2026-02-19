"""
Ball Tracking 模块 API 路由聚合
"""

from fastapi import APIRouter

from app.ball_tracking.api.videos import router as videos_router
from app.ball_tracking.api.trajectories import router as trajectories_router
from app.ball_tracking.api.analysis import router as analysis_router
from app.ball_tracking.api.visualization import router as visualization_router
from app.shared.gpu_manager import GPUManager

router = APIRouter()

# 注册子路由
router.include_router(videos_router, tags=["Videos"])
router.include_router(trajectories_router, tags=["Trajectories"])
router.include_router(analysis_router, tags=["Analysis"])
router.include_router(visualization_router, tags=["Visualization"])


@router.get("/health")
async def health_check():
    """球体追踪模块健康检查"""
    gpu_info = GPUManager.get_gpu_info()
    return {
        "module": "ball_tracking",
        "status": "healthy",
        "gpu": gpu_info,
    }
