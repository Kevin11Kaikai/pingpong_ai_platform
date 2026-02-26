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

---

## 2026-02-26 Ball Tracking 前端专项修复

### 背景
视频分析页面（http://localhost/video）上传视频后：轨迹叠加 canvas 无渲染、速度标签布局异常、数据库写入失败。

---

### 后端修复

#### `app/ball_tracking/api/videos.py`
1. **numpy JSON 序列化错误**（`TypeError: Object of type float32 is not JSON serializable`）
   - 根因：BlurBall pipeline 输出 `np.float32`/`np.float64` 标量，SQLAlchemy JSON 列用原生 `json.dumps` 无法序列化
   - 修复：新增 `_to_py(obj)` 递归转换器，在写入 `points_json` 和 `analysis_json` 前调用
   - 覆盖类型：`np.integer→int`、`np.floating→float`、`np.ndarray→list`、`np.bool_→bool`

2. **新增 `GET /jobs/{job_id}/video/original` 端点**
   - 根因：前端 `video.src = getVideoUrl(jobId, 'original')` 调用的路径不存在，视频播放器永远空白
   - 修复：新增 `FileResponse` 端点，支持 `.mp4/.avi/.mov/.mkv/.webm` 五种格式

3. **前后端字段名不一致修复**（上一 session 遗留，已确认）
   - `process_video_task` except 块缺少 `await db.rollback()` 导致 job 卡在 `processing` 状态
   - 修复：rollback 后重新查询 job 对象再写入 `status=failed`

#### `app/ball_tracking/api/visualization.py`
- 同上，`generate_visualization_task` except 块补充 `await db.rollback()` + 重新查询

#### `requirements.txt`
- 新增 BlurBall 运行时依赖：`pandas>=2.0.0`、`scikit-learn>=1.4.0`、`torchmetrics>=1.4.0`
- 根因：`external/blurball/src/runners/inference.py` 等文件通过 `sys.path.insert` 在运行时加载，包含 `import pandas`

#### `docker/Dockerfile.prod`
- 新增两个 COPY 层：
  ```dockerfile
  COPY --chown=pingpong:pingpong scripts/ ./scripts/
  COPY --chown=pingpong:pingpong data/test/ ./test_data/
  ```
- 原因：`/app/data/` 是 Docker volume 挂载点，image 内的文件会被覆盖；测试数据改放 `/app/test_data/`

---

### 前端修复

#### `frontend/js/api/ball-tracking.js`
- `getJobs` 参数名 `skip` → `offset`（后端 `list_jobs` 用 `offset` 查询参数）

#### `frontend/js/utils/format.js`
- `Format.status` defaultMap 补充 `queued: { label: '队列中', color: 'warning' }`

#### `frontend/pages/video.html`
- 所有 `<script>` 标签加 `?v=3` 后缀，强制浏览器绕过 ETag 缓存，加载最新 JS

#### `frontend/js/pages/video.js`
关键修复：
1. **`showHistory()` 响应结构错误**：`getJobs` 返回 `{ items:[], total, ... }`，原代码当数组用 → 改为 `response.items`
2. **`downloadVisualization()` 立即下载 404**：可视化文件异步生成，原代码拿到 202 立即下载 → 改为循环 HEAD 轮询，最多等 60s
3. **`play` 事件不检查 `showTrajectory` 状态** → 加守卫 `if (this.showTrajectory)`
4. **`setAnalysis` 防御性调用**：改为 `this.canvasController?.setAnalysis?.(result.analysis)` 兼容缓存场景
5. **分析完成后立即绘制一帧**：`this.canvasController.startAnimation()` 在 `onAnalysisComplete` 末尾调用，暂停状态也能看到轨迹
6. **`loadResults` 注入真实 FPS 和分析数据**：
   ```javascript
   this.canvasController.setTracks(this.tracks, fps);          // 真实帧率
   this.canvasController.setAnalysis(result.analysis);         // 速度数据
   ```

#### `frontend/js/utils/canvas.js`
四类 bug 全部修复：

**1. 数据结构不匹配（CRITICAL）**
- 根因：后端返回 `Track2DResponse[]`（嵌套 `points[]`），旧代码把它当扁平点数组 → `t.frame` 永远 `undefined`，过滤器始终返回空数组
- 修复：`setTracks` 展开嵌套结构，转换为 `{frame, x, y}` 扁平数组并按帧排序；同时构建 `segments[]` 存储每段元数据

**2. 坐标系映射错误（CRITICAL）**
- 根因：后端返回原始像素坐标（如 `x=423`），旧代码做 `point.x * canvas.width` = 542,080，远超画布范围
- 修复：`canvas.width = video.videoWidth`（原生分辨率），直接使用 `point.x/y`，CSS 负责缩放

**3. Canvas 初始尺寸为 0**
- 根因：`resize()` 仅绑定 `loadedmetadata` 事件，历史任务回放时 canvas 保持 0×0
- 修复：`initOverlay` 调用时立即执行一次 `resize()`

**4. `ctx` 状态污染（黄色大矩形 bug）**
- 根因：`drawSpeedLabel` 的 `isFastest` 分支调用了第二次 `fillRoundRect`，但此时 `ctx.fillStyle` 已被改为橙色文字色 `'#fa8c16'`，导致整个标签被橙色覆盖；且无 `save/restore` 导致 `lineWidth=1.5` 泄露到后续绘制
- 修复：删除重复的 `fillRoundRect` 调用（只 stroke 不 fill），整个 `drawSpeedLabel` 包裹 `ctx.save()` / `ctx.restore()`

**新增功能：速度标签 + 悬停详情**
- `setAnalysis(analysisData)`：按 `track_id` 匹配分析结果，回填 `maxSpeedKmh/avgSpeedKmh`，标记最高速段 `isFastest=true`
- `drawSpeedLabel(seg)`：在活跃段起点绘制 `"#N xx.x km/h"` 标签，最高速用橙色边框
- `drawHoverTooltip(seg)`：在 `canvas.parentElement` 监听 `mousemove`，悬停轨迹时显示详情框
- 速度标签过滤条件（最终）：`seg.startFrame <= currentFrame && currentFrame <= seg.endFrame`（只显示当前帧所属轨迹段）

---

### 待验证（下次 session 继续）

| 项目 | 预期效果 | 验证方法 |
|------|----------|----------|
| 速度标签一一对应 | 播放视频时只有当前帧所属轨迹段显示速度标签 | 播放并观察标签是否随帧切换 |
| 黄色矩形消失 | 标签为小型半透明暗色背景，不出现橙色大块 | 上传 test3.mp4，观察 canvas |
| 最高速橙色高亮 | 最快段标签有橙色边框 | 检查 `#2 27.1 km/h` 是否有边框 |
| 悬停详情框 | 鼠标移到轨迹线上出现详情 | 鼠标悬停轨迹区域 |
| 视频播放器加载 | `<video>` 元素能正常播放上传的视频 | 检查 Network 标签 `/video/original` 200 |

### 验证前快速检查步骤
```
# 确认容器 healthy
docker ps --format "table {{.Names}}\t{{.Status}}"

# 上传视频后检查 job 状态（应为 completed）
curl http://localhost/api/ball-tracking/jobs/{job_id}/status

# 检查轨迹数据格式（应包含 points[] 数组）
curl http://localhost/api/ball-tracking/jobs/{job_id}/tracks | python -m json.tool | head -30

# 浏览器 Console 验证
VideoPage.tracks                        # 应为 Track2DResponse[]
VideoPage.canvasController.setAnalysis  # 应为 function（非 undefined）
document.getElementById('overlayCanvas').width  # 应为视频原生宽度
```