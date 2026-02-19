"""
训练分析模块 Pydantic Schemas

包含训练会话、目标、分析和洞察的请求/响应模型。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ========== 枚举类型别名 ==========

SessionTypeEnum = Literal["practice", "drill", "match", "video_analysis"]
GoalStatusEnum = Literal["active", "achieved", "expired", "cancelled"]
GoalTypeEnum = Literal["speed", "accuracy", "consistency", "technique_mastery", "session_count", "total_duration"]
InsightTypeEnum = Literal["improvement", "warning", "achievement", "recommendation", "trend"]
PeriodTypeEnum = Literal["daily", "weekly", "monthly"]


# ========== 训练会话 Schemas ==========

class SessionCreate(BaseModel):
    """创建训练会话请求"""
    user_id: str = Field(..., description="用户ID")
    title: Optional[str] = Field(None, max_length=255, description="会话标题")
    session_type: SessionTypeEnum = Field(..., description="训练类型")
    description: Optional[str] = Field(None, description="描述")
    started_at: datetime = Field(..., description="开始时间")
    ended_at: Optional[datetime] = Field(None, description="结束时间")
    location: Optional[str] = Field(None, max_length=255, description="训练地点")
    equipment_notes: Optional[str] = Field(None, description="装备备注")
    practiced_techniques: Optional[List[str]] = Field(None, description="练习的技术")
    notes: Optional[str] = Field(None, description="训练笔记")
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5, description="满意度 1-5")
    fatigue_level: Optional[int] = Field(None, ge=1, le=5, description="疲劳程度 1-5")
    tags: Optional[List[str]] = Field(None, description="标签")


class SessionUpdate(BaseModel):
    """更新训练会话请求"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    ended_at: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    equipment_notes: Optional[str] = None
    practiced_techniques: Optional[List[str]] = None
    notes: Optional[str] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    fatigue_level: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None


class SessionBrief(BaseModel):
    """会话简要信息（列表用）"""
    id: str
    user_id: str
    title: Optional[str]
    session_type: str
    started_at: datetime
    duration_minutes: Optional[int]
    total_strokes: int
    avg_ball_speed_kmh: Optional[float]
    satisfaction_rating: Optional[int]
    video_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    """会话详情响应"""
    id: str
    user_id: str
    title: Optional[str]
    session_type: str
    description: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]
    location: Optional[str]
    equipment_notes: Optional[str]
    total_strokes: int
    avg_ball_speed_kmh: Optional[float]
    max_ball_speed_kmh: Optional[float]
    accuracy_score: Optional[float]
    consistency_score: Optional[float]
    practiced_techniques: Optional[List[str]]
    notes: Optional[str]
    satisfaction_rating: Optional[int]
    fatigue_level: Optional[int]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionBrief]
    total: int
    page: int
    page_size: int


# ========== 会话视频 Schemas ==========

class SessionVideoCreate(BaseModel):
    """添加视频到会话"""
    ball_tracking_job_id: str = Field(..., description="ball_tracking 任务 ID")
    segment_title: Optional[str] = Field(None, max_length=255, description="片段标题")
    start_time_seconds: float = Field(0, ge=0, description="开始时间（秒）")
    end_time_seconds: Optional[float] = Field(None, ge=0, description="结束时间（秒）")


class SessionVideoResponse(BaseModel):
    """会话视频响应"""
    id: str
    session_id: str
    ball_tracking_job_id: str
    segment_title: Optional[str]
    start_time_seconds: float
    end_time_seconds: Optional[float]
    stroke_count: Optional[int]
    avg_speed_kmh: Optional[float]
    max_speed_kmh: Optional[float]
    bounce_count: Optional[int]
    stroke_distribution: Optional[Dict[str, int]]
    analysis_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== 技术指标 Schemas ==========

