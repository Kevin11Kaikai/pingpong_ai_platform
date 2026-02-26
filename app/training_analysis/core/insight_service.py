"""
AI 洞察服务

提供基于 LLM 的训练洞察和建议生成。
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.training_analysis.models import (
    AIInsight, InsightType, TrainingSession, TrainingGoal,
    GoalStatus
)
from app.training_analysis.schemas import InsightFeedback, GenerateInsightsRequest
from config.settings import get_settings


class InsightService:
    """AI 洞察服务"""

    def __init__(self):
        self._llm_client = None
        self.settings = get_settings()

    @property
    def llm_client(self):
        """延迟加载 LLM 客户端"""
        if self._llm_client is None:
            try:
                from app.llm.core.llm_client import get_llm_client
                self._llm_client = get_llm_client()
            except ImportError:
                logger.warning("LLM 客户端未初始化")
        return self._llm_client

    async def generate_session_insights(
        self, db: AsyncSession, session_id: str
    ) -> List[AIInsight]:
        """
        为单次训练生成洞察

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            生成的洞察列表
        """
        # 获取会话数据
        from app.training_analysis.core.session_service import get_session_service
        session_service = get_session_service()
        session = await session_service.get_session(db, session_id)

        if not session:
            return []

        # 获取用户历史数据用于对比
        recent_sessions = await session_service.get_recent_sessions(
            db, session.user_id, limit=10
        )

        # 构建提示
        prompt = self._build_session_prompt(session, recent_sessions)

        # 调用 LLM
        insights_data = await self._call_llm(prompt)

        # 创建洞察记录
        insights = []
        for data in insights_data:
            insight = AIInsight(
                id=str(uuid.uuid4()),
                user_id=session.user_id,
                insight_type=InsightType(data.get("type", "recommendation")),
                session_id=session_id,
                title=data.get("title", "训练洞察"),
                content=data.get("content", ""),
                confidence_score=data.get("confidence", 0.8),
                priority=data.get("priority", 0),
                supporting_data=data.get("supporting_data"),
                action_items=data.get("action_items"),
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            db.add(insight)
            insights.append(insight)

        await db.flush()
        logger.info(f"为会话 {session_id} 生成 {len(insights)} 条洞察")
        return insights

    async def generate_weekly_insights(
        self, db: AsyncSession, user_id: str
    ) -> List[AIInsight]:
        """
        生成周度洞察

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            生成的洞察列表
        """
        # 获取本周数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        from app.training_analysis.core.analysis_service import get_analysis_service
        analysis_service = get_analysis_service()

        # 获取统计数据
        stats = await analysis_service.get_user_stats(db, user_id)

        # 获取趋势数据
        speed_trend = await analysis_service.get_trend_analysis(
            db, user_id, "speed", start_date, end_date, "daily"
        )

        # 构建提示
        prompt = self._build_weekly_prompt(stats, speed_trend)

        # 调用 LLM
        insights_data = await self._call_llm(prompt)

        # 创建洞察记录
        insights = []
        for data in insights_data:
            insight = AIInsight(
                id=str(uuid.uuid4()),
                user_id=user_id,
                insight_type=InsightType(data.get("type", "trend")),
                title=data.get("title", "周度总结"),
                content=data.get("content", ""),
                confidence_score=data.get("confidence", 0.8),
                priority=data.get("priority", 1),
                supporting_data=data.get("supporting_data"),
                action_items=data.get("action_items"),
                expires_at=datetime.utcnow() + timedelta(days=14),
            )
            db.add(insight)
            insights.append(insight)

        await db.flush()
        logger.info(f"为用户 {user_id} 生成 {len(insights)} 条周度洞察")
        return insights

    async def generate_goal_insights(
        self, db: AsyncSession, goal_id: str
    ) -> List[AIInsight]:
        """
        为目标进度生成洞察

        Args:
            db: 数据库会话
            goal_id: 目标ID

        Returns:
            生成的洞察列表
        """
        from app.training_analysis.core.goal_service import get_goal_service
        goal_service = get_goal_service()
        goal = await goal_service.get_goal(db, goal_id)

        if not goal:
            return []

        # 构建提示
        prompt = self._build_goal_prompt(goal)

        # 调用 LLM
        insights_data = await self._call_llm(prompt)

        # 创建洞察记录
        insights = []
        for data in insights_data:
            insight_type = InsightType.ACHIEVEMENT if goal.status == GoalStatus.ACHIEVED else InsightType.RECOMMENDATION
            insight = AIInsight(
                id=str(uuid.uuid4()),
                user_id=goal.user_id,
                insight_type=insight_type,
                goal_id=goal_id,
                title=data.get("title", "目标进度洞察"),
                content=data.get("content", ""),
                confidence_score=data.get("confidence", 0.8),
                priority=data.get("priority", 2),
                supporting_data=data.get("supporting_data"),
                action_items=data.get("action_items"),
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            db.add(insight)
            insights.append(insight)

        await db.flush()
        logger.info(f"为目标 {goal_id} 生成 {len(insights)} 条洞察")
        return insights

    async def generate_insights(
        self, db: AsyncSession, request: GenerateInsightsRequest
    ) -> List[AIInsight]:
        """
        根据请求类型生成洞察

        Args:
            db: 数据库会话
            request: 生成请求

        Returns:
            生成的洞察列表
        """
        if request.context_type == "session" and request.session_id:
            return await self.generate_session_insights(db, request.session_id)
        elif request.context_type == "goal" and request.goal_id:
            return await self.generate_goal_insights(db, request.goal_id)
        elif request.context_type == "weekly":
            return await self.generate_weekly_insights(db, request.user_id)
        else:
            # 通用洞察
            return await self.generate_weekly_insights(db, request.user_id)

    async def get_user_insights(
        self,
        db: AsyncSession,
        user_id: str,
        insight_type: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[AIInsight]:
        """
        获取用户洞察列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            insight_type: 洞察类型筛选
            unread_only: 仅未读
            limit: 返回数量

        Returns:
            洞察列表
        """
        conditions = [
            AIInsight.user_id == user_id,
            AIInsight.is_dismissed.is_(False),
        ]

        if insight_type:
            conditions.append(AIInsight.insight_type == InsightType(insight_type))
        if unread_only:
            conditions.append(AIInsight.is_read.is_(False))

        # 排除过期的洞察
        now = datetime.utcnow()
        conditions.append(
            (AIInsight.expires_at.is_(None)) | (AIInsight.expires_at > now)
        )

        result = await db.execute(
            select(AIInsight)
            .where(and_(*conditions))
            .order_by(AIInsight.priority.desc(), AIInsight.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_insight(
        self, db: AsyncSession, insight_id: str
    ) -> Optional[AIInsight]:
        """获取洞察详情"""
        result = await db.execute(
            select(AIInsight).where(AIInsight.id == insight_id)
        )
        return result.scalar_one_or_none()

    async def get_unread_count(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """获取未读洞察数量"""
        now = datetime.utcnow()
        result = await db.execute(
            select(func.count(AIInsight.id)).where(
                and_(
                    AIInsight.user_id == user_id,
                    AIInsight.is_read.is_(False),
                    AIInsight.is_dismissed.is_(False),
                    (AIInsight.expires_at.is_(None)) | (AIInsight.expires_at > now)
                )
            )
        )
        return result.scalar() or 0

    async def mark_as_read(
        self, db: AsyncSession, insight_id: str
    ) -> bool:
        """标记洞察为已读"""
        insight = await self.get_insight(db, insight_id)
        if not insight:
            return False

        insight.is_read = True
        await db.flush()
        return True

    async def dismiss_insight(
        self, db: AsyncSession, insight_id: str
    ) -> bool:
        """忽略洞察"""
        insight = await self.get_insight(db, insight_id)
        if not insight:
            return False

        insight.is_dismissed = True
        await db.flush()
        return True

    async def submit_feedback(
        self, db: AsyncSession, insight_id: str, feedback: InsightFeedback
    ) -> Optional[AIInsight]:
        """
        提交洞察反馈

        Args:
            db: 数据库会话
            insight_id: 洞察ID
            feedback: 反馈数据

        Returns:
            更新后的洞察或 None
        """
        insight = await self.get_insight(db, insight_id)
        if not insight:
            return None

        insight.is_helpful = feedback.is_helpful
        insight.user_feedback = feedback.feedback
        insight.is_read = True

        await db.flush()
        logger.info(f"洞察 {insight_id} 收到反馈: helpful={feedback.is_helpful}")
        return insight

    def _build_session_prompt(
        self,
        session: TrainingSession,
        recent_sessions: List[TrainingSession]
    ) -> str:
        """构建会话洞察提示"""
        # 计算历史平均值用于对比
        avg_speed = None
        if recent_sessions:
            speeds = [s.avg_ball_speed_kmh for s in recent_sessions if s.avg_ball_speed_kmh]
            avg_speed = sum(speeds) / len(speeds) if speeds else None

        prompt = f"""分析以下乒乓球训练数据并提供洞察建议。

