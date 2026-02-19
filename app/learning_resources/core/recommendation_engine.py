"""
学习推荐引擎
基于用户档案、学习历史和知识图谱进行个性化推荐
"""

from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.learning_resources.models import (
    LearningResource, LearningPath, UserLearningProfile,
    UserProgress, UserPathEnrollment, ResourceStatus,
)
from app.learning_resources.schemas import (
    RecommendedResource, RecommendedPath,
    ResourceBrief, LearningPathBrief,
)


class LearningRecommendationEngine:
    """学习推荐引擎"""

    # 难度级别权重（用于推荐计算）
    DIFFICULTY_ORDER = {
        "beginner": 1,
        "intermediate": 2,
        "advanced": 3,
        "professional": 4,
    }

    # 资源类型偏好权重
    TYPE_WEIGHTS = {
        "video": 1.0,
        "article": 0.9,
        "tutorial": 0.95,
        "exercise": 0.85,
        "course": 1.0,
        "book": 0.8,
    }

    def __init__(self):
        pass

    async def get_resource_recommendations(
        self,
        db: AsyncSession,
        profile: UserLearningProfile,
        top_k: int = 5,
        exclude_completed: bool = True,
    ) -> Tuple[List[RecommendedResource], str]:
        """
        获取资源推荐

        推荐策略:
        1. 基于用户当前水平推荐适合难度的资源
        2. 基于用户兴趣和目标匹配相关主题
        3. 基于学习历史推荐连续性内容
        4. 热门资源加权
        """
        # 获取已完成的资源 ID
        completed_ids = set()
        if exclude_completed:
            result = await db.execute(
                select(UserProgress.resource_id).where(
                    and_(
                        UserProgress.user_id == profile.user_id,
                        UserProgress.is_completed,
                    )
                )
            )
            completed_ids = {row[0] for row in result.all()}

        # 获取候选资源
        conditions = [
            LearningResource.status == ResourceStatus.PUBLISHED,
        ]

        # 排除已完成
        if completed_ids:
            conditions.append(LearningResource.id.notin_(completed_ids))

        result = await db.execute(
            select(LearningResource).where(and_(*conditions))
        )
        candidates = list(result.scalars().all())

        if not candidates:
            return [], "暂无可推荐的资源"

        # 计算推荐分数
        scored_resources = []
        for resource in candidates:
            score, reasons = self._calculate_resource_score(resource, profile)
            scored_resources.append((resource, score, reasons))

        # 按分数排序
        scored_resources.sort(key=lambda x: x[1], reverse=True)

        # 取 top_k
        recommendations = []
        for resource, score, reasons in scored_resources[:top_k]:
            recommendations.append(RecommendedResource(
                resource=self._to_resource_brief(resource),
                score=min(1.0, score),
                reasons=reasons,
            ))

        explanation = self._generate_explanation(profile, recommendations)
        return recommendations, explanation

    async def get_path_recommendations(
        self,
        db: AsyncSession,
        profile: UserLearningProfile,
        top_k: int = 5,
    ) -> Tuple[List[RecommendedPath], str]:
        """获取学习路径推荐"""
        # 获取已报名的路径
        enrolled_result = await db.execute(
            select(UserPathEnrollment.path_id).where(
                UserPathEnrollment.profile_id == profile.id
            )
        )
        enrolled_ids = {row[0] for row in enrolled_result.all()}

        # 获取候选路径
        conditions = [LearningPath.is_published]
        if enrolled_ids:
            conditions.append(LearningPath.id.notin_(enrolled_ids))

        result = await db.execute(
            select(LearningPath).where(and_(*conditions))
        )
        candidates = list(result.scalars().all())

        if not candidates:
            return [], "暂无可推荐的学习路径"

        # 计算推荐分数
        scored_paths = []
        for path in candidates:
            score, reasons = self._calculate_path_score(path, profile)
            scored_paths.append((path, score, reasons))

        # 按分数排序
        scored_paths.sort(key=lambda x: x[1], reverse=True)

        # 取 top_k
        recommendations = []
        for path, score, reasons in scored_paths[:top_k]:
            recommendations.append(RecommendedPath(
                path=self._to_path_brief(path),
                score=min(1.0, score),
                reasons=reasons,
            ))

        explanation = f"根据您的水平({profile.current_level.value})和学习目标推荐以下路径"
        return recommendations, explanation

    async def get_next_step(
        self,
        db: AsyncSession,
        profile: UserLearningProfile,
    ) -> Tuple[Optional[LearningResource], str]:
        """
        获取下一步学习建议

        优先级:
        1. 进行中的资源（继续学习）
        2. 已报名路径的下一个资源
        3. 新的推荐资源
        """
        # 1. 检查进行中的资源
        in_progress = await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.resource))
            .where(
                and_(
                    UserProgress.user_id == profile.user_id,
                    not UserProgress.is_completed,
                    UserProgress.progress_percent > 0,
                )
            )
            .order_by(UserProgress.last_accessed_at.desc())
            .limit(1)
        )
        progress = in_progress.scalar_one_or_none()
        if progress and progress.resource:
            return progress.resource, f"继续学习: {progress.resource.title} (进度 {progress.progress_percent:.0f}%)"

        # 2. 检查已报名路径的下一个资源
        enrollment = await db.execute(
            select(UserPathEnrollment)
            .options(selectinload(UserPathEnrollment.path))
            .where(
                and_(
                    UserPathEnrollment.profile_id == profile.id,
                    UserPathEnrollment.status.in_(["not_started", "in_progress"]),
                )
            )
            .order_by(UserPathEnrollment.updated_at.desc())
            .limit(1)
        )
        active_enrollment = enrollment.scalar_one_or_none()

        if active_enrollment and active_enrollment.path:
            # 获取路径下一个资源
            from app.learning_resources.models import LearningPathItem
            next_item = await db.execute(
                select(LearningPathItem)
                .options(selectinload(LearningPathItem.resource))
                .where(
                    and_(
                        LearningPathItem.path_id == active_enrollment.path_id,
                        LearningPathItem.order_index >= active_enrollment.current_item_index,
                    )
                )
                .order_by(LearningPathItem.order_index)
                .limit(1)
            )
            item = next_item.scalar_one_or_none()
            if item and item.resource:
                return item.resource, f"路径《{active_enrollment.path.title}》的下一步: {item.resource.title}"

        # 3. 推荐新资源
        recommendations, _ = await self.get_resource_recommendations(db, profile, top_k=1)
        if recommendations:
            # 获取完整资源对象
            resource = await db.execute(
                select(LearningResource).where(LearningResource.id == recommendations[0].resource.id)
            )
            res = resource.scalar_one_or_none()
            if res:
                return res, f"推荐学习: {res.title}"

        return None, "暂无学习建议"

    def _calculate_resource_score(
        self,
        resource: LearningResource,
        profile: UserLearningProfile,
    ) -> Tuple[float, List[str]]:
        """
        计算资源匹配分数

        Returns:
            (分数 0-1, 理由列表)
        """
        score = 0.0
        reasons = []

        # 1. 难度匹配 (0.3)
        user_level = self.DIFFICULTY_ORDER.get(profile.current_level.value, 1)
        resource_level = self.DIFFICULTY_ORDER.get(
            resource.difficulty_level.value if resource.difficulty_level else "beginner", 1
        )

        level_diff = abs(user_level - resource_level)
        if level_diff == 0:
            score += 0.3
            reasons.append("难度完全匹配")
        elif level_diff == 1:
            score += 0.2
            if resource_level > user_level:
                reasons.append("适度挑战")
            else:
                reasons.append("巩固基础")
        else:
            score += 0.1

        # 2. 兴趣匹配 (0.25)
        if profile.interests and resource.tags:
            common_tags = set(profile.interests) & set(resource.tags)
            if common_tags:
                interest_score = min(0.25, len(common_tags) * 0.1)
                score += interest_score
                reasons.append(f"符合兴趣: {', '.join(list(common_tags)[:2])}")

        # 3. 学习目标匹配 (0.25)
        if profile.learning_goals:
            goal_match = False
            for goal in profile.learning_goals:
                if resource.title and goal.lower() in resource.title.lower():
                    goal_match = True
                    break
                if resource.description and goal.lower() in resource.description.lower():
                    goal_match = True
                    break
                if resource.tags and any(goal.lower() in tag.lower() for tag in resource.tags):
                    goal_match = True
                    break
            if goal_match:
                score += 0.25
                reasons.append("契合学习目标")

        # 4. 资源类型偏好 (0.1)
        if profile.preferred_resource_types:
            res_type = resource.resource_type.value if resource.resource_type else "video"
            if res_type in profile.preferred_resource_types:
                score += 0.1
                reasons.append("偏好的资源类型")
        else:
            # 默认给视频和教程更高权重
            type_weight = self.TYPE_WEIGHTS.get(
                resource.resource_type.value if resource.resource_type else "video", 0.8
            )
            score += 0.1 * type_weight

        # 5. 热门度加权 (0.1)
        popularity = min(1.0, (resource.view_count or 0) / 1000 + (resource.like_count or 0) / 100)
        score += 0.1 * popularity
        if popularity > 0.5:
            reasons.append("热门资源")

        # 6. 精选推荐 (额外加分)
        if resource.is_featured:
            score += 0.05
            reasons.append("精选推荐")

        return score, reasons

    def _calculate_path_score(
        self,
        path: LearningPath,
        profile: UserLearningProfile,
    ) -> Tuple[float, List[str]]:
        """计算路径匹配分数"""
        score = 0.0
        reasons = []

        # 1. 难度匹配 (0.4)
        user_level = self.DIFFICULTY_ORDER.get(profile.current_level.value, 1)
        path_level = self.DIFFICULTY_ORDER.get(
            path.difficulty_level.value if path.difficulty_level else "beginner", 1
        )

        level_diff = abs(user_level - path_level)
        if level_diff == 0:
            score += 0.4
            reasons.append("难度完全匹配")
        elif level_diff == 1:
            score += 0.25
            reasons.append("难度适中")
        else:
            score += 0.1

        # 2. 分类匹配 (0.3)
        if profile.interests and path.category:
            path_cat = path.category.value if hasattr(path.category, 'value') else str(path.category)
            if any(interest.lower() in path_cat.lower() for interest in profile.interests):
                score += 0.3
                reasons.append("符合兴趣方向")

        # 3. 标签匹配 (0.2)
        if profile.learning_goals and path.tags:
            common = set()
            for goal in profile.learning_goals:
                for tag in path.tags:
                    if goal.lower() in tag.lower() or tag.lower() in goal.lower():
                        common.add(tag)
            if common:
                score += min(0.2, len(common) * 0.1)
                reasons.append("契合学习目标")

        # 4. 精选推荐 (0.1)
        if path.is_featured:
            score += 0.1
            reasons.append("精选路径")

        return score, reasons

    def _generate_explanation(
        self,
        profile: UserLearningProfile,
        recommendations: List[RecommendedResource],
    ) -> str:
        """生成推荐说明"""
        parts = [f"根据您的水平({profile.current_level.value})"]

        if profile.learning_goals:
            parts.append(f"和学习目标({', '.join(profile.learning_goals[:2])})")

        parts.append("为您推荐以下资源")

        return "".join(parts)

    def _to_resource_brief(self, resource: LearningResource) -> ResourceBrief:
        """转换为 ResourceBrief"""
        return ResourceBrief(
            id=resource.id,
            title=resource.title,
            resource_type=resource.resource_type.value if resource.resource_type else "video",
            category=resource.category.value if resource.category else "technique",
            difficulty_level=resource.difficulty_level.value if resource.difficulty_level else "beginner",
            duration_minutes=resource.duration_minutes,
            author=resource.author,
            source=resource.source,
            tags=resource.tags,
            view_count=resource.view_count or 0,
            like_count=resource.like_count or 0,
            is_featured=resource.is_featured or False,
            status=resource.status.value if resource.status else "published",
            created_at=resource.created_at or datetime.utcnow(),
        )

    def _to_path_brief(self, path: LearningPath) -> LearningPathBrief:
        """转换为 LearningPathBrief"""
        return LearningPathBrief(
            id=path.id,
            title=path.title,
            difficulty_level=path.difficulty_level.value if path.difficulty_level else "beginner",
            category=path.category.value if path.category else None,
            estimated_hours=path.estimated_hours,
            tags=path.tags,
            is_published=path.is_published or True,
            is_featured=path.is_featured or False,
            item_count=len(path.items) if path.items else 0,
            created_at=path.created_at or datetime.utcnow(),
        )


# 服务单例
_recommendation_engine: Optional[LearningRecommendationEngine] = None


def get_recommendation_engine() -> LearningRecommendationEngine:
    """获取推荐引擎单例"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = LearningRecommendationEngine()
    return _recommendation_engine
