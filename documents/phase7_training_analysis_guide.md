# Phase 7: 训练分析模块开发指南

## 模块概述

训练分析模块（Training Analysis）为乒乓球 AI 平台提供训练数据采集、统计分析、进度追踪和 AI 训练建议功能。

## 功能特性

- **训练会话管理**: 记录训练基本信息、时间、地点、练习技术
- **视频分析集成**: 与 ball_tracking 模块集成，提取技术指标
- **技术指标追踪**: 按技术类型聚合速度、准确率、稳定性
- **训练目标管理**: 设定和追踪速度、准确率等目标
- **进度快照**: 周期性（日/周/月）统计汇总
- **趋势分析**: 分析指标变化趋势
- **AI 训练建议**: 基于 LLM 的个性化训练洞察

## API 端点

### 健康检查
```
GET /api/training/health
```

### 训练会话 (`/api/training/sessions`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建训练会话 |
| GET | `/` | 会话列表（分页、筛选） |
| GET | `/{session_id}` | 获取会话详情 |
| PUT | `/{session_id}` | 更新会话 |
| DELETE | `/{session_id}` | 删除会话 |
| POST | `/{session_id}/videos` | 添加视频 |
| DELETE | `/{session_id}/videos/{video_id}` | 移除视频 |
| POST | `/{session_id}/analyze` | 触发分析 |
| GET | `/{session_id}/metrics` | 获取会话指标 |
| GET | `/user/{user_id}/recent` | 获取最近会话 |

### 训练目标 (`/api/training/goals`)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/` | 创建目标 |
| GET | `/` | 目标列表 |
| GET | `/{goal_id}` | 获取目标详情 |
| PUT | `/{goal_id}` | 更新目标 |
| DELETE | `/{goal_id}` | 删除目标 |
| POST | `/{goal_id}/refresh` | 刷新目标进度 |
| POST | `/{goal_id}/milestones` | 添加里程碑 |
| GET | `/user/{user_id}/active` | 获取活跃目标 |
| GET | `/user/{user_id}/achieved` | 获取已达成目标 |

### 统计分析 (`/api/training/analysis`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/user/{user_id}/stats` | 用户综合统计 |
| GET | `/user/{user_id}/trends` | 趋势分析 |
| POST | `/user/{user_id}/compare` | 周期对比 |
| GET | `/user/{user_id}/snapshots` | 快照列表 |
| GET | `/user/{user_id}/technique/{category}` | 技术分析 |
| POST | `/generate-snapshot` | 生成快照 |
| GET | `/user/{user_id}/streak` | 连续训练天数 |

### AI 洞察 (`/api/training/insights`)

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/user/{user_id}` | 获取用户洞察 |
| POST | `/generate` | 生成洞察 |
| GET | `/{insight_id}` | 获取洞察详情 |
| POST | `/{insight_id}/read` | 标记已读 |
| POST | `/{insight_id}/dismiss` | 忽略 |
| POST | `/{insight_id}/feedback` | 提交反馈 |
| GET | `/user/{user_id}/unread-count` | 未读数量 |

## curl 示例

### 1. 健康检查

```bash
curl http://localhost:8000/api/training/health
```

响应:
```json
{
  "module": "training_analysis",
  "status": "healthy",
  "sub_modules": ["sessions", "goals", "analysis", "insights"],
  "features": ["训练会话管理", "视频分析集成", "技术指标追踪", ...]
}
```

### 2. 创建训练会话

```bash
curl -X POST http://localhost:8000/api/training/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "title": "正手拉球专项训练",
    "session_type": "drill",
    "description": "练习正手弧圈球技术",
    "started_at": "2024-06-15T10:00:00",
    "ended_at": "2024-06-15T11:30:00",
    "location": "球馆A",
    "practiced_techniques": ["forehand_loop", "forehand_drive"],
    "satisfaction_rating": 4,
    "fatigue_level": 3,
    "tags": ["正手", "专项训练"]
  }'
```

### 3. 获取会话列表

```bash
curl "http://localhost:8000/api/training/sessions?user_id=user-123&page=1&page_size=10"
```

### 4. 添加视频到会话

```bash
curl -X POST http://localhost:8000/api/training/sessions/{session_id}/videos \
  -H "Content-Type: application/json" \
  -d '{
    "ball_tracking_job_id": "job-456",
    "segment_title": "正手拉球练习片段",
    "start_time_seconds": 0,
    "end_time_seconds": 120
  }'
```

### 5. 触发会话分析

```bash
curl -X POST http://localhost:8000/api/training/sessions/{session_id}/analyze \
  -H "Content-Type: application/json" \
  -d '{"force_reanalyze": false}'
```

### 6. 创建训练目标

```bash
curl -X POST http://localhost:8000/api/training/goals \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "title": "提升正手拉球速度",
    "goal_type": "speed",
    "technique_category": "forehand",
    "target_value": 30.0,
    "baseline_value": 25.0,
    "unit": "km/h",
    "start_date": "2024-06-01T00:00:00",
    "target_date": "2024-07-01T00:00:00"
  }'
```

### 7. 刷新目标进度

```bash
curl -X POST http://localhost:8000/api/training/goals/{goal_id}/refresh
```

### 8. 添加目标里程碑

```bash
curl -X POST http://localhost:8000/api/training/goals/{goal_id}/milestones \
  -H "Content-Type: application/json" \
  -d '{
    "value": 27.5,
    "note": "第一周进度"
  }'
