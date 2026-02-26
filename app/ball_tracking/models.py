"""
Ball Tracking 模块数据库模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.shared.database import Base


class ProcessingJob(Base):
    """视频处理任务"""
    __tablename__ = "ball_tracking_jobs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    status = Column(String(20), default="queued", index=True)
    progress_percent = Column(Float, default=0.0)
    current_stage = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # 视频元数据
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    video_fps = Column(Float, nullable=True)
    video_frames = Column(Integer, nullable=True)
    video_duration = Column(Float, nullable=True)
    video_codec = Column(String(20), nullable=True)

    # 处理结果统计
    detection_count = Column(Integer, nullable=True)
    track_count = Column(Integer, nullable=True)

    # 处理配置
    config = Column(JSON, nullable=True)

    # 处理时间
    processing_time_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    tracks = relationship("BallTrack2D", back_populates="job", cascade="all, delete-orphan")
    visualizations = relationship("VisualizationOutput", back_populates="job", cascade="all, delete-orphan")


class BallTrack2D(Base):
    """2D 球轨迹"""
    __tablename__ = "ball_tracks_2d"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("ball_tracking_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    start_frame = Column(Integer, nullable=False)
    end_frame = Column(Integer, nullable=False)
    point_count = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)

    # 存储轨迹点 JSON
    # 格式: [{"frame_idx": 0, "x": 100, "y": 200, "confidence": 0.9, ...}, ...]
    points_json = Column(JSON, nullable=False)

    # 分析结果 JSON
    # 格式: {"speed_stats": {...}, "motion_stats": {...}, "bounce_points": [...], "stroke_type": "..."}
    analysis_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    job = relationship("ProcessingJob", back_populates="tracks")


class VisualizationOutput(Base):
    """可视化输出"""
    __tablename__ = "ball_tracking_visualizations"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("ball_tracking_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    output_format = Column(String(20), nullable=False)  # mp4, gif
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    # 可视化配置
    config = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    job = relationship("ProcessingJob", back_populates="visualizations")
