"""
多帧追踪器
结合检测结果进行时序关联和轨迹插值
"""

from typing import List, Optional
from dataclasses import dataclass, field
import uuid
import numpy as np
from loguru import logger

from app.ball_tracking.core.detector import BallDetection
from config.settings import get_settings


@dataclass
class TrackPoint:
    """轨迹点"""
    frame_idx: int
    timestamp_ms: float
    x: float
    y: float
    confidence: float
    blur_angle: Optional[float] = None
    blur_length: Optional[float] = None
    interpolated: bool = False


@dataclass
class BallTrack:
    """完整球轨迹"""
    track_id: str
    points: List[TrackPoint] = field(default_factory=list)

    @property
    def start_frame(self) -> int:
        """起始帧"""
        return self.points[0].frame_idx if self.points else -1

    @property
    def end_frame(self) -> int:
        """结束帧"""
        return self.points[-1].frame_idx if self.points else -1

    @property
    def duration_ms(self) -> float:
        """轨迹时长（毫秒）"""
        if len(self.points) < 2:
            return 0.0
        return self.points[-1].timestamp_ms - self.points[0].timestamp_ms

    @property
    def point_count(self) -> int:
        """轨迹点数量"""
        return len(self.points)

    def to_numpy(self) -> np.ndarray:
        """转换为 numpy 数组 (N, 2)"""
        return np.array([[p.x, p.y] for p in self.points])


