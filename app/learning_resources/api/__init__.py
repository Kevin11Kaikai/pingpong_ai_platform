from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """学习资源模块健康检查"""
    return {"module": "learning_resources", "status": "healthy"}
