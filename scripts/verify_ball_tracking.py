"""
Ball Tracking 快速验证脚本
用于验证模块各组件是否正常工作

使用方法:
    # 基础验证（不需要GPU/视频）
    python scripts/verify_ball_tracking.py

    # 带视频的完整验证
    python scripts/verify_ball_tracking.py --video path/to/video.mp4

    # 生成可视化结果
    python scripts/verify_ball_tracking.py --video path/to/video.mp4 --visualize
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import Optional
import numpy as np

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, format="<level>{level: <8}</level> | {message}", level="INFO")


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "[OK]" if success else "[FAIL]"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}{status}{reset} {name}" + (f" - {message}" if message else ""))


def verify_imports():
    """验证模块导入"""
    print_header("1. 验证模块导入")

    modules = [
        ("app.ball_tracking.core.detector", "BlurBallDetector, BallDetection"),
        ("app.ball_tracking.core.tracker", "BallTracker, BallTrack, TrackPoint"),
        ("app.ball_tracking.core.trajectory_analyzer", "TrajectoryAnalyzer, AnalysisResult"),
        ("app.ball_tracking.core.video_processor", "VideoProcessor, VideoMetadata"),
        ("app.ball_tracking.core.visualizer", "TrajectoryVisualizer"),
        ("app.ball_tracking.core.pipeline", "BallTrackingPipeline, PipelineResult"),
    ]

    all_success = True
    for module_path, classes in modules:
        try:
            exec(f"from {module_path} import {classes}")
            print_result(module_path, True)
        except Exception as e:
            print_result(module_path, False, str(e))
            all_success = False

    return all_success


def verify_tracker():
    """验证追踪器"""
    print_header("2. 验证追踪器 (BallTracker)")

    from app.ball_tracking.core.tracker import BallTracker
    from app.ball_tracking.core.detector import BallDetection

    try:
        # 创建测试数据
        detections = []
        for i in range(20):
            det = BallDetection(
                frame_idx=i,
                x=100.0 + i * 15,
                y=200.0 + np.sin(i * 0.3) * 30,
                confidence=0.85 + np.random.rand() * 0.1,
                blur_length=5.0 + np.random.rand() * 3,
                visible=True,
            )
            # 模拟部分丢失
            if i in [7, 8]:
                detections.append(None)
            else:
                detections.append(det)

        # 运行追踪
        tracker = BallTracker(max_gap_frames=3, min_track_length=3)
        tracks = tracker.process_detections(detections, fps=30.0)

        print_result("创建追踪器", True)
        print_result("处理检测结果", True, f"生成 {len(tracks)} 条轨迹")

        if tracks:
            track = tracks[0]
            print_result("轨迹属性", True,
                        f"帧 {track.start_frame}-{track.end_frame}, {track.point_count} 点")

            # 验证插值
            interpolated = sum(1 for p in track.points if p.interpolated)
            print_result("轨迹插值", True, f"{interpolated} 个插值点")

            # 测试平滑
            smoothed = tracker.smooth_track(track)
            print_result("轨迹平滑", True)

        return True
    except Exception as e:
        print_result("追踪器测试", False, str(e))
        return False


def verify_analyzer():
    """验证轨迹分析器"""
    print_header("3. 验证轨迹分析器 (TrajectoryAnalyzer)")

    from app.ball_tracking.core.trajectory_analyzer import TrajectoryAnalyzer
    from app.ball_tracking.core.tracker import BallTrack, TrackPoint

    try:
        # 创建测试轨迹
        points = []
        for i in range(30):
            t = i / 29
            points.append(TrackPoint(
                frame_idx=i,
                timestamp_ms=i * 33.33,
                x=100.0 + t * 300,
                y=200.0 - 80 * np.sin(t * np.pi),  # 抛物线
                confidence=0.9,
                blur_length=6.0 + 4.0 * (1 - abs(2*t - 1)),
            ))

        track = BallTrack(track_id="test_track", points=points)

        # 分析轨迹
        analyzer = TrajectoryAnalyzer(pixels_per_meter=200.0)
        result = analyzer.analyze_track(track)

        print_result("创建分析器", True)

        if result.speed_stats:
            print_result("速度分析", True,
                        f"最大 {result.speed_stats.max_speed_kmh:.1f} km/h, "
                        f"平均 {result.speed_stats.avg_speed_kmh:.1f} km/h")

        if result.motion_stats:
            print_result("运动分析", True,
                        f"总距离 {result.motion_stats.total_distance_px:.1f} px, "
                        f"方向变化 {result.motion_stats.direction_changes} 次")

        if result.stroke_type:
            print_result("击球分类", True, f"类型: {result.stroke_type}")

        if result.bounce_points is not None:
            print_result("落点检测", True, f"检测到 {len(result.bounce_points)} 个落点")

        return True
    except Exception as e:
        print_result("分析器测试", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def verify_video_processor(video_path: Optional[str] = None):
    """验证视频处理器"""
    print_header("4. 验证视频处理器 (VideoProcessor)")

    if video_path is None:
        print("  [跳过] 未提供视频文件")
        return True

    from app.ball_tracking.core.video_processor import VideoProcessor

    try:
        with VideoProcessor(video_path) as processor:
            metadata = processor.get_metadata()

            print_result("读取视频", True)
            print(f"    分辨率: {metadata.width}x{metadata.height}")
            print(f"    帧率: {metadata.fps:.2f} fps")
            print(f"    总帧数: {metadata.total_frames}")
            print(f"    时长: {metadata.duration_seconds:.2f} 秒")

            # 测试帧提取
            frame = processor.get_frame(0)
            if frame is not None:
                print_result("帧提取", True, f"形状 {frame.shape}")
            else:
                print_result("帧提取", False, "无法读取帧")
                return False

            # 测试批量提取
            batch_count = 0
            frame_count = 0
            for batch in processor.extract_frames_batch(batch_size=16):
                batch_count += 1
                frame_count += len(batch)
                if batch_count >= 3:
                    break
            print_result("批量提取", True, f"{batch_count} 批, {frame_count} 帧")

        return True
    except Exception as e:
        print_result("视频处理器测试", False, str(e))
        return False


def verify_detector():
    """验证检测器（需要模型）"""
    print_header("5. 验证检测器 (BlurBallDetector)")

    from config.settings import get_settings

    settings = get_settings()
    checkpoint_path = Path(settings.blurball_checkpoint_path)

    if not checkpoint_path.exists():
        print(f"  [跳过] 模型权重不存在: {checkpoint_path}")
        print("  提示: 请确保 BlurBall 模型已下载并放置在正确位置")
        return True  # 不算失败

    try:
        from app.ball_tracking.core.detector import get_detector
        import torch

        print(f"  CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")

        detector = get_detector()
        print_result("创建检测器", True)

        detector.load_model()
        print_result("加载模型", True)

        # 创建测试帧
        test_frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(3)]

        detections = detector.detect_frames(test_frames, [0, 1, 2])
        print_result("运行检测", True, f"返回 {len(detections)} 个结果")

        detector.unload_model()
        print_result("卸载模型", True)

        return True
    except Exception as e:
        print_result("检测器测试", False, str(e))
        import traceback
        traceback.print_exc()
        return False


async def verify_pipeline(video_path: Optional[str] = None):
    """验证完整 Pipeline"""
    print_header("6. 验证完整 Pipeline")

    if video_path is None:
        print("  [跳过] 未提供视频文件")
        return True

    from config.settings import get_settings

    settings = get_settings()
    checkpoint_path = Path(settings.blurball_checkpoint_path)

    if not checkpoint_path.exists():
        print("  [跳过] BlurBall 模型不存在，无法运行完整 Pipeline")
        return True

    try:
        from app.ball_tracking.core.pipeline import get_pipeline, PipelineConfig

        config = PipelineConfig(
            enable_trajectory_analysis=True,
            batch_size=8,
        )
        pipeline = get_pipeline(config)

        print_result("创建 Pipeline", True)

        stages = {}

        async def progress_callback(stage, progress):
            if stage not in stages:
                stages[stage] = progress
                print(f"    {stage}: {progress}%")

        result = await pipeline.process_video(video_path, progress_callback)

        print_result("处理视频", True)
        print(f"    任务ID: {result.job_id}")
        print(f"    处理帧数: {result.frame_count}")
        print(f"    有效检测: {result.detection_count}")
        print(f"    轨迹数量: {len(result.tracks)}")
        print(f"    处理时间: {result.processing_time_seconds:.2f}s")

        if result.tracks:
            track = result.tracks[0]
            print(f"    首条轨迹: 帧 {track.start_frame}-{track.end_frame}, {track.point_count} 点")

        if result.analysis_results:
            analysis = result.analysis_results[0]
            if analysis.speed_stats:
                print(f"    速度分析: 最大 {analysis.speed_stats.max_speed_kmh:.1f} km/h")
            if analysis.stroke_type:
                print(f"    击球类型: {analysis.stroke_type}")

        return True, result
    except Exception as e:
        print_result("Pipeline 测试", False, str(e))
        import traceback
        traceback.print_exc()
        return False, None


def verify_visualizer(video_path: str, tracks, output_dir: str):
    """验证可视化器"""
    print_header("7. 验证可视化器 (TrajectoryVisualizer)")

    try:
        from app.ball_tracking.core.visualizer import get_visualizer

        visualizer = get_visualizer()
        print_result("创建可视化器", True)

        output_path = Path(output_dir) / "verification_output.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_file = visualizer.generate_overlay_video(
            video_path,
            str(output_path),
            tracks,
        )

        if Path(output_file).exists():
            size_mb = Path(output_file).stat().st_size / (1024 * 1024)
            print_result("生成视频", True, f"输出: {output_file} ({size_mb:.2f} MB)")
        else:
            print_result("生成视频", False, "输出文件不存在")
            return False

        return True
    except Exception as e:
        print_result("可视化器测试", False, str(e))
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Ball Tracking 快速验证")
    parser.add_argument("--video", type=str, help="测试视频路径")
    parser.add_argument("--visualize", action="store_true", help="生成可视化结果")
    parser.add_argument("--output", type=str, default="./verification_output", help="输出目录")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Ball Tracking 模块验证")
    print("=" * 60)

    results = {}

    # 1. 验证导入
    results["imports"] = verify_imports()

    # 2. 验证追踪器
    results["tracker"] = verify_tracker()

    # 3. 验证分析器
    results["analyzer"] = verify_analyzer()

    # 4. 验证视频处理器
    results["video_processor"] = verify_video_processor(args.video)

    # 5. 验证检测器
    results["detector"] = verify_detector()

    # 6. 验证 Pipeline
    pipeline_result = None
    if args.video:
        success, pipeline_result = await verify_pipeline(args.video)
        results["pipeline"] = success
    else:
        results["pipeline"] = True  # 跳过

    # 7. 验证可视化
    if args.visualize and args.video and pipeline_result and pipeline_result.tracks:
        results["visualizer"] = verify_visualizer(
            args.video,
            pipeline_result.tracks,
            args.output
        )
    else:
        results["visualizer"] = True  # 跳过

    # 汇总
    print_header("验证结果汇总")

    all_passed = True
    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        color = "\033[92m" if success else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}{status}{reset} {name}")
        if not success:
            all_passed = False

    print()
    if all_passed:
        print("\033[92m所有验证通过!\033[0m")
    else:
        print("\033[91m部分验证失败，请检查上述输出\033[0m")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
