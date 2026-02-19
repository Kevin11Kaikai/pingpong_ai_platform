"""
球追踪主 Pipeline
协调检测、追踪和分析流程
"""

from typing import Optional, List
from dataclasses import dataclass
import uuid
import time
from loguru import logger

from app.shared.gpu_manager import GPUManager
from app.ball_tracking.core.detector import BlurBallDetector, BallDetection, get_detector
from app.ball_tracking.core.tracker import BallTracker, BallTrack, get_tracker
from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer, AnalysisResult, get_analyzer
from app.ball_tracking.core.video_processor import VideoProcessor, VideoMetadata
from app.ball_tracking.core.visualizer import TrajectoryVisualizer, get_visualizer
from config.settings import get_settings


@dataclass
class PipelineConfig:
    """Pipeline 配置"""
    enable_trajectory_analysis: bool = True
    batch_size: int = 16
    detection_threshold: float = 0.5
    max_gap_frames: int = 5
    smooth_tracks: bool = True


@dataclass
class PipelineResult:
    """Pipeline 处理结果"""
    job_id: str
    video_metadata: VideoMetadata
    tracks: List[BallTrack]
    analysis_results: Optional[List[AnalysisResult]] = None
    processing_time_seconds: float = 0.0
    frame_count: int = 0
    detection_count: int = 0


