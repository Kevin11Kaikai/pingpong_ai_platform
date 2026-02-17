# 🏓 Pingpong AI Platform — 更新版开发计划

> **硬件环境**: 单机开发，NVIDIA RTX 4080 Super (16GB VRAM)
> **开发工具**: Claude Code + Skills + MCP
> **开发模式**: 单人/小团队快速迭代

---

## 📦 更新后项目架构

```
pingpong_ai_platform/
├── app/
│   ├── main.py                        # FastAPI entrypoint
│   ├── routers/                       # API routers
│   │   ├── llm.py
│   │   ├── tracking.py
│   │   ├── equipment.py
│   │   ├── social.py
│   │   ├── learning.py
│   │   └── analysis.py
│
│   ├── LLM/                           # LLM 智能学习助手
│   │   ├── core/
│   │   │   ├── data_loader.py             # PDF 加载 + OCR (PyMuPDF + pytesseract)
│   │   │   ├── vectorstore_builder.py     # FAISS 向量库构建
│   │   │   └── rag_chain.py               # RAG pipeline (LangChain)
│   │   ├── api/
│   │   │   └── chatbot.py
│   │   └── config.py
│
│   ├── Ball_Tracking/                 # 球体追踪系统 (BlurBall + TT3D)
│   │   ├── core/
│   │   │   ├── blurball_detector.py       # BlurBall 2D 检测 + 运动模糊估计
│   │   │   ├── tfort_fallback.py          # T-FORT 帧差法降级方案
│   │   │   ├── camera_calibration.py      # 相机标定 (PnP, 包装 TT3D)
│   │   │   ├── trajectory_3d.py           # 3D 轨迹重建 (包装 TT3D)
│   │   │   ├── bounce_detector.py         # 落点/弹跳点检测
│   │   │   └── spin_estimator.py          # 旋转类型估计
│   │   ├── api/
│   │   │   └── tracking_api.py
│   │   └── utils/
│   │       └── format_converter.py        # BlurBall→TT3D 格式转换
│
│   ├── Equipment_Recommendation/      # 装备推荐系统
│   │   ├── core/
│   │   │   ├── equipment_db.py            # 装备数据库 (SQLite + JSON)
│   │   │   ├── recommendation_engine.py   # 推荐算法 (基于规则 + 向量相似度)
│   │   │   └── user_profile.py            # 用户画像分析
│   │   └── api/
│   │       └── recommendation_api.py
│
│   ├── Social_Media/                  # 社交媒体问答
│   │   ├── core/
│   │   │   ├── forum_scraper.py           # Reddit PRAW 爬虫
│   │   │   ├── content_indexer.py         # FAISS 内容索引
│   │   │   └── hybrid_retriever.py        # RAG + 社区数据混合检索
│   │   └── api/
│   │       └── social_api.py
│
│   ├── Learning_Resources/            # 乒乓球学习资源
│   │   ├── core/
│   │   │   ├── resource_manager.py        # 资源 CRUD
│   │   │   ├── content_categorizer.py     # 内容分类 (基于 embedding 聚类)
│   │   │   └── search_engine.py           # FAISS 语义搜索
│   │   └── api/
│   │       └── resources_api.py
│
│   ├── Training_Analysis/             # 训练分析 (依赖 Ball_Tracking 输出)
│   │   ├── core/
│   │   │   ├── data_processor.py          # 轨迹数据处理
│   │   │   ├── performance_analyzer.py    # 技术统计分析
│   │   │   ├── improvement_suggestions.py # LLM 驱动的改进建议
│   │   │   └── session_manager.py         # 训练 session 管理
│   │   └── api/
│   │       └── analysis_api.py
│
│   ├── data/
│   │   ├── llm_data/                  # 乒乓球 PDF 资料
│   │   ├── ball_tracking_data/
│   │   │   ├── videos/                # 测试视频
│   │   │   └── weights/               # BlurBall + 对比模型权重
│   │   ├── equipment_data/            # 装备数据 JSON
│   │   ├── forum_data/                # 爬取的论坛数据
│   │   ├── learning_resources/        # 训练资料
│   │   └── training_data/             # 训练 session 数据
│
│   ├── vectorstore/                   # FAISS 索引 (统一管理)
│   │   ├── llm_index/
│   │   ├── forum_index/
│   │   └── equipment_index/
│
│   └── shared/
│       ├── database.py                # SQLite 连接 (开发阶段)
│       ├── gpu_manager.py             # GPU 显存管理工具
│       ├── auth.py                    # JWT 认证
│       └── utils.py
│
├── external/                          # 外部依赖仓库 (git submodule)
│   ├── BlurBall/                      # BlurBall 源码
│   └── tt3d/                          # TT3D 源码
│
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
│
├── config/
│   ├── .env.example
│   ├── settings.py                    # Pydantic Settings
│   └── logging.py
│
├── tests/
│   ├── test_llm/
│   ├── test_tracking/
│   ├── test_equipment/
│   ├── test_social/
│   ├── test_learning/
│   └── test_analysis/
│
├── scripts/
│   ├── setup_env.sh                   # 一键环境搭建
│   ├── download_weights.sh            # 下载所有预训练权重
│   ├── rebuild_vectorstore.py
│   └── convert_blurball_to_tt3d.py    # 格式转换工具
│
├── docker/
│   ├── Dockerfile                     # CUDA 12.x + Python 3.11
│   ├── docker-compose.yml             # app 单服务 (开发阶段)
│   └── nginx/
│
├── notebooks/
│   ├── blurball_experiments/          # BlurBall 检测实验
│   ├── rag_experiments/               # RAG 调参实验
│   └── analysis_experiments/
│
├── CLAUDE.md                          # Claude Code 项目记忆
├── .claude/
│   └── skills/                        # 自定义 Skills
│       ├── new-module/SKILL.md
│       ├── add-endpoint/SKILL.md
│       └── commit/SKILL.md
│
├── requirements.txt
├── requirements-gpu.txt               # PyTorch CUDA 12 + CV 依赖
├── requirements-dev.txt
└── README.md
```

