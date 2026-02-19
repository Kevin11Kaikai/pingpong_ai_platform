"""
统计分析服务

提供训练数据的统计分析、趋势计算和快照生成。
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.training_analysis.models import (
    TrainingSession, TechniqueMetrics, ProgressSnapshot
)
from app.training_analysis.schemas import (
    TrendDataPoint, TrendAnalysisResponse, ComparisonRequest,
    ComparisonResponse, PeriodSummary
)


class AnalysisService:
    """统计分析服务"""

    async def create_snapshot(
        self,
        db: AsyncSession,
        user_id: str,
        period_type: str,
        snapshot_date: datetime
    ) -> ProgressSnapshot:
        """
        创建进度快照

        Args:
            db: 数据库会话
            user_id: 用户ID
            period_type: 周期类型 (daily, weekly, monthly)
            snapshot_date: 快照日期

        Returns:
            创建的快照对象
        """
        # 计算周期范围
        start_date, end_date = self._get_period_range(snapshot_date, period_type)

        # 获取周期内的会话
        sessions = await self._get_sessions_in_range(db, user_id, start_date, end_date)

        # 计算统计数据
        session_count = len(sessions)
        total_duration = sum(s.duration_minutes or 0 for s in sessions)
        total_strokes = sum(s.total_strokes or 0 for s in sessions)

        # 计算平均指标
        speeds = [s.avg_ball_speed_kmh for s in sessions if s.avg_ball_speed_kmh]
        accuracies = [s.accuracy_score for s in sessions if s.accuracy_score]
        consistencies = [s.consistency_score for s in sessions if s.consistency_score]

        avg_speed = sum(speeds) / len(speeds) if speeds else None
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else None
        avg_consistency = sum(consistencies) / len(consistencies) if consistencies else None

        # 获取技术分类统计
        technique_breakdown = await self._get_technique_breakdown(
            db, user_id, start_date, end_date
        )

        # 获取上一周期数据用于对比
        prev_start, prev_end = self._get_previous_period(start_date, period_type)
        prev_snapshot = await self._get_snapshot(db, user_id, prev_start, period_type)

        # 计算变化
        speed_change = None
        accuracy_change = None
        consistency_change = None

        if prev_snapshot:
            if prev_snapshot.avg_ball_speed_kmh and avg_speed:
                speed_change = ((avg_speed - prev_snapshot.avg_ball_speed_kmh)
                               / prev_snapshot.avg_ball_speed_kmh * 100)
            if prev_snapshot.overall_accuracy and avg_accuracy:
                accuracy_change = ((avg_accuracy - prev_snapshot.overall_accuracy)
                                  / prev_snapshot.overall_accuracy * 100)
            if prev_snapshot.overall_consistency and avg_consistency:
                consistency_change = ((avg_consistency - prev_snapshot.overall_consistency)
                                     / prev_snapshot.overall_consistency * 100)

        # 生成亮点和问题
        highlights, concerns = self._generate_highlights_concerns(
            session_count, speed_change, accuracy_change, consistency_change
        )

        # 检查是否已存在
        existing = await self._get_snapshot(db, user_id, snapshot_date, period_type)
        if existing:
            # 更新现有快照
            snapshot = existing
        else:
            snapshot = ProgressSnapshot(
                id=str(uuid.uuid4()),
                user_id=user_id,
                snapshot_date=snapshot_date,
                period_type=period_type,
            )
            db.add(snapshot)

        snapshot.session_count = session_count
        snapshot.total_duration_minutes = total_duration
        snapshot.total_strokes = total_strokes
        snapshot.avg_ball_speed_kmh = avg_speed
        snapshot.overall_accuracy = avg_accuracy
        snapshot.overall_consistency = avg_consistency
        snapshot.technique_breakdown = technique_breakdown
        snapshot.speed_change_percent = speed_change
        snapshot.accuracy_change_percent = accuracy_change
        snapshot.consistency_change_percent = consistency_change
        snapshot.highlights = highlights
        snapshot.concerns = concerns

        await db.flush()
        logger.info(f"快照已创建: {user_id}, {period_type}, {snapshot_date}")
        return snapshot

    def _get_period_range(
        self, date: datetime, period_type: str
    ) -> Tuple[datetime, datetime]:
        """获取周期的开始和结束日期"""
        if period_type == "daily":
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period_type == "weekly":
            # 周一为起始
            weekday = date.weekday()
            start = (date - timedelta(days=weekday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(weeks=1)
        else:  # monthly
            start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end = start.replace(year=date.year + 1, month=1)
            else:
                end = start.replace(month=date.month + 1)
        return start, end

    def _get_previous_period(
        self, date: datetime, period_type: str
    ) -> Tuple[datetime, datetime]:
        """获取上一个周期的日期"""
        if period_type == "daily":
            prev = date - timedelta(days=1)
        elif period_type == "weekly":
            prev = date - timedelta(weeks=1)
        else:  # monthly
            if date.month == 1:
                prev = date.replace(year=date.year - 1, month=12)
            else:
                prev = date.replace(month=date.month - 1)
        return self._get_period_range(prev, period_type)

    async def _get_sessions_in_range(
        self,
        db: AsyncSession,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[TrainingSession]:
        """获取日期范围内的会话"""
        result = await db.execute(
            select(TrainingSession).where(
                and_(
                    TrainingSession.user_id == user_id,
                    TrainingSession.started_at >= start_date,
                    TrainingSession.started_at < end_date
                )
            )
        )
        return list(result.scalars().all())

    async def _get_snapshot(
        self,
        db: AsyncSession,
        user_id: str,
        date: datetime,
        period_type: str
    ) -> Optional[ProgressSnapshot]:
        """获取指定日期的快照"""
        start, _ = self._get_period_range(date, period_type)
        result = await db.execute(
            select(ProgressSnapshot).where(
                and_(
                    ProgressSnapshot.user_id == user_id,
                    ProgressSnapshot.snapshot_date == start,
                    ProgressSnapshot.period_type == period_type
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_technique_breakdown(
        self,
        db: AsyncSession,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取技术分类统计"""
        result = await db.execute(
            select(
                TechniqueMetrics.technique_category,
                func.sum(TechniqueMetrics.stroke_count).label("count"),
                func.avg(TechniqueMetrics.avg_speed_kmh).label("avg_speed"),
                func.avg(TechniqueMetrics.accuracy_score).label("accuracy"),
            )
            .join(TrainingSession)
            .where(
                and_(
                    TrainingSession.user_id == user_id,
                    TrainingSession.started_at >= start_date,
                    TrainingSession.started_at < end_date
                )
            )
            .group_by(TechniqueMetrics.technique_category)
        )

        breakdown = {}
        for row in result.all():
            breakdown[row.technique_category] = {
                "count": row.count or 0,
                "avg_speed": round(row.avg_speed, 2) if row.avg_speed else None,
                "accuracy": round(row.accuracy, 2) if row.accuracy else None,
            }
        return breakdown

    def _generate_highlights_concerns(
        self,
        session_count: int,
        speed_change: Optional[float],
        accuracy_change: Optional[float],
        consistency_change: Optional[float]
    ) -> Tuple[List[str], List[str]]:
        """生成亮点和问题列表"""
        highlights = []
        concerns = []

        if session_count >= 5:
            highlights.append(f"训练次数: {session_count} 次")
        elif session_count < 2:
            concerns.append("训练频率较低")

        if speed_change is not None:
            if speed_change > 5:
                highlights.append(f"球速提升 {speed_change:.1f}%")
            elif speed_change < -5:
                concerns.append(f"球速下降 {abs(speed_change):.1f}%")

        if accuracy_change is not None:
            if accuracy_change > 5:
                highlights.append(f"准确率提升 {accuracy_change:.1f}%")
            elif accuracy_change < -5:
                concerns.append(f"准确率下降 {abs(accuracy_change):.1f}%")

        if consistency_change is not None:
            if consistency_change > 5:
                highlights.append(f"稳定性提升 {consistency_change:.1f}%")
            elif consistency_change < -5:
                concerns.append(f"稳定性下降 {abs(consistency_change):.1f}%")

        return highlights, concerns

    async def get_trend_analysis(
        self,
        db: AsyncSession,
        user_id: str,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "daily"
    ) -> TrendAnalysisResponse:
        """
        获取趋势分析

        Args:
            db: 数据库会话
            user_id: 用户ID
            metric_name: 指标名称 (speed, accuracy, consistency)
            start_date: 开始日期
            end_date: 结束日期
            group_by: 分组方式

        Returns:
            趋势分析响应
        """
        # 获取会话数据
        sessions = await self._get_sessions_in_range(db, user_id, start_date, end_date)

        # 按日期分组
        grouped_data: Dict[str, List[TrainingSession]] = {}
        for session in sessions:
            if group_by == "daily":
                key = session.started_at.strftime("%Y-%m-%d")
            elif group_by == "weekly":
                # 周一为起始
                week_start = session.started_at - timedelta(days=session.started_at.weekday())
                key = week_start.strftime("%Y-%m-%d")
            else:  # monthly
                key = session.started_at.strftime("%Y-%m")

            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(session)

        # 提取指标值
        data_points = []
        values = []

        for date_str, group_sessions in sorted(grouped_data.items()):
            if metric_name == "speed":
                metric_values = [s.avg_ball_speed_kmh for s in group_sessions if s.avg_ball_speed_kmh]
            elif metric_name == "accuracy":
                metric_values = [s.accuracy_score for s in group_sessions if s.accuracy_score]
            elif metric_name == "consistency":
                metric_values = [s.consistency_score for s in group_sessions if s.consistency_score]
            else:
                metric_values = []

            if metric_values:
                avg_value = sum(metric_values) / len(metric_values)
                values.append(avg_value)

                # 解析日期
                if group_by == "monthly":
                    date = datetime.strptime(date_str + "-01", "%Y-%m-%d")
                else:
                    date = datetime.strptime(date_str, "%Y-%m-%d")

                data_points.append(TrendDataPoint(
                    date=date,
                    value=round(avg_value, 2),
                    session_count=len(group_sessions)
                ))

        # 计算趋势
        if len(values) >= 2:
            first_half = sum(values[:len(values)//2]) / (len(values)//2)
            second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            change = (second_half - first_half) / first_half * 100 if first_half else 0

            if change > 5:
                trend = "improving"
            elif change < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
            change = 0

        return TrendAnalysisResponse(
            metric_name=metric_name,
            data_points=data_points,
            overall_trend=trend,
            change_percent=round(change, 2),
            best_value=max(values) if values else 0,
            worst_value=min(values) if values else 0,
            average_value=sum(values) / len(values) if values else 0,
        )

    async def compare_periods(
        self, db: AsyncSession, user_id: str, request: ComparisonRequest
    ) -> ComparisonResponse:
        """
        对比两个时期

        Args:
            db: 数据库会话
            user_id: 用户ID
            request: 对比请求

        Returns:
            对比响应
        """
        # 获取两个周期的数据
        sessions1 = await self._get_sessions_in_range(
            db, user_id, request.period1_start, request.period1_end
        )
        sessions2 = await self._get_sessions_in_range(
            db, user_id, request.period2_start, request.period2_end
        )

        summary1 = self._calculate_period_summary(sessions1)
        summary2 = self._calculate_period_summary(sessions2)

        # 计算变化
        comparison = {}
        if summary1.avg_speed_kmh and summary2.avg_speed_kmh:
            comparison["speed_change"] = round(
                (summary2.avg_speed_kmh - summary1.avg_speed_kmh) / summary1.avg_speed_kmh * 100, 2
            )
        if summary1.avg_accuracy and summary2.avg_accuracy:
            comparison["accuracy_change"] = round(
                (summary2.avg_accuracy - summary1.avg_accuracy) / summary1.avg_accuracy * 100, 2
            )
        if summary1.avg_consistency and summary2.avg_consistency:
            comparison["consistency_change"] = round(
                (summary2.avg_consistency - summary1.avg_consistency) / summary1.avg_consistency * 100, 2
            )
        if summary1.session_count and summary2.session_count:
            comparison["session_change"] = round(
                (summary2.session_count - summary1.session_count) / summary1.session_count * 100, 2
            )

        # 生成洞察
        insights = self._generate_comparison_insights(summary1, summary2, comparison)

        return ComparisonResponse(
            period1_summary=summary1,
            period2_summary=summary2,
            comparison=comparison,
            insights=insights,
        )

    def _calculate_period_summary(
        self, sessions: List[TrainingSession]
    ) -> PeriodSummary:
        """计算周期汇总"""
        session_count = len(sessions)
        total_duration = sum(s.duration_minutes or 0 for s in sessions)
        total_strokes = sum(s.total_strokes or 0 for s in sessions)

        speeds = [s.avg_ball_speed_kmh for s in sessions if s.avg_ball_speed_kmh]
        accuracies = [s.accuracy_score for s in sessions if s.accuracy_score]
        consistencies = [s.consistency_score for s in sessions if s.consistency_score]

        return PeriodSummary(
            session_count=session_count,
            total_duration_minutes=total_duration,
            total_strokes=total_strokes,
            avg_speed_kmh=round(sum(speeds) / len(speeds), 2) if speeds else None,
            avg_accuracy=round(sum(accuracies) / len(accuracies), 2) if accuracies else None,
            avg_consistency=round(sum(consistencies) / len(consistencies), 2) if consistencies else None,
        )

    def _generate_comparison_insights(
        self,
        summary1: PeriodSummary,
        summary2: PeriodSummary,
        comparison: Dict[str, float]
    ) -> List[str]:
        """生成对比洞察"""
        insights = []

        if "speed_change" in comparison:
            change = comparison["speed_change"]
            if change > 10:
                insights.append(f"球速显著提升 {change:.1f}%")
            elif change < -10:
                insights.append(f"球速明显下降 {abs(change):.1f}%，建议加强力量训练")

        if "accuracy_change" in comparison:
            change = comparison["accuracy_change"]
            if change > 10:
                insights.append(f"准确率大幅提升 {change:.1f}%")
            elif change < -10:
                insights.append(f"准确率下降 {abs(change):.1f}%，建议进行针对性练习")

        if "session_change" in comparison:
            change = comparison["session_change"]
            if change > 50:
                insights.append("训练频率大幅提升，继续保持！")
            elif change < -50:
                insights.append("训练频率降低，建议保持稳定的训练节奏")

        if not insights:
            insights.append("两个时期表现相近，保持稳定训练")

        return insights

    async def get_user_stats(
        self, db: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """
        获取用户综合统计

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            统计数据字典
        """
        # 基础统计
        session_result = await db.execute(
            select(
                func.count(TrainingSession.id).label("count"),
                func.sum(TrainingSession.duration_minutes).label("duration"),
                func.sum(TrainingSession.total_strokes).label("strokes"),
            ).where(TrainingSession.user_id == user_id)
        )
        session_stats = session_result.one()

        total_sessions = session_stats.count or 0
        total_duration = session_stats.duration or 0
        total_strokes = session_stats.strokes or 0

        avg_duration = total_duration / total_sessions if total_sessions else 0
        avg_strokes = total_strokes / total_sessions if total_sessions else 0

        # 最常练习的技术
        technique_result = await db.execute(
            select(
                TechniqueMetrics.technique_category,
                func.sum(TechniqueMetrics.stroke_count).label("count")
            )
            .join(TrainingSession)
            .where(TrainingSession.user_id == user_id)
            .group_by(TechniqueMetrics.technique_category)
            .order_by(func.sum(TechniqueMetrics.stroke_count).desc())
            .limit(3)
        )
        favorite_techniques = [row.technique_category for row in technique_result.all()]

        # 连续训练天数
        streak = await self._calculate_streak(db, user_id)

        # 目标统计
        from app.training_analysis.core.goal_service import get_goal_service
        goal_service = get_goal_service()
        goals_active = await goal_service.get_active_goals_count(db, user_id)
        goals_achieved = await goal_service.get_achieved_goals_count(db, user_id)

        return {
            "user_id": user_id,
            "total_sessions": total_sessions,
            "total_duration_minutes": total_duration,
            "total_strokes": total_strokes,
            "avg_session_duration": round(avg_duration, 1),
            "avg_strokes_per_session": round(avg_strokes, 1),
            "favorite_techniques": favorite_techniques,
            "current_streak_days": streak["current"],
            "longest_streak_days": streak["longest"],
            "goals_achieved": goals_achieved,
            "goals_active": goals_active,
        }

    async def _calculate_streak(
        self, db: AsyncSession, user_id: str
    ) -> Dict[str, int]:
        """计算连续训练天数"""
        # 获取所有会话日期
        result = await db.execute(
            select(func.date(TrainingSession.started_at).label("date"))
            .where(TrainingSession.user_id == user_id)
            .distinct()
            .order_by(func.date(TrainingSession.started_at).desc())
        )
        dates = [row.date for row in result.all()]

        if not dates:
            return {"current": 0, "longest": 0}

        # 计算当前连续天数
        current_streak = 0
        today = datetime.utcnow().date()

        for i, date in enumerate(dates):
            expected_date = today - timedelta(days=i)
            if date == expected_date:
                current_streak += 1
            else:
                break

        # 计算最长连续天数
        longest_streak = 0
        streak = 1

        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1

        longest_streak = max(longest_streak, streak, current_streak)

        return {"current": current_streak, "longest": longest_streak}

    async def calculate_technique_trend(
        self,
        db: AsyncSession,
        user_id: str,
        technique_category: str,
        days: int = 30
    ) -> str:
        """
        计算技术趋势

        Args:
            db: 数据库会话
            user_id: 用户ID
            technique_category: 技术类别
            days: 分析天数

        Returns:
            趋势: improving, stable, declining
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        result = await db.execute(
            select(TechniqueMetrics.avg_speed_kmh, TrainingSession.started_at)
            .join(TrainingSession)
            .where(
                and_(
                    TrainingSession.user_id == user_id,
                    TechniqueMetrics.technique_category == technique_category,
                    TrainingSession.started_at >= start_date
                )
            )
            .order_by(TrainingSession.started_at)
        )

        rows = result.all()
        if len(rows) < 2:
            return "stable"

        # 前后半部分平均值对比
        mid = len(rows) // 2
        first_half = [r.avg_speed_kmh for r in rows[:mid] if r.avg_speed_kmh]
        second_half = [r.avg_speed_kmh for r in rows[mid:] if r.avg_speed_kmh]

        if not first_half or not second_half:
            return "stable"

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        change = (avg_second - avg_first) / avg_first * 100 if avg_first else 0

        if change > 5:
            return "improving"
        elif change < -5:
            return "declining"
        return "stable"

    async def get_snapshots(
        self,
        db: AsyncSession,
        user_id: str,
        period_type: Optional[str] = None,
        limit: int = 30
    ) -> List[ProgressSnapshot]:
        """
        获取快照列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            period_type: 周期类型筛选
            limit: 返回数量

        Returns:
            快照列表
        """
        conditions = [ProgressSnapshot.user_id == user_id]
        if period_type:
            conditions.append(ProgressSnapshot.period_type == period_type)

        result = await db.execute(
            select(ProgressSnapshot)
            .where(and_(*conditions))
            .order_by(ProgressSnapshot.snapshot_date.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# 服务单例
_analysis_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """获取分析服务单例"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
