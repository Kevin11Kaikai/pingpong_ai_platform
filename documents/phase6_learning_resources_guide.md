# Phase 6: 学习资源模块开发指南

## 模块概述

学习资源模块（Learning Resources）为乒乓球 AI 平台提供完整的教学资源管理、知识图谱、个性化学习推荐和进度追踪功能。

## 功能特性

- **资源管理**: 视频、文章、教程等学习资源的 CRUD 和语义搜索
- **知识图谱**: 乒乓球技术知识点的树形结构和关系管理
- **学习路径**: 系统化学习路径的创建和用户报名
- **进度追踪**: 用户学习进度、连续学习天数统计
- **智能推荐**: 基于用户档案的个性化资源和路径推荐
- **视频分析**: 与 ball_tracking 模块集成的技术动作分析

## API 端点

### 健康检查
```
GET /api/learning/health
```

### 资源管理 (`/api/learning/resources`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建资源 |
| GET | `/` | 资源列表（分页、筛选） |
| GET | `/{id}` | 获取资源详情 |
| PUT | `/{id}` | 更新资源 |
| DELETE | `/{id}` | 删除资源 |
| POST | `/{id}/like` | 点赞资源 |
| GET | `/search` | 语义搜索 |
| GET | `/stats` | 统计信息 |

### 学习路径 (`/api/learning/paths`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建路径 |
| GET | `/` | 路径列表 |
| GET | `/{id}` | 路径详情 |
| PUT | `/{id}` | 更新路径 |
| DELETE | `/{id}` | 删除路径 |
| POST | `/{id}/items` | 添加资源项 |
| DELETE | `/{id}/items/{resource_id}` | 移除资源项 |

### 知识图谱 (`/api/learning/knowledge`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建知识点 |
| GET | `/{id}` | 获取知识点 |
| PUT | `/{id}` | 更新知识点 |
| DELETE | `/{id}` | 删除知识点 |
| GET | `/tree` | 知识点树形结构 |
| GET | `/graph` | 完整知识图谱 |
| POST | `/relations` | 添加知识点关系 |
| GET | `/{id}/prerequisites` | 获取前置知识 |
| GET | `/search` | 知识点搜索 |

### 用户档案 (`/api/learning/profiles`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建用户档案 |
| GET | `/{user_id}` | 获取用户档案 |
| PUT | `/{user_id}` | 更新用户档案 |
| POST | `/{user_id}/enroll/{path_id}` | 报名学习路径 |
| GET | `/{user_id}/enrollments` | 用户报名列表 |
| POST | `/{user_id}/study-session` | 记录学习时长 |
| GET | `/{user_id}/stats` | 用户学习统计 |

### 智能推荐 (`/api/learning/recommendations`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 个性化推荐 |
| GET | `/quick` | 快速推荐 |
| GET | `/popular` | 热门资源 |
| GET | `/featured` | 精选资源 |

### 视频分析 (`/api/learning/video-analysis`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/link` | 创建视频分析关联 |
| GET | `/resource/{id}` | 获取资源的分析列表 |
| GET | `/link/{id}` | 获取分析详情 |
| POST | `/analyze` | 执行技术分析 |
| POST | `/link/{id}/commentary` | 生成 AI 解说 |

## curl 示例

### 1. 健康检查

```bash
curl http://localhost:8000/api/learning/health
```

响应:
```json
{
  "module": "learning_resources",
  "status": "healthy",
  "sub_modules": ["resources", "paths", "progress", "knowledge", "profiles", "recommendations", "video_analysis"],
  "features": ["资源 CRUD 管理", "语义向量搜索", "学习路径管理", ...]
}
```

### 2. 创建学习资源

```bash
curl -X POST http://localhost:8000/api/learning/resources \
  -H "Content-Type: application/json" \
  -d '{
    "title": "正手弧圈球入门教学",
    "description": "详细讲解正手弧圈球的动作要领和常见错误",
    "resource_type": "video",
    "category": "technique",
    "difficulty_level": "beginner",
    "url": "https://example.com/video/forehand-loop",
    "duration_minutes": 15,
    "author": "王教练",
    "tags": ["正手", "弧圈球", "入门"]
  }'
```

