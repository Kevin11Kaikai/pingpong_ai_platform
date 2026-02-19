"""
健康检查服务

提供数据库、GPU、Embedding 模型等组件的健康检查功能
"""

import time
from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from app.shared.database import get_session_factory


class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """单个组件健康状态"""
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[dict] = None


class FullHealthResponse(BaseModel):
    """完整健康检查响应"""
    status: HealthStatus
    version: str
    components: dict[str, ComponentHealth]
    uptime_seconds: Optional[float] = None


# 应用启动时间，用于计算 uptime
_start_time: float = time.time()


def get_uptime() -> float:
    """获取应用运行时间（秒）"""
    return time.time() - _start_time


async def check_database() -> ComponentHealth:
    """检查数据库连接"""
    start = time.time()
    try:
        from sqlalchemy import text
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            _ = result.scalar()
        latency = (time.time() - start) * 1000
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            message="Database connection OK"
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=f"Database error: {str(e)}"
        )


def check_gpu() -> ComponentHealth:
    """检查 GPU 可用性"""
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            memory_allocated = torch.cuda.memory_allocated(0) / (1024**3)
            memory_free = memory_total - memory_allocated

            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message=f"GPU available: {device_name}",
                details={
                    "device_count": device_count,
                    "device_name": device_name,
                    "memory_total_gb": round(memory_total, 2),
                    "memory_allocated_gb": round(memory_allocated, 2),
                    "memory_free_gb": round(memory_free, 2),
                    "cuda_version": torch.version.cuda
                }
            )
        else:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="CUDA not available, running in CPU mode"
            )
    except ImportError:
        return ComponentHealth(
            status=HealthStatus.DEGRADED,
            message="PyTorch not installed"
        )
    except Exception as e:
        logger.error(f"GPU health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"GPU check error: {str(e)}"
        )


def check_embedding() -> ComponentHealth:
    """检查 Embedding 模型加载状态"""
    try:
        from app.shared.embedding import get_embedding_service

        service = get_embedding_service()
        if service._model is not None:
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Embedding model loaded",
                details={
                    "model_name": service.model_name,
                    "dimension": service.dimension
                }
            )
        else:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="Embedding model not loaded yet"
            )
    except ImportError:
        return ComponentHealth(
            status=HealthStatus.DEGRADED,
            message="Embedding service not available"
        )
    except Exception as e:
        logger.error(f"Embedding health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"Embedding check error: {str(e)}"
        )


async def get_full_health(version: str = "0.1.0") -> FullHealthResponse:
    """执行完整健康检查"""
    components: dict[str, ComponentHealth] = {}

    # 检查数据库
    components["database"] = await check_database()

    # 检查 GPU
    components["gpu"] = check_gpu()

    # 检查 Embedding
    components["embedding"] = check_embedding()

    # 计算整体状态
    statuses = [c.status for c in components.values()]

    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall_status = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        # 如果关键组件失败则 unhealthy
        if components["database"].status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.DEGRADED

    return FullHealthResponse(
        status=overall_status,
        version=version,
        components=components,
        uptime_seconds=round(get_uptime(), 2)
    )


async def is_ready() -> bool:
    """检查应用是否就绪（Kubernetes readiness probe）"""
    try:
        db_health = await check_database()
        return db_health.status != HealthStatus.UNHEALTHY
    except Exception:
        return False


def is_alive() -> bool:
    """检查应用是否存活（Kubernetes liveness probe）"""
    # 简单检查进程是否响应
    return True
