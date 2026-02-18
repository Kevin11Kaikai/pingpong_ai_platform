from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """训练分析模块健康检查"""
    return {"module": "training_analysis", "status": "healthy"}
