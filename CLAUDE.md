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
- Docker: docker compose -f docker/docker-compose.yml up --build