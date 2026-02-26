"""
装备管理 API 路由
提供装备的 CRUD 和搜索功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.equipment_recommendation.core import get_equipment_service
from app.equipment_recommendation.schemas import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentListResponse,
    EquipmentSearchRequest,
    EquipmentCompareRequest,
    EquipmentCompareResponse,
    EquipmentBrief,
)

router = APIRouter()


@router.post("", response_model=EquipmentResponse)
async def create_equipment(
    data: EquipmentCreate,
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentResponse:
    """
    创建新装备

    需要提供装备名称、品牌ID、分类ID等基本信息。
    性能评分（速度、旋转、控制）为可选项。
    """
    service = get_equipment_service()
    try:
        equipment = await service.create_equipment(db, data)
        return _to_equipment_response(equipment)
    except Exception as e:
        logger.error(f"创建装备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentResponse:
    """
    获取装备详情

    返回装备的完整信息，包括品牌、分类、性能评分等。
    每次访问会增加浏览计数。
    """
    service = get_equipment_service()
    equipment = await service.get_equipment(db, equipment_id, increment_view=True)
    if not equipment:
        raise HTTPException(status_code=404, detail="装备不存在")
    return _to_equipment_response(equipment)


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: str,
    data: EquipmentUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentResponse:
    """
    更新装备信息

    可以部分更新，只提供需要修改的字段即可。
    """
    service = get_equipment_service()
    equipment = await service.update_equipment(db, equipment_id, data)
    if not equipment:
        raise HTTPException(status_code=404, detail="装备不存在")
    return _to_equipment_response(equipment)


@router.delete("/{equipment_id}")
async def delete_equipment(
    equipment_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    删除装备

    删除操作会同时删除关联的评价记录。
    """
    service = get_equipment_service()
    success = await service.delete_equipment(db, equipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="装备不存在")
    return {"message": "删除成功"}


@router.post("/search", response_model=EquipmentListResponse)
async def search_equipment(
    params: EquipmentSearchRequest,
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentListResponse:
    """
    搜索装备

    支持多种筛选条件：
    - query: 关键词搜索（名称、描述、型号）
    - category_id: 分类筛选
    - brand_ids: 品牌筛选（支持多选）
    - price_min/max: 价格范围
    - min_speed/spin/control: 最低性能要求
    - suitable_styles: 适合的打法
    - suitable_levels: 适合的水平
    - is_featured: 是否精选
    """
    service = get_equipment_service()
    equipment_list, total = await service.search_equipment(db, params)

    return EquipmentListResponse(
        equipment=[_to_equipment_brief(e) for e in equipment_list],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("", response_model=EquipmentListResponse)
async def list_equipment(
    category_id: str = Query(None, description="分类ID"),
    brand_id: str = Query(None, description="品牌ID"),
    is_featured: bool = Query(None, description="是否精选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentListResponse:
    """
    获取装备列表

    简单的列表接口，支持基本筛选。
    复杂筛选请使用 POST /search 接口。
    """
    params = EquipmentSearchRequest(
        category_id=category_id,
        brand_ids=[brand_id] if brand_id else None,
        is_featured=is_featured,
        page=page,
        page_size=page_size,
    )
    service = get_equipment_service()
    equipment_list, total = await service.search_equipment(db, params)

    return EquipmentListResponse(
        equipment=[_to_equipment_brief(e) for e in equipment_list],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/compare", response_model=EquipmentCompareResponse)
async def compare_equipment(
    data: EquipmentCompareRequest,
    db: AsyncSession = Depends(get_db_session),
) -> EquipmentCompareResponse:
    """
    对比装备

    支持 2-5 件装备的对比，返回详细信息和对比摘要。
    对比摘要包含各项指标的最大/最小值和最优装备标识。
    """
    service = get_equipment_service()
    equipment_list, summary = await service.compare_equipment(db, data.equipment_ids)

    if len(equipment_list) < 2:
        raise HTTPException(status_code=400, detail="至少需要2件装备进行对比")

    return EquipmentCompareResponse(
        equipment=[_to_equipment_response(e) for e in equipment_list],
        comparison_summary=summary,
    )


def _to_equipment_response(equipment) -> EquipmentResponse:
    """转换为响应模型"""
    return EquipmentResponse(
        id=equipment.id,
        name=equipment.name,
        brand_id=equipment.brand_id,
        brand_name=equipment.brand.name if equipment.brand else "",
        category_id=equipment.category_id,
        category_name=equipment.category.display_name if equipment.category else "",
        model_number=equipment.model_number,
        description=equipment.description,
        price_min=equipment.price_min,
        price_max=equipment.price_max,
        price_currency=equipment.price_currency,
        speed_rating=equipment.speed_rating,
        spin_rating=equipment.spin_rating,
        control_rating=equipment.control_rating,
        suitable_styles=equipment.suitable_styles,
        suitable_levels=equipment.suitable_levels,
        suitable_grips=equipment.suitable_grips,
        specifications=equipment.specifications,
        image_urls=equipment.image_urls,
        view_count=equipment.view_count,
        review_count=equipment.review_count,
        avg_rating=equipment.avg_rating,
        is_active=equipment.is_active,
        is_featured=equipment.is_featured,
        created_at=equipment.created_at,
        updated_at=equipment.updated_at,
    )


def _to_equipment_brief(equipment) -> EquipmentBrief:
    """转换为简要信息"""
    return EquipmentBrief(
        id=equipment.id,
        name=equipment.name,
        brand_name=equipment.brand.name if equipment.brand else "",
        category_name=equipment.category.display_name if equipment.category else "",
        price_min=equipment.price_min,
        price_max=equipment.price_max,
        speed_rating=equipment.speed_rating,
        spin_rating=equipment.spin_rating,
        control_rating=equipment.control_rating,
        avg_rating=equipment.avg_rating,
        review_count=equipment.review_count,
        image_url=equipment.image_urls[0] if equipment.image_urls else None,
    )