---

## 🖥️ 硬件约束与 GPU 显存预算

### RTX 4080 Super 规格
- **显存**: 16GB GDDR6X
- **CUDA 核心**: 10240
- **适用场景**: 推理为主，轻量微调可行，大规模训练不现实

### 显存预算分配（模块不可同时加载）

| 模块 | 模型 | 显存占用 | 说明 |
|------|------|----------|------|
| Ball_Tracking | BlurBall (HRNet-W48) | ~4-6 GB | 1-step 推理更省显存 |
| Ball_Tracking | RTMPose (姿态估计) | ~2 GB | TT3D 依赖 |
| Ball_Tracking | MotionBert (3D 提升) | ~2 GB | TT3D 依赖 |
| LLM | OpenAI API (云端) | 0 GB | 不占本地显存 |
| LLM | FAISS 索引 | CPU / ~0.5 GB | 小规模数据用 CPU 即可 |
| Equipment | Embedding 模型 | ~0.5 GB | sentence-transformers |
| Social | Embedding 模型 | 共享上面的 | 复用同一个模型实例 |

### 关键设计原则

1. **模块间串行推理**: Ball_Tracking 的 3 个模型分步加载，不同时占显存
2. **LLM 走云端 API**: 使用 OpenAI/Claude API，不在本地跑大语言模型，节省全部显存给 CV 模块
3. **Embedding 模型统一**: 全平台使用同一个 `sentence-transformers` 模型（如 `all-MiniLM-L6-v2`，~0.5GB），LLM、Equipment、Social 三个模块共享
4. **GPU 显存管理器**: `shared/gpu_manager.py` 实现模型按需加载/卸载，避免 OOM

```python
# shared/gpu_manager.py 核心逻辑
# - 加载模型前先检查显存余量
# - 推理完成后主动释放: torch.cuda.empty_cache()
# - 提供 @gpu_managed 装饰器，自动管理模型生命周期
# - 同一时间只允许一个重型模型在 GPU 上
```

---

## 🚀 开发计划（单人/小团队，10-14周）

