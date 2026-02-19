# Windows 10 + Docker Desktop 本地部署指南

## 概述

本文档记录在 **Windows 10 + Docker Desktop + NVIDIA RTX 4080 Super** 环境下，将 Pingpong AI Platform 以生产级 Docker 容器方式本地部署的完整流程，包括遇到的 3 个 bug 及其修复方案。

## 目录

1. [环境要求](#环境要求)
2. [环境验证](#环境验证)
3. [部署架构](#部署架构)
4. [部署步骤](#部署步骤)
5. [Bug 修复记录](#bug-修复记录)
6. [服务验证](#服务验证)
7. [访问方式](#访问方式)
8. [常用运维命令](#常用运维命令)
9. [已知问题与注意事项](#已知问题与注意事项)

---

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| OS | Windows 10 (19045+) | 需支持 WSL2 |
| Docker Desktop | 29.x+ | 启用 WSL2 后端 |
| Docker Compose | 2.40+ | 随 Docker Desktop 附带 |
| NVIDIA Driver | 566+ (Windows) | 宿主机驱动，WSL2 自动映射 |
| GPU | NVIDIA RTX 4080 Super | 16GB VRAM |
| 磁盘空间 | ≥ 30 GB | Docker 镜像约 15GB |

### Docker Desktop 设置

1. 安装 Docker Desktop for Windows
2. Settings → General → 勾选 **Use the WSL 2 based engine**
3. Settings → Resources → WSL Integration → 启用你的 WSL distro
4. **无需单独安装 NVIDIA Container Toolkit**（Docker Desktop for Windows 内置 GPU 支持）

---

## 环境验证

部署前运行以下命令确认环境就绪：

```powershell
# 检查 Docker 版本
docker --version
# 期望: Docker version 29.x+

# 检查 Docker Compose 版本
docker compose version
# 期望: Docker Compose version v2.40+

# 验证 GPU 透传（关键步骤）
docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi
# 期望: 正确显示 GPU 信息（NVIDIA GeForce RTX 4080 SUPER）
```

如果最后一条命令显示 GPU 信息，说明 Docker → WSL2 → NVIDIA GPU 通路正常。

---

## 部署架构

```
浏览器 (http://localhost)
   │
   ▼
┌─────────────────┐
│   Nginx (:80)   │  反向代理、安全头、限流
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ pingpong-api    │  FastAPI + uvicorn (:8000)
│ (:8001 映射)    │  GPU 访问、SQLite、Embedding
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│Prome-  │ │ Grafana  │
│theus   │ │ (:3000)  │
│(:9090) │ │ 仪表盘    │
└────────┘ └──────────┘
```

### 容器说明

| 容器 | 镜像 | 端口 | 功能 |
|------|------|------|------|
| pingpong-api | pingpong-api:latest (自建) | 8001→8000 | FastAPI 后端 + GPU 推理 |
| pingpong-nginx | nginx:1.25-alpine | 80, 443 | 反向代理、安全头、限流 |
| pingpong-prometheus | prom/prometheus:v2.48.0 | 9090 | 指标采集 |
| pingpong-grafana | grafana/grafana:10.2.2 | 3000 | 监控仪表盘 |

### 数据持久化 (Docker Volumes)

| Volume | 挂载点 | 说明 |
|--------|--------|------|
| pingpong-data | /app/data | SQLite 数据库、上传文件 |
| pingpong-logs | /app/logs | 应用日志 |
| pingpong-vectorstore | /app/app/vectorstore | FAISS 向量索引 |
| prometheus-data | /prometheus | Prometheus 时序数据 |
| grafana-data | /var/lib/grafana | Grafana 配置和仪表盘 |
| nginx-logs | /var/log/nginx | Nginx 访问/错误日志 |

---

## 部署步骤

### 1. 准备环境配置文件

```powershell
cd D:\others\Pingpong_2026

# 基于模板创建生产配置（如果尚未创建）
Copy-Item .env.production.example .env.production
```

编辑 `.env.production`，填入必需的密钥：

```ini
# 必须修改
LLM_API_KEY=your-actual-api-key
JWT_SECRET_KEY=your-random-64-char-hex
GRAFANA_ADMIN_PASSWORD=your-grafana-password

# 可选调整
CORS_ORIGINS=["http://localhost"]
DATABASE_URL=sqlite+aiosqlite:///./data/pingpong_prod.db
```

> **安全提示**: `.env.production` 已在 `.gitignore` 中，不会被提交到 Git。

### 2. 构建 Docker 镜像

```powershell
docker compose -f docker/docker-compose.prod.yml build pingpong-api
```

首次构建约 15 分钟（下载 CUDA 基础镜像 + PyTorch + NVIDIA 库约 8GB）。后续重建如果只修改应用代码，几秒即可完成（利用层缓存）。

### 3. 启动所有服务

```powershell
docker compose -f docker/docker-compose.prod.yml up -d
```

启动顺序由 Docker Compose 的 `depends_on` + `healthcheck` 控制：

1. **pingpong-api** 先启动，等待健康检查通过（60s start_period）
2. **pingpong-nginx** 和 **pingpong-prometheus** 等 API healthy 后启动
3. **pingpong-grafana** 等 Prometheus 启动后启动

### 4. 确认所有容器 healthy

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

期望输出（所有容器 `healthy`）：

```
NAMES                 STATUS                    PORTS
pingpong-api          Up X minutes (healthy)    0.0.0.0:8001->8000/tcp
pingpong-nginx        Up X minutes (healthy)    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
pingpong-prometheus   Up X minutes (healthy)    0.0.0.0:9090->9090/tcp
pingpong-grafana      Up X minutes (healthy)    0.0.0.0:3000->3000/tcp
```

---

## Bug 修复记录

部署过程中发现并修复了 3 个 bug，已提交至 GitHub（commit: `fix(infra): resolve 3 deployment bugs`）。

### Bug 1: Dockerfile 错误 COPY 了 external/ 而非 frontend/

**现象**: 容器内缺少前端文件，根路径 `/` 返回 404。

**原因**: `Dockerfile.prod` 中 `COPY external/ ./external/`，但 `.dockerignore` 排除了 `external/BlurBall/` 和 `external/tt3d/`（外部依赖通过 volume 挂载），同时漏掉了 `frontend/` 目录。

**修复**:

```dockerfile
# 修复前
COPY --chown=pingpong:pingpong external/ ./external/

# 修复后
COPY --chown=pingpong:pingpong frontend/ ./frontend/
```

### Bug 2: 数据库健康检查使用了 async generator 导致报错

**现象**: `/api/health/full` 返回 503，database 组件 unhealthy，错误信息：
`'async_generator' object does not support the asynchronous context manager protocol`

**原因**: `health.py` 中 `async with get_db_session() as session:` —— `get_db_session()` 是 FastAPI 依赖注入的 async generator（使用 `yield`），不能直接作为 async context manager 使用。

**修复**:

```python
# 修复前
from app.shared.database import get_db_session

async def check_database():
    async with get_db_session() as session:
        result = await session.execute("SELECT 1")

# 修复后
from app.shared.database import get_session_factory

async def check_database():
    from sqlalchemy import text
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
```

同时修复了 SQLAlchemy 2.x 要求用 `text()` 包裹原始 SQL 的问题。

### Bug 3: 非 root 用户无 home 目录导致 HuggingFace 模型缓存失败

**现象**: `POST /api/llm/chat` 返回 500，错误信息：
`PermissionError at /home/pingpong when downloading sentence-transformers/all-MiniLM-L6-v2`

**原因**: `useradd -r -g pingpong pingpong` 创建系统用户时没有 `-m` 参数，不会创建 home 目录。HuggingFace `transformers` 库默认将模型缓存到 `~/.cache/huggingface/`，导致写入失败。

**修复**:

```dockerfile
# 修复前
RUN groupadd -r pingpong && useradd -r -g pingpong pingpong

# 修复后（-m 创建 home 目录，-d 指定路径）
RUN groupadd -r pingpong && useradd -r -g pingpong -m -d /home/pingpong pingpong
```

---

## 服务验证

### 基本健康检查

```powershell
# 基本检查（通过 Nginx）
Invoke-RestMethod -Uri "http://localhost/api/health/"
# 期望: {"status":"healthy","version":"0.1.0"}

# 完整检查（包含 GPU、数据库、Embedding 状态）
Invoke-RestMethod -Uri "http://localhost/api/health/full" | ConvertTo-Json -Depth 5
```

完整健康检查期望结果：

```json
{
  "status": "degraded",
  "components": {
    "database": { "status": "healthy", "latency_ms": 1.17 },
    "gpu": {
      "status": "healthy",
      "message": "GPU available: NVIDIA GeForce RTX 4080 SUPER",
      "details": {
        "memory_total_gb": 15.99,
        "memory_free_gb": 15.9,
        "cuda_version": "12.4"
      }
    },
    "embedding": { "status": "degraded", "message": "Embedding service not available" }
  }
}
```

> **说明**: 整体状态 `degraded` 是正常的 —— Embedding 模型采用按需加载策略，首次调用 LLM chat 时自动下载并加载。

### LLM 对话测试

```powershell
$body = '{"message":"乒乓球正手攻球的要领是什么？","conversation_id":null}'
Invoke-RestMethod -Uri "http://localhost/api/llm/chat" -Method POST -Body $body -ContentType "application/json"
```

期望返回包含 `message`（AI 回复）、`conversation_id`（会话 ID）、`tokens_used`。

### 前端页面测试

```powershell
@("/", "/chat", "/video", "/equipment", "/learning", "/training", "/social") | ForEach-Object {
    $r = Invoke-WebRequest -Uri "http://localhost$_" -UseBasicParsing
    Write-Host "GET $_ : $($r.StatusCode)"
}
# 期望: 全部返回 200
```

### 监控验证

```powershell
# Prometheus targets
Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" |
    Select-Object -ExpandProperty data |
    Select-Object -ExpandProperty activeTargets |
    ForEach-Object { Write-Host "$($_.labels.job): $($_.health)" }
# 期望: pingpong-api: up, prometheus: up

# Grafana 健康
Invoke-RestMethod -Uri "http://localhost:3000/api/health"
# 期望: {"database":"ok","version":"10.2.2",...}
```

---

## 访问方式

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端首页 | http://localhost | Nginx 代理 |
| API 文档 (Swagger) | http://localhost:8001/docs | 直连 API |
| API 文档 (ReDoc) | http://localhost:8001/redoc | 直连 API |
| Prometheus | http://localhost:9090 | 指标查询 |
| Grafana | http://localhost:3000 | 用户名 admin，密码见 `.env.production` |

---

## 常用运维命令

### 服务管理

```powershell
# 查看所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 停止所有服务
docker compose -f docker/docker-compose.prod.yml down

# 停止并删除数据卷（慎用！会丢失数据库和日志）
docker compose -f docker/docker-compose.prod.yml down -v

# 重启单个服务
docker compose -f docker/docker-compose.prod.yml restart pingpong-api

# 仅重建并重启 API（代码变更后）
docker compose -f docker/docker-compose.prod.yml up -d --build pingpong-api
```

### 日志查看

```powershell
# API 日志（实时跟踪）
docker logs pingpong-api -f --tail 50

# Nginx 访问日志
docker logs pingpong-nginx -f --tail 50

# 查看特定容器的所有日志
docker logs pingpong-api 2>&1 | Select-String "ERROR"
```

### 数据库操作

```powershell
# 进入容器查看数据库
docker exec -it pingpong-api python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/pingpong_prod.db')
tables = conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()
print([t[0] for t in tables])
conn.close()
"

# 备份数据库
docker cp pingpong-api:/app/data/pingpong_prod.db ./backup_prod.db
```

### GPU 状态监控

```powershell
# 查看容器内 GPU 使用情况
docker exec pingpong-api python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device: {torch.cuda.get_device_name(0)}')
print(f'Memory: {torch.cuda.memory_allocated(0)/1024**3:.2f}/{torch.cuda.get_device_properties(0).total_mem/1024**3:.2f} GB')
"
```

### 镜像维护

```powershell
# 查看镜像大小
docker images pingpong-api

# 清理无用的构建缓存
docker builder prune -f

# 清理悬空镜像
docker image prune -f
```

---

## 已知问题与注意事项

### 1. 双 Worker 模式 POST 路由 404

**问题**: `--workers 2` 时，POST 请求（如 `/api/llm/chat`）偶发 404，GET 请求正常。

**临时方案**: 当前设为 `--workers 1`。

**根因分析**: 疑似 uvicorn 多进程模式下 FastAPI 路由注册不一致，或与 SQLite 单文件数据库并发访问有关。后续若需多 worker，建议：
- 切换到 Gunicorn + UvicornWorker
- 或切换数据库为 PostgreSQL

### 2. Embedding 模型首次加载延迟

**问题**: 首次调用 LLM chat 时需要下载 `sentence-transformers/all-MiniLM-L6-v2`（约 90MB），会有约 10-30 秒延迟。

**建议**: 后续可在 Dockerfile 中预下载模型，或在应用启动时（lifespan）预加载。

### 3. SQLite 并发限制

**问题**: SQLite 是单文件数据库，不支持高并发写入。

**影响范围**: 本地开发和单用户使用没有问题；多用户并发场景建议迁移到 PostgreSQL。

### 4. HTTPS 未配置

**现状**: Nginx 监听 443 端口但未配置 SSL 证书，仅 HTTP (80) 可用。

**本地使用**: 通过 `http://localhost` 访问，无安全风险。如需 HTTPS，可配置自签名证书或使用 mkcert 工具。

### 5. Windows 路径注意事项

Docker Desktop 通过 WSL2 运行 Linux 容器，`docker-compose.prod.yml` 中的 volume 路径使用相对路径（如 `../external:/app/external:ro`）。在 Windows 上这些路径会自动转换，一般无需手动处理。
