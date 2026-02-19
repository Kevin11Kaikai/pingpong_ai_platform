"""
视频分析集成 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.learning_resources.core import get_video_analysis_service
from app.learning_resources.schemas import (
    VideoAnalysisLinkCreate, VideoAnalysisLinkResponse,
    TechniqueAnalysisRequest, TechniqueAnalysisResponse,
)

router = APIRouter()


@router.post("/link", response_model=VideoAnalysisLinkResponse)
async def create_video_analysis_link(
    data: VideoAnalysisLinkCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建视频分析关联

    将学习资源与 ball_tracking 分析任务关联起来。
    """
    service = get_video_analysis_service()
    try:
        link = await service.create_link(db, data)
        return VideoAnalysisLinkResponse(
            id=link.id,
            resource_id=link.resource_id,
            ball_tracking_job_id=link.ball_tracking_job_id,
            start_time_seconds=link.start_time_seconds,
            end_time_seconds=link.end_time_seconds,
            analysis_type=link.analysis_type,
            technique_category=link.technique_category.value if link.technique_category else None,
            analysis_summary=link.analysis_summary,
            ai_commentary=link.ai_commentary,
            improvement_suggestions=link.improvement_suggestions,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建视频分析关联失败: {e}")
        raise HTTPException(status_code=500, detail="创建关联失败")


@router.get("/resource/{resource_id}", response_model=list[VideoAnalysisLinkResponse])
async def get_resource_analysis_links(
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取资源的视频分析列表

    返回与指定学习资源关联的所有视频分析。
    """
    service = get_video_analysis_service()
    links = await service.get_links_by_resource(db, resource_id)
    return [
        VideoAnalysisLinkResponse(
            id=link.id,
            resource_id=link.resource_id,
            ball_tracking_job_id=link.ball_tracking_job_id,
            start_time_seconds=link.start_time_seconds,
            end_time_seconds=link.end_time_seconds,
            analysis_type=link.analysis_type,
            technique_category=link.technique_category.value if link.technique_category else None,
            analysis_summary=link.analysis_summary,
            ai_commentary=link.ai_commentary,
            improvement_suggestions=link.improvement_suggestions,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )
        for link in links
    ]


@router.get("/link/{link_id}", response_model=VideoAnalysisLinkResponse)
async def get_video_analysis_link(
    link_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取视频分析关联详情
    """
    service = get_video_analysis_service()
    link = await service.get_link(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="分析关联不存在")
    return VideoAnalysisLinkResponse(
        id=link.id,
        resource_id=link.resource_id,
        ball_tracking_job_id=link.ball_tracking_job_id,
        start_time_seconds=link.start_time_seconds,
        end_time_seconds=link.end_time_seconds,
        analysis_type=link.analysis_type,
        technique_category=link.technique_category.value if link.technique_category else None,
        analysis_summary=link.analysis_summary,
        ai_commentary=link.ai_commentary,
        improvement_suggestions=link.improvement_suggestions,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.post("/analyze", response_model=TechniqueAnalysisResponse)
async def analyze_technique(
    request: TechniqueAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    分析教学视频中的技术动作

    执行技术动作分析：
    1. 获取 ball_tracking 轨迹数据
    2. 与标准动作参数对比
    3. 生成 AI 技术解说（可选）
    4. 提供改进建议
    """
    service = get_video_analysis_service()
    try:
        result = await service.analyze_technique(db, request)
        return TechniqueAnalysisResponse(
            link_id=result["link_id"],
            resource_id=result["resource_id"],
            ball_tracking_job_id=result["ball_tracking_job_id"],
            technique_category=result["technique_category"],
            analysis_summary=result["analysis_summary"],
            ai_commentary=result.get("ai_commentary"),
            improvement_suggestions=result.get("improvement_suggestions", []),
            comparison_score=result.get("comparison_score"),
        )
    except Exception as e:
        logger.error(f"技术分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/link/{link_id}/commentary")
async def generate_ai_commentary(
    link_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    生成 AI 技术解说

    为已有的视频分析关联生成 AI 解说。
    """
    service = get_video_analysis_service()
    link = await service.update_link_with_commentary(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="分析关联不存在")
    return {
        "link_id": link.id,
        "ai_commentary": link.ai_commentary,
        "message": "解说生成成功",
    }