### Phase 1: 基础架构搭建 (Week 1)

**目标**: 项目骨架可运行，`uvicorn` 启动无报错

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `app/main.py` | FastAPI 入口 | CORS 配置，注册 6 个 router（先用占位），健康检查 `/health` |
| `config/settings.py` | 全局配置 | `pydantic-settings`，从 `.env` 读取 OpenAI key、DB path、GPU 设置 |
| `config/logging.py` | 日志 | `loguru`，按模块分文件记录 |
| `shared/database.py` | 数据库 | SQLite + `aiosqlite`（开发阶段够用，后期可切 PostgreSQL） |
| `shared/gpu_manager.py` | GPU 管理 | 显存检查、模型加载/卸载、OOM 防护 |
| `shared/auth.py` | 认证 | `python-jose` JWT，简单 token 验证 |
| `shared/utils.py` | 工具函数 | 文件路径处理、时间格式化等 |
| `requirements.txt` | 基础依赖 | fastapi, uvicorn, pydantic-settings, loguru, aiosqlite, python-jose |
| `requirements-gpu.txt` | GPU 依赖 | `torch==2.5.x+cu124`, torchvision, 具体版本锁定 |
| `docker/Dockerfile` | 容器 | `nvidia/cuda:12.4.1-runtime-ubuntu22.04` + Python 3.11 |
| `docker/docker-compose.yml` | 编排 | 单服务 + GPU 透传 (`runtime: nvidia`) |
| `.env.example` | 环境变量模板 | OPENAI_API_KEY, DB_PATH, LOG_LEVEL, CUDA_VISIBLE_DEVICES |
| `CLAUDE.md` | Claude Code 配置 | 项目概述、技术栈、编码规范、开发顺序 |

**验证标准**:
- `uvicorn app.main:app --reload` 启动成功
- `/health` 返回 `{"status": "ok", "gpu": "RTX 4080 Super", "vram_free": "16GB"}`
- Docker build 成功并能跑起来

**Claude Code Prompt**:
```
进入 Plan Mode。帮我搭建 Phase 1 基础架构:
- FastAPI main.py，CORS 允许所有来源（开发阶段），注册 6 个模块 router 的占位
- pydantic-settings 的 config/settings.py，从 .env 读配置
- SQLite 数据库连接 (aiosqlite)
- GPU 显存管理工具 (检查 CUDA 可用性、显存余量、模型加载/卸载)
- JWT 认证工具
- loguru 日志配置
- Dockerfile 基于 nvidia/cuda:12.4.1 + Python 3.11
- docker-compose.yml 单服务 + GPU 透传
先出计划，我确认后执行。
```

---

### Phase 2: LLM 智能学习助手 (Week 2-3)

**目标**: 上传乒乓球 PDF → 构建向量库 → 中文问答可用

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `LLM/core/data_loader.py` | PDF 加载 | `PyMuPDF (fitz)` 提取文本，`pytesseract` OCR 扫描件，`RecursiveCharacterTextSplitter` 分块 (chunk_size=1000, overlap=200) |
| `LLM/core/vectorstore_builder.py` | 向量库 | `OpenAIEmbeddings` (text-embedding-3-small)，FAISS `IndexFlatIP`，支持增量添加文档 |
| `LLM/core/rag_chain.py` | RAG 管线 | LangChain `RetrievalQA`，检索 top_k=5，中文 system prompt，引用来源标注 |
| `LLM/api/chatbot.py` | 聊天 API | SSE 流式响应，对话历史管理 (最近 10 轮)，FastAPI WebSocket 备选 |
| `LLM/config.py` | 配置 | OpenAI API key, model name (gpt-4o-mini 默认), temperature, max_tokens |

**技术决策**:
- **Embedding**: `text-embedding-3-small`（OpenAI 云端，不占 GPU）
- **LLM**: `gpt-4o-mini`（云端，成本低，中文能力够用）
- **向量库**: FAISS CPU 模式（PDF 数据量不大，CPU 足够，GPU 留给 CV）
- **OCR**: `pytesseract + chi_sim` 语言包（中文 PDF 支持）
- **不用本地 LLM**: 4080 Super 16GB 跑本地 LLM 会挤占 CV 模块显存