class TechniqueMetricsResponse(BaseModel):
    """技术指标响应"""
    id: str
    session_id: str
    technique_category: str
    technique_name: Optional[str]
    stroke_count: int
    successful_count: int
    avg_speed_kmh: Optional[float]
    max_speed_kmh: Optional[float]
    min_speed_kmh: Optional[float]
    speed_std_dev: Optional[float]
    accuracy_score: Optional[float]
    consistency_score: Optional[float]
    detailed_stats: Optional[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class TechniqueMetricsSummary(BaseModel):
    """技术指标汇总"""
    technique_category: str
    total_sessions: int
    total_strokes: int
    avg_speed_kmh: Optional[float]
    avg_accuracy: Optional[float]
    avg_consistency: Optional[float]
    trend: str  # improving, stable, declining


# ========== 训练目标 Schemas ==========

class GoalCreate(BaseModel):
    """创建训练目标"""
    user_id: str = Field(..., description="用户ID")
    title: str = Field(..., min_length=1, max_length=255, description="目标标题")
    description: Optional[str] = Field(None, description="描述")
    goal_type: GoalTypeEnum = Field(..., description="目标类型")
    technique_category: Optional[str] = Field(None, description="关联技术类型")
    target_value: float = Field(..., description="目标值")
    baseline_value: Optional[float] = Field(None, description="基准值")
    unit: Optional[str] = Field(None, max_length=50, description="单位")
    start_date: datetime = Field(..., description="开始日期")
    target_date: datetime = Field(..., description="目标日期")


class GoalUpdate(BaseModel):
    """更新训练目标"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    target_date: Optional[datetime] = None
    status: Optional[GoalStatusEnum] = None


class GoalResponse(BaseModel):
    """目标响应"""
    id: str
    user_id: str
    title: str
    description: Optional[str]
    goal_type: str
    technique_category: Optional[str]
    target_value: float
    current_value: float
    baseline_value: Optional[float]
    unit: Optional[str]
    start_date: datetime
    target_date: datetime
    achieved_date: Optional[datetime]
    status: str
    progress_percent: float
    milestones: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalListResponse(BaseModel):
    """目标列表响应"""
    goals: List[GoalResponse]
    total: int


class MilestoneCreate(BaseModel):
    """添加里程碑"""
    value: float = Field(..., description="里程碑值")
    note: Optional[str] = Field(None, description="备注")


# ========== 进度快照 Schemas ==========

class SnapshotResponse(BaseModel):
    """进度快照响应"""
    id: str
    user_id: str
    snapshot_date: datetime
    period_type: str
    session_count: int
    total_duration_minutes: int
    total_strokes: int
    avg_ball_speed_kmh: Optional[float]
    overall_accuracy: Optional[float]
    overall_consistency: Optional[float]
    technique_breakdown: Optional[Dict[str, Any]]
    speed_change_percent: Optional[float]
    accuracy_change_percent: Optional[float]
    consistency_change_percent: Optional[float]
    highlights: Optional[List[str]]
    concerns: Optional[List[str]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SnapshotListResponse(BaseModel):
    """快照列表响应"""
    snapshots: List[SnapshotResponse]
    total: int


# ========== AI 洞察 Schemas ==========

class InsightResponse(BaseModel):
    """AI 洞察响应"""
    id: str
    user_id: str
    insight_type: str
    session_id: Optional[str]
    goal_id: Optional[str]
    snapshot_id: Optional[str]
    title: str
    content: str
    confidence_score: Optional[float]
    priority: int
    supporting_data: Optional[Dict[str, Any]]
    action_items: Optional[List[str]]
    is_read: bool
    is_dismissed: bool
    is_helpful: Optional[bool]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InsightFeedback(BaseModel):
    """洞察反馈"""
    is_helpful: bool = Field(..., description="是否有帮助")
    feedback: Optional[str] = Field(None, description="文字反馈")


class InsightListResponse(BaseModel):
    """洞察列表响应"""
    insights: List[InsightResponse]
    total: int
    unread_count: int


class GenerateInsightsRequest(BaseModel):
    """生成 AI 洞察请求"""
    user_id: str = Field(..., description="用户ID")
    context_type: Literal["session", "weekly", "goal", "general"] = Field(
        "general", description="上下文类型"
    )
    session_id: Optional[str] = Field(None, description="关联会话ID")
    goal_id: Optional[str] = Field(None, description="关联目标ID")
    force_regenerate: bool = Field(False, description="强制重新生成")


# ========== 统计分析 Schemas ==========

class AnalysisPeriodRequest(BaseModel):
    """分析周期请求"""
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    group_by: PeriodTypeEnum = Field("daily", description="分组方式")


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    date: datetime
    value: float
    session_count: int


class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    metric_name: str
    data_points: List[TrendDataPoint]
    overall_trend: str  # improving, stable, declining
    change_percent: float
    best_value: float
    worst_value: float
    average_value: float


class ComparisonRequest(BaseModel):
    """对比分析请求"""
    period1_start: datetime = Field(..., description="周期1开始")
    period1_end: datetime = Field(..., description="周期1结束")
    period2_start: datetime = Field(..., description="周期2开始")
    period2_end: datetime = Field(..., description="周期2结束")


class PeriodSummary(BaseModel):
    """周期汇总"""
    session_count: int
    total_duration_minutes: int
    total_strokes: int
    avg_speed_kmh: Optional[float]
    avg_accuracy: Optional[float]
    avg_consistency: Optional[float]


class ComparisonResponse(BaseModel):
    """对比分析响应"""
    period1_summary: PeriodSummary
    period2_summary: PeriodSummary
    comparison: Dict[str, Any]  # 各指标变化百分比
    insights: List[str]


class UserTrainingStatsResponse(BaseModel):
    """用户训练统计响应"""
    user_id: str
    total_sessions: int
    total_duration_minutes: int
    total_strokes: int
    avg_session_duration: float
    avg_strokes_per_session: float
    favorite_techniques: List[str]
    current_streak_days: int
    longest_streak_days: int
    goals_achieved: int
    goals_active: int
    technique_stats: Dict[str, TechniqueMetricsSummary]
    recent_insights: List[InsightResponse]


class TechniqueAnalysisResponse(BaseModel):
    """技术分析响应"""
    technique_category: str
    total_sessions: int
    total_strokes: int
    history: List[TechniqueMetricsResponse]
    trend: TrendAnalysisResponse
    summary: TechniqueMetricsSummary


# ========== 会话详情（带关联数据）==========

class SessionDetailResponse(BaseModel):
    """会话详情（包含视频和指标）"""
    session: SessionResponse
    videos: List[SessionVideoResponse]
    metrics: List[TechniqueMetricsResponse]


# ========== 触发分析请求 ==========

class AnalyzeSessionRequest(BaseModel):
    """触发会话分析请求"""
    force_reanalyze: bool = Field(False, description="强制重新分析")


class AnalyzeSessionResponse(BaseModel):
    """触发分析响应"""
    session_id: str
    status: str  # analyzing, completed, failed
    message: str
    metrics_updated: int
