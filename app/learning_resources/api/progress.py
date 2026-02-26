"""
用户学习进度 REST API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.learning_resources.core.progress_service import get_progress_service
from app.learning_resources.core.resource_service import get_resource_service
from app.learning_resources.schemas import (
    UserProgressCreate, UserProgressUpdate, UserProgressResponse,
    UserProgressSummary, UserPathProgress,
)

router = APIRouter()


# ========== 工具函数 ==========

def _to_progress_response(progress) -> UserProgressResponse:
    """ORM → UserProgressResponse"""
    resource_title = ""
    if progress.resource:
        resource_title = progress.resource.title
    return UserProgressResponse(
        id=progress.id,
        user_id=progress.user_id,
        resource_id=progress.resource_id,
        resource_title=resource_title,
        progress_percent=progress.progress_percent or 0.0,
        is_completed=progress.is_completed or False,
        rating=progress.rating,
        notes=progress.notes,
        last_accessed_at=progress.last_accessed_at,
        created_at=progress.created_at,
        updated_at=progress.updated_at,
    )


# ========== 进度 CRUD ==========

@router.post("", response_model=UserProgressResponse, status_code=201)
async def upsert_progress(
    data: UserProgressCreate,
    db: AsyncSession = Depends(get_db_session),
) -> UserProgressResponse:
    """
    创建或更新学习进度（upsert）

    如果该用户对该资源已有进度记录则更新，否则创建新记录。
    进度百分比只能增加，不能回退。
    """
    # 验证资源存在
    resource_svc = get_resource_service()
    resource = await resource_svc.get_resource(db, data.resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    progress_svc = get_progress_service()
    progress, _ = await progress_svc.upsert_progress(db, data)
    await db.commit()

    # 加载关联资源
    progress.resource = resource
    return _to_progress_response(progress)


@router.get("/{user_id}", response_model=dict)
async def list_user_progress(
    user_id: str,
    only_completed: bool = Query(False, description="仅返回已完成项"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    查询用户所有进度记录（分页）

    返回用户的学习进度列表，可按完成状态过滤。
    """
    service = get_progress_service()
    records, total = await service.list_user_progress(
        db,
        user_id=user_id,
        only_completed=only_completed,
        page=page,
        page_size=page_size,
    )
    return {
        "user_id": user_id,
        "progress": [_to_progress_response(r) for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}/summary", response_model=UserProgressSummary)
async def get_user_summary(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserProgressSummary:
    """
    获取用户学习统计摘要

    返回总进度、完成数量、完成率、累积学习时长等统计。
    """
    service = get_progress_service()
    return await service.get_user_summary(db, user_id)


@router.get("/{user_id}/path/{path_id}", response_model=UserPathProgress)
async def get_path_progress(
    user_id: str,
    path_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserPathProgress:
    """
    获取用户在特定学习路径的进度

    返回路径的每项资源的完成状态。
    """
    service = get_progress_service()
    result = await service.get_path_progress(db, user_id, path_id)
    if not result:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return result


@router.get("/{user_id}/resource/{resource_id}", response_model=UserProgressResponse)
async def get_resource_progress(
    user_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserProgressResponse:
    """
    获取用户对特定资源的进度

    返回进度百分比、完成状态和评分。
    """
    service = get_progress_service()
    progress = await service.get_user_progress(db, user_id, resource_id)
    if not progress:
        raise HTTPException(status_code=404, detail="进度记录不存在")

    # 加载资源名称
    resource_svc = get_resource_service()
    resource = await resource_svc.get_resource(db, resource_id)
    if resource:
        progress.resource = resource
    return _to_progress_response(progress)


@router.put("/{user_id}/resource/{resource_id}", response_model=UserProgressResponse)
async def update_progress(
    user_id: str,
    resource_id: str,
    data: UserProgressUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> UserProgressResponse:
    """
    更新资源学习进度

    可更新进度百分比、评分和笔记。
    """
    progress_svc = get_progress_service()
    # 先找到进度 ID
    progress = await progress_svc.get_user_progress(db, user_id, resource_id)
    if not progress:
        raise HTTPException(status_code=404, detail="进度记录不存在")

    updated = await progress_svc.update_progress(db, progress.id, data)
    await db.commit()

    resource_svc = get_resource_service()
    resource = await resource_svc.get_resource(db, resource_id)
    if resource:
        updated.resource = resource
    return _to_progress_response(updated)


@router.post("/{user_id}/resource/{resource_id}/complete", response_model=UserProgressResponse)
async def mark_complete(
    user_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserProgressResponse:
    """
    标记资源为已完成

    一键将学习进度设为 100% 并标记完成。
    """
    resource_svc = get_resource_service()
    resource = await resource_svc.get_resource(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    progress_svc = get_progress_service()
    progress = await progress_svc.mark_complete(db, user_id, resource_id)
    await db.commit()

    progress.resource = resource
    return _to_progress_response(progress)