**验证标准**:
- 上传 3-5 份乒乓球 PDF，构建向量库成功
- 问 "正手拉球的要点是什么？" 得到带来源引用的中文回答
- SSE 流式输出延迟 < 2 秒首 token

---

### Phase 3: 球体追踪系统 — BlurBall + TT3D (Week 3-6)

**目标**: 上传转播视频 → 2D 球检测 → 3D 轨迹重建 → 落点/旋转分析

**这是最复杂的模块，分 4 个子阶段：**

#### 3.1 环境准备 & BlurBall 安装 (Week 3)

| 任务 | 技术细节 |
|------|----------|
| 克隆 BlurBall | `git clone https://github.com/cogsys-tuebingen/BlurBall.git external/BlurBall` |
| 克隆 TT3D | `git clone https://github.com/cogsys-tuebingen/tt3d.git external/tt3d` |
| 安装 BlurBall 依赖 | `pip install -r external/BlurBall/requirements.txt`，注意 Hydra/OmegaConf 版本 |
| 安装 TT3D 依赖 | `pip install -r external/tt3d/requirements.txt` + RTMPose + MotionBert |
| 下载预训练权重 | BlurBall + 7 个对比模型权重 → `data/ball_tracking_data/weights/` |
| 下载 BlurBall 数据集 | 64K 帧标注数据 → `data/ball_tracking_data/dataset/` (可选，用于验证) |

**RTX 4080 Super 注意事项**:
- BlurBall 基于 HRNet-W48，推理占 ~4-6GB，16GB 显存充裕
- 使用 1-step 推理模式（更快、更省显存），阈值设 0.7
- PyTorch 版本需与 CUDA 12.x 兼容: `torch==2.5.x+cu124`

#### 3.2 BlurBall 2D 检测验证 (Week 3-4)

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Ball_Tracking/core/blurball_detector.py` | BlurBall 包装器 | 封装 BlurBall 推理接口，统一输入/输出格式，支持单帧和批量推理 |
| `Ball_Tracking/core/tfort_fallback.py` | T-FORT 降级 | 帧差法 (~150 行): 帧差→二值化→连通域→候选过滤(面积/圆度/HSV)→运动连续性→轨迹构建 |
| `Ball_Tracking/utils/format_converter.py` | 格式转换 | BlurBall CSV (Frame,Visibility,X,Y,θ,l) → TT3D ball_traj_2D.csv |

**验证 Checkpoint 1**:
- [ ] BlurBall 在自带数据集上的 F1/AP 与论文一致
- [ ] 在测试视频上能正确检测球位置
- [ ] 输出 CSV 包含有效的模糊角度 θ 和长度 l
- [ ] T-FORT 降级方案在低质量视频上可用
- [ ] 横向对比至少 WASB + TrackNetV2 两个模型

#### 3.3 TT3D 3D 重建集成 (Week 4-5)

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Ball_Tracking/core/camera_calibration.py` | 相机标定 | 包装 TT3D 标定模块，球台角点 PnP，支持手动/自动角点检测 |
| `Ball_Tracking/core/trajectory_3d.py` | 3D 重建 | 包装 TT3D rally.py，2D→3D 轨迹提升，轨迹分段（弹跳/击球分离） |
| `Ball_Tracking/core/bounce_detector.py` | 落点检测 | 从 3D 轨迹提取弹跳点，映射回球台坐标系，输出落点分布 |
| `Ball_Tracking/core/spin_estimator.py` | 旋转估计 | 基于轨迹曲率和模糊信息估计旋转类型（上旋/下旋/侧旋） |

**显存管理策略（分步加载，不同时占 GPU）**:
```
Step 1: 加载 BlurBall → 2D 检测 → 卸载 BlurBall (~4-6GB 释放)
Step 2: 加载 RTMPose → 2D 姿态估计 → 卸载 RTMPose (~2GB 释放)
Step 3: 加载 MotionBert → 3D 姿态提升 → 卸载 MotionBert (~2GB 释放)
Step 4: 3D 重建 + 落点分析 (CPU 为主，轻量 GPU)
```

