# Phase 10: 部署指南

## 概述

本文档提供 Pingpong AI Platform 的完整部署指南，包括 Docker 部署、CI/CD 配置、监控设置和运维操作。

## 目录

1. [前置要求](#前置要求)
2. [快速开始](#快速开始)
3. [配置参考](#配置参考)
4. [部署架构](#部署架构)
5. [运维操作](#运维操作)
6. [监控使用](#监控使用)
7. [故障排查](#故障排查)
8. [安全注意事项](#安全注意事项)

---

## 前置要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4 核 | 8 核 |
| 内存 | 8 GB | 16 GB |
| GPU | NVIDIA GTX 1080 | NVIDIA RTX 4080 |
| 存储 | 50 GB SSD | 200 GB NVMe SSD |

### 软件要求

- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **NVIDIA Driver**: 535+
- **NVIDIA Container Toolkit**: 安装指南见下文

### 安装 NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

---

## 快速开始

### 1. 克隆代码

```bash
git clone https://github.com/your-org/pingpong-ai.git
cd pingpong-ai
```

### 2. 配置环境变量

```bash
# 复制生产环境模板
cp .env.production.example .env.production

# 编辑配置文件
nano .env.production
```

**必须配置的变量：**

```bash
# LLM API 密钥
LLM_API_KEY=your-actual-api-key

# JWT 密钥（使用以下命令生成）
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your-generated-jwt-secret

# Grafana 密码
GRAFANA_ADMIN_PASSWORD=your-grafana-password
```

### 3. 构建并启动

```bash
# 构建镜像
docker compose -f docker/docker-compose.prod.yml build

# 启动服务
docker compose -f docker/docker-compose.prod.yml up -d

# 查看状态
docker compose -f docker/docker-compose.prod.yml ps
```

### 4. 验证部署

```bash
# 检查健康状态
curl http://localhost/api/health/
curl http://localhost/api/health/full

# 检查 API 文档
curl http://localhost/docs
```

---

## 配置参考

### 环境变量完整列表

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `APP_ENV` | development | 运行环境 (development/production) |
| `DEBUG` | true | 调试模式 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `LLM_API_KEY` | (必填) | OpenAI 兼容 API 密钥 |
| `LLM_BASE_URL` | https://api.ohmygpt.com/v1 | API 基础 URL |
| `JWT_SECRET_KEY` | (必填) | JWT 签名密钥 |
| `DATABASE_URL` | sqlite+aiosqlite:///./data/pingpong.db | 数据库连接 |
| `PROMETHEUS_ENABLED` | false | 启用 Prometheus 指标 |
| `CORS_ORIGINS` | ["*"] | 允许的 CORS 源 |

### Docker Compose 服务

| 服务 | 端口 | 描述 |
|------|------|------|
| nginx | 80, 443 | 反向代理 |
| pingpong-api | 8000 (内部) | 主 API 服务 |
| prometheus | 9090 | 指标收集 |
| grafana | 3000 | 监控仪表盘 |

---

## 部署架构

```
                    ┌─────────────────────┐
                    │       Nginx         │
                    │   (Port 80/443)     │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────┐
│                   pingpong-api                      │
│                   (Port 8000)                       │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ FastAPI    │  │ Embedding  │  │ GPU Models   │  │
│  │ Endpoints  │  │ Service    │  │ (BlurBall)   │  │
│  └────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐    ┌───────────────┐
│   Prometheus  │    │    Grafana    │
│  (Port 9090)  │    │  (Port 3000)  │
└───────────────┘    └───────────────┘
```

### 数据卷

| 卷名 | 挂载点 | 用途 |
|------|--------|------|
| pingpong-data | /app/data | 数据库和上传文件 |
| pingpong-logs | /app/logs | 应用日志 |
| pingpong-vectorstore | /app/app/vectorstore | FAISS 索引 |
| prometheus-data | /prometheus | 指标数据 |
| grafana-data | /var/lib/grafana | Grafana 配置 |

---

## 运维操作

### 日志查看

```bash
# 查看所有服务日志
docker compose -f docker/docker-compose.prod.yml logs -f

# 查看特定服务日志
docker compose -f docker/docker-compose.prod.yml logs -f pingpong-api

# 查看最近 100 行日志
docker compose -f docker/docker-compose.prod.yml logs --tail=100 pingpong-api
```

### 重启服务

```bash
# 重启单个服务
docker compose -f docker/docker-compose.prod.yml restart pingpong-api

# 重启所有服务
docker compose -f docker/docker-compose.prod.yml restart
```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker compose -f docker/docker-compose.prod.yml up -d --build

# 清理旧镜像
docker image prune -f
```

### 数据备份

```bash
# 备份数据卷
docker run --rm \
  -v pingpong-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/data-$(date +%Y%m%d).tar.gz /data

# 备份数据库
docker compose -f docker/docker-compose.prod.yml exec pingpong-api \
  cp /app/data/pingpong_prod.db /app/data/backup/
```

### 扩容

```bash
# 增加 API 服务副本（需修改 docker-compose）
docker compose -f docker/docker-compose.prod.yml up -d --scale pingpong-api=3
```

---

## 监控使用

### 访问监控

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (默认 admin/admin)

### 常用指标

| 指标 | 类型 | 描述 |
|------|------|------|
| `pingpong_requests_total` | Counter | 请求总数 |
| `pingpong_request_latency_seconds` | Histogram | 请求延迟 |
| `pingpong_active_requests` | Gauge | 活跃请求数 |
| `pingpong_llm_requests_total` | Counter | LLM 调用计数 |
| `pingpong_video_processing_seconds` | Histogram | 视频处理时长 |
| `pingpong_gpu_memory_bytes` | Gauge | GPU 内存使用 |

### Grafana 配置数据源

1. 登录 Grafana (http://localhost:3000)
2. 进入 Configuration > Data Sources
3. 添加 Prometheus 数据源
4. URL: `http://prometheus:9090`
5. 点击 Save & Test

### 常用 PromQL 查询

```promql
# 请求速率 (每秒请求数)
rate(pingpong_requests_total[5m])

# 平均请求延迟
histogram_quantile(0.95, rate(pingpong_request_latency_seconds_bucket[5m]))

# 错误率
sum(rate(pingpong_requests_total{status=~"5.."}[5m])) / sum(rate(pingpong_requests_total[5m]))

# GPU 内存使用
pingpong_gpu_memory_bytes{type="allocated"}
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 检查日志
docker compose -f docker/docker-compose.prod.yml logs pingpong-api

# 检查端口占用
netstat -tlnp | grep 8000

# 检查 GPU
nvidia-smi
```

#### 2. GPU 不可用

```bash
# 验证 NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi

# 检查 Docker GPU 配置
docker info | grep -i nvidia
```

#### 3. 数据库连接失败

```bash
# 检查数据卷
docker volume inspect pingpong-data

# 检查数据库文件权限
docker compose -f docker/docker-compose.prod.yml exec pingpong-api ls -la /app/data/
```

#### 4. 健康检查失败

```bash
# 手动检查
curl -v http://localhost:8000/api/health/full

# 进入容器调试
docker compose -f docker/docker-compose.prod.yml exec pingpong-api bash
```

### 性能问题

```bash
# 检查资源使用
docker stats

# 检查容器日志是否有内存/CPU 警告
docker compose -f docker/docker-compose.prod.yml logs --tail=1000 | grep -i "memory\|cpu\|oom"
```

---

## 安全注意事项

### 生产环境检查清单

- [ ] 修改默认密码（Grafana admin）
- [ ] 配置强 JWT 密钥（至少 32 字节）
- [ ] 限制 CORS 源（不要使用 `["*"]`）
- [ ] 配置 HTTPS（添加 SSL 证书到 Nginx）
- [ ] 限制 Prometheus/Grafana 访问（内网或 VPN）
- [ ] 定期备份数据
- [ ] 设置日志轮转

### HTTPS 配置

在 `docker/nginx/nginx.conf` 中添加 SSL 配置：

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... 其他配置
}
```

### 防火墙规则

```bash
# 只开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # API 端口只通过 Nginx 访问
sudo ufw deny 9090/tcp  # Prometheus 内网访问
sudo ufw deny 3000/tcp  # Grafana 内网访问
```

---

## CI/CD 流水线

### GitHub Actions 配置

项目包含三个工作流：

1. **test.yml**: 每次 push/PR 运行测试和 lint
2. **build.yml**: push 到 main 时构建并推送 Docker 镜像
3. **deploy.yml**: 手动触发部署到 staging/production

### 配置 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets：

| Secret | 描述 |
|--------|------|
| `LLM_API_KEY` | LLM API 密钥（测试用） |
| `JWT_SECRET_KEY` | JWT 密钥（测试用） |
| `DEPLOY_HOST` | 部署服务器地址 |
| `DEPLOY_USER` | 部署服务器用户名 |
| `DEPLOY_SSH_KEY` | SSH 私钥 |

### 手动部署

```bash
# 在 GitHub Actions 页面
# 1. 选择 Deploy workflow
# 2. 点击 Run workflow
# 3. 选择环境 (staging/production)
# 4. 点击 Run
```

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2026-02 | 初始部署文档 |

---

## 联系支持

- **GitHub Issues**: https://github.com/your-org/pingpong-ai/issues
- **技术文档**: /documents/
