"""
轨迹分析 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db_session
from app.ball_tracking.models import ProcessingJob, BallTrack2D
from app.ball_tracking.schemas import (
    TrajectoryAnalysisResponse,
    SpeedStatsResponse,
    MotionStatsResponse,
    BouncePointResponse,
)

router = APIRouter()


def _build_analysis_response(track: BallTrack2D) -> TrajectoryAnalysisResponse:
    """构建分析响应"""
    if not track.analysis_json:
        return TrajectoryAnalysisResponse(track_id=track.id)

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

    return TrajectoryAnalysisResponse(
        track_id=track.id,
        speed_stats=speed_stats,
        motion_stats=motion_stats,
        bounce_points=bounce_points,
        stroke_type=analysis_data.get("stroke_type"),
    )


@router.get("/jobs/{job_id}/analysis", response_model=list[TrajectoryAnalysisResponse])
async def get_job_analysis(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> list[TrajectoryAnalysisResponse]:
    """获取任务的所有轨迹分析结果"""
    # 检查任务是否存在
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

    # 获取轨迹
    result = await db.execute(
        select(BallTrack2D).where(BallTrack2D.job_id == job_id)
    )
    tracks = result.scalars().all()

    return [_build_analysis_response(track) for track in tracks]


@router.get("/tracks/{track_id}/analysis", response_model=TrajectoryAnalysisResponse)
async def get_track_analysis(
    track_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> TrajectoryAnalysisResponse:
    """获取指定轨迹的分析结果"""
    result = await db.execute(
        select(BallTrack2D).where(BallTrack2D.id == track_id)
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="轨迹不存在")

    return _build_analysis_response(track)
