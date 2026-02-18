from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """社交媒体问答模块健康检查"""
    return {"module": "social_media", "status": "healthy"}
