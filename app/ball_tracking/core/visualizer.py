"""
可视化模块
生成轨迹叠加视频和分析图表
"""

from typing import List, Optional, Tuple
from pathlib import Path
import numpy as np
import cv2
from loguru import logger

from app.ball_tracking.core.tracker import BallTrack
from app.ball_tracking.core.video_processor import VideoProcessor, save_video


class TrajectoryVisualizer:
    """
    轨迹可视化器
    """

    # 默认颜色 (BGR)
    DEFAULT_COLORS = {
        "trajectory": (0, 255, 0),      # 绿色
        "current_point": (0, 0, 255),   # 红色
        "interpolated": (255, 165, 0),  # 橙色
        "bounce": (255, 0, 255),        # 紫色
        "text": (255, 255, 255),        # 白色
        "background": (0, 0, 0),        # 黑色
    }

    def __init__(
        self,
        line_color: Tuple[int, int, int] = (0, 255, 0),
        point_color: Tuple[int, int, int] = (0, 0, 255),
        line_thickness: int = 2,
        point_radius: int = 5,
        trail_length: int = 30,
        show_blur: bool = True,
    ):
        """
        初始化可视化器

        Args:
            line_color: 轨迹线颜色 (BGR)
            point_color: 当前点颜色 (BGR)
            line_thickness: 轨迹线粗细
            point_radius: 点半径
            trail_length: 轨迹尾巴长度（帧数）
            show_blur: 是否显示模糊方向
        """
        self.line_color = line_color
        self.point_color = point_color
        self.line_thickness = line_thickness
        self.point_radius = point_radius
        self.trail_length = trail_length
        self.show_blur = show_blur

    def draw_track_on_frame(
        self,
        frame: np.ndarray,
        track: BallTrack,
        current_frame_idx: int,
        show_info: bool = True,
    ) -> np.ndarray:
        """
        在帧上绘制轨迹

        Args:
            frame: 视频帧 (BGR)
            track: 球轨迹
            current_frame_idx: 当前帧索引
            show_info: 是否显示信息文本

        Returns:
            绘制后的帧
        """
        result = frame.copy()

        # 找到当前帧之前的轨迹点
        visible_points = [
            p for p in track.points
            if p.frame_idx <= current_frame_idx
            and p.frame_idx >= current_frame_idx - self.trail_length
        ]

        if not visible_points:
            return result

        # 绘制轨迹线
        for i in range(1, len(visible_points)):
            p1 = visible_points[i - 1]
            p2 = visible_points[i]

            # 根据是否插值选择颜色
            color = self.DEFAULT_COLORS["interpolated"] if p2.interpolated else self.line_color

            # 根据时间计算透明度
            age = current_frame_idx - p2.frame_idx
            max(0.2, 1.0 - age / self.trail_length)

            # 绘制线段
            pt1 = (int(p1.x), int(p1.y))
            pt2 = (int(p2.x), int(p2.y))
            cv2.line(result, pt1, pt2, color, self.line_thickness)

        # 绘制当前点
        current_points = [p for p in visible_points if p.frame_idx == current_frame_idx]
        if current_points:
            current = current_points[0]
            center = (int(current.x), int(current.y))
            cv2.circle(result, center, self.point_radius, self.point_color, -1)
            cv2.circle(result, center, self.point_radius + 2, (255, 255, 255), 1)

            # 绘制模糊方向
            if self.show_blur and current.blur_angle is not None and current.blur_length is not None:
                angle_rad = np.radians(current.blur_angle)
                length = current.blur_length / 2
                dx = int(length * np.cos(angle_rad))
                dy = int(length * np.sin(angle_rad))
                pt1 = (center[0] - dx, center[1] - dy)
                pt2 = (center[0] + dx, center[1] + dy)
                cv2.line(result, pt1, pt2, (255, 255, 0), 2)

            # 显示信息
            if show_info:
                info_text = f"Conf: {current.confidence:.2f}"
                cv2.putText(
                    result,
                    info_text,
                    (center[0] + 10, center[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    self.DEFAULT_COLORS["text"],
                    1,
                )

        return result

    def generate_overlay_video(
        self,
        input_video_path: str,
        output_video_path: str,
        tracks: List[BallTrack],
        show_info: bool = True,
    ) -> str:
        """
        生成轨迹叠加视频

        Args:
            input_video_path: 输入视频路径
            output_video_path: 输出视频路径
            tracks: 轨迹列表
            show_info: 是否显示信息文本

        Returns:
            输出视频路径
        """
        logger.info(f"生成轨迹叠加视频: {output_video_path}")

        output_path = Path(output_video_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with VideoProcessor(input_video_path) as video:
            metadata = video.get_metadata()
            result_frames = []

            for frame_idx, frame in video.extract_frames():
                # 在帧上绘制所有轨迹
                result_frame = frame.copy()
                for track in tracks:
                    result_frame = self.draw_track_on_frame(
                        result_frame,
                        track,
                        frame_idx,
                        show_info=show_info,
                    )

                # 添加帧信息
                info_text = f"Frame: {frame_idx}"
                cv2.putText(
                    result_frame,
                    info_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    self.DEFAULT_COLORS["text"],
                    2,
                )

                result_frames.append(result_frame)

            # 保存视频
            save_video(result_frames, str(output_path), metadata.fps)

        logger.info(f"轨迹叠加视频已保存: {output_path}")
        return str(output_path)

    def generate_trajectory_image(
        self,
        track: BallTrack,
        image_size: Tuple[int, int] = (1280, 720),
        background_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> np.ndarray:
        """
        生成轨迹图像

        Args:
            track: 球轨迹
            image_size: 图像尺寸 (width, height)
            background_color: 背景颜色

        Returns:
            轨迹图像
        """
        width, height = image_size
        image = np.full((height, width, 3), background_color, dtype=np.uint8)

        if len(track.points) < 2:
            return image

        # 获取坐标范围
        coords = track.to_numpy()
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)

        # 添加边距
        margin = 50
        x_range = x_max - x_min
        y_range = y_max - y_min
        if x_range == 0:
            x_range = 1
        if y_range == 0:
            y_range = 1

        # 计算缩放
        scale_x = (width - 2 * margin) / x_range
        scale_y = (height - 2 * margin) / y_range
        scale = min(scale_x, scale_y)

        # 绘制轨迹
        for i in range(1, len(track.points)):
            p1 = track.points[i - 1]
            p2 = track.points[i]

            x1 = int(margin + (p1.x - x_min) * scale)
            y1 = int(margin + (p1.y - y_min) * scale)
            x2 = int(margin + (p2.x - x_min) * scale)
            y2 = int(margin + (p2.y - y_min) * scale)

            color = self.DEFAULT_COLORS["interpolated"] if p2.interpolated else self.line_color
            cv2.line(image, (x1, y1), (x2, y2), color, self.line_thickness)

        # 绘制起点和终点
        start = track.points[0]
        end = track.points[-1]

        start_pt = (int(margin + (start.x - x_min) * scale), int(margin + (start.y - y_min) * scale))
        end_pt = (int(margin + (end.x - x_min) * scale), int(margin + (end.y - y_min) * scale))

        cv2.circle(image, start_pt, 8, (0, 255, 0), -1)  # 绿色起点
        cv2.circle(image, end_pt, 8, (0, 0, 255), -1)    # 红色终点

        # 添加标签
        cv2.putText(image, "Start", (start_pt[0] + 10, start_pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(image, "End", (end_pt[0] + 10, end_pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        return image

    def generate_preview_frame(
        self,
        video_path: str,
        tracks: List[BallTrack],
        frame_idx: int = 0,
    ) -> np.ndarray:
        """
        生成预览帧

        Args:
            video_path: 视频路径
            tracks: 轨迹列表
            frame_idx: 帧索引

        Returns:
            预览帧图像
        """
        with VideoProcessor(video_path) as video:
            frame = video.get_frame(frame_idx)
            if frame is None:
                raise ValueError(f"无法读取帧 {frame_idx}")

            # 绘制轨迹
            for track in tracks:
                frame = self.draw_track_on_frame(frame, track, frame_idx, show_info=True)

            return frame


def get_visualizer(
    line_color: Optional[Tuple[int, int, int]] = None,
    point_color: Optional[Tuple[int, int, int]] = None,
    trail_length: int = 30,
) -> TrajectoryVisualizer:
    """
    获取可视化器实例

    Args:
        line_color: 轨迹线颜色
        point_color: 当前点颜色
        trail_length: 轨迹尾巴长度

    Returns:
        TrajectoryVisualizer 实例
    """
    return TrajectoryVisualizer(
        line_color=line_color or (0, 255, 0),
        point_color=point_color or (0, 0, 255),
        trail_length=trail_length,
    )
