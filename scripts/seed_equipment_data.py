"""
装备模块初始数据填充脚本
运行: python scripts/seed_equipment_data.py
"""

import asyncio
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.shared.database import init_db, get_session_factory
from app.equipment_recommendation.models import EquipmentCategory, Brand
import uuid


# 初始分类数据
CATEGORIES = [
    {"name": "blade", "display_name": "底板", "description": "乒乓球拍底板", "sort_order": 1},
    {"name": "rubber", "display_name": "胶皮", "description": "乒乓球拍胶皮", "sort_order": 2},
    {"name": "ball", "display_name": "乒乓球", "description": "比赛和训练用球", "sort_order": 3},
    {"name": "shoes", "display_name": "球鞋", "description": "乒乓球专用鞋", "sort_order": 4},
    {"name": "apparel", "display_name": "服装", "description": "乒乓球服装", "sort_order": 5},
    {"name": "accessories", "display_name": "配件", "description": "护边、胶水等配件", "sort_order": 6},
]

# 初始品牌数据
BRANDS = [
    {
        "name": "Butterfly",
        "display_name": "蝴蝶",
        "country": "Japan",
        "description": "日本知名乒乓球品牌，以高端底板和胶皮闻名",
    },
    {
        "name": "DHS",
        "display_name": "红双喜",
        "country": "China",
        "description": "中国国产品牌，国家队指定用品",
    },
    {
        "name": "Stiga",
        "display_name": "斯帝卡",
        "country": "Sweden",
        "description": "瑞典老牌乒乓球品牌",
    },
    {
        "name": "DONIC",
        "display_name": "多尼克",
        "country": "Germany",
        "description": "德国专业乒乓球品牌",
    },
    {
        "name": "TIBHAR",
        "display_name": "挺拔",
        "country": "Germany",
        "description": "德国高端乒乓球品牌",
    },
    {
        "name": "Yasaka",
        "display_name": "亚萨卡",
        "country": "Japan",
        "description": "日本经典乒乓球品牌",
    },
    {
        "name": "Nittaku",
        "display_name": "尼塔库",
        "country": "Japan",
        "description": "日本专业乒乓球品牌",
    },
    {
        "name": "JOOLA",
        "display_name": "优拉",
        "country": "Germany",
        "description": "德国乒乓球品牌，球台供应商",
    },
    {
        "name": "Xiom",
        "display_name": "骄猛",
        "country": "South Korea",
        "description": "韩国乒乓球品牌",
    },
    {
        "name": "729",
        "display_name": "友谊729",
        "country": "China",
        "description": "中国经典乒乓球品牌",
    },
    {
        "name": "Yinhe",
        "display_name": "银河",
        "country": "China",
        "description": "中国性价比品牌",
    },
    {
        "name": "Double Fish",
        "display_name": "双鱼",
        "country": "China",
        "description": "中国乒乓球和球台品牌",
    },
]


async def seed_data():
    """填充初始数据"""
    await init_db()

    session_factory = get_session_factory()
    async with session_factory() as session:
        # 检查是否已有数据
        from sqlalchemy import select, func

        cat_count = await session.execute(select(func.count(EquipmentCategory.id)))
        if cat_count.scalar() > 0:
            print("分类数据已存在，跳过...")
        else:
            # 添加分类
            for cat_data in CATEGORIES:
                category = EquipmentCategory(
                    id=str(uuid.uuid4()),
                    **cat_data
                )
                session.add(category)
            print(f"已添加 {len(CATEGORIES)} 个分类")

        brand_count = await session.execute(select(func.count(Brand.id)))
        if brand_count.scalar() > 0:
            print("品牌数据已存在，跳过...")
        else:
            # 添加品牌
            for brand_data in BRANDS:
                brand = Brand(
                    id=str(uuid.uuid4()),
                    **brand_data
                )
                session.add(brand)
            print(f"已添加 {len(BRANDS)} 个品牌")

        await session.commit()
        print("初始数据填充完成！")


if __name__ == "__main__":
    asyncio.run(seed_data())