```

### 9. 获取用户统计

```bash
curl http://localhost:8000/api/training/analysis/user/user-123/stats
```

### 10. 获取趋势分析

```bash
curl "http://localhost:8000/api/training/analysis/user/user-123/trends?metric=speed&days=30&group_by=daily"
```

### 11. 周期对比分析

```bash
curl -X POST http://localhost:8000/api/training/analysis/user/user-123/compare \
  -H "Content-Type: application/json" \
  -d '{
    "period1_start": "2024-06-01T00:00:00",
    "period1_end": "2024-06-15T00:00:00",
    "period2_start": "2024-06-15T00:00:00",
    "period2_end": "2024-06-30T00:00:00"
  }'
```

### 12. 获取技术分析

```bash
curl "http://localhost:8000/api/training/analysis/user/user-123/technique/forehand?days=30"
```

### 13. 生成进度快照

```bash
curl -X POST "http://localhost:8000/api/training/analysis/generate-snapshot?user_id=user-123&period_type=weekly"
```

### 14. 生成 AI 洞察

```bash
curl -X POST http://localhost:8000/api/training/insights/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "context_type": "weekly"
  }'
```

### 15. 获取用户洞察

```bash
curl "http://localhost:8000/api/training/insights/user/user-123?unread_only=true&limit=10"
```

### 16. 标记洞察已读

```bash
curl -X POST http://localhost:8000/api/training/insights/{insight_id}/read
```

### 17. 提交洞察反馈

```bash
curl -X POST http://localhost:8000/api/training/insights/{insight_id}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "is_helpful": true,
    "feedback": "这个建议很有帮助"
  }'
```

### 18. 获取连续训练天数

```bash
curl http://localhost:8000/api/training/analysis/user/user-123/streak
```

## 常见问题

### Q1: 会话分析返回空指标？

**原因**: 可能是关联的 ball_tracking 任务未完成或数据为空。

**解决方案**:
1. 确认 ball_tracking 任务状态为 completed
2. 检查任务是否有 BallTrack2D 数据
3. 使用 `force_reanalyze: true` 强制重新分析

### Q2: 目标进度不更新？

**原因**: 目标类型与现有数据不匹配。

**解决方案**:
1. 确保训练会话包含相关技术类型
2. 调用 `/goals/{id}/refresh` 手动刷新进度
3. 检查 `start_date` 是否晚于训练数据

### Q3: AI 洞察生成失败？

**原因**: LLM 服务不可用或配置错误。

**解决方案**:
1. 检查 `LLM_API_KEY` 环境变量
2. 检查 `training_insight_model` 配置
3. 查看日志中的错误信息
4. 无 LLM 时会返回默认洞察

### Q4: 趋势分析数据不准确？

**原因**: 训练数据不足或日期范围设置不当。

**解决方案**:
1. 增加训练记录数量
2. 调整 `days` 参数获取更多数据
3. 使用 `group_by=weekly` 减少数据点波动

### Q5: 连续天数被重置？

**原因**: 超过 24 小时未记录训练。

**解决方案**:
1. 连续训练天数按自然日计算
2. 确保每天至少记录一次训练
3. 连续天数会在最长天数中保留历史记录

## 配置项

在 `config/settings.py` 中可配置：

```python
# 分页
training_analysis_default_page_size: int = 20
training_analysis_max_sessions_per_query: int = 100

# 数据保留
training_analysis_snapshot_retention_days: int = 365
training_analysis_insight_retention_days: int = 90

# AI 洞察生成
training_insight_model: str = "gpt-4o-mini"
training_insight_temperature: float = 0.7
training_insight_max_tokens: int = 1000

# 指标计算
training_metrics_speed_conversion_factor: float = 3.6  # m/s to km/h
```

## 数据模型

### 枚举类型

- `SessionType`: practice, drill, match, video_analysis
- `GoalStatus`: active, achieved, expired, cancelled
- `GoalType`: speed, accuracy, consistency, technique_mastery, session_count, total_duration
- `InsightType`: improvement, warning, achievement, recommendation, trend

### 主要模型

| 模型 | 说明 |
|------|------|
| TrainingSession | 训练会话 |
| SessionVideo | 会话视频关联 |
| TechniqueMetrics | 技术指标 |
| TrainingGoal | 训练目标 |
| ProgressSnapshot | 进度快照 |
| AIInsight | AI 洞察 |

## 测试

运行单元测试：
```bash
pytest tests/test_training_analysis.py -v
```

运行特定测试类：
```bash
pytest tests/test_training_analysis.py::TestSessionSchemas -v
pytest tests/test_training_analysis.py::TestMetricsService -v
```

## 集成说明

### Ball Tracking 模块集成
- 通过 `SessionVideo` 关联 `ProcessingJob`
- 从 `BallTrack2D.analysis_json` 提取指标
- 自动映射击球类型到技术类别

### LLM 模块集成
- 使用 `LLMClient` 生成 AI 洞察
- 提示词模板支持会话、周度、目标等上下文
- 无 LLM 时返回默认建议

### Learning Resources 模块集成
- 技术类别枚举与 `TechniqueCategory` 保持一致
- 可关联用户学习档案和学习进度
