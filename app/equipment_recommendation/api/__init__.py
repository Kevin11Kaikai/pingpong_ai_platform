"""
装备推荐模块 API 路由聚合
"""

from fastapi import APIRouter

from app.equipment_recommendation.api.equipment import router as equipment_router
from app.equipment_recommendation.api.brands import router as brands_router
from app.equipment_recommendation.api.categories import router as categories_router
from app.equipment_recommendation.api.profiles import router as profiles_router
from app.equipment_recommendation.api.recommendations import router as recommendations_router
from app.equipment_recommendation.api.reviews import router as reviews_router

router = APIRouter()

# 聚合子路由
router.include_router(equipment_router, prefix="/equipment", tags=["装备管理"])
router.include_router(brands_router, prefix="/brands", tags=["品牌管理"])
router.include_router(categories_router, prefix="/categories", tags=["分类管理"])
router.include_router(profiles_router, prefix="/profiles", tags=["用户档案"])
router.include_router(recommendations_router, prefix="/recommendations", tags=["智能推荐"])
router.include_router(reviews_router, prefix="/reviews", tags=["评价管理"])


@router.get("/health")
async def health_check():
    """
    装备推荐模块健康检查

    返回模块状态和可用的子模块列表。
    """
    return {
        "module": "equipment_recommendation",
        "status": "healthy",
        "sub_modules": [
            "equipment",
            "brands",
            "categories",
            "profiles",
            "recommendations",
            "reviews",
        ],
        "features": [
            "装备 CRUD",
            "品牌和分类管理",
            "用户偏好档案",
            "个性化推荐",
            "相似装备推荐",
            "装备评价",
            "装备对比",
        ],
    }