class BallTrackingPipeline:
    """
    球追踪主 Pipeline

    处理流程:
    1. 视频读取和帧提取
    2. BlurBall 2D 检测（GPU）
    3. 多帧追踪和关联
    4. 轨迹分析

    显存管理:
    - 检测阶段使用 GPUManager 管理 GPU 显存
    - 追踪和分析在 CPU 上进行
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        初始化 Pipeline

        Args:
            config: Pipeline 配置
        """
        self.config = config or PipelineConfig()
        settings = get_settings()

        # 应用设置
        self.config.batch_size = settings.ball_tracking_batch_size
        self.config.detection_threshold = settings.ball_tracking_detection_threshold
        self.config.max_gap_frames = settings.ball_tracking_max_gap_frames

        # 组件（懒加载）
        self._detector: Optional[BlurBallDetector] = None
        self._tracker: Optional[BallTracker] = None
        self._analyzer: Optional[TrajectoryAnalyzer] = None
        self._visualizer: Optional[TrajectoryVisualizer] = None

    def _get_detector(self) -> BlurBallDetector:
        """获取检测器实例"""
        if self._detector is None:
            self._detector = get_detector(
                score_threshold=self.config.detection_threshold,
            )
        return self._detector

    def _get_tracker(self, fps: float) -> BallTracker:
        """获取追踪器实例"""
        self._tracker = get_tracker(
            max_gap_frames=self.config.max_gap_frames,
        )
        self._tracker.fps = fps
        return self._tracker

    def _get_analyzer(self) -> TrajectoryAnalyzer:
        """获取分析器实例"""
        if self._analyzer is None:
            self._analyzer = get_analyzer()
        return self._analyzer

    def _get_visualizer(self) -> TrajectoryVisualizer:
        """获取可视化器实例"""
        if self._visualizer is None:
            self._visualizer = get_visualizer()
        return self._visualizer

    async def process_video(
        self,
        video_path: str,
        progress_callback: Optional[callable] = None,
    ) -> PipelineResult:
        """
        处理视频文件

        Args:
            video_path: 视频文件路径
            progress_callback: 进度回调函数 (stage, progress_percent)

        Returns:
            处理结果
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        logger.info(f"开始处理视频: {video_path}, job_id={job_id}")

        # 1. 读取视频元数据
        if progress_callback:
            await progress_callback("reading_video", 0)

        video_processor = VideoProcessor(video_path)
        metadata = video_processor.get_metadata()
        logger.info(f"视频信息: {metadata.width}x{metadata.height}, {metadata.fps}fps, {metadata.total_frames}帧")

        # 2. 运行检测
        if progress_callback:
            await progress_callback("detecting", 10)

        detections = await self._run_detection(video_processor, progress_callback)
        logger.info(f"检测完成，共 {len(detections)} 帧")

        # 统计有效检测数
        detection_count = sum(1 for d in detections if d is not None and d.visible)

        # 3. 运行追踪
        if progress_callback:
            await progress_callback("tracking", 70)

        tracks = self._run_tracking(detections, metadata.fps)
        logger.info(f"追踪完成，生成 {len(tracks)} 条轨迹")

        # 4. 轨迹分析
        analysis_results = None
        if self.config.enable_trajectory_analysis:
            if progress_callback:
                await progress_callback("analyzing", 85)

            analysis_results = self._run_analysis(tracks)
            logger.info("分析完成")

        # 清理
        video_processor.close()

        processing_time = time.time() - start_time

        if progress_callback:
            await progress_callback("completed", 100)

        logger.info(f"处理完成，耗时 {processing_time:.2f} 秒")

        return PipelineResult(
            job_id=job_id,
            video_metadata=metadata,
            tracks=tracks,
            analysis_results=analysis_results,
            processing_time_seconds=processing_time,
            frame_count=metadata.total_frames,
            detection_count=detection_count,
        )

    async def _run_detection(
        self,
        video_processor: VideoProcessor,
        progress_callback: Optional[callable] = None,
    ) -> List[Optional[BallDetection]]:
        """
        运行检测阶段

        Args:
            video_processor: 视频处理器
            progress_callback: 进度回调

        Returns:
            检测结果列表
        """
        detections: List[Optional[BallDetection]] = []
        metadata = video_processor.get_metadata()

        with GPUManager.load_model("BlurBall"):
            detector = self._get_detector()
            detector.load_model()

            try:
                batch_count = 0
                total_batches = (metadata.total_frames + self.config.batch_size - 1) // self.config.batch_size

                for batch in video_processor.extract_frames_batch(batch_size=self.config.batch_size):
                    frames = [item[1] for item in batch]
                    indices = [item[0] for item in batch]

                    # 运行检测
                    batch_detections = detector.detect_frames(frames, indices)
                    detections.extend(batch_detections)

                    batch_count += 1

                    # 更新进度
                    if progress_callback:
                        progress = 10 + int(60 * batch_count / total_batches)
                        await progress_callback("detecting", progress)

            finally:
                detector.unload_model()

        return detections

    def _run_tracking(
        self,
        detections: List[Optional[BallDetection]],
        fps: float,
    ) -> List[BallTrack]:
        """
        运行追踪阶段

        Args:
            detections: 检测结果列表
            fps: 视频帧率

        Returns:
            轨迹列表
        """
        tracker = self._get_tracker(fps)
        tracks = tracker.process_detections(detections, fps)

        # 平滑轨迹
        if self.config.smooth_tracks:
            tracks = [tracker.smooth_track(track) for track in tracks]

        return tracks

    def _run_analysis(self, tracks: List[BallTrack]) -> List[AnalysisResult]:
        """
        运行分析阶段

        Args:
            tracks: 轨迹列表

        Returns:
            分析结果列表
        """
        analyzer = self._get_analyzer()
        return analyzer.analyze_multiple(tracks)

    async def generate_visualization(
        self,
        video_path: str,
        output_path: str,
        tracks: List[BallTrack],
    ) -> str:
        """
        生成可视化视频

        Args:
            video_path: 原始视频路径
            output_path: 输出视频路径
            tracks: 轨迹列表

        Returns:
            输出视频路径
        """
        visualizer = self._get_visualizer()
        return visualizer.generate_overlay_video(video_path, output_path, tracks)


def get_pipeline(config: Optional[PipelineConfig] = None) -> BallTrackingPipeline:
    """
    获取 Pipeline 实例

    Args:
        config: Pipeline 配置

    Returns:
        BallTrackingPipeline 实例
    """
    return BallTrackingPipeline(config)
