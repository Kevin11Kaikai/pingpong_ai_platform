# Windows 10 + Docker Desktop 本地部署指南

## 概述

本文档记录在 **Windows 10 + Docker Desktop + NVIDIA RTX 4080 Super** 环境下，将 Pingpong AI Platform 以生产级 Docker 容器方式本地部署的完整流程，包括遇到的 3 个 bug 及其修复方案。

## 目录

1. [Docker 基础概念](#docker-基础概念)
2. [Windows 上的 Docker 技术栈](#windows-上的-docker-技术栈)
3. [环境要求](#环境要求)
4. [环境验证](#环境验证)
5. [部署架构](#部署架构)
6. [核心配置文件详解](#核心配置文件详解)
7. [部署步骤](#部署步骤)
8. [构建与启动过程详解](#构建与启动过程详解)
9. [Bug 修复记录](#bug-修复记录)
10. [服务验证](#服务验证)
11. [访问方式](#访问方式)
12. [常用运维命令](#常用运维命令)
13. [已知问题与注意事项](#已知问题与注意事项)

---

## Docker 基础概念

### Docker 是什么？解决什么问题？

Docker 是一个**容器化平台**。它解决的核心问题是："在我电脑上能跑，到你电脑上就跑不了"。

传统部署的痛点：

- Python 版本不同（3.9 vs 3.11）
- 系统库缺失（libgl、libglib 等 OpenCV 依赖）
- CUDA 版本冲突（12.1 vs 12.4）
- 依赖包版本冲突
- 配置文件路径不同

Docker 的解决方案：**把应用 + 运行环境 + 依赖 + 配置打包成一个标准化的"容器"**，在任何安装了 Docker 的机器上都能以相同方式运行。

### 核心术语

```
┌─────────────────────────────────────────────────────────┐
│                    Docker 概念关系图                       │
│                                                         │
│  Dockerfile ──(build)──> Image ──(run)──> Container     │
│  (菜谱)                  (菜品模板)        (端上桌的菜)     │
│                                                         │
│  docker-compose.yml ──(up)──> 多个 Container 协同运行     │
│  (宴会菜单)                    (一桌完整的菜)              │
└─────────────────────────────────────────────────────────┘
```

| 概念 | 类比 | 说明 |
|------|------|------|
| **Image（镜像）** | 安装光盘 | 只读模板，包含 OS + 运行时 + 应用代码 + 依赖。可以从一个镜像启动多个容器 |
| **Container（容器）** | 运行中的虚拟机（但更轻量） | 镜像的运行实例。有自己的文件系统、网络、进程空间，但与宿主机共享 Linux 内核 |
| **Dockerfile** | 安装脚本 | 描述如何一步步构建镜像的文本文件。每条指令创建一个"层" |
| **Docker Compose** | 编排脚本 | 用 YAML 描述多个容器如何协同工作（网络、依赖顺序、端口、存储） |
| **Volume（卷）** | 外接硬盘 | 容器被删除后数据仍然保留的持久化存储。不随容器生命周期消失 |
| **Network（网络）** | 局域网 | 容器之间通过网络名互相访问（如 `pingpong-api:8000`），与宿主机隔离 |
| **Registry（仓库）** | 应用商店 | 存储和分发镜像的服务（如 Docker Hub、GitHub Container Registry） |

### 容器 vs 虚拟机

```
┌──────────────────────┐    ┌──────────────────────┐
│    虚拟机 (VM)         │    │    容器 (Container)    │
│                      │    │                      │
│  ┌────┐ ┌────┐      │    │  ┌────┐ ┌────┐      │
│  │App1│ │App2│      │    │  │App1│ │App2│      │
│  ├────┤ ├────┤      │    │  ├────┤ ├────┤      │
│  │Libs│ │Libs│      │    │  │Libs│ │Libs│      │
│  ├────┤ ├────┤      │    │  └──┬─┘ └─┬──┘      │
│  │ OS │ │ OS │ ← 每个 VM  │     └──┬──┘         │
│  └──┬─┘ └─┬──┘   都有完整OS│        │            │
│     └──┬──┘      │    │   Docker Engine        │
│   Hypervisor     │    │        │               │
│        │         │    │   宿主机 OS (共享内核)    │ ← 共享内核，轻量
│   宿主机 OS       │    │        │               │
│        │         │    │      硬件               │
│      硬件         │    └──────────────────────┘
└──────────────────────┘

启动: 分钟级               启动: 秒级
大小: GB 级                大小: MB 级
```

**本项目为什么选 Docker 而不是直接部署？**

- GPU 环境配置复杂：CUDA 12.4 + cuDNN + PyTorch 的兼容组合很难手动配对
- 多服务编排：4 个服务（API、Nginx、Prometheus、Grafana）需要协同工作
- 环境一致性：开发机部署和未来服务器部署使用相同配置
- 一键回滚：出问题直接 `docker compose down && docker compose up` 恢复

---

## Windows 上的 Docker 技术栈

### 整体架构

Windows 不能原生运行 Linux 容器（Docker 容器本质是 Linux 进程）。Docker Desktop 通过 WSL2（Windows Subsystem for Linux 2）解决这个问题：

```
┌──────────────────────────────────────────────────────────────┐
│                     Windows 10 宿主机                          │
│                                                              │
│  ┌─────────────┐     ┌─────────────────────────────────┐    │
│  │ PowerShell  │     │         WSL2 虚拟机               │    │
│  │ docker CLI  │────>│  ┌─────────────────────────┐    │    │
│  │ 浏览器       │     │  │   Docker Engine (dockerd) │    │    │
│  └─────────────┘     │  │                         │    │    │
│                      │  │  ┌─────┐ ┌─────┐       │    │    │
│                      │  │  │API  │ │Nginx│ ...   │    │    │
│                      │  │  │容器  │ │容器  │       │    │    │
│                      │  │  └──┬──┘ └─────┘       │    │    │
│                      │  └────┼────────────────────┘    │    │
│                      │       │                         │    │
│                      │  Linux 内核 (真正的内核，非模拟)    │    │
│                      └───────┼─────────────────────────┘    │
│                              │                              │
│  ┌───────────────────────────┼────────────────────────┐     │
│  │              NVIDIA GPU Driver (Windows)            │     │
│  │              GPU 驱动同时暴露给 Windows 和 WSL2       │     │
│  └───────────────────────────┼────────────────────────┘     │
│                              │                              │
│                    ┌─────────┴──────────┐                   │
│                    │ NVIDIA RTX 4080 S   │                   │
│                    │ 16GB VRAM           │                   │
│                    └────────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

### 关键技术点

**WSL2 是什么？**

WSL2（Windows Subsystem for Linux 2）是微软在 Windows 中嵌入的一个轻量级 Linux 虚拟机。与传统 VM 不同，它由 Windows 直接管理，启动快、资源共享好。Docker Desktop 利用 WSL2 的 Linux 内核来运行 Linux 容器。

**GPU 透传链路：**

```
容器内 PyTorch 调用 CUDA
    ↓
容器内 CUDA Runtime (nvidia/cuda 镜像自带)
    ↓
Docker --gpus all 参数将 /dev/nvidia* 设备映射进容器
    ↓
WSL2 内核的 NVIDIA 驱动模块
    ↓
Windows 宿主机 NVIDIA 驱动 (566.14)
    ↓
RTX 4080 Super 硬件
```

**为什么 Windows 上不需要安装 NVIDIA Container Toolkit？**

在 Linux 服务器上，需要单独安装 `nvidia-container-toolkit` 来让 Docker 访问 GPU。但在 Windows 上，Docker Desktop 内置了 GPU 支持：Windows NVIDIA 驱动会自动将 GPU 暴露给 WSL2，Docker Desktop 的 WSL2 后端直接使用它。

**端口映射原理：**

```
浏览器访问 http://localhost:80
    ↓
Windows 监听 0.0.0.0:80
    ↓
Docker Desktop 将端口转发到 WSL2 中的容器
    ↓
Nginx 容器 (0.0.0.0:80)
    ↓
通过 Docker 内部网络转发到 pingpong-api:8000
```

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

## 核心配置文件详解

本项目的 Docker 配置涉及 5 个关键文件，它们各自承担不同职责：

```
docker/
├── .dockerignore          ← 构建时忽略哪些文件（减小镜像体积）
├── Dockerfile.prod        ← 如何构建 API 镜像（安装依赖、打包代码）
├── docker-compose.prod.yml ← 如何编排 4 个容器协同运行
├── nginx/
│   └── nginx.conf         ← Nginx 反向代理配置
└── prometheus/
    └── prometheus.yml     ← Prometheus 指标采集配置
```

### 5.1 Dockerfile.prod 逐行解析

Dockerfile 是一个"构建脚本"，Docker 按顺序执行每条指令，每条指令生成一个"层"（layer），最终叠加成镜像。

本项目采用**多阶段构建（multi-stage build）**：先在一个"胖"环境里编译安装依赖，再把成果复制到"瘦"环境中运行，最终镜像不包含编译工具，体积更小。

```
┌───────────────────────────────────┐
│  Stage 1: builder                 │
│  基础镜像: cuda:12.4.1-devel      │  ← 包含 CUDA 编译工具（devel = development）
│  安装: Python 3.11, pip, 编译工具  │
│  产物: /opt/venv (含所有 Python 包)│
└───────────────┬───────────────────┘
                │ COPY --from=builder /opt/venv
                ▼
┌───────────────────────────────────┐
│  Stage 2: runtime                 │
│  基础镜像: cuda:12.4.1-runtime    │  ← 只有 CUDA 运行时（runtime），无编译器
│  复制: venv + 应用代码 + 前端      │
│  用户: pingpong (非 root)         │
│  最终产物: 可运行的镜像             │
└───────────────────────────────────┘
```

**逐行详解：**

```dockerfile
# === Stage 1: Builder ===
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS builder
```

`FROM` 指定基础镜像。`nvidia/cuda:12.4.1-devel-ubuntu22.04` 是 NVIDIA 官方镜像，包含 CUDA 12.4.1 开发工具和 Ubuntu 22.04 系统。`AS builder` 给这个阶段命名，后面的阶段可以从中复制文件。

```dockerfile
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
```

`ENV` 设置环境变量：
- `DEBIAN_FRONTEND=noninteractive`：apt-get 安装时不弹出交互式对话框
- `PYTHONUNBUFFERED=1`：Python 输出不缓冲，日志实时可见
- `PYTHONDONTWRITEBYTECODE=1`：不生成 `__pycache__`，减少镜像体积
- `PIP_NO_CACHE_DIR=1`：pip 不缓存下载包，减少镜像体积
- `PIP_DISABLE_PIP_VERSION_CHECK=1`：跳过 pip 版本检查，加速安装

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip build-essential \
    && rm -rf /var/lib/apt/lists/*
```

`RUN` 在镜像内执行命令。这里安装 Python 3.11 和编译工具（`build-essential` 包含 gcc 等，用于编译 C 扩展的 Python 包如 `cffi`）。`rm -rf /var/lib/apt/lists/*` 清理 apt 缓存，减少层的大小。

```dockerfile
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
```

创建 Python 虚拟环境在 `/opt/venv`，然后把它加到 PATH。后续 `pip install` 都安装到这个 venv 里。使用 venv 而不是系统 Python 的好处：可以干净地复制到下一阶段。

```dockerfile
WORKDIR /build
COPY requirements.txt requirements-gpu.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-gpu.txt && \
    pip install prometheus-client>=0.19.0
```

- `WORKDIR`：设置工作目录（类似 `cd`，不存在会自动创建）
- `COPY`：把宿主机的文件复制进镜像。**先复制 requirements.txt 再安装**是一个优化技巧——如果 requirements.txt 没变，Docker 会使用缓存层，不重新下载依赖（节省 15 分钟）
- `RUN pip install`：安装所有 Python 依赖。`requirements.txt` 是通用依赖，`requirements-gpu.txt` 是 PyTorch + CUDA 专用依赖

```dockerfile
# === Stage 2: Runtime ===
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS runtime
```

第二阶段用更小的 `runtime` 镜像（没有编译器，只有 CUDA 运行时）。

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 libgl1-mesa-glx libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/* && apt-get clean
```

安装运行时必需的系统库：
- `python3.11`：Python 解释器
- `libgl1-mesa-glx` + `libglib2.0-0`：OpenCV 的运行时依赖（没有这两个 `import cv2` 会报错）
- `curl`：用于健康检查（`HEALTHCHECK` 指令需要）

```dockerfile
RUN groupadd -r pingpong && useradd -r -g pingpong -m -d /home/pingpong pingpong
```

创建非 root 用户。生产容器不应以 root 运行（安全最佳实践）。`-m -d /home/pingpong` 创建 home 目录（Bug 3 的修复）。

```dockerfile
COPY --from=builder /opt/venv /opt/venv
```

**多阶段构建的关键**：从 builder 阶段复制已编译好的 Python 虚拟环境。builder 阶段的其他内容（编译器、源码、apt 缓存）全部丢弃。

```dockerfile
WORKDIR /app
RUN mkdir -p /app/data /app/logs /app/app/vectorstore && \
    chown -R pingpong:pingpong /app
```

创建数据目录并设置权限。`chown` 让 pingpong 用户拥有这些目录的写入权限。

```dockerfile
COPY --chown=pingpong:pingpong app/ ./app/
COPY --chown=pingpong:pingpong config/ ./config/
COPY --chown=pingpong:pingpong frontend/ ./frontend/
```

复制应用代码进镜像。`--chown=pingpong:pingpong` 确保文件属于非 root 用户。注意这里**不复制 `external/`**（CV 模型权重文件太大，通过 volume 挂载）。

```dockerfile
USER pingpong
EXPOSE 8000
```

切换到非 root 用户运行。`EXPOSE 8000` 声明容器监听 8000 端口（文档作用，实际端口映射由 docker-compose 控制）。

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1
```

Docker 内置健康检查：
- 每 30 秒检查一次
- 超时 10 秒算失败
- 启动后 60 秒内不检查（等待应用初始化）
- 连续失败 3 次标记为 unhealthy
- 检查方式：curl 访问健康端点，返回非 200 则失败

```dockerfile
CMD ["python3", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
```

容器启动命令：
- `uvicorn app.main:app`：启动 FastAPI 应用
- `--host 0.0.0.0`：监听所有网络接口（不只是 localhost）
- `--port 8000`：监听端口
- `--workers 1`：单进程（避免多 worker 的 404 bug）
- `--proxy-headers`：信任 Nginx 传递的 `X-Forwarded-For` 等头
- `--forwarded-allow-ips *`：允许任何 IP 的代理头

### 5.2 docker-compose.prod.yml 逐字段解析

Docker Compose 用 YAML 文件描述多个容器如何协同工作。一个 `docker compose up` 就能启动整个系统。

**pingpong-api 服务（核心）：**

```yaml
pingpong-api:
  build:                          # 如何构建镜像
    context: ..                   # 构建上下文 = 项目根目录（Dockerfile 中 COPY 相对于此）
    dockerfile: docker/Dockerfile.prod  # 使用哪个 Dockerfile
  image: pingpong-api:latest      # 构建后的镜像名和标签
  container_name: pingpong-api    # 容器名（docker ps 中显示的名字）
  ports:
    - "8001:8000"                 # 宿主机 8001 端口 → 容器 8000 端口
  volumes:
    - pingpong-data:/app/data           # 命名卷：数据库持久化
    - pingpong-logs:/app/logs           # 命名卷：日志持久化
    - pingpong-vectorstore:/app/app/vectorstore  # 命名卷：FAISS 索引
    - ../external:/app/external:ro      # 绑定挂载：模型权重（:ro = 只读）
  env_file:
    - ../.env.production          # 从文件加载环境变量（API key、数据库 URL 等）
  environment:
    - APP_ENV=production          # 额外环境变量（覆盖 env_file 中同名变量）
    - PROMETHEUS_ENABLED=true
  deploy:
    resources:
      limits:
        cpus: "4"                 # CPU 限制：最多 4 核
        memory: 8G                # 内存限制：最多 8GB
      reservations:
        devices:
          - driver: nvidia        # GPU 设备预留
            count: 1              # 使用 1 块 GPU
            capabilities: [gpu]   # 需要 GPU 计算能力
  restart: unless-stopped         # 崩溃自动重启（除非手动 stop）
  networks:
    - pingpong-network            # 加入自定义网络
  healthcheck:                    # 健康检查（与 Dockerfile 中的互相覆盖，compose 优先）
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
    interval: 30s
    timeout: 10s
    start_period: 60s
    retries: 3
```

**Nginx 服务（反向代理）：**

```yaml
nginx:
  image: nginx:1.25-alpine       # 使用官方 Nginx Alpine 镜像（轻量，~40MB）
  ports:
    - "80:80"                     # HTTP
    - "443:443"                   # HTTPS（预留）
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro  # 绑定挂载配置文件（只读）
    - nginx-logs:/var/log/nginx   # 日志持久化
  depends_on:
    pingpong-api:
      condition: service_healthy  # 关键：等 API 健康检查通过后才启动 Nginx
  restart: unless-stopped
```

`depends_on` + `condition: service_healthy` 确保启动顺序：API 必须先就绪，Nginx 才启动。否则 Nginx 启动时连不上上游，会直接报错退出。

**Prometheus 服务（监控）：**

```yaml
prometheus:
  image: prom/prometheus:v2.48.0
  command:                        # 覆盖默认启动命令
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.path=/prometheus"
    - "--storage.tsdb.retention.time=15d"   # 数据保留 15 天
    - "--web.enable-lifecycle"              # 允许热重载配置
  depends_on:
    pingpong-api:
      condition: service_healthy  # 同样等 API 就绪
```

**Grafana 服务（仪表盘）：**

```yaml
grafana:
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
    # ${VAR:-default} 语法：从 .env.production 读取，读不到用 "admin"
  depends_on:
    - prometheus                  # 简单依赖（不等健康检查，只等启动）
```

**Networks 和 Volumes：**

```yaml
networks:
  pingpong-network:
    driver: bridge     # 桥接网络：容器之间用容器名互相访问
                       # 例如 Nginx 配置中 `proxy_pass http://pingpong-api:8000`
                       # Docker DNS 自动解析 "pingpong-api" 为该容器的内部 IP

volumes:
  pingpong-data:
    driver: local      # 本地存储。容器删除后 volume 保留
                       # docker compose down -v 才会删除 volume
```

### 5.3 .dockerignore 详解

`.dockerignore` 的作用类似 `.gitignore`，但针对的是 Docker 构建上下文。当执行 `docker build` 时，Docker 会把整个 context（项目根目录）发送给 Docker Engine，`.dockerignore` 排除不需要的文件，**减小发送量和镜像体积**。

```
# 排除的关键类别：
__pycache__/        ← Python 缓存（运行时会重新生成）
.env.production     ← 敏感配置（通过 env_file 在运行时挂载，不烧进镜像）
tests/              ← 测试代码（生产镜像不需要）
.git/               ← Git 历史（几十 MB 的无用数据）
*.pt, *.pth         ← 模型权重文件（通过 volume 挂载，不烧进镜像）
data/, logs/        ← 数据目录（通过 volume 持久化）
external/BlurBall/  ← CV 外部仓库（通过 volume 挂载）
docker/             ← Docker 配置本身（不需要打进应用镜像）
```

排除 `.env.production` 特别重要：**绝对不能把 API Key 等敏感信息烧进镜像**。镜像可能被推送到 Registry，任何人 `docker pull` 后都能提取其中的文件。

### 5.4 nginx.conf 详解

Nginx 在架构中充当**反向代理**（Reverse Proxy）：浏览器不直接访问 FastAPI，而是通过 Nginx 中转。

```
浏览器 ──→ Nginx (:80) ──→ FastAPI (:8000)
                │
                ├─ 添加安全头（X-Frame-Options 等）
                ├─ 限流（每个 IP 最多 10 请求/秒）
                ├─ Gzip 压缩响应
                ├─ 支持 500MB 大文件上传
                └─ 隐藏后端服务器细节
```

**关键配置解释：**

```nginx
upstream pingpong_api {
    server pingpong-api:8000;    # Docker 网络中，用容器名代替 IP
    keepalive 32;                # 保持 32 个长连接，避免频繁建立 TCP 连接
}

limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
# 基于客户端 IP 限流：每个 IP 每秒最多 10 个请求
# $binary_remote_addr = 客户端 IP 的二进制形式（节省内存）
# zone=api_limit:10m = 用 10MB 内存存储限流状态

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # burst=20: 允许突发 20 个请求（令牌桶算法）
    # nodelay: 突发请求立即处理，不排队

    proxy_pass http://pingpong_api;
    # 转发请求到上游服务（FastAPI）

    proxy_set_header X-Real-IP $remote_addr;
    # 把客户端真实 IP 传给后端（否则后端看到的是 Nginx 的 IP）

    proxy_http_version 1.1;
    proxy_set_header Connection "";
    # 使用 HTTP 1.1 + 清空 Connection 头 = 启用 keepalive
}
```

**为什么视频上传有单独的 location 块？**

```nginx
location /api/ball-tracking/upload {
    limit_req zone=upload_limit burst=5 nodelay;  # 更严格：1 请求/秒
    proxy_send_timeout 600s;                       # 10 分钟超时（大文件慢传）
    proxy_read_timeout 600s;
}
```

视频文件可能几百 MB，上传和处理都很慢，需要更长的超时时间，同时限制上传频率防止滥用。

### 5.5 prometheus.yml 详解

Prometheus 是**拉取式（pull）**监控系统：它主动定期访问目标的 `/metrics` 端点收集数据。

```yaml
scrape_configs:
  - job_name: "pingpong-api"
    static_configs:
      - targets: ["pingpong-api:8000"]  # Prometheus 每 10 秒访问这个地址
    scrape_interval: 10s
    metrics_path: /metrics              # 访问 http://pingpong-api:8000/metrics
```

FastAPI 应用通过 `MetricsMiddleware` 在 `/metrics` 端点暴露指标（请求计数、延迟分布、错误率等），Prometheus 定期采集并存入时序数据库，Grafana 从 Prometheus 查询数据并绘制图表。

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

## 构建与启动过程详解

### `docker compose build` 内部发生了什么？

当你运行 `docker compose -f docker/docker-compose.prod.yml build pingpong-api` 时，以下过程依次发生：

```
Step 1: 准备构建上下文
──────────────────────────
Docker 读取 docker-compose.prod.yml 中 build.context = ".."（项目根目录）
Docker 读取 docker/.dockerignore，按规则排除文件
将剩余文件打包发送给 Docker Engine（在 WSL2 中运行）

Step 2: 解析 Dockerfile，执行 Stage 1 (builder)
──────────────────────────────────────────────────
[1/6] FROM nvidia/cuda:12.4.1-devel-ubuntu22.04
      → 从 Docker Hub 拉取 NVIDIA CUDA 开发镜像（~3.5GB，含编译器）
      → 首次拉取需要下载，后续使用本地缓存

[2/6] RUN apt-get update && apt-get install python3.11 ...
      → 在临时容器中执行 apt 安装
      → 产生一个新的镜像层（~200MB）

[3/6] RUN python3.11 -m venv /opt/venv
      → 创建虚拟环境（~15MB）

[4/6] WORKDIR /build
      → 设置工作目录（元数据变更，几乎无大小）

[5/6] COPY requirements.txt requirements-gpu.txt ./
      → 复制依赖声明文件（~2KB）
      → 这里的技巧：先 COPY 依赖文件，再 RUN pip install
        如果依赖没变，Docker 可以跳过 pip install 步骤（缓存命中）

[6/6] RUN pip install ...
      → 下载并安装所有 Python 包
      → PyTorch (915MB) + CUDA 库 (~3GB) + 其他依赖 (~500MB)
      → 这是最耗时的步骤（~10 分钟）
      → 产生的层很大（~8GB），但只要 requirements 不变就会被缓存

Step 3: 执行 Stage 2 (runtime)
───────────────────────────────
[1/9] FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04
      → 拉取 CUDA 运行时镜像（~1.5GB，比 devel 小很多）

[2/9] RUN apt-get install python3.11 libgl1 curl ...
      → 安装运行时依赖（~100MB）

[3/9] RUN groupadd ... useradd ...
      → 创建用户（几 KB）

[4/9] COPY --from=builder /opt/venv /opt/venv
      → 从 Stage 1 复制编译好的 Python 环境（~5GB）
      → 这一步是多阶段构建的核心

[5/9] WORKDIR /app
[6/9] RUN mkdir -p ... && chown ...
[7/9] COPY app/ ./app/
[8/9] COPY config/ ./config/
[9/9] COPY frontend/ ./frontend/
      → 复制应用代码（~1MB）

Step 4: 导出镜像
─────────────────
将所有层合并，生成最终镜像 pingpong-api:latest
镜像大小约 15GB（虚拟大小），实际存储约 5GB（层共享 + 压缩）
```

**层缓存（Layer Caching）的工作原理：**

```
第一次构建：每步都执行                  第二次构建（只改了代码）：
                                      
[1] FROM cuda ... ──→ 执行           [1] FROM cuda ... ──→ ✓ CACHED
[2] RUN apt install ──→ 执行         [2] RUN apt install ──→ ✓ CACHED
[3] RUN venv ──→ 执行                [3] RUN venv ──→ ✓ CACHED
[4] COPY requirements ──→ 执行       [4] COPY requirements ──→ ✓ CACHED（文件没变）
[5] RUN pip install ──→ 执行(15min)  [5] RUN pip install ──→ ✓ CACHED（太好了！）
[6] COPY app/ ──→ 执行               [6] COPY app/ ──→ ✗ 变了，重新执行
[7] COPY config/ ──→ 执行            [7] COPY config/ ──→ ✗ 缓存失效，重新执行
[8] COPY frontend/ ──→ 执行          [8] COPY frontend/ ──→ ✗ 缓存失效，重新执行

总计: ~15 分钟                        总计: ~5 秒
```

**缓存失效规则**：一旦某一层失效（文件内容变了），它之后的所有层都必须重新构建。所以 Dockerfile 的指令顺序很重要——把变化频率低的（依赖安装）放前面，变化频率高的（代码复制）放后面。

### `docker compose up -d` 内部发生了什么？

```
Step 1: 读取 docker-compose.prod.yml
─────────────────────────────────────
解析所有 services、networks、volumes 定义
读取 .env.production 中的环境变量

Step 2: 创建 Network
──────────────────────
docker network create pingpong-network (bridge 模式)
→ 创建一个隔离的虚拟网络
→ 同一网络中的容器可以用容器名互相访问
→ 外部（宿主机）默认不能直接访问容器内部

Step 3: 创建 Volumes
──────────────────────
docker volume create pingpong-data
docker volume create pingpong-logs
docker volume create pingpong-vectorstore
docker volume create prometheus-data
docker volume create grafana-data
docker volume create nginx-logs
→ 6 个命名卷，数据存储在 Docker 管理的目录中
→ 容器删除后卷仍然保留（docker compose down -v 才删除）

Step 4: 启动容器（按依赖顺序）
───────────────────────────────

[Phase 1] pingpong-api 启动
  → docker create + docker start
  → 容器启动后 uvicorn 加载 FastAPI 应用
  → 初始化数据库（SQLite 建表）
  → HEALTHCHECK 开始计时（60s start_period 内不检查）
  → 60 秒后开始健康检查：curl http://localhost:8000/api/health/
  → 返回 200 → 标记为 healthy ✓

[Phase 2] pingpong-nginx 启动（depends_on: condition: service_healthy）
  → 看到 pingpong-api 已 healthy，开始启动
  → 加载 nginx.conf
  → 通过 Docker DNS 解析 "pingpong-api" 为内部 IP
  → 开始监听 80/443 端口

[Phase 2] pingpong-prometheus 启动（同样等 API healthy）
  → 加载 prometheus.yml
  → 开始每 10 秒抓取 http://pingpong-api:8000/metrics

[Phase 3] pingpong-grafana 启动（depends_on: prometheus，不等 healthy）
  → Prometheus 容器启动即可（不需要等 healthy）
  → 初始化 Grafana 数据库
  → 开始监听 3000 端口

Step 5: -d 参数的作用
──────────────────────
-d = detached（后台运行）
Docker Compose 启动所有容器后返回命令行
容器在后台持续运行
没有 -d 的话，所有容器的日志会输出到当前终端，Ctrl+C 会停止所有容器
```

### 容器间的网络通信

```
┌─────────────────────── pingpong-network (172.18.0.0/16) ────────────────────┐
│                                                                             │
│  pingpong-nginx          pingpong-api          pingpong-prometheus          │
│  172.18.0.4:80           172.18.0.2:8000       172.18.0.3:9090             │
│       │                       ▲  ▲                  │                      │
│       │   proxy_pass          │  │   GET /metrics    │                      │
│       └───────────────────────┘  └───────────────────┘                      │
│                                                                             │
│  容器间用 "容器名:端口" 互相访问                                               │
│  Docker 内置 DNS 自动解析容器名 → 内部 IP                                      │
└─────────────────────────────────────────────────────────────────────────────┘
        │                   │                    │               │
        │ ports: 80:80      │ ports: 8001:8000   │ ports: 9090   │ ports: 3000
        ▼                   ▼                    ▼               ▼
   宿主机 :80          宿主机 :8001          宿主机 :9090     宿主机 :3000
        │
        ▼
   浏览器访问 http://localhost
```

**`ports` vs `expose` 的区别：**
- `ports: "8001:8000"` → 宿主机 8001 端口映射到容器 8000 端口。**宿主机和外部都能访问**
- `expose: "8000"` → 只在 Docker 内部网络中暴露。**只有同网络的容器能访问，宿主机不能直接访问**

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
