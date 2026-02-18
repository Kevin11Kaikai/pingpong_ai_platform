"""
LLM 模块 API 路由聚合
"""

from fastapi import APIRouter

from app.llm.api.chat import router as chat_router
from app.llm.api.conversations import router as conversations_router
from app.llm.api.documents import router as documents_router

router = APIRouter()

# 注册子路由
router.include_router(chat_router, tags=["Chat"])
router.include_router(conversations_router, tags=["Conversations"])
router.include_router(documents_router, tags=["Documents"])


@router.get("/health")
async def health_check():
    """LLM 模块健康检查"""
    return {"module": "llm", "status": "healthy"}