本次训练:
- 类型: {session.session_type.value}
- 时长: {session.duration_minutes or '未知'} 分钟
- 总击球数: {session.total_strokes}
- 平均球速: {session.avg_ball_speed_kmh or '未知'} km/h
- 最高球速: {session.max_ball_speed_kmh or '未知'} km/h
- 准确率: {session.accuracy_score or '未知'}%
- 稳定性: {session.consistency_score or '未知'}%
- 练习技术: {', '.join(session.practiced_techniques or [])}
- 满意度: {session.satisfaction_rating or '未评'}/5
- 疲劳度: {session.fatigue_level or '未评'}/5

历史数据对比:
- 近期平均球速: {avg_speed or '无数据'} km/h
- 最近训练次数: {len(recent_sessions)}

请提供 1-3 条洞察，每条包含:
1. 类型 (improvement/warning/recommendation)
2. 标题（简短）
3. 内容（详细分析）
4. 具体建议（可操作）

以 JSON 数组格式返回，例如:
[{{"type": "improvement", "title": "球速提升", "content": "...", "action_items": ["建议1", "建议2"]}}]
"""
        return prompt

    def _build_weekly_prompt(
        self, stats: Dict[str, Any], trend: Any
    ) -> str:
        """构建周度洞察提示"""
        prompt = f"""分析以下乒乓球周度训练数据并提供总结建议。

