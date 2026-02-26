"""
学习路径（课程计划）REST API 路由
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.learning_resources.core.curriculum_service import get_curriculum_service
from app.learning_resources.core.resource_service import get_resource_service
from app.learning_resources.schemas import (
    LearningPathCreate, LearningPathUpdate, LearningPathResponse,
    LearningPathBrief, LearningPathListResponse,
    LearningPathItemCreate, LearningPathItemResponse,
)

router = APIRouter()


# ========== 工具函数 ==========

def _to_path_brief(path, item_count: int = 0) -> LearningPathBrief:
    """ORM → LearningPathBrief"""
    return LearningPathBrief(
        id=path.id,
        title=path.title,
        difficulty_level=path.difficulty_level.value if hasattr(path.difficulty_level, "value") else str(path.difficulty_level),
        category=path.category.value if (path.category and hasattr(path.category, "value")) else (str(path.category) if path.category else None),
        estimated_hours=path.estimated_hours,
        tags=path.tags,
        is_published=path.is_published,
        is_featured=path.is_featured,
        item_count=item_count,
        created_at=path.created_at,
    )


def _to_path_response(path, item_count: int = 0, items=None) -> LearningPathResponse:
    """ORM → LearningPathResponse"""
    from app.learning_resources.api.resources import _to_resource_brief

    path_items = None
    if items is not None:
        path_items = []
        for item in items:
            if item.resource:
                path_items.append(
                    LearningPathItemResponse(
                        id=item.id,
                        resource_id=item.resource_id,
                        resource=_to_resource_brief(item.resource),
                        order_index=item.order_index,
                        notes=item.notes,
                        is_required=item.is_required,
                        created_at=item.created_at,
                    )
                )

    return LearningPathResponse(
        id=path.id,
        title=path.title,
        description=path.description,
        difficulty_level=path.difficulty_level.value if hasattr(path.difficulty_level, "value") else str(path.difficulty_level),
        category=path.category.value if (path.category and hasattr(path.category, "value")) else (str(path.category) if path.category else None),
        estimated_hours=path.estimated_hours,
        target_audience=path.target_audience,
        learning_objectives=path.learning_objectives,
        tags=path.tags,
        is_published=path.is_published,
        is_featured=path.is_featured,
        item_count=item_count,
        created_at=path.created_at,
        updated_at=path.updated_at,
        items=path_items,
    )


# ========== 学习路径 CRUD ==========

@router.post("", response_model=LearningPathResponse, status_code=201)
async def create_path(
    data: LearningPathCreate,
    db: AsyncSession = Depends(get_db_session),
) -> LearningPathResponse:
    """
    创建学习路径

    创建一条结构化的乒乓球学习路径，可后续添加资源。
    """
    service = get_curriculum_service()
    path = await service.create_path(db, data)
    await db.commit()
    return _to_path_response(path, item_count=0)


@router.get("", response_model=LearningPathListResponse)
async def list_paths(
    difficulty_level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_published: Optional[bool] = Query(True),
    is_featured: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> LearningPathListResponse:
    """
    分页查询学习路径列表

    支持按难度、分类、状态筛选。
    """
    service = get_curriculum_service()
    paths, total = await service.list_paths(
        db,
        difficulty_level=difficulty_level,
        category=category,
        is_published=is_published,
        is_featured=is_featured,
        page=page,
        page_size=page_size,
    )
    # 批量获取条目数
    briefs = []
    for path in paths:
        count = await service.get_item_count(db, path.id)
        briefs.append(_to_path_brief(path, count))

    return LearningPathListResponse(paths=briefs, total=total)


@router.get("/{path_id}", response_model=LearningPathResponse)
async def get_path(
    path_id: str,
    include_items: bool = Query(True, description="是否返回资源条目列表"),
    db: AsyncSession = Depends(get_db_session),
) -> LearningPathResponse:
    """
    获取学习路径详情

    默认返回完整资源条目列表，可通过参数控制。
    """
    service = get_curriculum_service()
    path = await service.get_path(db, path_id, with_items=include_items)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    items = path.items if include_items else None
    count = len(path.items) if include_items else await service.get_item_count(db, path.id)
    return _to_path_response(path, item_count=count, items=items)


@router.put("/{path_id}", response_model=LearningPathResponse)
async def update_path(
    path_id: str,
    data: LearningPathUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> LearningPathResponse:
    """
    更新学习路径

    支持部分更新，仅修改提供的字段。
    """
    service = get_curriculum_service()
    path = await service.update_path(db, path_id, data)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    count = await service.get_item_count(db, path_id)
    await db.commit()
    return _to_path_response(path, item_count=count)


@router.delete("/{path_id}", status_code=204)
async def delete_path(
    path_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    删除学习路径

    同时删除路径中所有资源条目（不删除资源本身）。
    """
    service = get_curriculum_service()
    deleted = await service.delete_path(db, path_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    await db.commit()


# ========== 路径资源条目管理 ==========

@router.post("/{path_id}/items", response_model=LearningPathItemResponse, status_code=201)
async def add_resource_to_path(
    path_id: str,
    data: LearningPathItemCreate,
    db: AsyncSession = Depends(get_db_session),
) -> LearningPathItemResponse:
    """
    向学习路径添加资源

    幂等操作，资源已存在于路径中时直接返回已有条目。
    """
    curriculum_svc = get_curriculum_service()
    resource_svc = get_resource_service()

    # 验证资源存在
    resource = await resource_svc.get_resource(db, data.resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")

    try:
        item, is_new = await curriculum_svc.add_resource_to_path(db, path_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if is_new:
        await db.commit()

    from app.learning_resources.api.resources import _to_resource_brief
    return LearningPathItemResponse(
        id=item.id,
        resource_id=item.resource_id,
        resource=_to_resource_brief(resource),
        order_index=item.order_index,
        notes=item.notes,
        is_required=item.is_required,
        created_at=item.created_at,
    )


@router.delete("/{path_id}/items/{resource_id}", status_code=204)
async def remove_resource_from_path(
    path_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    从学习路径移除资源

    仅移除资源与路径的关联，不删除资源本身。
    """
    service = get_curriculum_service()
    removed = await service.remove_resource_from_path(db, path_id, resource_id)
    if not removed:
        raise HTTPException(status_code=404, detail="路径中不存在该资源")
    await db.commit()


@router.put("/{path_id}/items/reorder", response_model=dict)
async def reorder_path_items(
    path_id: str,
    ordered_resource_ids: List[str] = Body(..., description="按期望顺序排列的资源 ID 列表"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    重新排序学习路径资源

    按传入的资源 ID 列表顺序更新路径中资源的排序。
    """
    service = get_curriculum_service()
    path = await service.get_path(db, path_id)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")

    items = await service.reorder_path_items(db, path_id, ordered_resource_ids)
    await db.commit()
    return {"path_id": path_id, "reordered_count": len(items)}