**验证 Checkpoint 2 & 3**:
- [ ] 相机标定重投影误差 < 5 pixels
- [ ] 3D 轨迹可视化合理（球在球台上方运动）
- [ ] 轨迹分段正确（弹跳点、击球点识别合理）
- [ ] 弹跳位置在球台范围内

#### 3.4 API 集成 & 视频处理管线 (Week 5-6)

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Ball_Tracking/api/tracking_api.py` | 追踪 API | 视频上传 (UploadFile)，异步任务处理，进度回调，结果下载 |

**API 设计**:
```
POST /tracking/upload          → 上传视频，返回 task_id
GET  /tracking/status/{id}     → 查询处理进度
GET  /tracking/result/{id}     → 获取分析结果 (JSON: 2D/3D轨迹, 落点, 旋转)
GET  /tracking/render/{id}     → 下载 3D 可视化视频
POST /tracking/quick-detect    → 单帧/短片段快速检测 (仅 BlurBall 2D)
```

**视频预处理**:
- FFmpeg 去重复帧: `mpdecimate` 滤镜（BlurBall MIMO 对重复帧敏感）
- 分辨率标准化: 统一缩放到 1920x1080 或 1280x720
- 镜头分割: 只保留全景帧（球台完整可见的段落）

---

### Phase 4: 装备推荐系统 (Week 6-7)

**目标**: 用户输入技术水平/打法 → 推荐底板+胶皮组合

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Equipment_Recommendation/core/equipment_db.py` | 装备数据库 | SQLite 存储，JSON 导入，字段: 品牌/型号/类型/硬度/速度/旋转/控制/价格/适合级别 |
| `Equipment_Recommendation/core/recommendation_engine.py` | 推荐引擎 | 混合策略: 规则过滤(级别/预算) + 向量相似度(打法描述 embedding 匹配) |
| `Equipment_Recommendation/core/user_profile.py` | 用户画像 | 技术水平(初级/中级/高级)、打法(弧圈/快攻/削球/全面)、预算范围、偏好 |
| `Equipment_Recommendation/api/recommendation_api.py` | API | POST 用户画像 → 返回 top 5 推荐 + 理由 |

**技术决策**:
- 装备数据手动整理为 JSON (初期 200-500 条)，不用爬虫
- Embedding 复用 LLM 模块的 `sentence-transformers` 模型
- 推荐理由由 LLM API 生成（调用 gpt-4o-mini 生成个性化推荐文案）
- **不需要 GPU**: 纯 CPU + API 调用

---

### Phase 5: 社交媒体问答 (Week 7-8)

**目标**: 爬取 Reddit 乒乓球社区 → 索引 → 混合 RAG 检索问答

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Social_Media/core/forum_scraper.py` | Reddit 爬虫 | `PRAW` 库，爬取 r/tabletennis 热帖+评论，增量更新，rate limiting |
| `Social_Media/core/content_indexer.py` | 内容索引 | 清洗 (去 HTML/短文过滤) → 分块 → Embedding → FAISS 索引 |
| `Social_Media/core/hybrid_retriever.py` | 混合检索 | 加权融合: 0.6×语义检索(FAISS) + 0.4×关键词检索(BM25)，结果去重排序 |
| `Social_Media/api/social_api.py` | API | 问答接口 + 热门话题接口 + 数据更新触发接口 |

**技术决策**:
- Reddit API 需要注册应用获取 client_id/secret
- FAISS 索引与 LLM 模块共享 embedding 模型
- BM25 用 `rank_bm25` 库，纯 CPU
- 爬虫用 cron 定时任务每日增量更新
- **不需要 GPU**: 纯 CPU + API 调用

---

### Phase 6: 乒乓球学习资源 (Week 8-9)

**目标**: 资源上传/分类/搜索管理系统

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Learning_Resources/core/resource_manager.py` | 资源 CRUD | 支持 PDF/视频链接/文章，SQLite 元数据存储，文件存本地 `data/learning_resources/` |
| `Learning_Resources/core/content_categorizer.py` | 内容分类 | 基于 embedding 的自动分类: 发球/接发球/正手/反手/步法/战术/规则，支持多标签 |
| `Learning_Resources/core/search_engine.py` | 语义搜索 | FAISS 语义检索 + SQLite 元数据过滤（按类别/难度/格式） |
| `Learning_Resources/api/resources_api.py` | API | CRUD + 搜索 + 分类浏览 |

