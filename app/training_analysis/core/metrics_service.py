"""
指标提取和聚合服务

提供从 ball_tracking 任务提取指标和聚合计算功能。
"""

import uuid
import math
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.training_analysis.models import (
    TrainingSession, SessionVideo, TechniqueMetrics
)
from config.settings import get_settings


class MetricsService:
    """指标提取和聚合服务"""

    def __init__(self):
        self.settings = get_settings()
        self.speed_factor = self.settings.training_metrics_speed_conversion_factor

    async def extract_metrics_from_job(
        self, db: AsyncSession, job_id: str
    ) -> Dict[str, Any]:
        """
        从 ball_tracking 任务提取指标

        Args:
            db: 数据库会话
            job_id: ball_tracking 任务 ID

        Returns:
            提取的指标字典
        """
        # 导入 ball_tracking 模型
        from app.ball_tracking.models import ProcessingJob, BallTrack2D

        # 查询任务
        job_result = await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            logger.warning(f"ball_tracking 任务不存在: {job_id}")
            return {}

        # 查询轨迹数据
        tracks_result = await db.execute(
            select(BallTrack2D).where(BallTrack2D.job_id == job_id)
        )
        tracks = list(tracks_result.scalars().all())

        metrics = {
            "job_id": job_id,
            "status": job.status,
            "detection_count": job.detection_count or 0,
            "track_count": job.track_count or 0,
            "video_frames": job.video_frames,
            "video_duration": job.video_duration,
            "fps": job.fps,
        }

        # 聚合轨迹数据
        all_speeds = []
        all_bounces = 0
        stroke_types = {}

        for track in tracks:
            if track.analysis_json:
                analysis = track.analysis_json

                # 提取速度统计
                if "speed_stats" in analysis:
                    speed_stats = analysis["speed_stats"]
                    if "avg_speed_m_s" in speed_stats:
                        all_speeds.append(speed_stats["avg_speed_m_s"] * self.speed_factor)

                # 提取弹跳点数量
                if "bounce_points" in analysis:
                    all_bounces += len(analysis["bounce_points"])

                # 提取击球类型
                if "stroke_type" in analysis:
                    stroke = analysis["stroke_type"]
                    stroke_types[stroke] = stroke_types.get(stroke, 0) + 1

        if all_speeds:
            metrics["avg_speed_kmh"] = sum(all_speeds) / len(all_speeds)
            metrics["max_speed_kmh"] = max(all_speeds)
            metrics["min_speed_kmh"] = min(all_speeds)

        metrics["bounce_count"] = all_bounces
        metrics["stroke_count"] = len(tracks)
        metrics["stroke_distribution"] = stroke_types

        logger.info(f"已从任务 {job_id} 提取指标: 轨迹数={len(tracks)}")
        return metrics

    async def update_video_metrics(
        self, db: AsyncSession, video: SessionVideo
    ) -> SessionVideo:
        """
        更新视频的指标数据

        Args:
            db: 数据库会话
            video: 视频对象

        Returns:
            更新后的视频对象
        """
        metrics = await self.extract_metrics_from_job(db, video.ball_tracking_job_id)

        if not metrics:
            video.analysis_status = "failed"
            await db.flush()
            return video

        video.stroke_count = metrics.get("stroke_count")
        video.avg_speed_kmh = metrics.get("avg_speed_kmh")
        video.max_speed_kmh = metrics.get("max_speed_kmh")
        video.bounce_count = metrics.get("bounce_count")
        video.stroke_distribution = metrics.get("stroke_distribution")
        video.analysis_status = "completed"
        video.analysis_summary = metrics

        await db.flush()
        logger.info(f"视频指标已更新: {video.id}")
        return video

    async def aggregate_session_metrics(
        self, db: AsyncSession, session_id: str
    ) -> Dict[str, Any]:
        """
        聚合会话所有视频的指标

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            聚合后的指标字典
        """
        # 获取会话及其视频
        result = await db.execute(
            select(SessionVideo).where(SessionVideo.session_id == session_id)
        )
        videos = list(result.scalars().all())

        if not videos:
            return {}

        # 聚合指标
        total_strokes = 0
        speeds = []
        max_speed = None
        total_bounces = 0
        combined_distribution = {}

        for video in videos:
            if video.stroke_count:
                total_strokes += video.stroke_count
            if video.avg_speed_kmh:
                speeds.append(video.avg_speed_kmh)
            if video.max_speed_kmh:
                if max_speed is None or video.max_speed_kmh > max_speed:
                    max_speed = video.max_speed_kmh
            if video.bounce_count:
                total_bounces += video.bounce_count
            if video.stroke_distribution:
                for stroke_type, count in video.stroke_distribution.items():
                    combined_distribution[stroke_type] = (
                        combined_distribution.get(stroke_type, 0) + count
                    )

        return {
            "total_strokes": total_strokes,
            "avg_speed_kmh": sum(speeds) / len(speeds) if speeds else None,
            "max_speed_kmh": max_speed,
            "total_bounces": total_bounces,
            "stroke_distribution": combined_distribution,
            "video_count": len(videos),
        }

    async def calculate_technique_metrics(
        self, db: AsyncSession, session_id: str
    ) -> List[TechniqueMetrics]:
        """
        计算每种技术的指标

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            技术指标列表
        """
        # 获取会话视频
        result = await db.execute(
            select(SessionVideo).where(
                and_(
                    SessionVideo.session_id == session_id,
                    SessionVideo.analysis_status == "completed"
                )
            )
        )
        videos = list(result.scalars().all())

        # 按技术类型分组
        technique_data: Dict[str, Dict[str, Any]] = {}

        for video in videos:
            if not video.stroke_distribution:
                continue

            for stroke_type, count in video.stroke_distribution.items():
                # 映射击球类型到技术类别
                category = self._map_stroke_to_category(stroke_type)

                if category not in technique_data:
                    technique_data[category] = {
                        "stroke_count": 0,
                        "speeds": [],
                        "technique_name": stroke_type,
                    }

                technique_data[category]["stroke_count"] += count
                if video.avg_speed_kmh:
                    technique_data[category]["speeds"].append(video.avg_speed_kmh)

        # 创建或更新 TechniqueMetrics
        metrics_list = []
        for category, data in technique_data.items():
            # 检查是否已存在
            existing_result = await db.execute(
                select(TechniqueMetrics).where(
                    and_(
                        TechniqueMetrics.session_id == session_id,
                        TechniqueMetrics.technique_category == category
                    )
                )
            )
            metric = existing_result.scalar_one_or_none()

            if not metric:
                metric = TechniqueMetrics(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    technique_category=category,
                )
                db.add(metric)

            metric.stroke_count = data["stroke_count"]
            metric.technique_name = data["technique_name"]

            if data["speeds"]:
                speeds = data["speeds"]
                metric.avg_speed_kmh = sum(speeds) / len(speeds)
                metric.max_speed_kmh = max(speeds)
                metric.min_speed_kmh = min(speeds)

                # 计算标准差
                if len(speeds) > 1:
                    mean = metric.avg_speed_kmh
                    variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
                    metric.speed_std_dev = math.sqrt(variance)

            # 计算准确率和稳定性评分
            metric.accuracy_score = self.calculate_accuracy_score(data)
            metric.consistency_score = self.calculate_consistency_score(data)

            metrics_list.append(metric)

        await db.flush()
        logger.info(f"会话 {session_id} 的技术指标已计算: {len(metrics_list)} 个类别")
        return metrics_list

    def _map_stroke_to_category(self, stroke_type: str) -> str:
        """
        将击球类型映射到技术类别

        Args:
            stroke_type: 击球类型

        Returns:
            技术类别
        """
        mapping = {
            "loop": "forehand",
            "drive": "forehand",
            "forehand_loop": "forehand",
            "forehand_drive": "forehand",
            "forehand_attack": "forehand",
            "backhand_loop": "backhand",
            "backhand_drive": "backhand",
            "backhand_attack": "backhand",
            "push": "receive",
            "chop": "receive",
            "block": "receive",
            "serve": "serve",
            "pendulum_serve": "serve",
            "reverse_serve": "serve",
            "smash": "forehand",
            "lob": "backhand",
        }
        return mapping.get(stroke_type.lower(), "other")

    def calculate_accuracy_score(self, data: Dict[str, Any]) -> float:
        """
        计算准确率分数

        基于击球数量和速度稳定性估算

        Args:
            data: 技术数据

        Returns:
            准确率分数 (0-100)
        """
        # 基础分数
        base_score = 50.0

        # 根据击球数量调整（假设更多击球意味着更多成功）
        stroke_count = data.get("stroke_count", 0)
        if stroke_count > 0:
            # 对数增长，避免过高
            base_score += min(20, math.log10(stroke_count + 1) * 15)

        # 根据速度稳定性调整
        speeds = data.get("speeds", [])
        if len(speeds) > 1:
            mean = sum(speeds) / len(speeds)
            variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
            std_dev = math.sqrt(variance)
            # 标准差越小，稳定性越好，分数越高
            stability_bonus = max(0, 30 - std_dev * 3)
            base_score += stability_bonus

        return min(100, max(0, base_score))

    def calculate_consistency_score(self, data: Dict[str, Any]) -> float:
        """
        计算稳定性分数

        基于速度方差计算

        Args:
            data: 技术数据

        Returns:
            稳定性分数 (0-100)
        """
        speeds = data.get("speeds", [])

        if len(speeds) < 2:
            return 50.0  # 数据不足，返回中等分数

        mean = sum(speeds) / len(speeds)
        variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
        std_dev = math.sqrt(variance)

        # 变异系数（CV），标准差/均值
        cv = std_dev / mean if mean > 0 else 0

        # CV 越小越稳定，分数越高
        # CV < 0.1: 非常稳定 (90+)
        # CV < 0.2: 稳定 (70-90)
        # CV < 0.3: 一般 (50-70)
        # CV >= 0.3: 不稳定 (<50)
        if cv < 0.1:
            score = 90 + (0.1 - cv) * 100
        elif cv < 0.2:
            score = 70 + (0.2 - cv) * 200
        elif cv < 0.3:
            score = 50 + (0.3 - cv) * 200
        else:
            score = max(10, 50 - (cv - 0.3) * 100)

        return min(100, max(0, score))

    async def get_user_technique_history(
        self,
        db: AsyncSession,
        user_id: str,
        technique_category: str,
        limit: int = 50
    ) -> List[TechniqueMetrics]:
        """
        获取用户某技术的历史数据

        Args:
            db: 数据库会话
            user_id: 用户ID
            technique_category: 技术类别
            limit: 返回数量

        Returns:
            技术指标历史列表
        """
        result = await db.execute(
            select(TechniqueMetrics)
            .join(TrainingSession)
            .where(
                and_(
                    TrainingSession.user_id == user_id,
                    TechniqueMetrics.technique_category == technique_category
                )
            )
            .order_by(TechniqueMetrics.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# 服务单例
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """获取指标服务单例"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
