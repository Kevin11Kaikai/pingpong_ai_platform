"""
品牌管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import get_equipment_service
from app.equipment_recommendation.schemas import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandListResponse,
)

router = APIRouter()


@router.post("", response_model=BrandResponse)
async def create_brand(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    """
    创建新品牌

    品牌名称必须唯一。
    """
    service = get_equipment_service()
    try:
        brand = await service.create_brand(db, data)
        return BrandResponse.model_validate(brand)
    except Exception as e:
        logger.error(f"创建品牌失败: {e}")
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=400, detail="品牌名称已存在")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=BrandListResponse)
async def list_brands(
    include_inactive: bool = Query(False, description="是否包含已停用的品牌"),
    db: AsyncSession = Depends(get_db_session),
) -> BrandListResponse:
    """
    获取品牌列表

    默认只返回活跃的品牌，设置 include_inactive=true 可包含已停用的品牌。
    """
    service = get_equipment_service()
    brands, total = await service.list_brands(db, include_inactive)
    return BrandListResponse(
        brands=[BrandResponse.model_validate(b) for b in brands],
        total=total,
    )


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    """
    获取品牌详情
    """
    service = get_equipment_service()
    brand = await service.get_brand(db, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    return BrandResponse.model_validate(brand)


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: str,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> BrandResponse:
    """
    更新品牌信息
    """
    service = get_equipment_service()
    brand = await service.update_brand(db, brand_id, data)
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    return BrandResponse.model_validate(brand)


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除品牌

    注意：删除品牌会同时删除该品牌下的所有装备。
    """
    service = get_equipment_service()
    success = await service.delete_brand(db, brand_id)
    if not success:
        raise HTTPException(status_code=404, detail="品牌不存在")
    return {"message": "删除成功"}