**技术决策**:
- 分类体系预定义 ~15 个标签，embedding 聚类自动归类
- 视频资源只存链接（YouTube/Bilibili），不存文件
- 复用全局 embedding 模型和 FAISS 基础设施
- **不需要 GPU**: 纯 CPU + API 调用

---

### Phase 7: 训练分析 (Week 9-10)

**目标**: 基于 Ball_Tracking 输出做技术统计 + LLM 生成改进建议

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `Training_Analysis/core/data_processor.py` | 数据处理 | 解析 Ball_Tracking 输出的 JSON (3D 轨迹/落点/旋转)，提取统计特征 |
| `Training_Analysis/core/performance_analyzer.py` | 技术统计 | 计算: 击球速度分布、落点热力图、旋转类型比例、回合长度、失误率 |
| `Training_Analysis/core/improvement_suggestions.py` | AI 建议 | 将统计结果作为 context 传给 LLM API，生成个性化训练建议 |
| `Training_Analysis/core/session_manager.py` | Session 管理 | 训练记录 CRUD，历史对比，进步趋势追踪 |
| `Training_Analysis/api/analysis_api.py` | API | 创建 session + 上传数据 + 获取分析报告 + 历史趋势 |

**技术决策**:
- 核心分析逻辑是纯数学计算（numpy/scipy），不需要 GPU
- 热力图用 `matplotlib` 或 `plotly` 生成
- 改进建议调用 LLM API (gpt-4o-mini)，把统计数据作为 prompt context
- 依赖 Ball_Tracking 模块的输出格式，需定义清晰的数据接口

**验证标准**:
- 输入一段 Ball_Tracking 分析结果，输出完整的技术统计报告
- LLM 生成的建议与统计数据一致且具体可操作

---

### Phase 8: 前端界面 (Week 10-11)

**目标**: 统一 Web 界面，集成所有模块

**核心任务**:

| 文件 | 内容 | 技术细节 |
|------|------|----------|
| `frontend/index.html` | 主页 | 模块导航，响应式布局 |
| `frontend/js/app.js` | 主逻辑 | fetch API 调用，路由切换 |
| `frontend/js/chat.js` | LLM 聊天 | SSE 流式显示，对话历史 |
| `frontend/js/tracking.js` | 球追踪 | 视频上传，进度条，结果展示（轨迹叠加视频） |
| `frontend/js/equipment.js` | 装备推荐 | 表单输入，推荐卡片展示 |
| `frontend/js/social.js` | 社区问答 | 搜索框 + 结果列表 |
| `frontend/js/resources.js` | 学习资源 | 分类浏览 + 搜索 |
| `frontend/js/analysis.js` | 训练分析 | 图表展示 (Chart.js)，历史趋势 |
| `frontend/css/style.css` | 样式 | 简洁现代风格，深色/浅色主题 |

**技术决策**:
- **不用 React/Vue 框架**: 原生 HTML + CSS + JS，6 个页面足够
- 图表库: Chart.js（落点热力图、速度分布、趋势图）
- 视频播放: HTML5 video + canvas 叠加轨迹
- 响应式: CSS Grid/Flexbox，移动端适配
- **不需要 GPU**: 纯前端

---

### Phase 9: 测试与集成 (Week 11-12)

**目标**: 全模块联调，自动化测试覆盖

