"""
Ball Tracking 模块 Pydantic Schema
定义所有 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Optional, List, Tuple, Literal
from pydantic import BaseModel, Field


# ========== 基础类型 ==========

class Point2D(BaseModel):
    """2D 点"""
    x: float
    y: float


class BoundingBox(BaseModel):
    """边界框"""
    x1: float
    y1: float
    x2: float
    y2: float


# ========== 视频处理相关 Schema ==========

class VideoUploadResponse(BaseModel):
    """视频上传响应"""
    job_id: str
    filename: str
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime

    class Config:
        from_attributes = True


class VideoMetadataResponse(BaseModel):
    """视频元数据响应"""
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    codec: str


class ProcessingJobStatus(BaseModel):
    """处理任务状态"""
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress_percent: float = Field(ge=0, le=100)
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 检测和追踪相关 Schema ==========

class DetectionResult(BaseModel):
    """单帧检测结果"""
    frame_idx: int
    timestamp_ms: float
    position: Point2D
    confidence: float
    blur_angle: Optional[float] = None
    blur_length: Optional[float] = None
    visible: bool = True


class TrackPoint2D(BaseModel):
    """2D轨迹点"""
    frame_idx: int
    timestamp_ms: float
    x: float
    y: float
    confidence: float
    blur_angle: Optional[float] = None
    blur_length: Optional[float] = None
    interpolated: bool = False


class Track2DResponse(BaseModel):
    """2D轨迹响应"""
    track_id: str
    points: List[TrackPoint2D]
    start_frame: int
    end_frame: int
    duration_ms: float
    point_count: int

    class Config:
        from_attributes = True


# ========== 分析相关 Schema ==========

class SpeedStatsResponse(BaseModel):
    """速度统计响应"""
    max_speed_mps: float
    max_speed_kmh: float
    avg_speed_mps: float
    avg_speed_kmh: float
    initial_speed_mps: float


class MotionStatsResponse(BaseModel):
    """运动统计响应"""
    total_distance_px: float
    max_displacement_px: float
    avg_displacement_px: float
    direction_changes: int
    avg_blur_length: Optional[float] = None


class BouncePointResponse(BaseModel):
    """落点响应"""
    frame_idx: int
    timestamp_ms: float
    x: float
    y: float
    bounce_type: str


class TrajectoryAnalysisResponse(BaseModel):
    """轨迹分析响应"""
    track_id: str
    speed_stats: Optional[SpeedStatsResponse] = None
    motion_stats: Optional[MotionStatsResponse] = None
    bounce_points: List[BouncePointResponse] = []
    stroke_type: Optional[str] = None


# ========== 完整处理结果 Schema ==========

class ProcessingResultResponse(BaseModel):
    """处理结果响应"""
    job_id: str
    video_metadata: VideoMetadataResponse
    tracks: List[Track2DResponse]
    analysis: Optional[List[TrajectoryAnalysisResponse]] = None
    processing_time_seconds: float
    frame_count: int
    detection_count: int

    class Config:
        from_attributes = True


# ========== 可视化相关 Schema ==========

class VisualizationRequest(BaseModel):
    """可视化请求"""
    output_format: Literal["mp4", "gif"] = "mp4"
    include_trajectory: bool = True
    include_analysis_overlay: bool = False
    trail_length: int = Field(30, ge=1, le=100)


class VisualizationResponse(BaseModel):
    """可视化响应"""
    job_id: str
    visualization_id: str
    output_url: str
    format: str
    file_size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 列表查询响应 ==========

class JobListItem(BaseModel):
    """任务列表项"""
    job_id: str
    filename: str
    status: str
    progress_percent: float
    created_at: datetime
    processing_time_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """任务列表响应"""
    items: List[JobListItem]
    total: int
    limit: int
    offset: int
