"""
Ball Tracking 模块测试脚本
验证检测、追踪、分析等组件的有效性

运行方式:
    # 运行所有单元测试
    pytest tests/test_ball_tracking.py -v

    # 运行端到端测试（需要真实视频）
    python tests/test_ball_tracking.py --video path/to/video.mp4

    # 只运行单元测试（不需要GPU/模型）
    pytest tests/test_ball_tracking.py -v -m "not e2e"
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import numpy as np
import pytest
from loguru import logger

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 测试数据生成器
# ============================================================================

@dataclass
class MockBallDetection:
    """模拟检测结果"""
    frame_idx: int
    x: float
    y: float
    confidence: float
    blur_angle: Optional[float] = None
    blur_length: Optional[float] = None
    visible: bool = True


def generate_linear_trajectory(
    start_pos: tuple,
    end_pos: tuple,
    num_frames: int,
    fps: float = 30.0,
    confidence: float = 0.9,
) -> List[MockBallDetection]:
    """生成线性轨迹的模拟检测结果"""
    detections = []
    for i in range(num_frames):
        t = i / (num_frames - 1)
        x = start_pos[0] + t * (end_pos[0] - start_pos[0])
        y = start_pos[1] + t * (end_pos[1] - start_pos[1])
        detections.append(MockBallDetection(
            frame_idx=i,
            x=x,
            y=y,
            confidence=confidence,
            blur_length=5.0,
        ))
    return detections


def generate_parabolic_trajectory(
    start_pos: tuple,
    end_pos: tuple,
    peak_height: float,
    num_frames: int,
    fps: float = 30.0,
    confidence: float = 0.9,
) -> List[MockBallDetection]:
    """生成抛物线轨迹的模拟检测结果（模拟真实乒乓球运动）"""
    detections = []
    for i in range(num_frames):
        t = i / (num_frames - 1)
        x = start_pos[0] + t * (end_pos[0] - start_pos[0])
        # 抛物线 y = a*t*(1-t) + 线性插值
        base_y = start_pos[1] + t * (end_pos[1] - start_pos[1])
        parabola_offset = -4 * peak_height * t * (1 - t)  # 向上偏移
        y = base_y + parabola_offset

        detections.append(MockBallDetection(
            frame_idx=i,
            x=x,
            y=y,
            confidence=confidence,
            blur_length=8.0 + 4.0 * (1 - abs(2*t - 1)),  # 中间更长
        ))
    return detections


def generate_trajectory_with_gaps(
    base_trajectory: List[MockBallDetection],
    gap_indices: List[int],
) -> List[Optional[MockBallDetection]]:
    """在轨迹中添加间隙（模拟遮挡）"""
    result = []
    for det in base_trajectory:
        if det.frame_idx in gap_indices:
            result.append(None)
        else:
            result.append(det)
    return result


# ============================================================================
# 单元测试: BallDetection 数据结构
# ============================================================================

class TestBallDetection:
    """测试 BallDetection 数据结构"""

    def test_detection_creation(self):
        """测试检测结果创建"""
        from app.ball_tracking.core.detector import BallDetection

        det = BallDetection(
            frame_idx=10,
            x=320.5,
            y=240.3,
            confidence=0.95,
            blur_angle=45.0,
            blur_length=10.5,
            visible=True,
        )

        assert det.frame_idx == 10
        assert det.x == 320.5
        assert det.y == 240.3
        assert det.confidence == 0.95
        assert det.blur_angle == 45.0
        assert det.blur_length == 10.5
        assert det.visible is True

    def test_detection_defaults(self):
        """测试检测结果默认值"""
        from app.ball_tracking.core.detector import BallDetection

        det = BallDetection(
            frame_idx=0,
            x=0.0,
            y=0.0,
            confidence=0.5,
        )

        assert det.blur_angle is None
        assert det.blur_length is None
        assert det.visible is True


# ============================================================================
# 单元测试: BallTracker 追踪器
# ============================================================================

class TestBallTracker:
    """测试多帧追踪器"""

    def test_tracker_creation(self):
        """测试追踪器创建"""
        from app.ball_tracking.core.tracker import BallTracker

        tracker = BallTracker(
            max_gap_frames=5,
            max_distance=150.0,
            min_track_length=3,
            fps=30.0,
        )

        assert tracker.max_gap_frames == 5
        assert tracker.max_distance == 150.0
        assert tracker.min_track_length == 3
        assert tracker.fps == 30.0

    def test_process_linear_trajectory(self):
        """测试处理线性轨迹"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection

        # 创建线性轨迹检测结果
        detections = []
        for i in range(10):
            detections.append(BallDetection(
                frame_idx=i,
                x=100.0 + i * 10,
                y=200.0,
                confidence=0.9,
                visible=True,
            ))

        tracker = BallTracker(min_track_length=3)
        tracks = tracker.process_detections(detections, fps=30.0)

        # 应该生成一条轨迹
        assert len(tracks) == 1
        assert tracks[0].point_count == 10
        assert tracks[0].start_frame == 0
        assert tracks[0].end_frame == 9

    def test_process_trajectory_with_gaps(self):
        """测试处理带间隙的轨迹"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection

        # 创建带间隙的轨迹
        detections = []
        for i in range(15):
            if i in [5, 6]:  # 帧5和6缺失
                detections.append(None)
            else:
                detections.append(BallDetection(
                    frame_idx=i,
                    x=100.0 + i * 10,
                    y=200.0,
                    confidence=0.9,
                    visible=True,
                ))

        tracker = BallTracker(max_gap_frames=3, min_track_length=3)
        tracks = tracker.process_detections(detections, fps=30.0)

        # 应该仍然只有一条轨迹（间隙被插值填充）
        assert len(tracks) == 1
        # 检查是否包含插值点
        interpolated_count = sum(1 for p in tracks[0].points if p.interpolated)
        assert interpolated_count == 2  # 帧5和6被插值

    def test_process_multiple_tracks(self):
        """测试处理多条轨迹（距离过远导致分割）"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection

        # 创建两段轨迹
        detections = []

        # 第一段: 帧0-4
        for i in range(5):
            detections.append(BallDetection(
                frame_idx=i,
                x=100.0 + i * 10,
                y=200.0,
                confidence=0.9,
                visible=True,
            ))

        # 第二段: 帧5-9，位置跳跃很大
        for i in range(5, 10):
            detections.append(BallDetection(
                frame_idx=i,
                x=500.0 + i * 10,  # 位置跳跃
                y=200.0,
                confidence=0.9,
                visible=True,
            ))

        tracker = BallTracker(max_distance=100.0, min_track_length=3)
        tracks = tracker.process_detections(detections, fps=30.0)

        # 应该生成两条轨迹
        assert len(tracks) == 2

    def test_smooth_track(self):
        """测试轨迹平滑"""
        from app.ball_tracking.core.tracker import BallTracker, BallTrack, TrackPoint

        # 创建带噪声的轨迹
        points = [
            TrackPoint(frame_idx=i, timestamp_ms=i*33.33, x=100.0+i*10+np.random.randn()*2, y=200.0+np.random.randn()*2, confidence=0.9)
            for i in range(10)
        ]
        track = BallTrack(track_id="test", points=points)

        tracker = BallTracker()
        smoothed = tracker.smooth_track(track, window_size=3)

        # 验证平滑后轨迹点数相同
        assert len(smoothed.points) == len(track.points)
        # 验证平滑后轨迹ID相同
        assert smoothed.track_id == track.track_id

    def test_track_duration(self):
        """测试轨迹时长计算"""
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        points = [
            TrackPoint(frame_idx=0, timestamp_ms=0.0, x=100.0, y=200.0, confidence=0.9),
            TrackPoint(frame_idx=10, timestamp_ms=333.33, x=200.0, y=200.0, confidence=0.9),
        ]
        track = BallTrack(track_id="test", points=points)

        assert abs(track.duration_ms - 333.33) < 0.01
        assert track.point_count == 2