### 3. 语义搜索资源

```bash
curl "http://localhost:8000/api/learning/resources/search?query=正手发球技术&top_k=5&min_score=0.3"
```

### 4. 创建学习路径

```bash
curl -X POST http://localhost:8000/api/learning/paths \
  -H "Content-Type: application/json" \
  -d '{
    "title": "乒乓球初学者30天入门计划",
    "description": "从零开始的系统学习路径",
    "difficulty_level": "beginner",
    "category": "technique",
    "estimated_hours": 20,
    "learning_objectives": ["掌握基本握拍", "学会正手推挡", "掌握基本发球"],
    "tags": ["初学者", "入门", "30天计划"]
  }'
```

### 5. 向路径添加资源

```bash
curl -X POST http://localhost:8000/api/learning/paths/{path_id}/items \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": "resource-uuid-here",
    "order_index": 0,
    "is_required": true,
    "notes": "第一周学习内容"
  }'
```

### 6. 创建知识点

```bash
curl -X POST http://localhost:8000/api/learning/knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "name": "forehand_loop",
    "display_name": "正手弧圈球",
    "description": "乒乓球最重要的进攻技术之一",
    "category": "forehand",
    "difficulty_level": "intermediate",
    "key_points": ["引拍充分", "摩擦为主", "收小臂加速"]
  }'
```

### 7. 添加知识点关系

```bash
curl -X POST http://localhost:8000/api/learning/knowledge/relations \
  -H "Content-Type: application/json" \
  -d '{
    "from_point_id": "basic-attack-id",
    "to_point_id": "forehand-loop-id",
    "relation_type": "prerequisite",
    "weight": 0.9,
    "description": "学习弧圈球前需要掌握基本攻球"
  }'
```

### 8. 获取知识图谱

```bash
curl http://localhost:8000/api/learning/knowledge/graph
```

### 9. 创建用户学习档案

```bash
curl -X POST http://localhost:8000/api/learning/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "nickname": "乒乓爱好者",
    "current_level": "beginner",
    "years_playing": 1,
    "learning_goals": ["提高正手弧圈", "改善步法"],
    "weak_points": ["反手", "发球变化"],
    "preferred_resource_types": ["video", "tutorial"],
    "daily_goal_minutes": 30
  }'
```

### 10. 报名学习路径

```bash
curl -X POST http://localhost:8000/api/learning/profiles/user-123/enroll/path-456
```

### 11. 记录学习时长

```bash
curl -X POST "http://localhost:8000/api/learning/profiles/user-123/study-session?study_minutes=45"
```

### 12. 获取个性化推荐

```bash
curl -X POST http://localhost:8000/api/learning/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "recommendation_type": "resources",
    "top_k": 5,
    "exclude_completed": true
  }'
```

### 13. 获取快速推荐

```bash
curl "http://localhost:8000/api/learning/recommendations/quick?user_id=user-123&limit=3"
```

### 14. 更新学习进度

```bash
curl -X POST http://localhost:8000/api/learning/progress \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": "resource-123",
    "user_id": "user-456",
    "progress_percent": 75.0,
    "study_duration_minutes": 20
  }'
```

### 15. 标记资源完成

```bash
curl -X POST http://localhost:8000/api/learning/progress/user-456/resource/resource-123/complete
```

### 16. 创建视频分析关联

```bash
curl -X POST http://localhost:8000/api/learning/video-analysis/link \
  -H "Content-Type: application/json" \
  -d '{
    "resource_id": "video-resource-id",
    "ball_tracking_job_id": "tracking-job-id",
    "start_time_seconds": 10.5,
    "end_time_seconds": 25.0,
    "analysis_type": "technique_demo",
    "technique_category": "forehand"
  }'
```

### 17. 执行技术分析

```bash
curl -X POST http://localhost:8000/api/learning/video-analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "link_id": "analysis-link-id",
    "generate_ai_commentary": true
  }'
```

### 18. 生成 AI 技术解说

```bash
curl -X POST http://localhost:8000/api/learning/video-analysis/link/{link_id}/commentary
```

