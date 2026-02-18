"""
可视化输出 API
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.shared.database import get_db_session
from app.ball_tracking.models import ProcessingJob, BallTrack2D, VisualizationOutput
from app.ball_tracking.schemas import (
    VisualizationRequest,
    VisualizationResponse,
)
from app.ball_tracking.core.pipeline import get_pipeline
from app.ball_tracking.core.tracker import BallTrack, TrackPoint
from config.settings import get_settings

router = APIRouter()


async def generate_visualization_task(
    viz_id: str,
    job_id: str,
    video_path: str,
    output_path: str,
    tracks_data: list,
    config: dict,
):
    """后台生成可视化任务"""
    from app.shared.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # 重建轨迹对象
            tracks = []
            for track_data in tracks_data:
                points = [
                    TrackPoint(
                        frame_idx=p["frame_idx"],
                        timestamp_ms=p["timestamp_ms"],
                        x=p["x"],
                        y=p["y"],
                        confidence=p["confidence"],
                        blur_angle=p.get("blur_angle"),
                        blur_length=p.get("blur_length"),
                        interpolated=p.get("interpolated", False),
                    )
                    for p in track_data["points"]
                ]
                tracks.append(BallTrack(track_id=track_data["id"], points=points))

            # 生成可视化
            pipeline = get_pipeline()
            output_file = await pipeline.generate_visualization(
                video_path, output_path, tracks
            )

            # 获取文件大小
            file_size = os.path.getsize(output_file)

            # 更新数据库记录
            result = await db.execute(
                select(VisualizationOutput).where(VisualizationOutput.id == viz_id)
            )
            viz = result.scalar_one_or_none()
            if viz:
                viz.file_size_bytes = file_size
                await db.commit()

            logger.info(f"可视化生成完成: {viz_id}")

        except Exception as e:
            logger.exception(f"生成可视化失败: {viz_id}")
            # 删除失败的记录
            result = await db.execute(
                select(VisualizationOutput).where(VisualizationOutput.id == viz_id)
            )
            viz = result.scalar_one_or_none()
            if viz:
                await db.delete(viz)
                await db.commit()


@router.post("/jobs/{job_id}/visualize", response_model=VisualizationResponse, status_code=202)
async def create_visualization(
    job_id: str,
    request: VisualizationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> VisualizationResponse:
    """
    创建轨迹可视化

    - 生成带有轨迹叠加的视频
    - 支持 mp4 格式
    """
    settings = get_settings()

    # 检查任务
    job_result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {job.status}",
        )

    # 获取轨迹数据
    tracks_result = await db.execute(
        select(BallTrack2D).where(BallTrack2D.job_id == job_id)
    )
    tracks = tracks_result.scalars().all()

    if not tracks:
        raise HTTPException(status_code=400, detail="没有可用的轨迹数据")

    # 准备轨迹数据
    tracks_data = [
        {
            "id": track.id,
            "points": track.points_json,
        }
        for track in tracks
    ]

    # 创建输出目录
    output_dir = Path(settings.ball_tracking_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成可视化 ID 和输出路径
    viz_id = str(uuid.uuid4())
    output_filename = f"{viz_id}.{request.output_format}"
    output_path = output_dir / output_filename

    # 创建数据库记录
    viz = VisualizationOutput(
        id=viz_id,
        job_id=job_id,
        output_format=request.output_format,
        file_path=str(output_path),
        file_size_bytes=0,  # 稍后更新
        config={
            "include_trajectory": request.include_trajectory,
            "include_analysis_overlay": request.include_analysis_overlay,
            "trail_length": request.trail_length,
        },
    )
    db.add(viz)
    await db.commit()

    # 启动后台任务
    background_tasks.add_task(
        generate_visualization_task,
        viz_id,
        job_id,
        job.file_path,
        str(output_path),
        tracks_data,
        {
            "include_trajectory": request.include_trajectory,
            "trail_length": request.trail_length,
        },
    )

    return VisualizationResponse(
        job_id=job_id,
        visualization_id=viz_id,
        output_url=f"/api/ball-tracking/visualizations/{viz_id}/download",
        format=request.output_format,
        file_size_bytes=0,  # 处理完成后更新
        created_at=viz.created_at,
    )


@router.get("/visualizations/{viz_id}/download")
async def download_visualization(
    viz_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """下载可视化文件"""
    result = await db.execute(
        select(VisualizationOutput).where(VisualizationOutput.id == viz_id)
    )
    viz = result.scalar_one_or_none()

    if not viz:
        raise HTTPException(status_code=404, detail="可视化文件不存在")

    if not os.path.exists(viz.file_path):
        raise HTTPException(status_code=404, detail="文件正在生成中或已被删除")

    return FileResponse(
        viz.file_path,
        media_type="video/mp4" if viz.output_format == "mp4" else "image/gif",
        filename=f"trajectory_{viz.job_id}.{viz.output_format}",
    )


@router.get("/jobs/{job_id}/preview")
async def get_preview_frame(
    job_id: str,
    frame_idx: int = Query(0, ge=0),
    include_trajectory: bool = True,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取带轨迹的预览帧

    返回 JPEG 图像
    """
    import io
    import cv2
    from fastapi.responses import StreamingResponse

    # 检查任务
    job_result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"任务尚未完成，当前状态: {job.status}",
        )

    # 获取轨迹数据
    tracks = []
    if include_trajectory:
        tracks_result = await db.execute(
            select(BallTrack2D).where(BallTrack2D.job_id == job_id)
        )
        tracks_db = tracks_result.scalars().all()

        for track_db in tracks_db:
            points = [
                TrackPoint(
                    frame_idx=p["frame_idx"],
                    timestamp_ms=p["timestamp_ms"],
                    x=p["x"],
                    y=p["y"],
                    confidence=p["confidence"],
                    blur_angle=p.get("blur_angle"),
                    blur_length=p.get("blur_length"),
                    interpolated=p.get("interpolated", False),
                )
                for p in track_db.points_json
            ]
            tracks.append(BallTrack(track_id=track_db.id, points=points))

    # 生成预览帧
    from app.ball_tracking.core.visualizer import get_visualizer

    visualizer = get_visualizer()
    frame = visualizer.generate_preview_frame(job.file_path, tracks, frame_idx)

    # 编码为 JPEG
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    io_buf = io.BytesIO(buffer.tobytes())

    return StreamingResponse(io_buf, media_type="image/jpeg")
