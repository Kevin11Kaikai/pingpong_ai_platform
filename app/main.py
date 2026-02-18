from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.ball_tracking.api import router as ball_tracking_router
from app.equipment_recommendation.api import router as equipment_router
from app.learning_resources.api import router as learning_router
from app.llm.api import router as llm_router
from app.social_media.api import router as social_media_router
from app.training_analysis.api import router as training_router
from config.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logging()
    logger.info("Pingpong AI Platform 启动中...")
    logger.info("所有模块 router 已注册")
    yield
    # 关闭时
    logger.info("Pingpong AI Platform 关闭")


app = FastAPI(
    title="Pingpong AI Platform",
    description="模块化乒乓球 AI 平台",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册各模块 router
app.include_router(llm_router, prefix="/api/llm", tags=["LLM"])
app.include_router(ball_tracking_router, prefix="/api/ball-tracking", tags=["Ball Tracking"])
app.include_router(equipment_router, prefix="/api/equipment", tags=["Equipment"])
app.include_router(social_media_router, prefix="/api/social-media", tags=["Social Media"])
app.include_router(learning_router, prefix="/api/learning", tags=["Learning Resources"])
app.include_router(training_router, prefix="/api/training", tags=["Training Analysis"])


@app.get("/health")
async def health_check():
    """全局健康检查"""
    return {"status": "healthy", "version": "0.1.0"}
