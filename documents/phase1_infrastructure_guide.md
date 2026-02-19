# Phase 1: 基础架构

## Overview

基础架构层为整个 Pingpong AI Platform 提供运行骨架，包括 FastAPI 应用入口、配置管理、数据库、GPU 管理、日志、认证、健康检查和监控。所有 6 个业务模块都依赖这一层。

---

## 目录

1. [模块架构](#1-模块架构)
2. [配置管理](#2-配置管理)
3. [数据库](#3-数据库)
4. [GPU 显存管理](#4-gpu-显存管理)
5. [日志系统](#5-日志系统)
6. [健康检查](#6-健康检查)
7. [Prometheus 监控](#7-prometheus-监控)
8. [FastAPI 应用入口](#8-fastapi-应用入口)
9. [依赖管理](#9-依赖管理)
10. [使用指南](#10-使用指南)

---

## 1. 模块架构

### 1.1 目录结构

```
app/
├── main.py                  # FastAPI 入口，路由注册，生命周期管理
├── api/
│   └── health.py            # 健康检查 API（basic / full / ready / live）
└── shared/                  # 共享工具层（所有模块依赖）
    ├── database.py          # 异步 SQLAlchemy 引擎 + 会话管理
    ├── gpu_manager.py       # GPU 显存生命周期管理
    ├── health.py            # 组件级健康检查服务
    └── metrics.py           # Prometheus 指标中间件

config/
├── settings.py              # Pydantic Settings（从 .env 加载全部配置）
└── logging.py               # Loguru 日志配置（控制台 + 分模块文件）

.env.example                 # 环境变量模板
requirements.txt             # 通用 Python 依赖
requirements-gpu.txt         # PyTorch + CUDA 专用依赖
```

### 1.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                     app/main.py (FastAPI)                        │
│                                                                 │
│  lifespan() → setup_logging() → init_db() → register routers   │
│                                                                 │
│  中间件: CORSMiddleware │ MetricsMiddleware                      │
│                                                                 │
│  路由注册:                                                       │
│    /api/health  → health_router                                 │
│    /api/llm     → llm_router                                   │
│    /api/ball-tracking → ball_tracking_router                    │
│    /api/equipment     → equipment_router                        │
│    /api/social-media  → social_media_router                     │
│    /api/learning      → learning_router                         │
│    /api/training      → training_router                         │
│    /metrics     → Prometheus 端点                                │
│    /static      → 前端静态文件                                    │
│    /            → index.html (SPA 路由回退)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  config/   │ │  shared/   │ │  shared/   │
│ settings.py│ │ database.py│ │gpu_manager │
│  (配置)    │ │  (数据库)  │ │  (GPU)     │
└────────────┘ └────────────┘ └────────────┘
```

---

## 2. 配置管理

### 2.1 config/settings.py

使用 `pydantic-settings` 从 `.env` 文件集中加载所有配置，通过 `@lru_cache` 实现单例。

**核心类: `Settings`**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

**配置分组：**

| 分组 | 字段 | 默认值 | 说明 |
|------|------|--------|------|
| **应用** | `app_env` | `"development"` | 运行环境 |
| | `debug` | `True` | 调试模式 |
| | `log_level` | `"DEBUG"` | 日志级别 |
| **LLM** | `llm_api_key` | 必填 | OpenAI 兼容 API Key |
| | `llm_base_url` | `"https://api.ohmygpt.com/v1"` | API 地址 |
| **数据库** | `database_url` | `"sqlite+aiosqlite:///./data/pingpong.db"` | 异步连接字符串 |
| **JWT** | `jwt_secret_key` | 必填 | 签名密钥 |
| | `jwt_algorithm` | `"HS256"` | 签名算法 |
| | `jwt_expire_minutes` | `1440` | Token 有效期（分钟） |
| **Ball Tracking** | `ball_tracking_upload_dir` | `"./data/uploads/videos"` | 视频上传目录 |
| | `ball_tracking_max_file_size_mb` | `500` | 最大文件大小 |
| **Equipment** | `equipment_default_page_size` | `20` | 分页大小 |
| **Social Media** | `social_media_scrape_enabled` | `True` | 是否启用爬取 |
| **Learning** | `learning_resource_upload_dir` | `"./data/uploads/learning"` | 资源上传目录 |
| **Training** | `training_insight_model` | `"gpt-4o-mini"` | AI 洞察模型 |
| **Prometheus** | `prometheus_enabled` | `False` | 是否启用监控 |
| **CORS** | `cors_origins` | `["*"]` | 允许的跨域来源 |
| **Server** | `server_workers` | `1` | Uvicorn worker 数 |

**单例访问：**

```python
from config.settings import get_settings

settings = get_settings()  # @lru_cache 保证全局唯一实例
print(settings.llm_api_key)
```

### 2.2 .env.example

环境变量模板，开发者 copy 为 `.env` 后填入实际值：

```ini
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.ohmygpt.com/v1
APP_ENV=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./data/pingpong.db
JWT_SECRET_KEY=your-secret-key
```

> **安全规则**：`.env` 和 `.env.production` 均在 `.gitignore` 中，永远不会提交到 Git。

---

## 3. 数据库

### 3.1 app/shared/database.py

使用 SQLAlchemy 2.x 异步引擎 + aiosqlite 驱动，提供全局连接管理。

**核心组件：**

| 组件 | 说明 |
|------|------|
| `Base` | SQLAlchemy `DeclarativeBase`，所有 ORM 模型继承此基类 |
| `get_engine()` | 全局异步引擎单例（`pool_pre_ping=True` 自动检测断连） |
| `get_session_factory()` | 全局 `async_sessionmaker` 单例 |
| `get_db_session()` | FastAPI 依赖注入用的 async generator，自动 commit/rollback |
| `init_db()` | 创建所有表结构（`Base.metadata.create_all()`） |
| `close_db()` | 关闭引擎、释放连接池 |

**依赖注入用法：**

```python
from app.shared.database import get_db_session

@router.post("/endpoint")
async def endpoint(db: AsyncSession = Depends(get_db_session)):
    # db 会在请求结束后自动 commit 或 rollback
    result = await db.execute(select(MyModel))
    return result.scalars().all()
```

**生命周期集成（main.py lifespan）：**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()       # 启动时建表
    yield
    await close_db()      # 关闭时释放连接
```

---

## 4. GPU 显存管理

### 4.1 app/shared/gpu_manager.py

管理 GPU 模型的加载/卸载生命周期，确保同一时间只有一个重型模型在 GPU 上。

**核心类: `GPUManager`**

| 方法 | 说明 |
|------|------|
| `get_device()` | 返回 `cuda` 或 `cpu` 设备 |
| `get_gpu_info()` | 返回 GPU 名称、总显存、已分配、已缓存 |
| `load_model(name)` | 上下文管理器：加载前卸载旧模型，退出时清理缓存 |
| `clear_cache()` | 调用 `torch.cuda.empty_cache()` |

**设计原则：**

```
CV 模型串行加载（不同时占 GPU）：
  Step 1: load BlurBall (~4-6GB) → detect → unload
  Step 2: load RTMPose (~2GB)    → pose   → unload
  Step 3: load MotionBert (~2GB) → 3D     → unload

LLM: 全走云端 API，零 GPU 占用
Embedding: 常驻 CPU/GPU (~0.5GB)
```

**使用示例：**

```python
from app.shared.gpu_manager import GPUManager

gpu = GPUManager()
with gpu.load_model("blurball"):
    # 模型在 GPU 上，执行推理
    result = model.predict(frame)
# 退出上下文后自动 empty_cache()
```

---

## 5. 日志系统

### 5.1 config/logging.py

使用 Loguru 替代标准 logging，提供结构化日志和自动文件分割。

**日志输出通道：**

| 通道 | 文件 | 级别 | 说明 |
|------|------|------|------|
| 控制台 | stdout | 由 `LOG_LEVEL` 控制 | 彩色格式化输出 |
| 全局日志 | `logs/app_{date}.log` | DEBUG+ | 10MB 自动轮转，保留 30 天，zip 压缩 |
| 错误日志 | `logs/error_{date}.log` | ERROR+ | 单独记录错误和异常 |
| 模块日志 | `logs/{module}_{date}.log` | DEBUG+ | 6 个模块各自独立文件 |

**模块级日志分离：**

每个业务模块（llm、ball_tracking、equipment、social_media、learning、training）写入单独的日志文件，便于定位问题。

**日志格式：**

```
2026-02-19 15:42:03 | INFO | app.main:lifespan:29 | Pingpong AI Platform 启动中...
```

---

## 6. 健康检查

### 6.1 app/shared/health.py — 检查服务

提供三个组件的独立健康检查：

| 组件 | 检查方式 | Healthy | Degraded | Unhealthy |
|------|----------|---------|----------|-----------|
| **Database** | 执行 `SELECT 1`，测量延迟 | 查询成功 | — | 连接失败或查询超时 |
| **GPU** | 检查 `torch.cuda.is_available()` | CUDA 可用 | CPU 模式 / PyTorch 未安装 | 检查异常 |
| **Embedding** | 检查模型是否已加载到内存 | 模型已加载 | 模型未加载 | 检查异常 |

**整体状态计算规则：**

- 全部 HEALTHY → 整体 HEALTHY
- Database UNHEALTHY → 整体 UNHEALTHY（关键组件）
- 其他组件 UNHEALTHY/DEGRADED → 整体 DEGRADED

### 6.2 app/api/health.py — API 端点

| 端点 | 方法 | 用途 | 响应 |
|------|------|------|------|
| `/api/health/` | GET | 负载均衡器快速检查 | `{"status":"healthy","version":"0.1.0"}` |
| `/api/health/full` | GET | 完整组件状态 | `FullHealthResponse`（含各组件详情和 uptime） |
| `/api/health/ready` | GET | K8s readiness probe | 200 或 503 |
| `/api/health/live` | GET | K8s liveness probe | 200 或 503 |

**完整健康检查响应示例：**

```json
{
  "status": "degraded",
  "version": "0.1.0",
  "components": {
    "database": { "status": "healthy", "latency_ms": 1.17, "message": "Database connection OK" },
    "gpu": {
      "status": "healthy",
      "message": "GPU available: NVIDIA GeForce RTX 4080 SUPER",
      "details": { "memory_total_gb": 15.99, "memory_free_gb": 15.9, "cuda_version": "12.4" }
    },
    "embedding": { "status": "degraded", "message": "Embedding service not available" }
  },
  "uptime_seconds": 311.25
}
```

---

## 7. Prometheus 监控

### 7.1 app/shared/metrics.py

当 `PROMETHEUS_ENABLED=true` 时，通过中间件自动采集 HTTP 请求指标。

**指标定义：**

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `http_requests_total` | Counter | method, endpoint, status | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | method, endpoint | 请求延迟分布 |
| `http_requests_in_progress` | Gauge | — | 当前并发请求数 |
| `llm_requests_total` | Counter | model, status | LLM API 调用计数 |
| `video_processing_duration_seconds` | Histogram | operation | 视频处理耗时 |
| `gpu_memory_bytes` | Gauge | device, type | GPU 显存使用（total / allocated / cached） |

**MetricsMiddleware 工作流程：**

```
请求进入 → ACTIVE_REQUESTS +1 → 计时开始
    ↓
请求处理（FastAPI 路由）
    ↓
请求完成 → ACTIVE_REQUESTS -1 → REQUEST_COUNT +1 → REQUEST_LATENCY 记录耗时
```

**路径归一化：** 将 UUID 和数字 ID 替换为 `{id}` / `{uuid}`，避免高基数指标。

**端点：** `GET /metrics` 返回 Prometheus 文本格式，同时更新 GPU 显存指标。

---

## 8. FastAPI 应用入口

### 8.1 app/main.py

**生命周期管理 (lifespan)：**

```
启动阶段                          关闭阶段
────────                         ────────
setup_logging()                  close_db()
get_settings()                   logger.info("关闭")
init_db()
logger.info("router 已注册")
         ↓
      yield（应用运行中）
         ↓
```

**中间件栈（按注册顺序，执行顺序相反）：**

1. `CORSMiddleware` — 跨域请求处理，`allow_origins` 从配置读取
2. `MetricsMiddleware` — Prometheus 指标采集（条件启用）

**静态文件与 SPA 路由：**

```python
# 如果 frontend/ 目录存在
app.mount("/static", StaticFiles(directory=FRONTEND_DIR))

@app.get("/")           # → frontend/index.html
@app.get("/{path:path}")  # → frontend/pages/{path}.html 或回退到 index.html
```

路由优先级：`/api/*` 的 API 路由先注册，优先匹配；`/{path:path}` 是兜底路由，处理前端页面。

---

## 9. 依赖管理

### 9.1 requirements.txt（通用依赖，42 个包）

| 类别 | 包 |
|------|-----|
| **Web 框架** | fastapi, uvicorn[standard], pydantic, pydantic-settings |
| **数据库** | sqlalchemy, aiosqlite |
| **AI/ML** | sentence-transformers, faiss-cpu, openai |
| **CV** | opencv-python, hydra-core, omegaconf, pytorch-lightning, timm, einops, scipy, scikit-image |
| **日志/配置** | loguru, python-dotenv |
| **认证** | python-jose[cryptography] |
| **爬虫** | beautifulsoup4, lxml, fake-useragent, tenacity |
| **文件** | python-multipart, aiofiles |
| **监控** | prometheus-client |
| **测试** | pytest, pytest-asyncio, ruff |
| **HTTP** | httpx |
| **可视化** | matplotlib, shapely, imageio |

### 9.2 requirements-gpu.txt（GPU 专用，3 个包）

```
--extra-index-url https://download.pytorch.org/whl/cu124
torch==2.5.1+cu124
torchvision==0.20.1+cu124
torchaudio==2.5.1+cu124
```

**安装顺序很重要：** 先装 `requirements.txt`（通用依赖），再装 `requirements-gpu.txt`（覆盖 PyTorch 为 CUDA 版本）。

---

## 10. 使用指南

### 10.1 本地开发启动

```bash
conda activate pingpong_ai
pip install -r requirements.txt
pip install -r requirements-gpu.txt

cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY 和 JWT_SECRET_KEY

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 10.2 验证基础架构

```bash
# 基本健康检查
curl http://localhost:8000/api/health/
# {"status":"healthy","version":"0.1.0"}

# 完整健康检查（含 GPU 状态）
curl http://localhost:8000/api/health/full

# Swagger 文档
# 浏览器打开 http://localhost:8000/docs
```

### 10.3 Docker 部署

```bash
docker compose -f docker/docker-compose.prod.yml build pingpong-api
docker compose -f docker/docker-compose.prod.yml up -d

# 4 个容器：API + Nginx + Prometheus + Grafana
docker ps --format "table {{.Names}}\t{{.Status}}"
```

详细 Docker 部署流程参见 [Windows Docker Desktop 部署指南](windows_docker_desktop.md)。
