import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.ball_tracking.api import router as ball_tracking_router
from app.equipment_recommendation.api import router as equipment_router
from app.learning_resources.api import router as learning_router
from app.llm.api import router as llm_router
from app.social_media.api import router as social_media_router
from app.training_analysis.api import router as training_router
from app.shared.database import init_db, close_db
from config.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    setup_logging()
    logger.info("Pingpong AI Platform 启动中...")

    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")

    logger.info("所有模块 router 已注册")
    yield
    # 关闭时
    await close_db()
    logger.info("Pingpong AI Platform 关闭")


app = FastAPI(
    title="Pingpong AI Platform",
    description="模块化乒乓球 AI 平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# 静态文件服务 - 前端
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(FRONTEND_DIR):
    # 挂载静态文件
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        """提供首页"""
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not found")

    @app.get("/{path:path}")
    async def serve_pages(path: str):
        """提供页面路由"""
        # API 路由跳过
        if path.startswith("api/") or path.startswith("static/"):
            raise HTTPException(status_code=404)

        # 尝试返回对应 HTML
        html_path = os.path.join(FRONTEND_DIR, "pages", f"{path}.html")
        if os.path.exists(html_path):
            return FileResponse(html_path)

        # 回退到 index.html (SPA 支持)
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="Page not found")
