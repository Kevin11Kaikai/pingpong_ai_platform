"""
视频上传和处理 API
"""

import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.shared.database import get_db_session
from app.ball_tracking.models import ProcessingJob, BallTrack2D
from app.ball_tracking.schemas import (
    VideoUploadResponse,
    ProcessingJobStatus,
    ProcessingResultResponse,
    VideoMetadataResponse,
    Track2DResponse,
    TrackPoint2D,
    TrajectoryAnalysisResponse,
    SpeedStatsResponse,
    MotionStatsResponse,
    BouncePointResponse,
    JobListResponse,
    JobListItem,
)
from app.ball_tracking.core.pipeline import get_pipeline, PipelineResult
from config.settings import get_settings

router = APIRouter()

# 支持的视频格式
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


async def process_video_task(job_id: str, video_path: str):
    """
    后台处理视频任务
    """
    from app.shared.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # 更新状态为处理中
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"任务不存在: {job_id}")
                return

            job.status = "processing"
            job.current_stage = "initializing"
            await db.commit()

            # 定义进度回调
            async def progress_callback(stage: str, progress: float):
                job.current_stage = stage
                job.progress_percent = progress
                await db.commit()

            # 运行 Pipeline
            pipeline = get_pipeline()
            pipeline_result: PipelineResult = await pipeline.process_video(
                video_path,
                progress_callback=progress_callback,
            )

            # 保存结果
            job.video_width = pipeline_result.video_metadata.width
            job.video_height = pipeline_result.video_metadata.height
            job.video_fps = pipeline_result.video_metadata.fps
            job.video_frames = pipeline_result.video_metadata.total_frames
            job.video_duration = pipeline_result.video_metadata.duration_seconds
            job.video_codec = pipeline_result.video_metadata.codec
            job.detection_count = pipeline_result.detection_count
            job.track_count = len(pipeline_result.tracks)
            job.processing_time_seconds = pipeline_result.processing_time_seconds

            # 保存轨迹
            for track in pipeline_result.tracks:
                # 序列化轨迹点
                points_json = [
                    {
                        "frame_idx": p.frame_idx,
                        "timestamp_ms": p.timestamp_ms,
                        "x": p.x,
                        "y": p.y,
                        "confidence": p.confidence,
                        "blur_angle": p.blur_angle,
                        "blur_length": p.blur_length,
                        "interpolated": p.interpolated,
                    }
                    for p in track.points
                ]

                # 查找对应的分析结果
                analysis_json = None
                if pipeline_result.analysis_results:
                    for analysis in pipeline_result.analysis_results:
                        if analysis.track_id == track.track_id:
                            analysis_json = {
                                "speed_stats": {
                                    "max_speed_mps": analysis.speed_stats.max_speed_mps,
                                    "avg_speed_mps": analysis.speed_stats.avg_speed_mps,
                                    "initial_speed_mps": analysis.speed_stats.initial_speed_mps,
                                    "max_speed_kmh": analysis.speed_stats.max_speed_kmh,
                                    "avg_speed_kmh": analysis.speed_stats.avg_speed_kmh,
                                } if analysis.speed_stats else None,
                                "motion_stats": {
                                    "total_distance_px": analysis.motion_stats.total_distance_px,
                                    "max_displacement_px": analysis.motion_stats.max_displacement_px,
                                    "avg_displacement_px": analysis.motion_stats.avg_displacement_px,
                                    "direction_changes": analysis.motion_stats.direction_changes,
                                    "avg_blur_length": analysis.motion_stats.avg_blur_length,
                                } if analysis.motion_stats else None,
                                "bounce_points": [
                                    {
                                        "frame_idx": bp.frame_idx,
                                        "timestamp_ms": bp.timestamp_ms,
                                        "x": bp.x,
                                        "y": bp.y,
                                        "bounce_type": bp.bounce_type,
                                    }
                                    for bp in (analysis.bounce_points or [])
                                ],
                                "stroke_type": analysis.stroke_type,
                            }
                            break

                track_record = BallTrack2D(
                    id=track.track_id,
                    job_id=job_id,
                    start_frame=track.start_frame,
                    end_frame=track.end_frame,
                    point_count=track.point_count,
                    duration_ms=track.duration_ms,
                    points_json=points_json,
                    analysis_json=analysis_json,
                )
                db.add(track_record)

            # 更新任务状态
            job.status = "completed"
            job.progress_percent = 100
            job.current_stage = "completed"
            job.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(f"任务完成: {job_id}")

        except Exception as e:
            logger.exception(f"处理任务失败: {job_id}")
            job.status = "failed"
            job.error_message = str(e)
            job.current_stage = "error"
            await db.commit()


