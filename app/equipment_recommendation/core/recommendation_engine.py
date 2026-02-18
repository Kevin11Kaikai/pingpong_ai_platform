"""
装备推荐引擎
基于用户档案和装备特性进行智能推荐
使用规则匹配 + 向量相似度混合策略
"""

import uuid
from typing import Optional, List, Tuple
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.equipment_recommendation.models import (
    Equipment, UserEquipmentProfile, EquipmentRecommendation,
    PlayingStyle, SkillLevel
)
from app.equipment_recommendation.schemas import (
    RecommendationRequest, RecommendedItem, EquipmentBrief
)
from app.shared.embedding_service import EmbeddingService


class RecommendationEngine:
    """装备推荐引擎"""

    # 打法风格与装备特性的映射
    STYLE_WEIGHTS = {
        PlayingStyle.OFFENSIVE: {"speed": 0.5, "spin": 0.3, "control": 0.2},
        PlayingStyle.DEFENSIVE: {"speed": 0.2, "spin": 0.3, "control": 0.5},
        PlayingStyle.ALL_ROUND: {"speed": 0.33, "spin": 0.34, "control": 0.33},
        PlayingStyle.CHOPPER: {"speed": 0.2, "spin": 0.4, "control": 0.4},
    }

    # 技术水平与推荐策略的映射
    LEVEL_PREFERENCES = {
        SkillLevel.BEGINNER: {
            "control_min": 60,  # 初学者需要高控制
            "price_weight": 0.3,  # 性价比重要
            "prefer_forgiving": True,  # 容错性高的装备
        },
        SkillLevel.INTERMEDIATE: {
            "control_min": 40,
            "price_weight": 0.2,
            "prefer_forgiving": False,
        },
        SkillLevel.ADVANCED: {
            "control_min": 20,
            "price_weight": 0.1,
            "prefer_forgiving": False,
        },
        SkillLevel.PROFESSIONAL: {
            "control_min": 0,
            "price_weight": 0.05,
            "prefer_forgiving": False,
        },
    }

    def __init__(self):
        pass

    async def get_recommendations(
        self,
        db: AsyncSession,
        profile: UserEquipmentProfile,
        request: RecommendationRequest,
    ) -> Tuple[List[RecommendedItem], str]:
        """
        获取个性化推荐

        Args:
            db: 数据库会话
            profile: 用户偏好档案
            request: 推荐请求

        Returns:
            推荐项列表和推荐说明
        """
        # 应用临时覆盖参数
        effective_style = (
            PlayingStyle(request.override_style)
            if request.override_style
            else profile.playing_style
        )
        effective_level = (
            SkillLevel(request.override_level)
            if request.override_level
            else profile.skill_level
        )
        effective_budget = request.override_budget_max or profile.budget_max

        # 获取候选装备
        candidates = await self._get_candidate_equipment(
            db, request.recommendation_type, effective_budget
        )

        if not candidates:
            return [], "未找到符合条件的装备"

        # 计算每个候选装备的匹配分数
        scored_items = []
        for equipment in candidates:
            score, reasons = self._calculate_match_score(
                equipment, profile, effective_style, effective_level
            )
            if score > 0:
                scored_items.append((equipment, score, reasons))

        # 按分数排序并取 top_k
        scored_items.sort(key=lambda x: x[1], reverse=True)
        top_items = scored_items[: request.top_k]

        # 构建推荐结果
        recommended_items = []
        for equipment, score, reasons in top_items:
            item = RecommendedItem(
                equipment=self._to_equipment_brief(equipment),
                score=round(score, 3),
                reasons=reasons,
            )
            recommended_items.append(item)

        # 生成推荐说明
        explanation = self._generate_explanation(
            profile, effective_style, effective_level, len(recommended_items)
        )

        # 保存推荐记录
        await self._save_recommendation_record(
            db, profile.id, request.recommendation_type, recommended_items, explanation
        )

        return recommended_items, explanation

    async def get_similar_equipment(
        self, db: AsyncSession, equipment_id: str, top_k: int = 5
    ) -> Tuple[Optional[Equipment], List[Equipment], List[float]]:
        """
        获取相似装备（基于向量相似度）

        Args:
            db: 数据库会话
            equipment_id: 参考装备ID
            top_k: 返回数量

        Returns:
            参考装备, 相似装备列表, 相似度分数列表
        """
        # 获取参考装备
        ref_result = await db.execute(
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(Equipment.id == equipment_id)
        )
        ref_equipment = ref_result.scalar_one_or_none()

        if not ref_equipment or not ref_equipment.embedding:
            return ref_equipment, [], []

        ref_embedding = np.array(ref_equipment.embedding)

        # 获取同类别的所有装备
        result = await db.execute(
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(
                Equipment.category_id == ref_equipment.category_id,
                Equipment.id != equipment_id,
                Equipment.is_active == True,
                Equipment.embedding.isnot(None),
            )
        )
        candidates = list(result.scalars().all())

        if not candidates:
            return ref_equipment, [], []

        # 计算相似度
        similarities = []
        for eq in candidates:
            if eq.embedding:
                eq_embedding = np.array(eq.embedding)
                similarity = self._cosine_similarity(ref_embedding, eq_embedding)
                similarities.append((eq, similarity))

        # 排序并取 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar = similarities[:top_k]

        similar_equipment = [item[0] for item in top_similar]
        scores = [item[1] for item in top_similar]

        return ref_equipment, similar_equipment, scores

    async def _get_candidate_equipment(
        self,
        db: AsyncSession,
        recommendation_type: str,
        budget_max: Optional[float],
    ) -> List[Equipment]:
        """获取候选装备"""
        query = (
            select(Equipment)
            .options(selectinload(Equipment.brand), selectinload(Equipment.category))
            .where(Equipment.is_active == True)
        )

        # 根据推荐类型筛选分类
        if recommendation_type == "blade":
            query = query.join(Equipment.category).where(
                Equipment.category.has(name="blade")
            )
        elif recommendation_type == "rubber":
            query = query.join(Equipment.category).where(
                Equipment.category.has(name="rubber")
            )
        # full_setup 不限制分类

        # 预算筛选
        if budget_max is not None:
            query = query.where(
                (Equipment.price_min <= budget_max) | (Equipment.price_min.is_(None))
            )

        result = await db.execute(query)
        return list(result.scalars().all())

    def _calculate_match_score(
        self,
        equipment: Equipment,
        profile: UserEquipmentProfile,
        style: Optional[PlayingStyle],
        level: Optional[SkillLevel],
    ) -> Tuple[float, List[str]]:
        """
        计算装备与用户的匹配分数

        Returns:
            (分数 0-1, 推荐理由列表)
        """
        score = 0.0
        reasons = []
        weights_sum = 0.0

        # 1. 打法风格匹配 (权重 0.3)
        style_score, style_reason = self._match_playing_style(equipment, profile, style)
        if style_score > 0:
            score += style_score * 0.3
            weights_sum += 0.3
            if style_reason:
                reasons.append(style_reason)

        # 2. 技术水平匹配 (权重 0.25)
        level_score, level_reason = self._match_skill_level(equipment, level)
        if level_score > 0:
            score += level_score * 0.25
            weights_sum += 0.25
            if level_reason:
                reasons.append(level_reason)

        # 3. 用户偏好匹配 (权重 0.25)
        pref_score, pref_reasons = self._match_user_preferences(equipment, profile)
        if pref_score > 0:
            score += pref_score * 0.25
            weights_sum += 0.25
            reasons.extend(pref_reasons)

        # 4. 评价和热度 (权重 0.2)
        rating_score, rating_reason = self._match_rating_popularity(equipment)
        if rating_score > 0:
            score += rating_score * 0.2
            weights_sum += 0.2
            if rating_reason:
                reasons.append(rating_reason)

        # 归一化分数
        if weights_sum > 0:
            score = score / weights_sum
        else:
            score = 0.5  # 默认中等分数

        # 精选装备加分
        if equipment.is_featured:
            score = min(1.0, score + 0.05)
            reasons.append("编辑精选推荐")

        return score, reasons

    def _match_playing_style(
        self,
        equipment: Equipment,
        profile: UserEquipmentProfile,
        style: Optional[PlayingStyle],
    ) -> Tuple[float, Optional[str]]:
        """匹配打法风格"""
        if not style:
            return 0.5, None  # 无风格信息返回中等分数

        # 检查装备是否标记为适合该打法
        if equipment.suitable_styles:
            if style.value in equipment.suitable_styles:
                return 1.0, f"适合{self._style_to_chinese(style)}打法"
            # 检查是否与用户风格完全不匹配
            incompatible = self._check_style_incompatibility(style, equipment.suitable_styles)
            if incompatible:
                return 0.2, None

        # 基于性能评分计算匹配度
        weights = self.STYLE_WEIGHTS.get(style, {"speed": 0.33, "spin": 0.34, "control": 0.33})

        score = 0.0
        if equipment.speed_rating:
            score += (equipment.speed_rating / 100) * weights["speed"]
        if equipment.spin_rating:
            score += (equipment.spin_rating / 100) * weights["spin"]
        if equipment.control_rating:
            score += (equipment.control_rating / 100) * weights["control"]

        return score, None

    def _match_skill_level(
        self, equipment: Equipment, level: Optional[SkillLevel]
    ) -> Tuple[float, Optional[str]]:
        """匹配技术水平"""
        if not level:
            return 0.5, None

        # 检查装备是否标记为适合该水平
        if equipment.suitable_levels:
            if level.value in equipment.suitable_levels:
                return 1.0, f"适合{self._level_to_chinese(level)}水平"
            # 检查水平差距
            level_diff = self._calculate_level_difference(level, equipment.suitable_levels)
            if level_diff > 1:
                return 0.3, None

        # 基于控制评分（初学者需要高控制）
        prefs = self.LEVEL_PREFERENCES.get(level, {})
        control_min = prefs.get("control_min", 0)

        if equipment.control_rating and equipment.control_rating >= control_min:
            return 0.8, None

        return 0.5, None

    def _match_user_preferences(
        self, equipment: Equipment, profile: UserEquipmentProfile
    ) -> Tuple[float, List[str]]:
        """匹配用户偏好设置"""
        scores = []
        reasons = []

        # 速度偏好匹配
        if equipment.speed_rating and profile.prefer_speed:
            # 用户偏好越高，越倾向高速度装备
            target_speed = profile.prefer_speed
            actual_speed = equipment.speed_rating
            speed_match = 1 - abs(target_speed - actual_speed) / 100
            scores.append(speed_match)
            if speed_match > 0.8 and target_speed > 60:
                reasons.append("符合速度偏好")

        # 旋转偏好匹配
        if equipment.spin_rating and profile.prefer_spin:
            target_spin = profile.prefer_spin
            actual_spin = equipment.spin_rating
            spin_match = 1 - abs(target_spin - actual_spin) / 100
            scores.append(spin_match)
            if spin_match > 0.8 and target_spin > 60:
                reasons.append("符合旋转偏好")

        # 控制偏好匹配
        if equipment.control_rating and profile.prefer_control:
            target_control = profile.prefer_control
            actual_control = equipment.control_rating
            control_match = 1 - abs(target_control - actual_control) / 100
            scores.append(control_match)
            if control_match > 0.8 and target_control > 60:
                reasons.append("符合控制偏好")

        # 预算匹配
        if profile.budget_max and equipment.price_min:
            if equipment.price_min <= profile.budget_max:
                scores.append(1.0)
                if equipment.price_min <= profile.budget_max * 0.7:
                    reasons.append("价格实惠")
            else:
                scores.append(0.3)

        if scores:
            return sum(scores) / len(scores), reasons
        return 0.5, []

    def _match_rating_popularity(
        self, equipment: Equipment
    ) -> Tuple[float, Optional[str]]:
        """匹配评价和热度"""
        score = 0.5  # 基础分

        # 评分加成
        if equipment.avg_rating >= 4.5:
            score += 0.3
            reason = "用户好评度高"
        elif equipment.avg_rating >= 4.0:
            score += 0.2
            reason = "用户评价良好"
        elif equipment.avg_rating >= 3.5:
            score += 0.1
            reason = None
        else:
            reason = None

        # 评论数量加成（热门程度）
        if equipment.review_count >= 100:
            score += 0.15
        elif equipment.review_count >= 50:
            score += 0.1
        elif equipment.review_count >= 20:
            score += 0.05

        return min(1.0, score), reason if score > 0.6 else None

    def _generate_explanation(
        self,
        profile: UserEquipmentProfile,
        style: Optional[PlayingStyle],
        level: Optional[SkillLevel],
        result_count: int,
    ) -> str:
        """生成推荐说明"""
        parts = []

        if result_count == 0:
            return "抱歉，未能找到符合您条件的装备推荐。建议调整筛选条件后重试。"

        parts.append(f"根据您的偏好，为您推荐了 {result_count} 款装备。")

        if style:
            parts.append(f"考虑到您的{self._style_to_chinese(style)}打法，")
            if style == PlayingStyle.OFFENSIVE:
                parts.append("推荐的装备注重速度和旋转性能。")
            elif style == PlayingStyle.DEFENSIVE:
                parts.append("推荐的装备注重控制和稳定性。")
            elif style == PlayingStyle.CHOPPER:
                parts.append("推荐的装备注重削球控制和旋转能力。")
            else:
                parts.append("推荐的装备综合性能均衡。")

        if level:
            if level == SkillLevel.BEGINNER:
                parts.append("作为初学者，建议选择控制性好、容错率高的装备。")
            elif level == SkillLevel.PROFESSIONAL:
                parts.append("专业级别可以考虑更具攻击性的高端装备。")

        return "".join(parts)

    async def _save_recommendation_record(
        self,
        db: AsyncSession,
        profile_id: str,
        recommendation_type: str,
        items: List[RecommendedItem],
        explanation: str,
    ) -> EquipmentRecommendation:
        """保存推荐记录"""
        record = EquipmentRecommendation(
            id=str(uuid.uuid4()),
            user_profile_id=profile_id,
            recommendation_type=recommendation_type,
            recommended_items=[
                {
                    "equipment_id": item.equipment.id,
                    "score": item.score,
                    "reasons": item.reasons,
                }
                for item in items
            ],
            explanation=explanation,
        )
        db.add(record)
        await db.flush()
        return record

    def _to_equipment_brief(self, equipment: Equipment) -> EquipmentBrief:
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

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def _style_to_chinese(style: PlayingStyle) -> str:
        """打法风格转中文"""
        mapping = {
            PlayingStyle.OFFENSIVE: "进攻型",
            PlayingStyle.DEFENSIVE: "防守型",
            PlayingStyle.ALL_ROUND: "全面型",
            PlayingStyle.CHOPPER: "削球型",
        }
        return mapping.get(style, str(style.value))

    @staticmethod
    def _level_to_chinese(level: SkillLevel) -> str:
        """技术水平转中文"""
        mapping = {
            SkillLevel.BEGINNER: "初学者",
            SkillLevel.INTERMEDIATE: "中级",
            SkillLevel.ADVANCED: "高级",
            SkillLevel.PROFESSIONAL: "专业",
        }
        return mapping.get(level, str(level.value))

    @staticmethod
    def _check_style_incompatibility(
        user_style: PlayingStyle, equipment_styles: List[str]
    ) -> bool:
        """检查打法是否完全不兼容"""
        # 进攻型与纯防守装备不兼容
        if user_style == PlayingStyle.OFFENSIVE:
            return "defensive" in equipment_styles and "offensive" not in equipment_styles
        # 防守型与纯进攻装备不兼容
        if user_style == PlayingStyle.DEFENSIVE:
            return "offensive" in equipment_styles and "defensive" not in equipment_styles
        return False

    @staticmethod
    def _calculate_level_difference(
        user_level: SkillLevel, equipment_levels: List[str]
    ) -> int:
        """计算技术水平差距"""
        level_order = ["beginner", "intermediate", "advanced", "professional"]
        user_idx = level_order.index(user_level.value)

        min_diff = 4
        for eq_level in equipment_levels:
            if eq_level in level_order:
                eq_idx = level_order.index(eq_level)
                diff = abs(user_idx - eq_idx)
                min_diff = min(min_diff, diff)

        return min_diff


# 单例模式
_recommendation_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """获取推荐引擎单例"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine
