"""
装备管理服务
提供装备、品牌、分类的 CRUD 操作
"""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.equipment_recommendation.models import (
    Equipment, Brand, EquipmentCategory
)
from app.equipment_recommendation.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentSearchRequest,
    BrandCreate, BrandUpdate,
    CategoryCreate, CategoryUpdate,
)
from app.shared.embedding_service import EmbeddingService


class EquipmentService:
    """装备管理服务"""

    def __init__(self):
        pass

    # ========== 品牌管理 ==========

    async def create_brand(
        self, db: AsyncSession, data: BrandCreate
    ) -> Brand:
        """创建品牌"""
        brand = Brand(
            id=str(uuid.uuid4()),
            name=data.name,
            display_name=data.display_name,
            country=data.country,
            description=data.description,
            logo_url=data.logo_url,
            website_url=data.website_url,
        )
        db.add(brand)
        await db.flush()
        logger.info(f"品牌创建成功: {brand.name}")
        return brand

    async def get_brand(self, db: AsyncSession, brand_id: str) -> Optional[Brand]:
        """获取品牌"""
        result = await db.execute(
            select(Brand).where(Brand.id == brand_id)
        )
        return result.scalar_one_or_none()

    async def list_brands(
        self, db: AsyncSession, include_inactive: bool = False
    ) -> Tuple[List[Brand], int]:
        """获取品牌列表"""
        query = select(Brand)
        if not include_inactive:
            query = query.where(Brand.is_active == True)
        query = query.order_by(Brand.name)

        result = await db.execute(query)
        brands = list(result.scalars().all())

        # 计数
        count_query = select(func.count(Brand.id))
        if not include_inactive:
            count_query = count_query.where(Brand.is_active == True)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return brands, total

    async def update_brand(
        self, db: AsyncSession, brand_id: str, data: BrandUpdate
    ) -> Optional[Brand]:
        """更新品牌"""
        brand = await self.get_brand(db, brand_id)
        if not brand:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(brand, key, value)

        await db.flush()
        logger.info(f"品牌更新成功: {brand.name}")
        return brand

    async def delete_brand(self, db: AsyncSession, brand_id: str) -> bool:
        """删除品牌"""
        brand = await self.get_brand(db, brand_id)
        if not brand:
            return False

        await db.delete(brand)
        await db.flush()
        logger.info(f"品牌删除成功: {brand.name}")
        return True

    # ========== 分类管理 ==========

    async def create_category(
        self, db: AsyncSession, data: CategoryCreate
    ) -> EquipmentCategory:
        """创建分类"""
        category = EquipmentCategory(
            id=str(uuid.uuid4()),
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
        )
        db.add(category)
        await db.flush()
        logger.info(f"分类创建成功: {category.name}")
        return category

    async def get_category(
        self, db: AsyncSession, category_id: str
    ) -> Optional[EquipmentCategory]:
        """获取分类"""
        result = await db.execute(
            select(EquipmentCategory).where(EquipmentCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def list_categories(
        self, db: AsyncSession, parent_id: Optional[str] = None
    ) -> Tuple[List[EquipmentCategory], int]:
        """获取分类列表"""
        query = select(EquipmentCategory)
        if parent_id is not None:
            query = query.where(EquipmentCategory.parent_id == parent_id)
        else:
            query = query.where(EquipmentCategory.parent_id.is_(None))
        query = query.order_by(EquipmentCategory.sort_order, EquipmentCategory.name)

        result = await db.execute(query)
        categories = list(result.scalars().all())

        count_result = await db.execute(select(func.count(EquipmentCategory.id)))
        total = count_result.scalar() or 0

        return categories, total

    async def get_category_tree(
        self, db: AsyncSession
    ) -> List[EquipmentCategory]:
        """获取分类树（含子分类）"""
        query = (
            select(EquipmentCategory)
            .options(selectinload(EquipmentCategory.subcategories))
            .where(EquipmentCategory.parent_id.is_(None))
            .order_by(EquipmentCategory.sort_order)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_category(
        self, db: AsyncSession, category_id: str, data: CategoryUpdate
    ) -> Optional[EquipmentCategory]:
        """更新分类"""
        category = await self.get_category(db, category_id)
        if not category:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)

        await db.flush()
        logger.info(f"分类更新成功: {category.name}")
        return category

    async def delete_category(self, db: AsyncSession, category_id: str) -> bool:
        """删除分类"""
        category = await self.get_category(db, category_id)
        if not category:
            return False

        await db.delete(category)
        await db.flush()
        logger.info(f"分类删除成功: {category.name}")
        return True

    # ========== 装备管理 ==========

    async def create_equipment(
        self, db: AsyncSession, data: EquipmentCreate
    ) -> Equipment:
        """创建装备"""
        # 生成嵌入向量（用于相似度搜索）
        embedding = await self._generate_equipment_embedding(data)

        equipment = Equipment(
            id=str(uuid.uuid4()),
            name=data.name,
            brand_id=data.brand_id,
            category_id=data.category_id,
            model_number=data.model_number,
            description=data.description,
            price_min=data.price_min,
            price_max=data.price_max,
            price_currency=data.price_currency,
            speed_rating=data.speed_rating,
            spin_rating=data.spin_rating,
            control_rating=data.control_rating,
            suitable_styles=data.suitable_styles,
            suitable_levels=data.suitable_levels,
            suitable_grips=data.suitable_grips,
            specifications=data.specifications,
            image_urls=data.image_urls,
            is_featured=data.is_featured,
            embedding=embedding,
        )
        db.add(equipment)
        await db.flush()

        # 加载关联对象
        await db.refresh(equipment, ["brand", "category"])
        logger.info(f"装备创建成功: {equipment.name}")
        return equipment

    async def get_equipment(
        self, db: AsyncSession, equipment_id: str, increment_view: bool = False
    ) -> Optional[Equipment]:
        """获取装备详情"""
        result = await db.execute(
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(Equipment.id == equipment_id)
        )
        equipment = result.scalar_one_or_none()

        if equipment and increment_view:
            equipment.view_count += 1
            await db.flush()

        return equipment

    async def search_equipment(
        self, db: AsyncSession, params: EquipmentSearchRequest
    ) -> Tuple[List[Equipment], int]:
        """搜索装备"""
        query = (
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(Equipment.is_active == True)
        )

        # 关键词搜索
        if params.query:
            search_term = f"%{params.query}%"
            query = query.where(
                or_(
                    Equipment.name.ilike(search_term),
                    Equipment.description.ilike(search_term),
                    Equipment.model_number.ilike(search_term),
                )
            )

        # 分类筛选
        if params.category_id:
            query = query.where(Equipment.category_id == params.category_id)

        # 品牌筛选
        if params.brand_ids:
            query = query.where(Equipment.brand_id.in_(params.brand_ids))

        # 价格筛选
        if params.price_min is not None:
            query = query.where(
                or_(
                    Equipment.price_min >= params.price_min,
                    Equipment.price_max >= params.price_min,
                )
            )
        if params.price_max is not None:
            query = query.where(
                or_(
                    Equipment.price_min <= params.price_max,
                    Equipment.price_max.is_(None),
                )
            )

        # 性能评分筛选
        if params.min_speed is not None:
            query = query.where(Equipment.speed_rating >= params.min_speed)
        if params.min_spin is not None:
            query = query.where(Equipment.spin_rating >= params.min_spin)
        if params.min_control is not None:
            query = query.where(Equipment.control_rating >= params.min_control)

        # 精选筛选
        if params.is_featured is not None:
            query = query.where(Equipment.is_featured == params.is_featured)

        # 适合的打法/水平筛选 (JSON 字段)
        # SQLite JSON 字段使用 LIKE 匹配
        if params.suitable_styles:
            for style in params.suitable_styles:
                query = query.where(
                    func.json_extract(Equipment.suitable_styles, '$').like(f'%"{style}"%')
                )
        if params.suitable_levels:
            for level in params.suitable_levels:
                query = query.where(
                    func.json_extract(Equipment.suitable_levels, '$').like(f'%"{level}"%')
                )

        # 排序
        sort_column = getattr(Equipment, params.sort_by, Equipment.created_at)
        if params.sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await db.execute(query)
        equipment_list = list(result.scalars().all())

        return equipment_list, total

    async def update_equipment(
        self, db: AsyncSession, equipment_id: str, data: EquipmentUpdate
    ) -> Optional[Equipment]:
        """更新装备"""
        equipment = await self.get_equipment(db, equipment_id)
        if not equipment:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 如果更新了影响嵌入的字段，重新生成嵌入
        embedding_fields = {"name", "description", "suitable_styles", "suitable_levels"}
        if embedding_fields & set(update_data.keys()):
            # 合并现有数据和更新数据来生成新嵌入
            merged_data = EquipmentCreate(
                name=update_data.get("name", equipment.name),
                brand_id=update_data.get("brand_id", equipment.brand_id),
                category_id=update_data.get("category_id", equipment.category_id),
                description=update_data.get("description", equipment.description),
                suitable_styles=update_data.get("suitable_styles", equipment.suitable_styles),
                suitable_levels=update_data.get("suitable_levels", equipment.suitable_levels),
            )
            update_data["embedding"] = await self._generate_equipment_embedding(merged_data)

        for key, value in update_data.items():
            setattr(equipment, key, value)

        await db.flush()
        await db.refresh(equipment, ["brand", "category"])
        logger.info(f"装备更新成功: {equipment.name}")
        return equipment

    async def delete_equipment(self, db: AsyncSession, equipment_id: str) -> bool:
        """删除装备"""
        equipment = await self.get_equipment(db, equipment_id)
        if not equipment:
            return False

        await db.delete(equipment)
        await db.flush()
        logger.info(f"装备删除成功: {equipment.name}")
        return True

    async def compare_equipment(
        self, db: AsyncSession, equipment_ids: List[str]
    ) -> Tuple[List[Equipment], dict]:
        """对比装备"""
        query = (
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(Equipment.id.in_(equipment_ids))
        )
        result = await db.execute(query)
        equipment_list = list(result.scalars().all())

        # 生成对比摘要
        summary = self._generate_comparison_summary(equipment_list)

        return equipment_list, summary

    def _generate_comparison_summary(self, equipment_list: List[Equipment]) -> dict:
        """生成装备对比摘要"""
        if not equipment_list:
            return {}

        # 计算各项指标的最大/最小值
        speed_ratings = [e.speed_rating for e in equipment_list if e.speed_rating]
        spin_ratings = [e.spin_rating for e in equipment_list if e.spin_rating]
        control_ratings = [e.control_rating for e in equipment_list if e.control_rating]
        prices = [e.price_min for e in equipment_list if e.price_min]

        summary = {
            "count": len(equipment_list),
            "speed": {
                "max": max(speed_ratings) if speed_ratings else None,
                "min": min(speed_ratings) if speed_ratings else None,
                "avg": sum(speed_ratings) / len(speed_ratings) if speed_ratings else None,
            },
            "spin": {
                "max": max(spin_ratings) if spin_ratings else None,
                "min": min(spin_ratings) if spin_ratings else None,
                "avg": sum(spin_ratings) / len(spin_ratings) if spin_ratings else None,
            },
            "control": {
                "max": max(control_ratings) if control_ratings else None,
                "min": min(control_ratings) if control_ratings else None,
                "avg": sum(control_ratings) / len(control_ratings) if control_ratings else None,
            },
            "price": {
                "max": max(prices) if prices else None,
                "min": min(prices) if prices else None,
            },
            "best_for_speed": None,
            "best_for_spin": None,
            "best_for_control": None,
        }

        # 找出各项最优
        if speed_ratings:
            best_speed = max(equipment_list, key=lambda e: e.speed_rating or 0)
            summary["best_for_speed"] = best_speed.id
        if spin_ratings:
            best_spin = max(equipment_list, key=lambda e: e.spin_rating or 0)
            summary["best_for_spin"] = best_spin.id
        if control_ratings:
            best_control = max(equipment_list, key=lambda e: e.control_rating or 0)
            summary["best_for_control"] = best_control.id

        return summary

    async def _generate_equipment_embedding(
        self, data: EquipmentCreate
    ) -> Optional[List[float]]:
        """生成装备的嵌入向量"""
        try:
            # 构建用于嵌入的文本
            text_parts = [data.name]
            if data.description:
                text_parts.append(data.description)
            if data.suitable_styles:
                text_parts.append(f"适合打法: {', '.join(data.suitable_styles)}")
            if data.suitable_levels:
                text_parts.append(f"适合水平: {', '.join(data.suitable_levels)}")

            text = " ".join(text_parts)
            embedding = EmbeddingService.encode_single(text)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"生成装备嵌入向量失败: {e}")
            return None


# 单例模式
_equipment_service: Optional[EquipmentService] = None


def get_equipment_service() -> EquipmentService:
    """获取装备服务单例"""
    global _equipment_service
    if _equipment_service is None:
        _equipment_service = EquipmentService()
    return _equipment_service