本周统计:
- 训练次数: {stats.get('total_sessions', 0)}
- 总时长: {stats.get('total_duration_minutes', 0)} 分钟
- 总击球数: {stats.get('total_strokes', 0)}
- 平均每次训练时长: {stats.get('avg_session_duration', 0)} 分钟
- 连续训练天数: {stats.get('current_streak_days', 0)}
- 最常练习技术: {', '.join(stats.get('favorite_techniques', []))}

趋势分析:
- 球速趋势: {trend.overall_trend if trend else '无数据'}
- 变化幅度: {trend.change_percent if trend else 0}%

请提供 2-3 条周度洞察，包含:
1. 本周亮点
2. 需要改进的地方
3. 下周训练建议

以 JSON 数组格式返回。
"""
        return prompt

    def _build_goal_prompt(self, goal: TrainingGoal) -> str:
        """构建目标洞察提示"""
        days_left = (goal.target_date - datetime.utcnow()).days if goal.target_date else 0

        prompt = f"""分析以下乒乓球训练目标进度并提供建议。

目标信息:
- 标题: {goal.title}
- 类型: {goal.goal_type.value}
- 关联技术: {goal.technique_category or '全部'}
- 目标值: {goal.target_value} {goal.unit or ''}
- 当前值: {goal.current_value} {goal.unit or ''}
- 进度: {goal.progress_percent:.1f}%
- 状态: {goal.status.value}
- 剩余天数: {days_left}

请提供 1-2 条洞察:
1. 进度评估
2. 达成建议（如何调整训练）

以 JSON 数组格式返回。
"""
        return prompt

    async def _call_llm(self, prompt: str) -> List[Dict[str, Any]]:
        """
        调用 LLM 生成洞察

        Args:
            prompt: 提示文本

        Returns:
            洞察数据列表
        """
        if not self.llm_client:
            # 没有 LLM 客户端时返回默认洞察
            return self._generate_default_insights()

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.settings.training_insight_model,
                temperature=self.settings.training_insight_temperature,
                max_tokens=self.settings.training_insight_max_tokens,
            )

            # 解析 JSON 响应
            content = response.get("content", "[]")

            # 尝试提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except json.JSONDecodeError as e:
            logger.warning(f"解析 LLM 响应失败: {e}")
            return self._generate_default_insights()
        except Exception as e:
            logger.error(f"调用 LLM 失败: {e}")
            return self._generate_default_insights()

    def _generate_default_insights(self) -> List[Dict[str, Any]]:
        """生成默认洞察（LLM 不可用时）"""
        return [
            {
                "type": "recommendation",
                "title": "保持训练频率",
                "content": "建议每周至少训练 3-4 次，保持技术的连续性和肌肉记忆。",
                "confidence": 0.6,
                "priority": 0,
                "action_items": ["制定周训练计划", "设置训练提醒"]
            }
        ]


# 服务单例
_insight_service: Optional[InsightService] = None


def get_insight_service() -> InsightService:
    """获取洞察服务单例"""
    global _insight_service
    if _insight_service is None:
        _insight_service = InsightService()
    return _insight_service
