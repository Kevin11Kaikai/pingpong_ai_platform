"""
轨迹数据查询 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db_session
from app.ball_tracking.models import ProcessingJob, BallTrack2D
from app.ball_tracking.schemas import (
    Track2DResponse,
    TrackPoint2D,
)

router = APIRouter()


@router.get("/jobs/{job_id}/tracks", response_model=list[Track2DResponse])
async def get_tracks(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> list[Track2DResponse]:
    """获取任务的所有 2D 轨迹"""
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

    response = []
    for track in tracks:
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

        response.append(
            Track2DResponse(
                track_id=track.id,
                points=points,
                start_frame=track.start_frame,
                end_frame=track.end_frame,
                duration_ms=track.duration_ms,
                point_count=track.point_count,
            )
        )

    return response


@router.get("/jobs/{job_id}/tracks/{track_id}", response_model=Track2DResponse)
async def get_track(
    job_id: str,
    track_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Track2DResponse:
    """获取指定 2D 轨迹"""
    result = await db.execute(
        select(BallTrack2D).where(
            BallTrack2D.job_id == job_id,
            BallTrack2D.id == track_id,
        )
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="轨迹不存在")

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

    return Track2DResponse(
        track_id=track.id,
        points=points,
        start_frame=track.start_frame,
        end_frame=track.end_frame,
        duration_ms=track.duration_ms,
        point_count=track.point_count,
    )


@router.get("/tracks/{track_id}", response_model=Track2DResponse)
async def get_track_by_id(
    track_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Track2DResponse:
    """根据轨迹 ID 获取轨迹"""
    result = await db.execute(
        select(BallTrack2D).where(BallTrack2D.id == track_id)
    )
    track = result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="轨迹不存在")

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

    return Track2DResponse(
        track_id=track.id,
        points=points,
        start_frame=track.start_frame,
        end_frame=track.end_frame,
        duration_ms=track.duration_ms,
        point_count=track.point_count,
    )
