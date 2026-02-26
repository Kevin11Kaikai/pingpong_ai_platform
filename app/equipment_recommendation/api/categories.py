"""
装备分类 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import get_equipment_service
from app.equipment_recommendation.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryTreeResponse,
)

router = APIRouter()


@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """
    创建新分类

    可以创建顶级分类或子分类（通过 parent_id 指定父分类）。
    分类名称（name）在同一级别必须唯一。
    """
    service = get_equipment_service()
    try:
        category = await service.create_category(db, data)
        return CategoryResponse.model_validate(category)
    except Exception as e:
        logger.error(f"创建分类失败: {e}")
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=400, detail="分类名称已存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    parent_id: str = Query(None, description="父分类ID，不传则返回顶级分类"),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryListResponse:
    """
    获取分类列表

    不传 parent_id 返回顶级分类，传入 parent_id 返回其子分类。
    """
    service = get_equipment_service()
    categories, total = await service.list_categories(db, parent_id)
    return CategoryListResponse(
        categories=[CategoryResponse.model_validate(c) for c in categories],
        total=total,
    )


@router.get("/tree", response_model=list[CategoryTreeResponse])
async def get_category_tree(
    db: AsyncSession = Depends(get_db_session),
) -> list[CategoryTreeResponse]:
    """
    获取分类树

    返回完整的分类层级结构，包含所有子分类。
    """
    service = get_equipment_service()
    categories = await service.get_category_tree(db)
    return [_to_tree_response(c) for c in categories]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """
    获取分类详情
    """
    service = get_equipment_service()
    category = await service.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return CategoryResponse.model_validate(category)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """
    更新分类信息
    """
    service = get_equipment_service()
    category = await service.update_category(db, category_id, data)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除分类

    注意：删除分类会同时删除该分类下的所有装备和子分类。
    """
    service = get_equipment_service()
    success = await service.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"message": "删除成功"}


def _to_tree_response(category) -> CategoryTreeResponse:
    """转换为树形响应"""
    return CategoryTreeResponse(
        id=category.id,
        name=category.name,
        display_name=category.display_name,
        description=category.description,
        sort_order=category.sort_order,
        subcategories=[
            _to_tree_response(sub) for sub in (category.subcategories or [])
        ],
    )