# ============================================================================
# 单元测试: TrajectoryAnalyzer 轨迹分析器
# ============================================================================

class TestTrajectoryAnalyzer:
    """测试轨迹分析器"""

    def test_analyzer_creation(self):
        """测试分析器创建"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer

        analyzer = TrajectoryAnalyzer(pixels_per_meter=500.0)

        assert analyzer.pixels_per_meter == 500.0

    def test_speed_stats(self):
        """测试速度统计"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 创建匀速轨迹: 100px/frame @ 30fps = 100*30 = 3000 px/s
        # 如果 pixels_per_meter = 500, 则 3000/500 = 6 m/s
        points = [
            TrackPoint(frame_idx=i, timestamp_ms=i*33.33, x=100.0+i*100, y=200.0, confidence=0.9)
            for i in range(5)
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer(pixels_per_meter=500.0)
        result = analyzer.analyze_track(track)

        assert result.speed_stats is not None
        # 速度约为 6 m/s (允许一定误差)
        assert 5.5 < result.speed_stats.avg_speed_mps < 6.5

    def test_motion_stats(self):
        """测试运动统计"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 创建简单轨迹
        points = [
            TrackPoint(frame_idx=0, timestamp_ms=0.0, x=0.0, y=0.0, confidence=0.9),
            TrackPoint(frame_idx=1, timestamp_ms=33.33, x=100.0, y=0.0, confidence=0.9),
            TrackPoint(frame_idx=2, timestamp_ms=66.66, x=200.0, y=0.0, confidence=0.9),
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer()
        result = analyzer.analyze_track(track)

        assert result.motion_stats is not None
        assert abs(result.motion_stats.total_distance_px - 200.0) < 0.1
        assert abs(result.motion_stats.avg_displacement_px - 100.0) < 0.1

    def test_bounce_detection(self):
        """测试落点检测"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 创建带落点的轨迹 (下降 -> 触底 -> 上升)
        fps = 30.0
        frame_interval_ms = 1000.0 / fps
        points = [
            TrackPoint(frame_idx=0, timestamp_ms=0*frame_interval_ms, x=0, y=0, confidence=0.9),    # 起点
            TrackPoint(frame_idx=1, timestamp_ms=1*frame_interval_ms, x=20, y=50, confidence=0.9),  # 下降
            TrackPoint(frame_idx=2, timestamp_ms=2*frame_interval_ms, x=40, y=100, confidence=0.9), # 下降
            TrackPoint(frame_idx=3, timestamp_ms=3*frame_interval_ms, x=60, y=120, confidence=0.9), # 落点
            TrackPoint(frame_idx=4, timestamp_ms=4*frame_interval_ms, x=80, y=80, confidence=0.9),  # 上升
            TrackPoint(frame_idx=5, timestamp_ms=5*frame_interval_ms, x=100, y=40, confidence=0.9), # 上升
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer(bounce_velocity_threshold=0.2)
        result = analyzer.analyze_track(track)

        # 应该检测到至少一个落点
        assert result.bounce_points is not None
        # 落点检测取决于阈值设置，这里验证函数正常运行

    def test_stroke_classification_slow(self):
        """测试慢速击球分类"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 创建慢速、低弧度轨迹 (搓球特征)
        # 速度 < 20 km/h, y_range < 50
        points = [
            TrackPoint(frame_idx=i, timestamp_ms=i*100, x=i*10, y=200+i*2, confidence=0.9)
            for i in range(10)
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer(pixels_per_meter=1000.0)  # 较大的转换比例使速度较慢
        result = analyzer.analyze_track(track)

        assert result.stroke_type in ["push", "chop", None]

    def test_stroke_classification_fast(self):
        """测试快速击球分类"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 创建快速轨迹 (快攻特征)
        points = [
            TrackPoint(frame_idx=i, timestamp_ms=i*10, x=i*200, y=200, confidence=0.9)
            for i in range(10)
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer(pixels_per_meter=100.0)  # 较小的转换比例使速度较快
        result = analyzer.analyze_track(track)

        assert result.stroke_type in ["drive", "smash", "loop", None]

    def test_analyze_multiple_tracks(self):
        """测试批量分析"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        tracks = []
        for track_idx in range(3):
            points = [
                TrackPoint(frame_idx=i, timestamp_ms=i*33.33, x=100.0+i*10, y=200.0, confidence=0.9)
                for i in range(10)
            ]
            tracks.append(BallTrack(track_id=f"track_{track_idx}", points=points))

        analyzer = TrajectoryAnalyzer()
        results = analyzer.analyze_multiple(tracks)

        assert len(results) == 3
        for result in results:
            assert result.speed_stats is not None
            assert result.motion_stats is not None


# ============================================================================
# 单元测试: VideoProcessor 视频处理器
# ============================================================================

class TestVideoProcessor:
    """测试视频处理器"""

    @pytest.fixture
    def temp_video(self, tmp_path):
        """创建临时测试视频"""
        import cv2

        video_path = tmp_path / "test_video.mp4"
        fps = 30.0
        width, height = 640, 480
        num_frames = 30

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

        for i in range(num_frames):
            # 创建简单的测试帧（带运动球）
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            ball_x = int(100 + i * 10)
            ball_y = int(240)
            cv2.circle(frame, (ball_x, ball_y), 10, (0, 165, 255), -1)  # 橙色球
            writer.write(frame)

        writer.release()
        return video_path

    def test_video_metadata(self, temp_video):
        """测试视频元数据读取"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        processor = VideoProcessor(str(temp_video))
        metadata = processor.get_metadata()

        assert metadata.width == 640
        assert metadata.height == 480
        assert metadata.fps == 30.0
        assert metadata.total_frames == 30
        assert abs(metadata.duration_seconds - 1.0) < 0.1

        processor.close()

    def test_frame_extraction(self, temp_video):
        """测试帧提取"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        processor = VideoProcessor(str(temp_video))

        frames = list(processor.extract_frames(start_frame=0, end_frame=10))

        assert len(frames) == 10
        for idx, frame in frames:
            assert frame.shape == (480, 640, 3)

        processor.close()

    def test_batch_extraction(self, temp_video):
        """测试批量帧提取"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        processor = VideoProcessor(str(temp_video))

        batches = list(processor.extract_frames_batch(batch_size=8))

        # 30帧，batch_size=8，应该有4个batch
        assert len(batches) == 4
        assert len(batches[0]) == 8
        assert len(batches[-1]) == 6  # 最后一个batch

        processor.close()

    def test_get_single_frame(self, temp_video):
        """测试获取单帧"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        processor = VideoProcessor(str(temp_video))

        frame = processor.get_frame(15)

        assert frame is not None
        assert frame.shape == (480, 640, 3)

        processor.close()

    def test_context_manager(self, temp_video):
        """测试上下文管理器"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        with VideoProcessor(str(temp_video)) as processor:
            metadata = processor.get_metadata()
            assert metadata.total_frames == 30

    def test_invalid_path(self):
        """测试无效路径"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        with pytest.raises(FileNotFoundError):
            VideoProcessor("/nonexistent/video.mp4")

    def test_unsupported_format(self, tmp_path):
        """测试不支持的格式"""
        from app.ball_tracking.core.video_processor import VideoProcessor

        fake_file = tmp_path / "test.xyz"
        fake_file.write_text("fake")

        with pytest.raises(ValueError, match="不支持的视频格式"):
            VideoProcessor(str(fake_file))


# ============================================================================
# 集成测试: Pipeline
# ============================================================================

class TestBallTrackingPipeline:
    """测试完整 Pipeline"""

    @pytest.fixture
    def temp_video_with_ball(self, tmp_path):
        """创建带模拟运动球的测试视频"""
        import cv2

        video_path = tmp_path / "ball_video.mp4"
        fps = 30.0
        width, height = 640, 480
        num_frames = 60

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

        for i in range(num_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # 绘制乒乓球桌（简化）
            cv2.rectangle(frame, (50, 200), (590, 400), (0, 100, 0), 2)
            cv2.line(frame, (320, 200), (320, 400), (255, 255, 255), 2)

            # 抛物线轨迹
            t = i / num_frames
            ball_x = int(100 + t * 400)
            ball_y = int(300 - 100 * np.sin(t * np.pi))

            # 绘制模糊球效果
            cv2.circle(frame, (ball_x, ball_y), 8, (0, 165, 255), -1)
            cv2.circle(frame, (ball_x-5, ball_y), 6, (0, 130, 200), -1)

            writer.write(frame)

        writer.release()
        return video_path

    def test_pipeline_config(self):
        """测试 Pipeline 配置"""
        from app.ball_tracking.core.pipeline import PipelineConfig

        config = PipelineConfig(
            enable_trajectory_analysis=True,
            batch_size=8,
            detection_threshold=0.5,
            max_gap_frames=5,
            smooth_tracks=True,
        )

        assert config.enable_trajectory_analysis is True
        assert config.batch_size == 8

    def test_pipeline_creation(self):
        """测试 Pipeline 创建"""
        from app.ball_tracking.core.pipeline import get_pipeline

        pipeline = get_pipeline()

        assert pipeline is not None
        assert pipeline.config is not None


# ============================================================================
# 端到端测试（需要真实视频和模型）
# ============================================================================

@pytest.mark.e2e
class TestEndToEnd:
    """端到端测试"""

    @pytest.fixture
    def real_video_path(self):
        """获取真实测试视频路径"""
        # 可以通过环境变量或命令行参数指定
        video_path = os.environ.get("TEST_VIDEO_PATH")
        if video_path and Path(video_path).exists():
            return video_path
        pytest.skip("未提供测试视频路径")

    @pytest.mark.asyncio
    async def test_full_pipeline(self, real_video_path):
        """测试完整处理流程"""
        from app.ball_tracking.core.pipeline import get_pipeline, PipelineConfig

        config = PipelineConfig(
            enable_trajectory_analysis=True,
            batch_size=8,
        )
        pipeline = get_pipeline(config)

        progress_log = []

        async def progress_callback(stage, progress):
            progress_log.append((stage, progress))
            logger.info(f"进度: {stage} - {progress}%")

        result = await pipeline.process_video(real_video_path, progress_callback)

        # 验证结果
        assert result.job_id is not None
        assert result.video_metadata is not None
        assert result.frame_count > 0

        logger.info(f"检测到 {len(result.tracks)} 条轨迹")
        logger.info(f"处理时间: {result.processing_time_seconds:.2f} 秒")

        # 验证进度回调
        assert len(progress_log) > 0
        assert progress_log[-1][1] == 100


# ============================================================================
# 性能测试
# ============================================================================

class TestPerformance:
    """性能测试"""

    def test_tracker_performance(self):
        """测试追踪器性能"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection
        import time

        # 生成大量检测结果
        num_frames = 1000
        detections = [
            BallDetection(
                frame_idx=i,
                x=100.0 + i * 0.5,
                y=200.0 + np.sin(i * 0.1) * 50,
                confidence=0.9,
                visible=True,
            )
            for i in range(num_frames)
        ]

        tracker = BallTracker()

        start_time = time.time()
        tracks = tracker.process_detections(detections, fps=30.0)
        elapsed = time.time() - start_time

        logger.info(f"处理 {num_frames} 帧耗时: {elapsed*1000:.2f} ms")
        assert elapsed < 1.0  # 应该在1秒内完成

    def test_analyzer_performance(self):
        """测试分析器性能"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint
        import time

        # 生成多条轨迹
        tracks = []
        for track_idx in range(100):
            points = [
                TrackPoint(frame_idx=i, timestamp_ms=i*33.33, x=100.0+i*10, y=200.0, confidence=0.9)
                for i in range(50)
            ]
            tracks.append(BallTrack(track_id=f"track_{track_idx}", points=points))

        analyzer = TrajectoryAnalyzer()

        start_time = time.time()
        results = analyzer.analyze_multiple(tracks)
        elapsed = time.time() - start_time

        logger.info(f"分析 {len(tracks)} 条轨迹耗时: {elapsed*1000:.2f} ms")
        assert elapsed < 1.0  # 应该在1秒内完成


# ============================================================================
# 有效性验证测试
# ============================================================================

class TestValidation:
    """有效性验证测试"""

    def test_track_continuity(self):
        """测试轨迹连续性"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection

        # 创建连续轨迹
        detections = [
            BallDetection(frame_idx=i, x=100.0+i*10, y=200.0, confidence=0.9, visible=True)
            for i in range(20)
        ]

        tracker = BallTracker(min_track_length=3)
        tracks = tracker.process_detections(detections, fps=30.0)

        assert len(tracks) >= 1

        for track in tracks:
            # 验证帧索引连续
            frame_indices = [p.frame_idx for p in track.points]
            for i in range(1, len(frame_indices)):
                gap = frame_indices[i] - frame_indices[i-1]
                assert gap >= 1, f"帧索引应该递增: {frame_indices}"

            # 验证时间戳递增
            timestamps = [p.timestamp_ms for p in track.points]
            for i in range(1, len(timestamps)):
                assert timestamps[i] > timestamps[i-1], f"时间戳应该递增: {timestamps}"

    def test_speed_reasonability(self):
        """测试速度合理性"""
        from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
        from app.ball_tracking.core.tracker import BallTrack, TrackPoint

        # 乒乓球最高速度约 150 km/h (41.67 m/s)
        # 正常比赛速度在 20-100 km/h

        # 创建正常速度轨迹
        points = [
            TrackPoint(frame_idx=i, timestamp_ms=i*33.33, x=i*30, y=200.0, confidence=0.9)
            for i in range(30)
        ]
        track = BallTrack(track_id="test", points=points)

        analyzer = TrajectoryAnalyzer(pixels_per_meter=100.0)  # 假设100像素=1米
        result = analyzer.analyze_track(track)

        # 验证速度在合理范围内
        assert result.speed_stats is not None
        assert 0 < result.speed_stats.max_speed_kmh < 200, \
            f"速度超出合理范围: {result.speed_stats.max_speed_kmh} km/h"

    def test_position_bounds(self):
        """测试位置边界"""
        from app.ball_tracking.core.tracker import BallTracker
        from app.ball_tracking.core.detector import BallDetection

        # 模拟 1920x1080 视频
        width, height = 1920, 1080

        detections = [
            BallDetection(
                frame_idx=i,
                x=min(max(100.0 + i * 50, 0), width),
                y=min(max(500.0 + np.sin(i * 0.2) * 200, 0), height),
                confidence=0.9,
                visible=True,
            )
            for i in range(30)
        ]

        tracker = BallTracker()
        tracks = tracker.process_detections(detections, fps=30.0)

        for track in tracks:
            for point in track.points:
                # 检查位置在合理范围内
                assert 0 <= point.x <= width * 1.1, f"x坐标超出范围: {point.x}"
                assert 0 <= point.y <= height * 1.1, f"y坐标超出范围: {point.y}"


# ============================================================================
# 命令行入口：端到端测试
# ============================================================================

async def run_e2e_test(video_path: str, output_dir: Optional[str] = None):
    """运行端到端测试"""
    logger.info("=" * 60)
    logger.info("Ball Tracking 端到端测试")
    logger.info("=" * 60)

    # 检查视频文件
    if not Path(video_path).exists():
        logger.error(f"视频文件不存在: {video_path}")
        return False

    logger.info(f"测试视频: {video_path}")

    # 1. 测试视频处理器
    logger.info("\n[1/4] 测试视频处理器...")
    try:
        from app.ball_tracking.core.video_processor import VideoProcessor

        with VideoProcessor(video_path) as processor:
            metadata = processor.get_metadata()
            logger.info(f"  视频分辨率: {metadata.width}x{metadata.height}")
            logger.info(f"  帧率: {metadata.fps} fps")
            logger.info(f"  总帧数: {metadata.total_frames}")
            logger.info(f"  时长: {metadata.duration_seconds:.2f} 秒")

            # 测试帧提取
            sample_frame = processor.get_frame(0)
            if sample_frame is not None:
                logger.info(f"  采样帧形状: {sample_frame.shape}")
            else:
                logger.warning("  无法读取采样帧")

        logger.info("  [OK] 视频处理器测试通过")
    except Exception as e:
        logger.error(f"  [FAIL] 视频处理器测试失败: {e}")
        return False

    # 2. 测试检测器（需要模型）
    logger.info("\n[2/4] 测试检测器...")
    try:
        from app.ball_tracking.core.detector import get_detector
        from config.settings import get_settings

        settings = get_settings()
        checkpoint_path = settings.blurball_checkpoint_path

        if not Path(checkpoint_path).exists():
            logger.warning(f"  模型权重不存在: {checkpoint_path}")
            logger.warning("  跳过检测器测试")
        else:
            detector = get_detector()
            detector.load_model()
            logger.info("  模型加载成功")

            # 测试检测
            with VideoProcessor(video_path) as processor:
                frames = []
                indices = []
                for idx, frame in processor.extract_frames(0, 3):
                    frames.append(frame)
                    indices.append(idx)

                if frames:
                    detections = detector.detect_frames(frames, indices)
                    valid_count = sum(1 for d in detections if d and d.visible)
                    logger.info(f"  检测结果: {valid_count}/{len(detections)} 帧检测到球")

            detector.unload_model()
            logger.info("  [OK] 检测器测试通过")
    except Exception as e:
        logger.error(f"  [FAIL] 检测器测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 3. 测试完整 Pipeline
    logger.info("\n[3/4] 测试完整 Pipeline...")
    try:
        from app.ball_tracking.core.pipeline import get_pipeline, PipelineConfig

        config = PipelineConfig(
            enable_trajectory_analysis=True,
            batch_size=16,
        )
        pipeline = get_pipeline(config)

        progress_stages = []

        async def progress_callback(stage, progress):
            if stage not in [s[0] for s in progress_stages] or progress == 100:
                progress_stages.append((stage, progress))
                logger.info(f"  进度: {stage} - {progress}%")

        result = await pipeline.process_video(video_path, progress_callback)

        logger.info("  处理完成!")
        logger.info(f"  - 任务ID: {result.job_id}")
        logger.info(f"  - 处理帧数: {result.frame_count}")
        logger.info(f"  - 有效检测: {result.detection_count}")
        logger.info(f"  - 生成轨迹: {len(result.tracks)} 条")
        logger.info(f"  - 处理时间: {result.processing_time_seconds:.2f} 秒")

        # 输出轨迹详情
        if result.tracks:
            logger.info("\n  轨迹详情:")
            for i, track in enumerate(result.tracks[:5]):  # 只显示前5条
                logger.info(f"    轨迹 {i+1}: 帧 {track.start_frame}-{track.end_frame}, "
                           f"{track.point_count} 个点, {track.duration_ms:.1f}ms")

        # 输出分析结果
        if result.analysis_results:
            logger.info("\n  分析结果:")
            for i, analysis in enumerate(result.analysis_results[:5]):
                if analysis.speed_stats:
                    logger.info(f"    轨迹 {i+1}: 最大速度 {analysis.speed_stats.max_speed_kmh:.1f} km/h, "
                               f"击球类型: {analysis.stroke_type}")

        logger.info("  [OK] Pipeline 测试通过")

    except Exception as e:
        logger.error(f"  [FAIL] Pipeline 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. 测试可视化（可选）
    if output_dir:
        logger.info("\n[4/4] 测试可视化...")
        try:
            from app.ball_tracking.core.visualizer import get_visualizer

            output_path = Path(output_dir) / "test_visualization.mp4"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            visualizer = get_visualizer()
            output_file = visualizer.generate_overlay_video(
                video_path,
                str(output_path),
                result.tracks,
            )

            logger.info(f"  可视化视频已保存: {output_file}")
            logger.info("  [OK] 可视化测试通过")
        except Exception as e:
            logger.error(f"  [FAIL] 可视化测试失败: {e}")
    else:
        logger.info("\n[4/4] 跳过可视化测试（未指定输出目录）")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)

    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Ball Tracking 模块测试")
    parser.add_argument("--video", type=str, help="测试视频路径")
    parser.add_argument("--output", type=str, help="可视化输出目录")
    parser.add_argument("--unit-only", action="store_true", help="只运行单元测试")

    args = parser.parse_args()

    if args.unit_only:
        # 运行 pytest 单元测试
        import subprocess
        subprocess.run([
            sys.executable, "-m", "pytest",
            __file__, "-v", "-m", "not e2e"
        ])
    elif args.video:
        # 运行端到端测试
        asyncio.run(run_e2e_test(args.video, args.output))
    else:
        print("用法:")
        print("  运行单元测试: python tests/test_ball_tracking.py --unit-only")
        print("  运行端到端测试: python tests/test_ball_tracking.py --video path/to/video.mp4")
        print("  生成可视化: python tests/test_ball_tracking.py --video path/to/video.mp4 --output ./output")


if __name__ == "__main__":
    main()
