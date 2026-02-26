"""
统计分析 API 路由
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.training_analysis.core import get_analysis_service, get_metrics_service
from app.training_analysis.schemas import (
    TrendAnalysisResponse, ComparisonRequest, ComparisonResponse,
    UserTrainingStatsResponse, SnapshotResponse, SnapshotListResponse,
    TechniqueAnalysisResponse, TechniqueMetricsSummary,
)

router = APIRouter()


@router.get("/user/{user_id}/stats", response_model=UserTrainingStatsResponse)
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户综合训练统计

    包含总训练次数、时长、连续天数、目标达成等。
    """
    service = get_analysis_service()
    stats = await service.get_user_stats(db, user_id)

    # 获取最近洞察
    from app.training_analysis.core import get_insight_service
    insight_service = get_insight_service()
    await insight_service.get_user_insights(db, user_id, limit=5)

    # 获取技术统计
    technique_stats = {}
    for tech in stats.get("favorite_techniques", []):
        trend = await service.calculate_technique_trend(db, user_id, tech)
        technique_stats[tech] = TechniqueMetricsSummary(
            technique_category=tech,
            total_sessions=0,  # 简化，实际应查询
            total_strokes=0,
            avg_speed_kmh=None,
            avg_accuracy=None,
            avg_consistency=None,
            trend=trend,
        )

    return UserTrainingStatsResponse(
        user_id=user_id,
        total_sessions=stats["total_sessions"],
        total_duration_minutes=stats["total_duration_minutes"],
        total_strokes=stats["total_strokes"],
        avg_session_duration=stats["avg_session_duration"],
        avg_strokes_per_session=stats["avg_strokes_per_session"],
        favorite_techniques=stats["favorite_techniques"],
        current_streak_days=stats["current_streak_days"],
        longest_streak_days=stats["longest_streak_days"],
        goals_achieved=stats["goals_achieved"],
        goals_active=stats["goals_active"],
        technique_stats=technique_stats,
        recent_insights=[],  # 简化响应，避免循环导入
    )


@router.get("/user/{user_id}/trends", response_model=TrendAnalysisResponse)
async def get_trends(
    user_id: str,
    metric: str = Query("speed", description="指标名称 (speed/accuracy/consistency)"),
    days: int = Query(30, ge=7, le=365, description="分析天数"),
    group_by: str = Query("daily", description="分组方式 (daily/weekly/monthly)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取训练趋势分析

    分析指定指标在一段时间内的变化趋势。
    """
    service = get_analysis_service()

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    trend = await service.get_trend_analysis(
        db, user_id, metric, start_date, end_date, group_by
    )

    return trend


@router.post("/user/{user_id}/compare", response_model=ComparisonResponse)
async def compare_periods(
    user_id: str,
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    对比两个时期的训练数据

    返回两个周期的统计汇总和变化分析。
    """
    service = get_analysis_service()
    comparison = await service.compare_periods(db, user_id, request)

    return comparison


@router.get("/user/{user_id}/snapshots", response_model=SnapshotListResponse)
async def get_snapshots(
    user_id: str,
    period_type: Optional[str] = Query(None, description="周期类型 (daily/weekly/monthly)"),
    limit: int = Query(30, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户进度快照列表
    """
    service = get_analysis_service()
    snapshots = await service.get_snapshots(db, user_id, period_type, limit)

    return SnapshotListResponse(
        snapshots=[SnapshotResponse.model_validate(s) for s in snapshots],
        total=len(snapshots),
    )


@router.get("/user/{user_id}/technique/{category}", response_model=TechniqueAnalysisResponse)
async def get_technique_analysis(
    user_id: str,
    category: str,
    days: int = Query(30, ge=7, le=365, description="分析天数"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取特定技术的分析

    返回该技术的历史数据、趋势和汇总。
    """
    analysis_service = get_analysis_service()
    metrics_service = get_metrics_service()

    # 获取历史数据
    history = await metrics_service.get_user_technique_history(
        db, user_id, category, limit=50
    )

    if not history:
        raise HTTPException(status_code=404, detail="该技术无训练数据")

    # 获取趋势
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    trend = await analysis_service.get_trend_analysis(
        db, user_id, "speed", start_date, end_date, "daily"
    )

    # 计算汇总
    total_strokes = sum(m.stroke_count or 0 for m in history)
    speeds = [m.avg_speed_kmh for m in history if m.avg_speed_kmh]
    accuracies = [m.accuracy_score for m in history if m.accuracy_score]
    consistencies = [m.consistency_score for m in history if m.consistency_score]

    technique_trend = await analysis_service.calculate_technique_trend(
        db, user_id, category, days
    )

    summary = TechniqueMetricsSummary(
        technique_category=category,
        total_sessions=len(history),
        total_strokes=total_strokes,
        avg_speed_kmh=sum(speeds) / len(speeds) if speeds else None,
        avg_accuracy=sum(accuracies) / len(accuracies) if accuracies else None,
        avg_consistency=sum(consistencies) / len(consistencies) if consistencies else None,
        trend=technique_trend,
    )

    # 转换历史数据
    from app.training_analysis.schemas import TechniqueMetricsResponse
    history_resp = [TechniqueMetricsResponse.model_validate(m) for m in history[:20]]

    return TechniqueAnalysisResponse(
        technique_category=category,
        total_sessions=len(history),
        total_strokes=total_strokes,
        history=history_resp,
        trend=trend,
        summary=summary,
    )


@router.post("/generate-snapshot", response_model=SnapshotResponse)
async def generate_snapshot(
    user_id: str = Query(..., description="用户ID"),
    period_type: str = Query("daily", description="周期类型 (daily/weekly/monthly)"),
    snapshot_date: Optional[datetime] = Query(None, description="快照日期（默认今天）"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    生成进度快照

    管理接口，用于手动触发快照生成。
    """
    service = get_analysis_service()

    date = snapshot_date or datetime.utcnow()
    snapshot = await service.create_snapshot(db, user_id, period_type, date)

    return SnapshotResponse.model_validate(snapshot)


@router.get("/user/{user_id}/streak")
async def get_streak(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户连续训练天数
    """
    service = get_analysis_service()
    stats = await service.get_user_stats(db, user_id)

    return {
        "user_id": user_id,
        "current_streak_days": stats["current_streak_days"],
        "longest_streak_days": stats["longest_streak_days"],
    }
