"""
健康检查 API 路由

提供多种健康检查端点：
- /api/health/ - 基本检查（负载均衡器）
- /api/health/full - 完整检查（所有组件）
- /api/health/ready - 就绪检查（K8s readiness）
- /api/health/live - 存活检查（K8s liveness）
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.shared.health import (
    get_full_health,
    is_ready,
    is_alive,
    HealthStatus,
    FullHealthResponse,
)

router = APIRouter()


@router.get("/")
async def health_check():
    """
    基本健康检查

    用于负载均衡器健康检查，快速返回
    """
    return {"status": "healthy", "version": "0.1.0"}


@router.get("/full", response_model=FullHealthResponse)
async def full_health_check():
    """
    完整健康检查

    检查所有组件状态：数据库、GPU、Embedding 模型
    """
    health = await get_full_health(version="0.1.0")

    # 根据状态返回不同的 HTTP 状态码
    if health.status == HealthStatus.UNHEALTHY:
        return JSONResponse(content=health.model_dump(), status_code=503)
    elif health.status == HealthStatus.DEGRADED:
        return JSONResponse(content=health.model_dump(), status_code=200)
    return health


@router.get("/ready")
async def readiness_check():
    """
    就绪检查（Kubernetes readiness probe）

    检查应用是否准备好接收流量
    """
    ready = await is_ready()
    if ready:
        return {"status": "ready"}
    return JSONResponse(
        content={"status": "not_ready"},
        status_code=503
    )


@router.get("/live")
async def liveness_check():
    """
    存活检查（Kubernetes liveness probe）

    检查应用进程是否存活
    """
    if is_alive():
        return {"status": "alive"}
    return JSONResponse(
        content={"status": "dead"},
        status_code=503
    )
