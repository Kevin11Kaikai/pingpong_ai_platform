"""
轨迹分析模块
分析球的速度、落点等物理属性
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from loguru import logger

from app.ball_tracking.core.tracker import BallTrack, TrackPoint


@dataclass
class SpeedStats:
    """速度统计"""
    max_speed_mps: float       # 最大速度 m/s
    avg_speed_mps: float       # 平均速度 m/s
    initial_speed_mps: float   # 初始速度 m/s
    max_speed_kmh: float       # 最大速度 km/h
    avg_speed_kmh: float       # 平均速度 km/h


@dataclass
class MotionStats:
    """运动统计"""
    total_distance_px: float   # 总移动距离（像素）
    max_displacement_px: float # 最大单帧位移（像素）
    avg_displacement_px: float # 平均单帧位移（像素）
    direction_changes: int     # 方向变化次数
    avg_blur_length: Optional[float] = None  # 平均模糊长度


@dataclass
class BouncePoint:
    """落点信息"""
    frame_idx: int
    timestamp_ms: float
    x: float
    y: float
    bounce_type: str  # "table", "ground", "other"


@dataclass
class AnalysisResult:
    """轨迹分析结果"""
    track_id: str
    speed_stats: Optional[SpeedStats] = None
    motion_stats: Optional[MotionStats] = None
    bounce_points: Optional[List[BouncePoint]] = None
    stroke_type: Optional[str] = None


class TrajectoryAnalyzer:
    """
    轨迹分析器
    从轨迹提取物理信息
    """

    # 乒乓球桌尺寸（毫米）
    TABLE_LENGTH_MM = 2740
    TABLE_WIDTH_MM = 1525
    TABLE_HEIGHT_MM = 760
    NET_HEIGHT_MM = 152.5

    # 假设像素到米的转换比例（需要根据相机标定调整）
    DEFAULT_PIXELS_PER_METER = 500.0

    def __init__(
        self,
        pixels_per_meter: float = 500.0,
        bounce_velocity_threshold: float = 0.3,
    ):
        """
        初始化分析器

        Args:
            pixels_per_meter: 像素到米的转换比例
            bounce_velocity_threshold: 落点检测速度阈值（垂直方向）
        """
        self.pixels_per_meter = pixels_per_meter
        self.bounce_velocity_threshold = bounce_velocity_threshold

    def analyze_track(self, track: BallTrack) -> AnalysisResult:
        """
        分析单条轨迹

        Args:
            track: 球轨迹

        Returns:
            分析结果
        """
        if len(track.points) < 2:
            return AnalysisResult(track_id=track.track_id)

        # 计算速度统计
        speed_stats = self._compute_speed_stats(track)

        # 计算运动统计
        motion_stats = self._compute_motion_stats(track)

        # 检测落点
        bounce_points = self._detect_bounces(track)

        # 分类击球类型
        stroke_type = self._classify_stroke(track, speed_stats)

        return AnalysisResult(
            track_id=track.track_id,
            speed_stats=speed_stats,
            motion_stats=motion_stats,
            bounce_points=bounce_points,
            stroke_type=stroke_type,
        )

    def _compute_speed_stats(self, track: BallTrack) -> SpeedStats:
        """计算速度统计"""
        speeds_mps: List[float] = []

        for i in range(1, len(track.points)):
            p1 = track.points[i - 1]
            p2 = track.points[i]

            # 计算位移（像素）
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            distance_px = np.sqrt(dx * dx + dy * dy)

            # 计算时间差（秒）
            dt_ms = p2.timestamp_ms - p1.timestamp_ms
            if dt_ms <= 0:
                continue
            dt_s = dt_ms / 1000.0

            # 转换为米/秒
            distance_m = distance_px / self.pixels_per_meter
            speed_mps = distance_m / dt_s

            speeds_mps.append(speed_mps)

        if not speeds_mps:
            return SpeedStats(
                max_speed_mps=0.0,
                avg_speed_mps=0.0,
                initial_speed_mps=0.0,
                max_speed_kmh=0.0,
                avg_speed_kmh=0.0,
            )

        max_speed = max(speeds_mps)
        avg_speed = sum(speeds_mps) / len(speeds_mps)
        initial_speed = speeds_mps[0] if speeds_mps else 0.0

        return SpeedStats(
            max_speed_mps=max_speed,
            avg_speed_mps=avg_speed,
            initial_speed_mps=initial_speed,
            max_speed_kmh=max_speed * 3.6,
            avg_speed_kmh=avg_speed * 3.6,
        )

    def _compute_motion_stats(self, track: BallTrack) -> MotionStats:
        """计算运动统计"""
        displacements: List[float] = []
        directions: List[float] = []
        blur_lengths: List[float] = []

        for i in range(1, len(track.points)):
            p1 = track.points[i - 1]
            p2 = track.points[i]

            # 计算位移
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            displacement = np.sqrt(dx * dx + dy * dy)
            displacements.append(displacement)

            # 计算方向
            direction = np.arctan2(dy, dx)
            directions.append(direction)

            # 收集模糊长度
            if p2.blur_length is not None:
                blur_lengths.append(p2.blur_length)

        # 计算方向变化次数
        direction_changes = 0
        direction_threshold = np.pi / 4  # 45度
        for i in range(1, len(directions)):
            angle_diff = abs(directions[i] - directions[i - 1])
            if angle_diff > np.pi:
                angle_diff = 2 * np.pi - angle_diff
            if angle_diff > direction_threshold:
                direction_changes += 1

        total_distance = sum(displacements) if displacements else 0.0
        max_displacement = max(displacements) if displacements else 0.0
        avg_displacement = total_distance / len(displacements) if displacements else 0.0
        avg_blur = sum(blur_lengths) / len(blur_lengths) if blur_lengths else None

        return MotionStats(
            total_distance_px=total_distance,
            max_displacement_px=max_displacement,
            avg_displacement_px=avg_displacement,
            direction_changes=direction_changes,
            avg_blur_length=avg_blur,
        )

    def _detect_bounces(self, track: BallTrack) -> List[BouncePoint]:
        """
        检测落点

        通过检测 y 方向速度的符号变化来识别落点
        """
        bounces: List[BouncePoint] = []

        if len(track.points) < 3:
            return bounces

        # 计算 y 方向速度
        vy_list: List[float] = []
        for i in range(1, len(track.points)):
            p1 = track.points[i - 1]
            p2 = track.points[i]
            dt_ms = p2.timestamp_ms - p1.timestamp_ms
            if dt_ms > 0:
                vy = (p2.y - p1.y) / dt_ms
                vy_list.append(vy)
            else:
                vy_list.append(0.0)

        # 检测速度符号变化（从正变负表示从下降变为上升，即落点）
        for i in range(1, len(vy_list)):
            # 检测从向下运动变为向上运动的点
            if vy_list[i - 1] > self.bounce_velocity_threshold and vy_list[i] < -self.bounce_velocity_threshold:
                # 这是一个可能的落点
                point = track.points[i]
                bounces.append(
                    BouncePoint(
                        frame_idx=point.frame_idx,
                        timestamp_ms=point.timestamp_ms,
                        x=point.x,
                        y=point.y,
                        bounce_type="table",  # 默认假设是桌面落点
                    )
                )

        return bounces

    def _classify_stroke(
        self,
        track: BallTrack,
        speed_stats: Optional[SpeedStats],
    ) -> Optional[str]:
        """
        分类击球类型

        基于速度、轨迹形状等特征进行分类
        """
        if speed_stats is None or len(track.points) < 3:
            return None

        # 简单分类规则
        avg_speed_kmh = speed_stats.avg_speed_kmh

        # 计算轨迹的平均 y 方向变化
        y_coords = [p.y for p in track.points]
        y_range = max(y_coords) - min(y_coords)

        # 计算 x 方向总位移
        x_displacement = abs(track.points[-1].x - track.points[0].x)

        # 基于速度和轨迹形状分类
        if avg_speed_kmh < 20:
            if y_range < 50:
                return "push"  # 搓球
            else:
                return "chop"  # 削球
        elif avg_speed_kmh < 60:
            if y_range > 100:
                return "loop"  # 弧圈球
            else:
                return "drive"  # 快攻
        else:
            if x_displacement < 100:
                return "smash"  # 扣杀
            else:
                return "drive"  # 快攻

    def analyze_multiple(self, tracks: List[BallTrack]) -> List[AnalysisResult]:
        """
        分析多条轨迹

        Args:
            tracks: 轨迹列表

        Returns:
            分析结果列表
        """
        results = []
        for track in tracks:
            result = self.analyze_track(track)
            results.append(result)

        logger.info(f"完成 {len(results)} 条轨迹的分析")
        return results


def get_analyzer(
    pixels_per_meter: Optional[float] = None,
) -> TrajectoryAnalyzer:
    """
    获取轨迹分析器实例

    Args:
        pixels_per_meter: 像素到米的转换比例

    Returns:
        TrajectoryAnalyzer 实例
    """
    return TrajectoryAnalyzer(
        pixels_per_meter=pixels_per_meter or TrajectoryAnalyzer.DEFAULT_PIXELS_PER_METER,
    )