class BallTracker:
    """
    乒乓球追踪器
    负责跨帧关联检测结果，处理遮挡和丢失
    """

    def __init__(
        self,
        max_gap_frames: int = 5,
        max_distance: float = 150.0,
        min_track_length: int = 3,
        fps: float = 30.0,
    ):
        """
        初始化追踪器

        Args:
            max_gap_frames: 最大允许丢失帧数
            max_distance: 最大帧间位移（像素）
            min_track_length: 最小轨迹长度
            fps: 视频帧率
        """
        self.max_gap_frames = max_gap_frames
        self.max_distance = max_distance
        self.min_track_length = min_track_length
        self.fps = fps

    def process_detections(
        self,
        detections: List[Optional[BallDetection]],
        fps: Optional[float] = None,
    ) -> List[BallTrack]:
        """
        处理检测序列，生成轨迹

        Args:
            detections: 按帧顺序的检测结果列表
            fps: 视频帧率

        Returns:
            轨迹列表
        """
        if fps is not None:
            self.fps = fps

        tracks: List[BallTrack] = []
        current_track: Optional[BallTrack] = None
        gap_count: int = 0

        for i, det in enumerate(detections):
            if det is None or not det.visible or det.confidence < 0.1:
                # 无检测或不可见
                if current_track is not None:
                    gap_count += 1
                    if gap_count > self.max_gap_frames:
                        # 轨迹结束
                        if len(current_track.points) >= self.min_track_length:
                            tracks.append(current_track)
                        current_track = None
                        gap_count = 0
                continue

            timestamp_ms = (det.frame_idx / self.fps) * 1000

            if current_track is None:
                # 开始新轨迹
                current_track = BallTrack(
                    track_id=str(uuid.uuid4()),
                    points=[
                        TrackPoint(
                            frame_idx=det.frame_idx,
                            timestamp_ms=timestamp_ms,
                            x=det.x,
                            y=det.y,
                            confidence=det.confidence,
                            blur_angle=det.blur_angle,
                            blur_length=det.blur_length,
                            interpolated=False,
                        )
                    ],
                )
                gap_count = 0
            else:
                # 检查是否属于当前轨迹
                last_point = current_track.points[-1]
                distance = np.sqrt(
                    (det.x - last_point.x) ** 2 + (det.y - last_point.y) ** 2
                )

                # 考虑帧间隔调整最大距离
                adjusted_max_dist = self.max_distance * (gap_count + 1)

                if distance <= adjusted_max_dist:
                    # 属于当前轨迹
                    # 如果有间隔，先插值填充
                    if gap_count > 0:
                        interpolated_points = self._interpolate_gap(
                            current_track.points[-1],
                            TrackPoint(
                                frame_idx=det.frame_idx,
                                timestamp_ms=timestamp_ms,
                                x=det.x,
                                y=det.y,
                                confidence=det.confidence,
                                blur_angle=det.blur_angle,
                                blur_length=det.blur_length,
                                interpolated=False,
                            ),
                        )
                        current_track.points.extend(interpolated_points)

                    current_track.points.append(
                        TrackPoint(
                            frame_idx=det.frame_idx,
                            timestamp_ms=timestamp_ms,
                            x=det.x,
                            y=det.y,
                            confidence=det.confidence,
                            blur_angle=det.blur_angle,
                            blur_length=det.blur_length,
                            interpolated=False,
                        )
                    )
                    gap_count = 0
                else:
                    # 距离太远，结束当前轨迹，开始新轨迹
                    if len(current_track.points) >= self.min_track_length:
                        tracks.append(current_track)

                    current_track = BallTrack(
                        track_id=str(uuid.uuid4()),
                        points=[
                            TrackPoint(
                                frame_idx=det.frame_idx,
                                timestamp_ms=timestamp_ms,
                                x=det.x,
                                y=det.y,
                                confidence=det.confidence,
                                blur_angle=det.blur_angle,
                                blur_length=det.blur_length,
                                interpolated=False,
                            )
                        ],
                    )
                    gap_count = 0

        # 处理最后一个轨迹
        if current_track is not None and len(current_track.points) >= self.min_track_length:
            tracks.append(current_track)

        logger.info(f"生成 {len(tracks)} 条轨迹")
        return tracks

    def _interpolate_gap(
        self,
        start: TrackPoint,
        end: TrackPoint,
    ) -> List[TrackPoint]:
        """
        插值填充缺失帧

        Args:
            start: 起始点
            end: 结束点

        Returns:
            插值点列表（不包含起始和结束点）
        """
        interpolated = []
        frame_gap = end.frame_idx - start.frame_idx

        if frame_gap <= 1:
            return interpolated

        for i in range(1, frame_gap):
            t = i / frame_gap
            frame_idx = start.frame_idx + i
            timestamp_ms = start.timestamp_ms + t * (end.timestamp_ms - start.timestamp_ms)

            # 线性插值位置
            x = start.x + t * (end.x - start.x)
            y = start.y + t * (end.y - start.y)

            # 插值置信度（降低）
            confidence = min(start.confidence, end.confidence) * 0.5

            # 插值模糊参数
            blur_angle = None
            blur_length = None
            if start.blur_angle is not None and end.blur_angle is not None:
                blur_angle = start.blur_angle + t * (end.blur_angle - start.blur_angle)
            if start.blur_length is not None and end.blur_length is not None:
                blur_length = start.blur_length + t * (end.blur_length - start.blur_length)

            interpolated.append(
                TrackPoint(
                    frame_idx=frame_idx,
                    timestamp_ms=timestamp_ms,
                    x=x,
                    y=y,
                    confidence=confidence,
                    blur_angle=blur_angle,
                    blur_length=blur_length,
                    interpolated=True,
                )
            )

        return interpolated

    def smooth_track(self, track: BallTrack, window_size: int = 3) -> BallTrack:
        """
        平滑轨迹

        Args:
            track: 原始轨迹
            window_size: 平滑窗口大小

        Returns:
            平滑后的轨迹
        """
        if len(track.points) <= window_size:
            return track

        coords = track.to_numpy()
        smoothed_coords = np.copy(coords)

        half_window = window_size // 2
        for i in range(half_window, len(coords) - half_window):
            window = coords[i - half_window : i + half_window + 1]
            smoothed_coords[i] = np.mean(window, axis=0)

        # 创建平滑后的轨迹
        smoothed_points = []
        for i, point in enumerate(track.points):
            smoothed_points.append(
                TrackPoint(
                    frame_idx=point.frame_idx,
                    timestamp_ms=point.timestamp_ms,
                    x=smoothed_coords[i, 0],
                    y=smoothed_coords[i, 1],
                    confidence=point.confidence,
                    blur_angle=point.blur_angle,
                    blur_length=point.blur_length,
                    interpolated=point.interpolated,
                )
            )

        return BallTrack(track_id=track.track_id, points=smoothed_points)


def get_tracker(
    max_gap_frames: Optional[int] = None,
    max_distance: Optional[float] = None,
) -> BallTracker:
    """
    获取追踪器实例

    Args:
        max_gap_frames: 最大允许丢失帧数
        max_distance: 最大帧间位移

    Returns:
        BallTracker 实例
    """
    settings = get_settings()
    return BallTracker(
        max_gap_frames=max_gap_frames or settings.ball_tracking_max_gap_frames,
        max_distance=max_distance or 150.0,
    )
