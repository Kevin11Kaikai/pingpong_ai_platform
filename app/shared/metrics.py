"""
Prometheus 指标收集模块

提供请求计数、延迟直方图、GPU 内存等指标
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

# 延迟导入，避免在未启用时报错
_prometheus_available = False
_metrics_initialized = False

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _prometheus_available = True
except ImportError:
    logger.warning("prometheus_client not installed, metrics disabled")


# 全局注册器
REGISTRY = CollectorRegistry() if _prometheus_available else None

# 指标定义
if _prometheus_available:
    # 请求计数器
    REQUEST_COUNT = Counter(
        "pingpong_requests_total",
        "Total number of HTTP requests",
        ["method", "endpoint", "status"],
        registry=REGISTRY
    )

    # 请求延迟直方图
    REQUEST_LATENCY = Histogram(
        "pingpong_request_latency_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=REGISTRY
    )

    # 活跃请求数
    ACTIVE_REQUESTS = Gauge(
        "pingpong_active_requests",
        "Number of active requests",
        registry=REGISTRY
    )

    # LLM 调用计数
    LLM_REQUEST_COUNT = Counter(
        "pingpong_llm_requests_total",
        "Total number of LLM API calls",
        ["model", "status"],
        registry=REGISTRY
    )

    # 视频处理时长
    VIDEO_PROCESSING_DURATION = Histogram(
        "pingpong_video_processing_seconds",
        "Video processing duration in seconds",
        ["operation"],
        buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
        registry=REGISTRY
    )

    # GPU 内存使用
    GPU_MEMORY_BYTES = Gauge(
        "pingpong_gpu_memory_bytes",
        "GPU memory usage in bytes",
        ["device", "type"],
        registry=REGISTRY
    )


def record_llm_request(model: str, success: bool):
    """记录 LLM API 调用"""
    if _prometheus_available:
        status = "success" if success else "error"
        LLM_REQUEST_COUNT.labels(model=model, status=status).inc()


def record_video_processing(operation: str, duration: float):
    """记录视频处理时长"""
    if _prometheus_available:
        VIDEO_PROCESSING_DURATION.labels(operation=operation).observe(duration)


def update_gpu_metrics():
    """更新 GPU 内存指标"""
    if not _prometheus_available:
        return

    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i)
                reserved = torch.cuda.memory_reserved(i)
                GPU_MEMORY_BYTES.labels(device=str(i), type="allocated").set(allocated)
                GPU_MEMORY_BYTES.labels(device=str(i), type="reserved").set(reserved)
    except Exception as e:
        logger.debug(f"Failed to update GPU metrics: {e}")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus 指标收集中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not _prometheus_available:
            return await call_next(request)

        # 跳过 metrics 端点自身
        if request.url.path == "/metrics":
            return await call_next(request)

        # 记录活跃请求
        ACTIVE_REQUESTS.inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            # 计算延迟
            duration = time.time() - start_time

            # 简化端点路径（移除动态参数）
            endpoint = self._normalize_path(request.url.path)

            # 记录指标
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            ACTIVE_REQUESTS.dec()

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """规范化路径，移除动态参数"""
        parts = path.split("/")
        normalized = []
        for part in parts:
            # 替换数字 ID
            if part.isdigit():
                normalized.append("{id}")
            # 替换 UUID
            elif len(part) == 36 and part.count("-") == 4:
                normalized.append("{uuid}")
            else:
                normalized.append(part)
        return "/".join(normalized)


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus 指标端点"""
    if not _prometheus_available:
        return Response(
            content="Prometheus client not installed",
            status_code=503,
            media_type="text/plain"
        )

    # 更新 GPU 指标
    update_gpu_metrics()

    # 生成指标
    metrics_output = generate_latest(REGISTRY)
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )


def is_metrics_enabled() -> bool:
    """检查指标是否启用"""
    return _prometheus_available
