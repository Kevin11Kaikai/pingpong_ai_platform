"""
训练目标服务

提供训练目标的 CRUD 操作和进度管理。
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.training_analysis.models import (
    TrainingGoal, GoalStatus, GoalType, TrainingSession, TechniqueMetrics
)
from app.training_analysis.schemas import GoalCreate, GoalUpdate, MilestoneCreate


class GoalService:
    """训练目标服务"""

    async def create_goal(
        self, db: AsyncSession, data: GoalCreate
    ) -> TrainingGoal:
        """
        创建训练目标

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的目标对象
        """
        goal = TrainingGoal(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            title=data.title,
            description=data.description,
            goal_type=GoalType(data.goal_type),
            technique_category=data.technique_category,
            target_value=data.target_value,
            baseline_value=data.baseline_value,
            current_value=data.baseline_value or 0,
            unit=data.unit,
            start_date=data.start_date,
            target_date=data.target_date,
            status=GoalStatus.ACTIVE,
            progress_percent=0,
            milestones=[],
        )

        db.add(goal)
        await db.flush()
        logger.info(f"训练目标已创建: {goal.id}, 用户: {data.user_id}")
        return goal

    async def get_goal(
        self, db: AsyncSession, goal_id: str
    ) -> Optional[TrainingGoal]:
        """
        获取目标详情

        Args:
            db: 数据库会话
            goal_id: 目标ID

        Returns:
            目标对象或 None
        """
        result = await db.execute(
            select(TrainingGoal).where(TrainingGoal.id == goal_id)
        )
        return result.scalar_one_or_none()

    async def list_user_goals(
        self,
        db: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        goal_type: Optional[str] = None
    ) -> List[TrainingGoal]:
        """
        列出用户目标

        Args:
            db: 数据库会话
            user_id: 用户ID
            status: 状态筛选
            goal_type: 类型筛选

        Returns:
            目标列表
        """
        conditions = [TrainingGoal.user_id == user_id]

        if status:
            conditions.append(TrainingGoal.status == GoalStatus(status))
        if goal_type:
            conditions.append(TrainingGoal.goal_type == GoalType(goal_type))

        result = await db.execute(
            select(TrainingGoal)
            .where(and_(*conditions))
            .order_by(TrainingGoal.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_goal(
        self, db: AsyncSession, goal_id: str, data: GoalUpdate
    ) -> Optional[TrainingGoal]:
        """
        更新目标

        Args:
            db: 数据库会话
            goal_id: 目标ID
            data: 更新数据

        Returns:
            更新后的目标或 None
        """
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 处理状态枚举
        if "status" in update_data and update_data["status"]:
            update_data["status"] = GoalStatus(update_data["status"])

        for field, value in update_data.items():
            setattr(goal, field, value)

        # 重新计算进度
        if goal.target_value and goal.baseline_value is not None:
            range_value = goal.target_value - goal.baseline_value
            if range_value != 0:
                progress = (goal.current_value - goal.baseline_value) / range_value * 100
                goal.progress_percent = min(100, max(0, progress))

        # 检查是否达成
        if goal.current_value >= goal.target_value and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.ACHIEVED
            goal.achieved_date = datetime.utcnow()
            logger.info(f"目标已达成: {goal_id}")

        goal.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"训练目标已更新: {goal_id}")
        return goal

    async def delete_goal(self, db: AsyncSession, goal_id: str) -> bool:
        """
        删除目标

        Args:
            db: 数据库会话
            goal_id: 目标ID

        Returns:
            是否删除成功
        """
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return False

        await db.delete(goal)
        await db.flush()
        logger.info(f"训练目标已删除: {goal_id}")
        return True

    async def update_goal_progress(
        self, db: AsyncSession, goal_id: str
    ) -> Optional[TrainingGoal]:
        """
        根据最新训练数据更新目标进度

        Args:
            db: 数据库会话
            goal_id: 目标ID

        Returns:
            更新后的目标或 None
        """
        goal = await self.get_goal(db, goal_id)
        if not goal or goal.status != GoalStatus.ACTIVE:
            return goal

        # 根据目标类型计算当前值
        new_value = await self._calculate_current_value(db, goal)

        if new_value is not None:
            goal.current_value = new_value

            # 计算进度百分比
            if goal.target_value and goal.baseline_value is not None:
                range_value = goal.target_value - goal.baseline_value
                if range_value != 0:
                    progress = (goal.current_value - goal.baseline_value) / range_value * 100
                    goal.progress_percent = min(100, max(0, progress))

            # 检查是否达成
            if goal.current_value >= goal.target_value:
                goal.status = GoalStatus.ACHIEVED
                goal.achieved_date = datetime.utcnow()
                logger.info(f"目标已达成: {goal_id}")

            goal.updated_at = datetime.utcnow()
            await db.flush()

        return goal

    async def _calculate_current_value(
        self, db: AsyncSession, goal: TrainingGoal
    ) -> Optional[float]:
        """
        根据目标类型计算当前值

        Args:
            db: 数据库会话
            goal: 目标对象

        Returns:
            当前值或 None
        """
        user_id = goal.user_id
        start_date = goal.start_date

        if goal.goal_type == GoalType.SESSION_COUNT:
            # 统计训练次数
            result = await db.execute(
                select(func.count(TrainingSession.id)).where(
                    and_(
                        TrainingSession.user_id == user_id,
                        TrainingSession.started_at >= start_date
                    )
                )
            )
            return float(result.scalar() or 0)

        elif goal.goal_type == GoalType.TOTAL_DURATION:
            # 统计总时长
            result = await db.execute(
                select(func.sum(TrainingSession.duration_minutes)).where(
                    and_(
                        TrainingSession.user_id == user_id,
                        TrainingSession.started_at >= start_date
                    )
                )
            )
            return float(result.scalar() or 0)

        elif goal.goal_type == GoalType.SPEED:
            # 获取最新平均速度
            if goal.technique_category:
                result = await db.execute(
                    select(TechniqueMetrics.avg_speed_kmh)
                    .join(TrainingSession)
                    .where(
                        and_(
                            TrainingSession.user_id == user_id,
                            TechniqueMetrics.technique_category == goal.technique_category,
                            TrainingSession.started_at >= start_date
                        )
                    )
                    .order_by(TrainingSession.started_at.desc())
                    .limit(1)
                )
                speed = result.scalar()
                return float(speed) if speed else None
            else:
                result = await db.execute(
                    select(TrainingSession.avg_ball_speed_kmh)
                    .where(
                        and_(
                            TrainingSession.user_id == user_id,
                            TrainingSession.started_at >= start_date
                        )
                    )
                    .order_by(TrainingSession.started_at.desc())
                    .limit(1)
                )
                speed = result.scalar()
                return float(speed) if speed else None

        elif goal.goal_type == GoalType.ACCURACY:
            # 获取最新准确率
            if goal.technique_category:
                result = await db.execute(
                    select(TechniqueMetrics.accuracy_score)
                    .join(TrainingSession)
                    .where(
                        and_(
                            TrainingSession.user_id == user_id,
                            TechniqueMetrics.technique_category == goal.technique_category,
                            TrainingSession.started_at >= start_date
                        )
                    )
                    .order_by(TrainingSession.started_at.desc())
                    .limit(1)
                )
                score = result.scalar()
                return float(score) if score else None

        elif goal.goal_type == GoalType.CONSISTENCY:
            # 获取最新稳定性
            if goal.technique_category:
                result = await db.execute(
                    select(TechniqueMetrics.consistency_score)
                    .join(TrainingSession)
                    .where(
                        and_(
                            TrainingSession.user_id == user_id,
                            TechniqueMetrics.technique_category == goal.technique_category,
                            TrainingSession.started_at >= start_date
                        )
                    )
                    .order_by(TrainingSession.started_at.desc())
                    .limit(1)
                )
                score = result.scalar()
                return float(score) if score else None

        return None

    async def check_goal_achievements(
        self, db: AsyncSession, user_id: str
    ) -> List[TrainingGoal]:
        """
        检查用户是否达成任何目标

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            新达成的目标列表
        """
        # 获取活跃目标
        active_goals = await self.list_user_goals(db, user_id, status="active")

        achieved = []
        for goal in active_goals:
            updated = await self.update_goal_progress(db, goal.id)
            if updated and updated.status == GoalStatus.ACHIEVED:
                achieved.append(updated)

        if achieved:
            logger.info(f"用户 {user_id} 达成 {len(achieved)} 个目标")

        return achieved

    async def add_milestone(
        self,
        db: AsyncSession,
        goal_id: str,
        data: MilestoneCreate
    ) -> Optional[TrainingGoal]:
        """
        添加里程碑

        Args:
            db: 数据库会话
            goal_id: 目标ID
            data: 里程碑数据

        Returns:
            更新后的目标或 None
        """
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return None

        milestone = {
            "value": data.value,
            "achieved_at": datetime.utcnow().isoformat(),
            "note": data.note,
        }

        milestones = goal.milestones or []
        milestones.append(milestone)
        goal.milestones = milestones
        goal.updated_at = datetime.utcnow()

        await db.flush()
        logger.info(f"目标 {goal_id} 添加里程碑: {data.value}")
        return goal

    async def expire_overdue_goals(self, db: AsyncSession) -> int:
        """
        过期超时目标

        Args:
            db: 数据库会话

        Returns:
            过期的目标数量
        """
        now = datetime.utcnow()

        result = await db.execute(
            select(TrainingGoal).where(
                and_(
                    TrainingGoal.status == GoalStatus.ACTIVE,
                    TrainingGoal.target_date < now
                )
            )
        )
        overdue_goals = list(result.scalars().all())

        for goal in overdue_goals:
            goal.status = GoalStatus.EXPIRED
            goal.updated_at = now

        await db.flush()

        if overdue_goals:
            logger.info(f"已过期 {len(overdue_goals)} 个目标")

        return len(overdue_goals)

    async def get_active_goals_count(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """
        获取用户活跃目标数量

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            活跃目标数量
        """
        result = await db.execute(
            select(func.count(TrainingGoal.id)).where(
                and_(
                    TrainingGoal.user_id == user_id,
                    TrainingGoal.status == GoalStatus.ACTIVE
                )
            )
        )
        return result.scalar() or 0

    async def get_achieved_goals_count(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """
        获取用户已达成目标数量

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            已达成目标数量
        """
        result = await db.execute(
            select(func.count(TrainingGoal.id)).where(
                and_(
                    TrainingGoal.user_id == user_id,
                    TrainingGoal.status == GoalStatus.ACHIEVED
                )
            )
        )
        return result.scalar() or 0


# 服务单例
_goal_service: Optional[GoalService] = None


def get_goal_service() -> GoalService:
    """获取目标服务单例"""
    global _goal_service
    if _goal_service is None:
        _goal_service = GoalService()
    return _goal_service