| 测试类型 | 工具 | 覆盖范围 |
|----------|------|----------|
| 单元测试 | pytest | 每个 core/ 模块的核心函数 |
| API 测试 | pytest + httpx | 所有 endpoint 的请求/响应验证 |
| 集成测试 | pytest | 跨模块数据流 (Ball_Tracking → Training_Analysis) |
| GPU 测试 | pytest + torch | GPU 可用性、显存管理、模型加载/卸载 |
| 前端测试 | 手动 + Playwright (可选) | 页面渲染、API 调用、交互逻辑 |

**关键集成测试场景**:
1. 上传视频 → BlurBall 检测 → TT3D 3D 重建 → 训练分析报告（全链路）
2. 上传 PDF → 向量库构建 → RAG 问答（LLM 全链路）
3. 并发请求时 GPU 显存管理不 OOM

---

### Phase 10: 部署与优化 (Week 12-14)

| 任务 | 技术细节 |
|------|----------|
| Docker 镜像优化 | 多阶段构建，减小镜像体积，分离 CPU/GPU 层 |
| Nginx 反向代理 | 静态文件服务 + API 代理 + WebSocket 支持 |
| 视频处理队列 | `celery` + `redis` 异步任务（球追踪是长时间任务） |
| 监控 | `prometheus` + `grafana` 监控 GPU 使用率/API 延迟/错误率 |
| 安全加固 | HTTPS, rate limiting, 输入验证, 文件类型检查 |
| 文档 | API 文档 (FastAPI 自带 Swagger), 部署指南, 用户手册 |

---

## ⚠️ 风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| BlurBall/TT3D 依赖冲突 | Phase 3 阻塞 | 用 conda 环境隔离，或 Docker 内单独构建 |
| RTMPose/MotionBert 安装复杂 | Phase 3.3 延迟 | 先跳过姿态估计，只做球追踪+标定+3D重建 |
| 转播视频镜头切换频繁 | 标定失败 | 预处理: FFmpeg 场景检测 → 只保留全景段 |
| 16GB 显存不够同时跑多模型 | OOM | 严格串行加载+卸载，gpu_manager 强制管理 |
| OpenAI API 成本 | 长期运营成本 | 开发阶段用 gpt-4o-mini (便宜)，后期可切本地模型 |
| Reddit API 限流 | 爬虫效率低 | 增量更新 + 本地缓存 + 合理 rate limiting |

---

## 📋 核心依赖版本锁定

```txt
# requirements.txt (基础)
fastapi==0.115.*
uvicorn[standard]==0.34.*
pydantic-settings==2.*
loguru==0.7.*
aiosqlite==0.20.*
python-jose[cryptography]==3.3.*
python-multipart==0.0.*
httpx==0.28.*

# requirements-gpu.txt (CV / ML)
torch==2.5.*+cu124
torchvision==0.20.*+cu124
numpy==1.26.*
opencv-python-headless==4.10.*
scipy==1.14.*
hydra-core==1.3.*
omegaconf==2.3.*

# LLM / RAG
langchain==0.3.*
langchain-openai==0.3.*
langchain-community==0.3.*
faiss-cpu==1.9.*
sentence-transformers==3.*
PyMuPDF==1.25.*
pytesseract==0.3.*
rank_bm25==0.2.*

# Reddit
praw==7.*

# Frontend 可视化
matplotlib==3.9.*
plotly==5.24.*

# 开发
pytest==8.*
pytest-asyncio==0.24.*
ruff==0.8.*
```

---

## 📌 参考资源

| 资源 | 链接 |
|------|------|
| BlurBall 论文 | https://arxiv.org/abs/2509.18387 |
| BlurBall 代码 | https://github.com/cogsys-tuebingen/BlurBall |
| BlurBall 数据集 | https://cloud.cs.uni-tuebingen.de/index.php/s/C3pJEPKWQAkono7 |
| BlurBall 权重 | https://cloud.cs.uni-tuebingen.de/index.php/s/6Z8TpM3sXRKHzGC |
| TT3D 论文 | https://arxiv.org/abs/2504.10035 |
| TT3D 代码 | https://github.com/cogsys-tuebingen/tt3d |
| SpinDOE (旋转估计) | https://github.com/cogsys-tuebingen/spindoe |
| WASB 基线框架 | https://github.com/nttcom/WASB-SBDT |
