"""
训练会话服务

提供训练会话的 CRUD 操作和视频管理。
"""

import uuid
from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.training_analysis.models import (
    TrainingSession, SessionVideo, SessionType
)
from app.training_analysis.schemas import (
    SessionCreate, SessionUpdate, SessionVideoCreate
)


class SessionService:
    """训练会话服务"""

    async def create_session(
        self, db: AsyncSession, data: SessionCreate
    ) -> TrainingSession:
        """
        创建训练会话

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的会话对象
        """
        # 计算持续时间
        duration = None
        if data.ended_at and data.started_at:
            duration = int((data.ended_at - data.started_at).total_seconds() / 60)

        session = TrainingSession(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            title=data.title,
            session_type=SessionType(data.session_type),
            description=data.description,
            started_at=data.started_at,
            ended_at=data.ended_at,
            duration_minutes=duration,
            location=data.location,
            equipment_notes=data.equipment_notes,
            practiced_techniques=data.practiced_techniques,
            notes=data.notes,
            satisfaction_rating=data.satisfaction_rating,
            fatigue_level=data.fatigue_level,
            tags=data.tags,
            total_strokes=0,
        )

        db.add(session)
        await db.flush()
        logger.info(f"训练会话已创建: {session.id}, 用户: {data.user_id}")
        return session

    async def get_session(
        self, db: AsyncSession, session_id: str
    ) -> Optional[TrainingSession]:
        """
        获取会话详情

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            会话对象或 None
        """
        result = await db.execute(
            select(TrainingSession)
            .options(selectinload(TrainingSession.videos))
            .options(selectinload(TrainingSession.metrics))
            .where(TrainingSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        session_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TrainingSession], int]:
        """
        列出用户会话

        Args:
            db: 数据库会话
            user_id: 用户ID
            session_type: 会话类型筛选
            start_date: 开始日期筛选
            end_date: 结束日期筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (会话列表, 总数)
        """
        # 构建查询条件
        conditions = [TrainingSession.user_id == user_id]

        if session_type:
            conditions.append(TrainingSession.session_type == SessionType(session_type))
        if start_date:
            conditions.append(TrainingSession.started_at >= start_date)
        if end_date:
            conditions.append(TrainingSession.started_at <= end_date)

        # 查询总数
        count_query = select(func.count(TrainingSession.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询分页数据
        query = (
            select(TrainingSession)
            .options(selectinload(TrainingSession.videos))
            .where(and_(*conditions))
            .order_by(TrainingSession.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(query)
        sessions = list(result.scalars().all())

        return sessions, total

    async def update_session(
        self, db: AsyncSession, session_id: str, data: SessionUpdate
    ) -> Optional[TrainingSession]:
        """
        更新会话

        Args:
            db: 数据库会话
            session_id: 会话ID
            data: 更新数据

        Returns:
            更新后的会话或 None
        """
        session = await self.get_session(db, session_id)
        if not session:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(session, field, value)

        # 重新计算持续时间
        if session.ended_at and session.started_at:
            session.duration_minutes = int(
                (session.ended_at - session.started_at).total_seconds() / 60
            )

        session.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"训练会话已更新: {session_id}")
        return session

    async def delete_session(self, db: AsyncSession, session_id: str) -> bool:
        """
        删除会话

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        session = await self.get_session(db, session_id)
        if not session:
            return False

        await db.delete(session)
        await db.flush()
        logger.info(f"训练会话已删除: {session_id}")
        return True

    async def add_video(
        self, db: AsyncSession, session_id: str, data: SessionVideoCreate
    ) -> Optional[SessionVideo]:
        """
        添加视频到会话

        Args:
            db: 数据库会话
            session_id: 会话ID
            data: 视频创建数据

        Returns:
            创建的视频关联或 None
        """
        session = await self.get_session(db, session_id)
        if not session:
            return None

        video = SessionVideo(
            id=str(uuid.uuid4()),
            session_id=session_id,
            ball_tracking_job_id=data.ball_tracking_job_id,
            segment_title=data.segment_title,
            start_time_seconds=data.start_time_seconds,
            end_time_seconds=data.end_time_seconds,
            analysis_status="pending",
        )

        db.add(video)
        await db.flush()
        logger.info(f"视频已添加到会话: {session_id}, 视频ID: {video.id}")
        return video

    async def remove_video(
        self, db: AsyncSession, session_id: str, video_id: str
    ) -> bool:
        """
        移除视频

        Args:
            db: 数据库会话
            session_id: 会话ID
            video_id: 视频ID

        Returns:
            是否移除成功
        """
        result = await db.execute(
            select(SessionVideo).where(
                and_(
                    SessionVideo.id == video_id,
                    SessionVideo.session_id == session_id
                )
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            return False

        await db.delete(video)
        await db.flush()
        logger.info(f"视频已从会话移除: {session_id}, 视频ID: {video_id}")
        return True

    async def get_session_videos(
        self, db: AsyncSession, session_id: str
    ) -> List[SessionVideo]:
        """
        获取会话的所有视频

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            视频列表
        """
        result = await db.execute(
            select(SessionVideo)
            .where(SessionVideo.session_id == session_id)
            .order_by(SessionVideo.created_at)
        )
        return list(result.scalars().all())

    async def recalculate_session_metrics(
        self, db: AsyncSession, session_id: str
    ) -> Optional[TrainingSession]:
        """
        重新计算会话聚合指标

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            更新后的会话或 None
        """
        session = await self.get_session(db, session_id)
        if not session:
            return None

        # 聚合视频指标
        total_strokes = 0
        speeds = []
        max_speed = None

        for video in session.videos:
            if video.stroke_count:
                total_strokes += video.stroke_count
            if video.avg_speed_kmh:
                speeds.append(video.avg_speed_kmh)
            if video.max_speed_kmh:
                if max_speed is None or video.max_speed_kmh > max_speed:
                    max_speed = video.max_speed_kmh

        session.total_strokes = total_strokes
        session.max_ball_speed_kmh = max_speed
        session.avg_ball_speed_kmh = sum(speeds) / len(speeds) if speeds else None

        # 聚合技术指标的准确率和稳定性
        accuracies = []
        consistencies = []
        for metric in session.metrics:
            if metric.accuracy_score is not None:
                accuracies.append(metric.accuracy_score)
            if metric.consistency_score is not None:
                consistencies.append(metric.consistency_score)

        session.accuracy_score = sum(accuracies) / len(accuracies) if accuracies else None
        session.consistency_score = sum(consistencies) / len(consistencies) if consistencies else None

        session.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"会话指标已重新计算: {session_id}")
        return session

    async def get_recent_sessions(
        self, db: AsyncSession, user_id: str, limit: int = 10
    ) -> List[TrainingSession]:
        """
        获取用户最近的会话

        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量

        Returns:
            会话列表
        """
        result = await db.execute(
            select(TrainingSession)
            .where(TrainingSession.user_id == user_id)
            .order_by(TrainingSession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# 服务单例
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """获取会话服务单例"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
