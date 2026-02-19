# Pingpong AI Platform

## 项目概述
模块化乒乓球 AI 平台，6 个核心模块：
LLM 学习助手 | 球体追踪 (BlurBall+TT3D) | 装备推荐 | 社交媒体问答 | 学习资源 | 训练分析

## 硬件环境
- GPU: NVIDIA RTX 4080 Super (16GB VRAM)
- CUDA: 12.4
- OS: Windows 10
- Python: 3.11 (conda env: pingpong_ai)
- PyTorch: 2.5.1+cu124

## 环境管理
- Conda 环境: pingpong_ai (python=3.11)
- 激活命令: conda activate pingpong_ai
- 所有 pip install 必须在 pingpong_ai 环境中执行
- 禁止使用 --break-system-packages 安装到系统 Python

## 技术栈
- Backend: FastAPI + uvicorn + pydantic-settings
- LLM: OpenAI API (gpt-4o-mini)，不跑本地大模型
- Embedding: sentence-transformers (all-MiniLM-L6-v2)，全模块共享
- 向量库: FAISS CPU 模式
- CV: BlurBall (HRNet-W48) + TT3D + RTMPose + MotionBert
- Database: SQLite + aiosqlite (开发阶段)
- 日志: loguru
- 认证: python-jose JWT
- 容器: Docker + nvidia/cuda:12.4.1 基础镜像

## 项目结构约定
- app/ 下每个模块有 core/（业务逻辑）和 api/（路由）两层
- 外部依赖仓库放 external/ (BlurBall, tt3d)
- 共享工具在 app/shared/（含 gpu_manager.py）
- 所有 API router 注册到 app/main.py
- FAISS 索引统一存放 app/vectorstore/
- 外部依赖仓库 BlurBall 和 TT3D 通过 git clone 放在 external/，代码中通过 sys.path 或相对导入引用

## 显存管理规则（重要）
- CV 模型串行加载：BlurBall → RTMPose → MotionBert，不同时占 GPU
- LLM 全部走云端 API，不占本地显存
- Embedding 模型常驻内存 (~0.5GB)，其余按需加载/卸载
- 使用 shared/gpu_manager.py 管理模型生命周期
- 每次推理后调用 torch.cuda.empty_cache()

## 编码规范
- Python type hints 必须写
- 每个 API endpoint 写中文 docstring
- 函数和变量用英文命名，注释用中文
- 每个模块独立可测试
- 异步优先: API 层用 async def
- 敏感配置（API keys 等）统一用 .env 文件管理，通过 config/settings.py 的 pydantic-settings 读取，禁止硬编码到代码中

## 开发顺序
Phase 1: 基础架构 → Phase 2: LLM/RAG → Phase 3: Ball Tracking (BlurBall+TT3D)
→ Phase 4: Equipment → Phase 5: Social Media
→ Phase 6: Learning Resources → Phase 7: Training Analysis
→ Phase 8: Frontend → Phase 9: 测试 → Phase 10: 部署

## 常用命令
- 启动: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
- 测试: pytest tests/ -v
- Lint: ruff check .
- Docker 构建: docker compose -f docker/docker-compose.prod.yml build
- Docker 启动: docker compose -f docker/docker-compose.prod.yml up -d
- Docker 状态: docker ps --format "table {{.Names}}\t{{.Status}}"
- Docker 日志: docker logs pingpong-api --tail 50

## 当前进度（2026-02-19）

### 已完成
- Phase 1-10 全部开发完成，191 个 API 路由，前端 11 个页面
- 本地 Docker Desktop 部署完成，4 容器全部 healthy：
  - pingpong-api (FastAPI, port 8001:8000)
  - pingpong-nginx (反向代理, port 80)
  - pingpong-prometheus (监控, port 9090)
  - pingpong-grafana (仪表盘, port 3000)
- 部署过程中修复 3 个 bug：
  1. Dockerfile COPY 错误：external/ → frontend/（前端文件缺失导致 404）
  2. health.py async generator 误用：get_db_session() 不能直接 async with，改用 get_session_factory()
  3. 非 root 用户缺 home 目录：useradd 加 -m -d /home/pingpong，解决 HuggingFace 模型缓存权限问题
- 全部技术文档完成并推送 GitHub：
  - documents/phase1_infrastructure_guide.md ~ phase10_deployment.md（共 10 份）
  - documents/windows_docker_desktop.md（Docker 部署指南，含原理深度讲解）
  - README.md 已重写（项目概览、架构图、Quick Start、API 总览、统计）
- Git 远程: origin → https://github.com/Kevin11Kaikai/pingpong_ai_platform.git
- 分支: master (本地) → PingPong_2026 (远程跟踪)

### 已知问题
- 多 worker 404 bug：Uvicorn --workers 2 时 POST /api/llm/chat 间歇性 404，临时改为 --workers 1 规避。根因疑似多进程路由注册不一致，需切 Gunicorn+UvicornWorker 或迁移 PostgreSQL
- Embedding 模型未预加载：首次调用有延迟，/api/health/full 显示 embedding 组件 degraded
- 部分端点返回 404：/api/social-media/topics 和 /api/learning/profiles/test-user，疑似缺少数据 seeding 或模块初始化

### 下一步可选
- 修复多 worker bug（Gunicorn 适配或路由注册审查）
- Embedding 启动时预加载（消除 degraded 状态）
- HTTPS 配置（Let's Encrypt / self-signed）
- 数据 seeding 脚本（补全 social-media 和 learning 初始数据）
- 云服务器部署（如果有远程 Linux 机器）