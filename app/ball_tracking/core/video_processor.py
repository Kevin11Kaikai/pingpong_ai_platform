"""
视频处理模块
负责视频读取、帧提取和预处理
"""

from typing import Generator, Tuple, Optional, List
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import cv2
from loguru import logger


@dataclass
class VideoMetadata:
    """视频元数据"""
    path: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    codec: str


class VideoProcessor:
    """
    视频处理器
    支持多种视频格式的读取和帧提取
    """

    SUPPORTED_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

    def __init__(self, video_path: str):
        """
        初始化视频处理器

        Args:
            video_path: 视频文件路径
        """
        self.video_path = Path(video_path)
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None

        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        suffix = self.video_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的视频格式: {suffix}")

    def _ensure_capture(self) -> cv2.VideoCapture:
        """确保视频捕获对象已打开"""
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(str(self.video_path))
            if not self._cap.isOpened():
                raise RuntimeError(f"无法打开视频: {self.video_path}")
        return self._cap

    def _load_metadata(self) -> None:
        """加载视频元数据"""
        cap = self._ensure_capture()

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 获取编码器信息
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

        duration = total_frames / fps if fps > 0 else 0.0

        self._metadata = VideoMetadata(
            path=str(self.video_path),
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=duration,
            codec=codec,
        )

        logger.info(
            f"视频元数据: {width}x{height}, {fps:.2f}fps, "
            f"{total_frames}帧, {duration:.2f}秒"
        )

    def get_metadata(self) -> VideoMetadata:
        """获取视频元数据"""
        if self._metadata is None:
            self._load_metadata()
        return self._metadata

    def extract_frames(
        self,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        step: int = 1,
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        提取视频帧

        Args:
            start_frame: 起始帧索引
            end_frame: 结束帧索引（不包含），None 表示到视频末尾
            step: 帧间隔

        Yields:
            (frame_index, frame_array) 元组，frame_array 为 BGR 格式
        """
        cap = self._ensure_capture()
        metadata = self.get_metadata()

        if end_frame is None:
            end_frame = metadata.total_frames

        # 设置起始位置
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        current_frame = start_frame
        while current_frame < end_frame:
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"读取帧 {current_frame} 失败，提前结束")
                break

            yield current_frame, frame

            # 跳帧
            if step > 1:
                skip_count = step - 1
                for _ in range(skip_count):
                    cap.read()
                    current_frame += 1
                    if current_frame >= end_frame:
                        break

            current_frame += 1

    def extract_frames_batch(
        self,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        batch_size: int = 16,
    ) -> Generator[List[Tuple[int, np.ndarray]], None, None]:
        """
        批量提取视频帧

        Args:
            start_frame: 起始帧索引
            end_frame: 结束帧索引
            batch_size: 批次大小

        Yields:
            帧批次列表 [(frame_index, frame_array), ...]
        """
        batch: List[Tuple[int, np.ndarray]] = []

        for frame_idx, frame in self.extract_frames(start_frame, end_frame):
            batch.append((frame_idx, frame))

            if len(batch) >= batch_size:
                yield batch
                batch = []

        # 返回剩余帧
        if batch:
            yield batch

    def extract_clip(
        self,
        start_time: float,
        end_time: float,
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        按时间提取片段

        Args:
            start_time: 起始时间（秒）
            end_time: 结束时间（秒）

        Yields:
            (frame_index, frame_array) 元组
        """
        metadata = self.get_metadata()
        start_frame = int(start_time * metadata.fps)
        end_frame = int(end_time * metadata.fps)

        yield from self.extract_frames(start_frame, end_frame)

    def get_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """
        获取指定帧

        Args:
            frame_idx: 帧索引

        Returns:
            帧数组或 None
        """
        cap = self._ensure_capture()
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if ret:
            return frame
        return None

    def close(self) -> None:
        """释放资源"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.debug("视频捕获对象已释放")

    def __enter__(self) -> "VideoProcessor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()


def save_video(
    frames: List[np.ndarray],
    output_path: str,
    fps: float,
    codec: str = "mp4v",
) -> str:
    """
    保存视频

    Args:
        frames: 帧列表 (BGR 格式)
        output_path: 输出路径
        fps: 帧率
        codec: 编码器

    Returns:
        输出文件路径
    """
    if not frames:
        raise ValueError("帧列表为空")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    try:
        for frame in frames:
            writer.write(frame)
        logger.info(f"视频已保存: {output_path}, {len(frames)}帧")
    finally:
        writer.release()

    return str(output_path)
