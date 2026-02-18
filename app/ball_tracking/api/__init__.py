from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """球体追踪模块健康检查"""
    return {"module": "ball_tracking", "status": "healthy"}