## 常见问题

### Q1: 语义搜索返回结果为空？

**原因**: 可能是 FAISS 索引未初始化或资源未生成向量嵌入。

**解决方案**:
1. 确保 `EmbeddingService` 正常工作
2. 创建资源时会自动生成向量，检查日志确认无错误
3. 检查 `min_score` 参数是否设置过高（默认 0.3）

### Q2: 推荐结果不符合预期？

**原因**: 用户档案信息不完整或没有足够的学习历史。

**解决方案**:
1. 确保用户档案包含 `current_level`、`learning_goals`、`weak_points`
2. 记录更多学习进度数据，推荐算法会根据历史调整
3. 检查 `exclude_completed` 参数设置

### Q3: 视频分析关联失败？

**原因**: 资源 ID 或 ball_tracking job ID 不存在。

**解决方案**:
1. 确认学习资源已创建且为视频类型
2. 确认 ball_tracking 任务已完成
3. 检查时间范围是否在视频时长内

### Q4: 知识图谱关系创建失败？

**原因**: 知识点 ID 不存在或创建了循环关系。

**解决方案**:
1. 先创建所有知识点，再建立关系
2. 避免 A→B→A 的循环 prerequisite 关系
3. 使用 `/knowledge/tree` 检查现有结构

### Q5: 学习连续天数重置了？

**原因**: 超过 48 小时未记录学习时长。

**解决方案**:
1. 配置项 `learning_streak_reset_hours` 控制重置时间
2. 使用 `/profiles/{user_id}/study-session` 每日记录学习时长
3. 最小记录单位为 1 分钟

### Q6: 进度更新后百分比未变化？

**原因**: 可能是更新了相同的进度值或资源已完成。

**解决方案**:
1. 已完成的资源进度固定为 100%
2. 使用 `is_completed: false` 重置完成状态
3. 检查返回的 `is_completed` 字段

## 配置项

在 `config/settings.py` 中可配置：

```python
# 分页
learning_resources_default_page_size: int = 20

# 搜索
learning_resources_search_top_k: int = 10
learning_resources_search_min_score: float = 0.3

# 推荐
learning_path_recommendation_top_k: int = 5
learning_resources_featured_count: int = 6

# 用户档案
learning_resource_upload_dir: str = "./data/uploads/learning"
learning_daily_study_goal_minutes: int = 30
learning_streak_reset_hours: int = 48

# 视频分析
learning_video_analysis_enabled: bool = True
learning_ai_commentary_model: str = "gpt-4o-mini"
learning_ai_commentary_temperature: float = 0.7
```

## 数据模型

### 枚举类型

- `ResourceType`: video, article, tutorial, exercise, course, book
- `DifficultyLevel`: beginner, intermediate, advanced, professional
- `ResourceCategory`: technique, tactics, rules, equipment, fitness, mental, competition, history
- `TechniqueCategory`: forehand, backhand, serve, receive, footwork, spin, push, block, smash, chop, lob
- `LearningStatus`: not_started, in_progress, completed, mastered

### 主要模型

| 模型 | 说明 |
|------|------|
| LearningResource | 学习资源 |
| LearningPath | 学习路径 |
| LearningPathItem | 路径资源项 |
| KnowledgePoint | 知识点 |
| KnowledgeRelation | 知识点关系 |
| UserLearningProfile | 用户学习档案 |
| UserPathEnrollment | 用户路径报名 |
| UserProgress | 用户学习进度 |
| VideoAnalysisLink | 视频分析关联 |

## 测试

运行单元测试：
```bash
pytest tests/test_learning_resources.py -v
```

运行特定测试类：
```bash
pytest tests/test_learning_resources.py::TestSchemas -v
pytest tests/test_learning_resources.py::TestResourceAPI -v
```

## 集成说明

### LLM 模块集成
- 使用 `EmbeddingService` 生成资源向量
- 使用 `RAGService` 生成 AI 推荐说明和技术解说

### Ball Tracking 模块集成
- `VideoAnalysisLink` 关联 `ProcessingJob`
- 提取轨迹数据用于技术动作分析
- 与标准参数对比生成改进建议
