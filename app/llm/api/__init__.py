from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """LLM 模块健康检查"""
    return {"module": "llm", "status": "healthy"}
