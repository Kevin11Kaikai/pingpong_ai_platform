from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """装备推荐模块健康检查"""
    return {"module": "equipment_recommendation", "status": "healthy"}