@router.post("/upload", response_model=VideoUploadResponse, status_code=202)
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db_session),
) -> VideoUploadResponse:
    """
    上传视频文件进行球追踪分析

    - 支持格式: mp4, avi, mov, mkv, webm
    - 最大文件大小: 500MB
    - 上传后自动加入处理队列
    """
    settings = get_settings()

    # 检查文件扩展名
    filename = file.filename or "video.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 创建上传目录
    upload_dir = Path(settings.ball_tracking_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    job_id = str(uuid.uuid4())
    safe_filename = f"{job_id}{ext}"
    file_path = upload_dir / safe_filename

    # 保存文件
    file_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(chunk)
            # 检查文件大小
            if file_size > settings.ball_tracking_max_file_size_mb * 1024 * 1024:
                await f.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"文件过大，最大允许 {settings.ball_tracking_max_file_size_mb}MB",
                )
            await f.write(chunk)

    # 创建任务记录
    job = ProcessingJob(
        id=job_id,
        filename=filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        status="queued",
        progress_percent=0,
    )
    db.add(job)
    await db.commit()

    # 添加后台处理任务
    if background_tasks:
        background_tasks.add_task(process_video_task, job_id, str(file_path))

    logger.info(f"视频上传成功: {filename}, job_id={job_id}")

    return VideoUploadResponse(
        job_id=job_id,
        filename=filename,
        status="queued",
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}/status", response_model=ProcessingJobStatus)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ProcessingJobStatus:
    """获取处理任务状态"""
    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    return ProcessingJobStatus(
        job_id=job.id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_stage=job.current_stage,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/result", response_model=ProcessingResultResponse)
async def get_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ProcessingResultResponse:
    """
    获取处理结果

    - 仅当任务状态为 completed 时可用
    - 返回完整的追踪和分析结果
    """
    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {job.status}",
        )

    # 获取轨迹
    tracks_result = await db.execute(
        select(BallTrack2D).where(BallTrack2D.job_id == job_id)
    )
    tracks = tracks_result.scalars().all()

    # 构建响应
    tracks_response = []
    analysis_response = []

    for track in tracks:
        # 轨迹点
        points = [
            TrackPoint2D(
                frame_idx=p["frame_idx"],
                timestamp_ms=p["timestamp_ms"],
                x=p["x"],
                y=p["y"],
                confidence=p["confidence"],
                blur_angle=p.get("blur_angle"),
                blur_length=p.get("blur_length"),
                interpolated=p.get("interpolated", False),
            )
            for p in track.points_json
        ]

        tracks_response.append(
            Track2DResponse(
                track_id=track.id,
                points=points,
                start_frame=track.start_frame,
                end_frame=track.end_frame,
                duration_ms=track.duration_ms,
                point_count=track.point_count,
            )
        )

        # 分析结果
        if track.analysis_json:
            analysis_data = track.analysis_json

            speed_stats = None
            if analysis_data.get("speed_stats"):
                ss = analysis_data["speed_stats"]
                speed_stats = SpeedStatsResponse(
                    max_speed_mps=ss["max_speed_mps"],
                    max_speed_kmh=ss["max_speed_kmh"],
                    avg_speed_mps=ss["avg_speed_mps"],
                    avg_speed_kmh=ss["avg_speed_kmh"],
                    initial_speed_mps=ss["initial_speed_mps"],
                )

            motion_stats = None
            if analysis_data.get("motion_stats"):
                ms = analysis_data["motion_stats"]
                motion_stats = MotionStatsResponse(
                    total_distance_px=ms["total_distance_px"],
                    max_displacement_px=ms["max_displacement_px"],
                    avg_displacement_px=ms["avg_displacement_px"],
                    direction_changes=ms["direction_changes"],
                    avg_blur_length=ms.get("avg_blur_length"),
                )

            bounce_points = [
                BouncePointResponse(
                    frame_idx=bp["frame_idx"],
                    timestamp_ms=bp["timestamp_ms"],
                    x=bp["x"],
                    y=bp["y"],
                    bounce_type=bp["bounce_type"],
                )
                for bp in analysis_data.get("bounce_points", [])
            ]

            analysis_response.append(
                TrajectoryAnalysisResponse(
                    track_id=track.id,
                    speed_stats=speed_stats,
                    motion_stats=motion_stats,
                    bounce_points=bounce_points,
                    stroke_type=analysis_data.get("stroke_type"),
                )
            )

    return ProcessingResultResponse(
        job_id=job.id,
        video_metadata=VideoMetadataResponse(
            width=job.video_width,
            height=job.video_height,
            fps=job.video_fps,
            total_frames=job.video_frames,
            duration_seconds=job.video_duration,
            codec=job.video_codec or "unknown",
        ),
        tracks=tracks_response,
        analysis=analysis_response if analysis_response else None,
        processing_time_seconds=job.processing_time_seconds or 0,
        frame_count=job.video_frames or 0,
        detection_count=job.detection_count or 0,
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """删除处理任务及相关数据"""
    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除视频文件
    if job.file_path and os.path.exists(job.file_path):
        try:
            os.remove(job.file_path)
        except OSError as e:
            logger.warning(f"删除视频文件失败: {e}")

    # 删除数据库记录（级联删除轨迹）
    await db.delete(job)
    await db.commit()

    logger.info(f"任务已删除: {job_id}")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> JobListResponse:
    """列出处理任务"""
    # 构建查询
    query = select(ProcessingJob)
    count_query = select(func.count(ProcessingJob.id))

    if status:
        query = query.where(ProcessingJob.status == status)
        count_query = count_query.where(ProcessingJob.status == status)

    # 排序和分页
    query = query.order_by(ProcessingJob.created_at.desc()).offset(offset).limit(limit)

    # 执行查询
    result = await db.execute(query)
    jobs = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 构建响应
    items = [
        JobListItem(
            job_id=job.id,
            filename=job.filename,
            status=job.status,
            progress_percent=job.progress_percent,
            created_at=job.created_at,
            processing_time_seconds=job.processing_time_seconds,
        )
        for job in jobs
    ]

    return JobListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
