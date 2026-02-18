"""
Equipment Recommendation Module Verification Script
Run: python scripts/verify_equipment_recommendation.py

Features:
1. Initialize data (brands, categories)
2. Create sample equipment
3. Create user profiles
4. Test personalized recommendations
5. Test similar equipment recommendations
6. Test equipment search and comparison
7. Test review functionality
"""

import asyncio
import sys
import os
import uuid
import argparse
from typing import Optional

# Set stdout encoding to utf-8 for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")


def print_step(step: int, text: str):
    print(f"\n{Colors.CYAN}[Step {step}]{Colors.RESET} {text}")


def print_success(text: str):
    print(f"  {Colors.GREEN}[OK]{Colors.RESET} {text}")


def print_warning(text: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {text}")


def print_error(text: str):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {text}")


def print_info(text: str):
    print(f"  {Colors.CYAN}  ->{Colors.RESET} {text}")


async def run_verification(verbose: bool = False):
    """运行完整验证流程"""
    from app.shared.database import init_db, get_session_factory, close_db
    from app.equipment_recommendation.models import (
        EquipmentCategory, Brand, Equipment, UserEquipmentProfile,
        EquipmentReview, PlayingStyle, GripStyle, SkillLevel
    )
    from app.equipment_recommendation.core import (
        get_equipment_service, get_profile_service,
        get_recommendation_engine, get_review_service
    )
    from app.equipment_recommendation.schemas import (
        BrandCreate, CategoryCreate, EquipmentCreate, EquipmentSearchRequest,
        UserProfileCreate, UserProfileUpdate, RecommendationRequest, ReviewCreate
    )
    from sqlalchemy import select, func

    print_header("Phase 4: Equipment Recommendation 验证")

    # 初始化数据库
    print_step(1, "初始化数据库")
    await init_db()
    print_success("数据库初始化完成")

    session_factory = get_session_factory()
    equipment_service = get_equipment_service()
    profile_service = get_profile_service()
    recommendation_engine = get_recommendation_engine()
    review_service = get_review_service()

    results = {
        "brands": 0,
        "categories": 0,
        "equipment": 0,
        "profiles": 0,
        "recommendations": 0,
        "reviews": 0,
        "errors": []
    }

    async with session_factory() as db:
        try:
            # ========== Step 2: 初始化品牌数据 ==========
            print_step(2, "初始化品牌数据")

            brands_data = [
                {"name": "Butterfly", "display_name": "蝴蝶", "country": "Japan"},
                {"name": "DHS", "display_name": "红双喜", "country": "China"},
                {"name": "Stiga", "display_name": "斯帝卡", "country": "Sweden"},
                {"name": "DONIC", "display_name": "多尼克", "country": "Germany"},
                {"name": "TIBHAR", "display_name": "挺拔", "country": "Germany"},
                {"name": "Yasaka", "display_name": "亚萨卡", "country": "Japan"},
            ]

            # 检查是否已存在
            brand_count = await db.execute(select(func.count(Brand.id)))
            existing_brands = brand_count.scalar() or 0

            if existing_brands >= len(brands_data):
                print_warning(f"品牌数据已存在 ({existing_brands} 个)")
            else:
                for brand_data in brands_data:
                    try:
                        existing = await db.execute(
                            select(Brand).where(Brand.name == brand_data["name"])
                        )
                        if not existing.scalar_one_or_none():
                            brand = await equipment_service.create_brand(
                                db, BrandCreate(**brand_data)
                            )
                            if verbose:
                                print_info(f"创建品牌: {brand.name}")
                    except Exception as e:
                        if verbose:
                            print_warning(f"品牌已存在或创建失败: {brand_data['name']}")

            brand_count = await db.execute(select(func.count(Brand.id)))
            results["brands"] = brand_count.scalar() or 0
            print_success(f"品牌总数: {results['brands']}")

            # ========== Step 3: 初始化分类数据 ==========
            print_step(3, "初始化分类数据")

            categories_data = [
                {"name": "blade", "display_name": "底板", "sort_order": 1},
                {"name": "rubber", "display_name": "胶皮", "sort_order": 2},
                {"name": "ball", "display_name": "乒乓球", "sort_order": 3},
                {"name": "shoes", "display_name": "球鞋", "sort_order": 4},
            ]

            for cat_data in categories_data:
                try:
                    existing = await db.execute(
                        select(EquipmentCategory).where(EquipmentCategory.name == cat_data["name"])
                    )
                    if not existing.scalar_one_or_none():
                        cat = await equipment_service.create_category(
                            db, CategoryCreate(**cat_data)
                        )
                        if verbose:
                            print_info(f"创建分类: {cat.display_name}")
                except Exception as e:
                    if verbose:
                        print_warning(f"分类已存在或创建失败: {cat_data['name']}")

            cat_count = await db.execute(select(func.count(EquipmentCategory.id)))
            results["categories"] = cat_count.scalar() or 0
            print_success(f"分类总数: {results['categories']}")

            # 获取分类和品牌 ID
            blade_result = await db.execute(
                select(EquipmentCategory).where(EquipmentCategory.name == "blade")
            )
            blade_cat = blade_result.scalar_one_or_none()

            rubber_result = await db.execute(
                select(EquipmentCategory).where(EquipmentCategory.name == "rubber")
            )
            rubber_cat = rubber_result.scalar_one_or_none()

            butterfly_result = await db.execute(
                select(Brand).where(Brand.name == "Butterfly")
            )
            butterfly_brand = butterfly_result.scalar_one_or_none()

            dhs_result = await db.execute(
                select(Brand).where(Brand.name == "DHS")
            )
            dhs_brand = dhs_result.scalar_one_or_none()

            stiga_result = await db.execute(
                select(Brand).where(Brand.name == "Stiga")
            )
            stiga_brand = stiga_result.scalar_one_or_none()

            # ========== Step 4: 创建示例装备 ==========
            print_step(4, "创建示例装备")

            equipment_data = [
                # 底板
                {
                    "name": "Butterfly Viscaria",
                    "brand_id": butterfly_brand.id if butterfly_brand else None,
                    "category_id": blade_cat.id if blade_cat else None,
                    "description": "经典弧圈底板，手感通透，适合中远台弧圈进攻",
                    "price_min": 800, "price_max": 1200,
                    "speed_rating": 85, "spin_rating": 80, "control_rating": 70,
                    "suitable_styles": ["offensive", "all_round"],
                    "suitable_levels": ["intermediate", "advanced"],
                    "is_featured": True
                },
                {
                    "name": "DHS Hurricane Long 5",
                    "brand_id": dhs_brand.id if dhs_brand else None,
                    "category_id": blade_cat.id if blade_cat else None,
                    "description": "马龙同款底板，极致速度与暴力",
                    "price_min": 600, "price_max": 800,
                    "speed_rating": 92, "spin_rating": 75, "control_rating": 55,
                    "suitable_styles": ["offensive"],
                    "suitable_levels": ["advanced", "professional"],
                    "is_featured": True
                },
                {
                    "name": "Stiga Clipper Wood",
                    "brand_id": stiga_brand.id if stiga_brand else None,
                    "category_id": blade_cat.id if blade_cat else None,
                    "description": "经典7层纯木底板，手感扎实，控制出色",
                    "price_min": 350, "price_max": 450,
                    "speed_rating": 72, "spin_rating": 70, "control_rating": 85,
                    "suitable_styles": ["all_round", "defensive"],
                    "suitable_levels": ["beginner", "intermediate"],
                    "is_featured": False
                },
                {
                    "name": "Stiga Allround Classic",
                    "brand_id": stiga_brand.id if stiga_brand else None,
                    "category_id": blade_cat.id if blade_cat else None,
                    "description": "入门神器，5层纯木，手感柔和",
                    "price_min": 200, "price_max": 280,
                    "speed_rating": 60, "spin_rating": 65, "control_rating": 90,
                    "suitable_styles": ["all_round", "defensive"],
                    "suitable_levels": ["beginner"],
                    "is_featured": False
                },
                # 胶皮
                {
                    "name": "Butterfly Tenergy 05",
                    "brand_id": butterfly_brand.id if butterfly_brand else None,
                    "category_id": rubber_cat.id if rubber_cat else None,
                    "description": "顶级弧圈胶皮，旋转强劲，世界冠军之选",
                    "price_min": 450, "price_max": 550,
                    "speed_rating": 80, "spin_rating": 95, "control_rating": 65,
                    "suitable_styles": ["offensive"],
                    "suitable_levels": ["intermediate", "advanced", "professional"],
                    "is_featured": True
                },
                {
                    "name": "DHS Hurricane 3 Neo",
                    "brand_id": dhs_brand.id if dhs_brand else None,
                    "category_id": rubber_cat.id if rubber_cat else None,
                    "description": "国套胶皮，粘性强，弧圈杀手",
                    "price_min": 150, "price_max": 200,
                    "speed_rating": 70, "spin_rating": 90, "control_rating": 70,
                    "suitable_styles": ["offensive", "all_round"],
                    "suitable_levels": ["intermediate", "advanced"],
                    "is_featured": True
                },
                {
                    "name": "DHS Hurricane 8",
                    "brand_id": dhs_brand.id if dhs_brand else None,
                    "category_id": rubber_cat.id if rubber_cat else None,
                    "description": "涩性胶皮，出球速度快，适合快攻",
                    "price_min": 120, "price_max": 160,
                    "speed_rating": 85, "spin_rating": 75, "control_rating": 65,
                    "suitable_styles": ["offensive"],
                    "suitable_levels": ["intermediate", "advanced"],
                    "is_featured": False
                },
                {
                    "name": "Butterfly Sriver",
                    "brand_id": butterfly_brand.id if butterfly_brand else None,
                    "category_id": rubber_cat.id if rubber_cat else None,
                    "description": "经典入门胶皮，全面均衡",
                    "price_min": 180, "price_max": 220,
                    "speed_rating": 70, "spin_rating": 70, "control_rating": 80,
                    "suitable_styles": ["all_round"],
                    "suitable_levels": ["beginner", "intermediate"],
                    "is_featured": False
                },
            ]

            created_equipment = []
            for eq_data in equipment_data:
                if not eq_data.get("brand_id") or not eq_data.get("category_id"):
                    continue
                try:
                    # 检查是否已存在
                    existing = await db.execute(
                        select(Equipment).where(Equipment.name == eq_data["name"])
                    )
                    if not existing.scalar_one_or_none():
                        eq = await equipment_service.create_equipment(
                            db, EquipmentCreate(**eq_data)
                        )
                        created_equipment.append(eq)
                        if verbose:
                            print_info(f"创建装备: {eq.name} (速度:{eq.speed_rating}, 旋转:{eq.spin_rating}, 控制:{eq.control_rating})")
                    else:
                        # 获取已存在的装备
                        existing_eq = await db.execute(
                            select(Equipment).where(Equipment.name == eq_data["name"])
                        )
                        created_equipment.append(existing_eq.scalar_one())
                except Exception as e:
                    if verbose:
                        print_warning(f"装备创建失败: {eq_data['name']} - {e}")

            eq_count = await db.execute(select(func.count(Equipment.id)))
            results["equipment"] = eq_count.scalar() or 0
            print_success(f"装备总数: {results['equipment']}")

            # ========== Step 5: 创建测试用户档案 ==========
            print_step(5, "创建测试用户档案")

            test_users = [
                {
                    "user_id": "test_offensive_intermediate",
                    "nickname": "弧圈小王",
                    "years_playing": 3,
                    "playing_style": "offensive",
                    "grip_style": "shakehand",
                    "skill_level": "intermediate",
                    "prefer_speed": 70,
                    "prefer_spin": 85,
                    "prefer_control": 50,
                    "budget_max": 600.0,
                },
                {
                    "user_id": "test_defensive_beginner",
                    "nickname": "稳健新手",
                    "years_playing": 1,
                    "playing_style": "defensive",
                    "grip_style": "shakehand",
                    "skill_level": "beginner",
                    "prefer_speed": 40,
                    "prefer_spin": 50,
                    "prefer_control": 90,
                    "budget_max": 300.0,
                },
                {
                    "user_id": "test_allround_advanced",
                    "nickname": "全面高手",
                    "years_playing": 8,
                    "playing_style": "all_round",
                    "grip_style": "shakehand",
                    "skill_level": "advanced",
                    "prefer_speed": 75,
                    "prefer_spin": 75,
                    "prefer_control": 75,
                    "budget_max": 1000.0,
                },
            ]

            created_profiles = []
            for user_data in test_users:
                try:
                    existing = await profile_service.get_profile_by_user_id(db, user_data["user_id"])
                    if not existing:
                        profile = await profile_service.create_profile(
                            db, UserProfileCreate(**user_data)
                        )
                        created_profiles.append(profile)
                        if verbose:
                            print_info(f"创建档案: {profile.nickname} ({profile.playing_style.value}, {profile.skill_level.value})")
                    else:
                        created_profiles.append(existing)
                        if verbose:
                            print_warning(f"档案已存在: {user_data['nickname']}")
                except Exception as e:
                    if verbose:
                        print_warning(f"档案创建失败: {user_data['nickname']} - {e}")

            profile_count = await db.execute(select(func.count(UserEquipmentProfile.id)))
            results["profiles"] = profile_count.scalar() or 0
            print_success(f"用户档案总数: {results['profiles']}")

            # ========== Step 6: 测试个性化推荐 ==========
            print_step(6, "测试个性化推荐")

            for profile in created_profiles[:2]:  # 测试前两个用户
                print_info(f"\n  用户: {profile.nickname}")
                print_info(f"  Playing Style: {profile.playing_style.value if profile.playing_style else 'N/A'}, " +
                          f"Level: {profile.skill_level.value if profile.skill_level else 'N/A'}, " +
                          f"Budget: {profile.budget_max or 'N/A'} CNY")

                request = RecommendationRequest(
                    user_id=profile.user_id,
                    recommendation_type="full_setup",
                    top_k=3
                )

                try:
                    items, explanation = await recommendation_engine.get_recommendations(
                        db, profile, request
                    )
                    results["recommendations"] += len(items)

                    print_info(f"  推荐说明: {explanation[:50]}..." if len(explanation) > 50 else f"  推荐说明: {explanation}")
                    print_info(f"  推荐结果 ({len(items)} 件):")
                    for i, item in enumerate(items, 1):
                        eq = item.equipment
                        print(f"      {i}. {eq.name} (分数: {item.score:.2f})")
                        print(f"         {eq.brand_name} | 速度:{eq.speed_rating} 旋转:{eq.spin_rating} 控制:{eq.control_rating}")
                        print(f"         理由: {', '.join(item.reasons[:2])}")

                    # 验证推荐合理性
                    if items:
                        if profile.playing_style == PlayingStyle.OFFENSIVE:
                            # 进攻型用户应该推荐高速度/旋转的装备
                            avg_speed = sum(i.equipment.speed_rating or 0 for i in items) / len(items)
                            avg_spin = sum(i.equipment.spin_rating or 0 for i in items) / len(items)
                            if avg_speed >= 70 or avg_spin >= 75:
                                print_success(f"  推荐合理性验证通过 (平均速度:{avg_speed:.0f}, 平均旋转:{avg_spin:.0f})")
                            else:
                                print_warning(f"  推荐可能不够进攻性 (平均速度:{avg_speed:.0f}, 平均旋转:{avg_spin:.0f})")
                        elif profile.playing_style == PlayingStyle.DEFENSIVE:
                            # 防守型用户应该推荐高控制的装备
                            avg_control = sum(i.equipment.control_rating or 0 for i in items) / len(items)
                            if avg_control >= 70:
                                print_success(f"  推荐合理性验证通过 (平均控制:{avg_control:.0f})")
                            else:
                                print_warning(f"  推荐可能控制性不足 (平均控制:{avg_control:.0f})")

                except Exception as e:
                    print_error(f"  推荐失败: {e}")
                    results["errors"].append(f"推荐失败: {e}")

            print_success(f"推荐测试完成，共生成 {results['recommendations']} 条推荐")

            # ========== Step 7: 测试装备搜索 ==========
            print_step(7, "测试装备搜索")

            # 搜索进攻型底板
            search_params = EquipmentSearchRequest(
                category_id=blade_cat.id if blade_cat else None,
                suitable_styles=["offensive"],
                min_speed=70,
                page=1,
                page_size=10
            )
            eq_list, total = await equipment_service.search_equipment(db, search_params)
            print_info(f"搜索 '进攻型底板 (速度>=70)': {total} 件")
            for eq in eq_list[:3]:
                print(f"      - {eq.name} (速度:{eq.speed_rating})")

            # 关键词搜索
            search_params = EquipmentSearchRequest(
                query="Hurricane",
                page=1,
                page_size=10
            )
            eq_list, total = await equipment_service.search_equipment(db, search_params)
            print_info(f"搜索关键词 'Hurricane': {total} 件")
            for eq in eq_list:
                print(f"      - {eq.name}")

            print_success("装备搜索测试完成")

            # ========== Step 8: 测试装备对比 ==========
            print_step(8, "测试装备对比")

            # 获取所有底板
            blade_result = await db.execute(
                select(Equipment).where(Equipment.category_id == blade_cat.id).limit(3)
            )
            blades = list(blade_result.scalars().all())

            if len(blades) >= 2:
                blade_ids = [b.id for b in blades[:3]]
                eq_list, summary = await equipment_service.compare_equipment(db, blade_ids)

                print_info(f"对比 {len(eq_list)} 件底板:")
                for eq in eq_list:
                    print(f"      - {eq.name}: 速度{eq.speed_rating} / 旋转{eq.spin_rating} / 控制{eq.control_rating}")

                print_info(f"对比摘要:")
                print(f"      速度最高: {summary.get('best_for_speed', 'N/A')[:8]}...")
                print(f"      旋转最高: {summary.get('best_for_spin', 'N/A')[:8]}...")
                print(f"      控制最高: {summary.get('best_for_control', 'N/A')[:8]}...")

                print_success("装备对比测试完成")
            else:
                print_warning("底板数量不足，跳过对比测试")

            # ========== Step 9: 测试相似装备推荐 ==========
            print_step(9, "测试相似装备推荐")

            if created_equipment:
                ref_eq = created_equipment[0]
                print_info(f"参考装备: {ref_eq.name}")

                ref_eq_full, similar_list, scores = await recommendation_engine.get_similar_equipment(
                    db, ref_eq.id, top_k=3
                )

                if similar_list:
                    print_info(f"相似装备 ({len(similar_list)} 件):")
                    for eq, score in zip(similar_list, scores):
                        print(f"      - {eq.name} (相似度: {score:.3f})")
                    print_success("相似装备推荐测试完成")
                else:
                    print_warning("未找到相似装备（可能是同分类装备数量不足）")
            else:
                print_warning("无装备数据，跳过相似推荐测试")

            # ========== Step 10: 测试评价功能 ==========
            print_step(10, "测试评价功能")

            if created_equipment and created_profiles:
                eq = created_equipment[0]
                profile = created_profiles[0]

                # 创建评价
                review_data = ReviewCreate(
                    equipment_id=eq.id,
                    overall_rating=5,
                    speed_rating=4,
                    spin_rating=5,
                    control_rating=3,
                    title="非常棒的底板",
                    content="手感通透，弧圈质量高，非常适合中远台进攻",
                    pros=["手感好", "弧圈质量高", "做工精细"],
                    cons=["价格偏高", "近台略显不足"],
                    usage_duration="3-6 months"
                )

                try:
                    review = await review_service.create_review(db, review_data, profile.id)
                    results["reviews"] += 1
                    print_info(f"创建评价: {review.title} ({review.overall_rating}星)")

                    # 获取评分汇总
                    summary = await review_service.get_rating_summary(db, eq.id)
                    print_info(f"评分汇总: 平均 {summary['avg_overall']:.1f} 分, 共 {summary['total_reviews']} 条评价")

                    print_success("评价功能测试完成")
                except Exception as e:
                    print_warning(f"评价创建失败（可能已存在）: {e}")
            else:
                print_warning("数据不足，跳过评价测试")

            await db.commit()

        except Exception as e:
            await db.rollback()
            print_error(f"验证过程出错: {e}")
            results["errors"].append(str(e))
            raise

    # ========== 验证总结 ==========
    print_header("验证结果总结")

    print(f"""
  {Colors.CYAN}数据统计:{Colors.RESET}
    品牌:     {results['brands']} 个
    分类:     {results['categories']} 个
    装备:     {results['equipment']} 件
    用户档案: {results['profiles']} 个
    推荐:     {results['recommendations']} 条
    评价:     {results['reviews']} 条
""")

    if results["errors"]:
        print(f"  {Colors.RED}错误 ({len(results['errors'])}):{Colors.RESET}")
        for err in results["errors"]:
            print(f"    - {err}")
        print()

    # 判断验证是否通过
    passed = (
        results["brands"] >= 3 and
        results["categories"] >= 2 and
        results["equipment"] >= 3 and
        results["profiles"] >= 1 and
        results["recommendations"] >= 1 and
        len(results["errors"]) == 0
    )

    if passed:
        print(f"  {Colors.GREEN}{Colors.BOLD}[PASS] Phase 4 验证通过!{Colors.RESET}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}[FAIL] Phase 4 验证未完全通过{Colors.RESET}")

    await close_db()
    return passed


async def run_api_test(host: str = "127.0.0.1", port: int = 8000):
    """运行 API 测试（需要服务器运行）"""
    import urllib.request
    import json

    print_header("Phase 4: API 端点测试")

    base_url = f"http://{host}:{port}/api/equipment"

    tests = [
        ("健康检查", f"{base_url}/health", "GET", None),
        ("品牌列表", f"{base_url}/brands", "GET", None),
        ("分类列表", f"{base_url}/categories", "GET", None),
        ("装备列表", f"{base_url}/equipment", "GET", None),
    ]

    passed = 0
    failed = 0

    for name, url, method, data in tests:
        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.add_header('Content-Type', 'application/json')
                req.data = json.dumps(data).encode('utf-8')

            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                print_success(f"{name}: OK")
                passed += 1
        except Exception as e:
            print_error(f"{name}: {e}")
            failed += 1

    print(f"\n  测试结果: {passed} 通过, {failed} 失败")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="装备推荐模块验证脚本")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    parser.add_argument("--api-test", action="store_true", help="测试 API 端点（需要服务器运行）")
    parser.add_argument("--host", default="127.0.0.1", help="API 服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="API 服务器端口")

    args = parser.parse_args()

    if args.api_test:
        success = asyncio.run(run_api_test(args.host, args.port))
    else:
        success = asyncio.run(run_verification(args.verbose))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
