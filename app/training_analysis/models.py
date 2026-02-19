"""
训练分析模块数据模型

包含训练会话、技术指标、训练目标、进度快照和 AI 洞察等核心模型。
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Float,
    Boolean, Enum as SQLEnum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.shared.database import Base


# ========== 枚举类型 ==========

class SessionType(str, enum.Enum):
    """训练类型"""
    PRACTICE = "practice"           # 自由练习
    DRILL = "drill"                 # 专项训练
    MATCH = "match"                 # 对打/比赛
    VIDEO_ANALYSIS = "video_analysis"  # 视频分析


class GoalStatus(str, enum.Enum):
    """目标状态"""
    ACTIVE = "active"       # 进行中
    ACHIEVED = "achieved"   # 已达成
    EXPIRED = "expired"     # 已过期
    CANCELLED = "cancelled" # 已取消


class GoalType(str, enum.Enum):
    """目标类型"""
    SPEED = "speed"                     # 速度提升
    ACCURACY = "accuracy"               # 准确率
    CONSISTENCY = "consistency"         # 稳定性
    TECHNIQUE_MASTERY = "technique_mastery"  # 技术掌握
    SESSION_COUNT = "session_count"     # 训练次数
    TOTAL_DURATION = "total_duration"   # 总时长


class MetricType(str, enum.Enum):
    """指标类型"""
    BALL_SPEED = "ball_speed"           # 球速
    SPIN_RATE = "spin_rate"             # 旋转率
    ACCURACY = "accuracy"               # 准确率
    CONSISTENCY = "consistency"         # 稳定性
    BOUNCE_COUNT = "bounce_count"       # 落点数
    STROKE_COUNT = "stroke_count"       # 击球数


class InsightType(str, enum.Enum):
    """洞察类型"""
    IMPROVEMENT = "improvement"         # 进步提示
    WARNING = "warning"                 # 警告/退步
    ACHIEVEMENT = "achievement"         # 成就达成
    RECOMMENDATION = "recommendation"   # 训练建议
    TREND = "trend"                     # 趋势分析


# ========== ORM 模型 ==========

class TrainingSession(Base):
    """训练会话模型"""
    __tablename__ = "training_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)

    # 基本信息
    title = Column(String(255), nullable=True)
    session_type = Column(SQLEnum(SessionType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # 时间信息
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # 位置/设备
    location = Column(String(255), nullable=True)
    equipment_notes = Column(Text, nullable=True)

    # 聚合指标（从关联的视频分析中汇总）
    total_strokes = Column(Integer, default=0)
    avg_ball_speed_kmh = Column(Float, nullable=True)
    max_ball_speed_kmh = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)  # 0-100
    consistency_score = Column(Float, nullable=True)  # 0-100

    # 主要练习技术（JSON数组）
    practiced_techniques = Column(JSON, nullable=True)  # ["forehand_loop", "backhand_drive"]

    # 用户笔记和感受
    notes = Column(Text, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)  # 1-5
    fatigue_level = Column(Integer, nullable=True)  # 1-5

    # 元数据
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    videos = relationship(
        "SessionVideo",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    metrics = relationship(
        "TechniqueMetrics",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class SessionVideo(Base):
    """训练会话视频关联（与 ball_tracking 集成）"""
    __tablename__ = "session_videos"
    __table_args__ = (
        UniqueConstraint("session_id", "ball_tracking_job_id", name="uq_session_job"),
    )

    id = Column(String(36), primary_key=True)
    session_id = Column(
        String(36),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ball_tracking_job_id = Column(String(36), nullable=False, index=True)

    # 视频片段信息
    segment_title = Column(String(255), nullable=True)
    start_time_seconds = Column(Float, default=0)
    end_time_seconds = Column(Float, nullable=True)

    # 从 ball_tracking 提取的指标
    stroke_count = Column(Integer, nullable=True)
    avg_speed_kmh = Column(Float, nullable=True)
    max_speed_kmh = Column(Float, nullable=True)
    bounce_count = Column(Integer, nullable=True)

    # 检测到的击球类型分布（JSON）
    stroke_distribution = Column(JSON, nullable=True)
    # {"loop": 45, "drive": 30, "push": 15, "smash": 10}

    # 分析状态
    analysis_status = Column(String(20), default="pending")  # pending, completed, failed
    analysis_summary = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    session = relationship("TrainingSession", back_populates="videos")


class TechniqueMetrics(Base):
    """技术指标模型（按技术类型聚合）"""
    __tablename__ = "technique_metrics"
    __table_args__ = (
        UniqueConstraint("session_id", "technique_category", name="uq_session_technique"),
    )

    id = Column(String(36), primary_key=True)
    session_id = Column(
        String(36),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 技术类型（使用与 learning_resources 相同的分类）
    technique_category = Column(String(50), nullable=False, index=True)
    # forehand, backhand, serve, receive, footwork

    # 具体技术动作
    technique_name = Column(String(100), nullable=True)
    # forehand_loop, backhand_drive, pendulum_serve, etc.

    # 数量指标
    stroke_count = Column(Integer, default=0)
    successful_count = Column(Integer, default=0)

    # 速度指标
    avg_speed_kmh = Column(Float, nullable=True)
    max_speed_kmh = Column(Float, nullable=True)
    min_speed_kmh = Column(Float, nullable=True)
    speed_std_dev = Column(Float, nullable=True)  # 标准差，反映稳定性

    # 质量指标 (0-100)
    accuracy_score = Column(Float, nullable=True)
    consistency_score = Column(Float, nullable=True)

    # 详细统计（JSON）
    detailed_stats = Column(JSON, nullable=True)
    # {"bounce_distribution": {...}, "speed_histogram": [...], ...}

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    session = relationship("TrainingSession", back_populates="metrics")


class TrainingGoal(Base):
    """训练目标模型"""
    __tablename__ = "training_goals"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)

    # 目标定义
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(SQLEnum(GoalType), nullable=False, index=True)

    # 关联的技术类型（可选）
    technique_category = Column(String(50), nullable=True)

    # 目标值
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)
    unit = Column(String(50), nullable=True)  # km/h, %, count, minutes

    # 基准值（设定目标时的起点）
    baseline_value = Column(Float, nullable=True)

    # 时间范围
    start_date = Column(DateTime, nullable=False)
    target_date = Column(DateTime, nullable=False)
    achieved_date = Column(DateTime, nullable=True)

    # 状态
    status = Column(SQLEnum(GoalStatus), default=GoalStatus.ACTIVE, index=True)
    progress_percent = Column(Float, default=0)  # 0-100

    # 检查点/里程碑（JSON）
    milestones = Column(JSON, nullable=True)
    # [{"value": 25, "achieved_at": "...", "note": "..."}, ...]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProgressSnapshot(Base):
    """进度快照模型（周期性聚合）"""
    __tablename__ = "progress_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", "period_type", name="uq_user_period_snapshot"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)

    # 快照周期
    snapshot_date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly

    # 训练统计
    session_count = Column(Integer, default=0)
    total_duration_minutes = Column(Integer, default=0)
    total_strokes = Column(Integer, default=0)

    # 综合指标
    avg_ball_speed_kmh = Column(Float, nullable=True)
    overall_accuracy = Column(Float, nullable=True)
    overall_consistency = Column(Float, nullable=True)

    # 按技术分类的指标（JSON）
    technique_breakdown = Column(JSON, nullable=True)
    # {"forehand": {"count": 100, "avg_speed": 25.5, "accuracy": 85}, ...}

    # 与上一周期对比
    speed_change_percent = Column(Float, nullable=True)
    accuracy_change_percent = Column(Float, nullable=True)
    consistency_change_percent = Column(Float, nullable=True)

    # 亮点和问题（JSON）
    highlights = Column(JSON, nullable=True)  # ["速度提升5%", "正手稳定性提高"]
    concerns = Column(JSON, nullable=True)    # ["反手准确率下降", "训练频率不足"]

    created_at = Column(DateTime, default=datetime.utcnow)


class AIInsight(Base):
    """AI 洞察/建议模型"""
    __tablename__ = "ai_insights"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)

    # 洞察类型
    insight_type = Column(SQLEnum(InsightType), nullable=False, index=True)

    # 关联上下文
    session_id = Column(String(36), nullable=True, index=True)
    goal_id = Column(String(36), nullable=True)
    snapshot_id = Column(String(36), nullable=True)

    # 内容
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # 置信度和优先级
    confidence_score = Column(Float, nullable=True)  # 0-1
    priority = Column(Integer, default=0)  # 越高越重要

    # 相关数据（JSON）
    supporting_data = Column(JSON, nullable=True)
    # {"metric": "forehand_speed", "current": 25, "target": 30, "trend": "improving"}

    # 可操作建议（JSON数组）
    action_items = Column(JSON, nullable=True)
    # ["增加正手拉球练习频率", "注意发力时机", ...]

    # 用户反馈
    is_helpful = Column(Boolean, nullable=True)
    user_feedback = Column(Text, nullable=True)

    # 状态
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)

    # 有效期
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
